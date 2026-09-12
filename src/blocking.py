"""Blocking: cutting 56 million possible pairs down to a workable shortlist.

Matching every Walmart record against every Amazon record would mean
2,554 x 22,074 = 56,378,196 comparisons. Almost all of those are obviously
unrelated. *Blocking* is the cheap first pass that decides which pairs are
worth comparing properly, so the expensive scoring only runs where it might
matter.

The danger is one-sided. A pair blocking throws away can never be recovered
later, however good the scoring is — so blocking sets a hard ceiling on how
many real matches the system can ever find. A pair blocking wrongly keeps
merely costs a little compute, because the scoring step will reject it. That
asymmetry is why the rules below are generous rather than tight.

**Five rules, applied together.** A pair becomes a candidate if *any* rule
accepts it. Splink's own guidance is that a long list of strict rules beats a
short list of loose ones, and each rule here looks for a different kind of
evidence:

- **R1 — a shared rare word.** Two records using the same uncommon word is
  unlikely to be coincidence. Common words like "black" or "with" are ignored.
- **R2 — a shared part-number-shaped word.** A token mixing letters and digits
  (``ph3100u``, ``elplp12``) is almost always a manufacturer part number, which
  is close to decisive evidence.
- **R3 — the same brand, plus one other shared word.** Brand alone is far too
  broad (the "hp" block holds 318 Amazon records), but combined with any second
  shared word it narrows sharply.
- **R5 — a shared rare character sequence.** Catches part numbers the two
  retailers punctuate differently, which word-level rules miss entirely. See
  ``text_normalisation`` and docs/DECISIONS.md (D15).
- **R4 — a last-resort safety net.** Any Walmart record that *still* has no
  candidate is matched to its nearest Amazon records by text similarity, so no
  record is left with nothing.

Rules are numbered for their order of design, not their order of application —
R4 was designed before R5 and deliberately runs last, since it only exists to
catch what the others miss.

Thresholds are recorded in docs/DECISIONS.md (D16) along with the measurements
behind them.

Run ``python -m src.blocking`` to generate candidates and print a report.
"""

import collections
from dataclasses import dataclass, field

import pandas as pd

from src.data_loading import ID_COLUMN, attribute_columns, load_source_tables
from src.text_normalisation import char_ngrams, word_tokens

# --- Settings, with the reasoning in docs/DECISIONS.md (D16) -----------------

# R1: ignore a word once it appears in more than this many records. Measured
# across both tables pooled.
R1_MAX_DOC_FREQUENCY = 100

# R2: what counts as "part-number shaped" — at least this long, and containing
# both a letter and a digit.
R2_MIN_IDENTIFIER_LENGTH = 5

# R5: ignore a character sequence once it appears in more than this many
# *Amazon* records. Counted on the Amazon side only, because that is what
# determines how many candidates the sequence actually pulls in.
R5_MAX_DOC_FREQUENCY = 50

# R4: how many nearest neighbours to offer a record that nothing else reached.
# Chosen to be close to the median number of candidates a normal record gets,
# so a rescued record is neither starved nor flooded.
R4_NEIGHBOURS = 100


def is_identifier_like(token: str) -> bool:
    """Does this word look like a manufacturer part number?

    The test is deliberately crude — long enough, and mixing letters with
    digits. Words like "ph3100u" or "elplp12" pass; "black" and "1080" do not.
    """
    return (
        len(token) >= R2_MIN_IDENTIFIER_LENGTH
        and any(c.isalpha() for c in token)
        and any(c.isdigit() for c in token)
    )


def record_text(row: pd.Series, columns: list[str]) -> str:
    """Join a record's attribute values into one lowercase string.

    All attributes are pooled deliberately. The benchmark's corruption moved
    values into the wrong columns, so a brand or part number is often sitting
    in ``title`` rather than its own field. Treating the record as one bag of
    text sidesteps that entirely.
    """
    return " ".join(str(v) for v in row[columns] if pd.notna(v)).lower()


@dataclass
class BlockingIndex:
    """Pre-computed lookups so the rules don't rescan the tables repeatedly."""

    a_tokens: dict[str, set[str]]
    b_tokens: dict[str, set[str]]
    a_ngrams: dict[str, set[str]]
    b_ngrams: dict[str, set[str]]
    a_brands: dict[str, set[str]]
    b_brands: dict[str, set[str]]
    token_doc_frequency: collections.Counter          # pooled across both tables
    b_token_index: dict[str, set[str]] = field(default_factory=dict)
    b_ngram_index: dict[str, set[str]] = field(default_factory=dict)
    b_brand_index: dict[str, set[str]] = field(default_factory=dict)


def build_index(table_a: pd.DataFrame, table_b: pd.DataFrame) -> BlockingIndex:
    """Prepare every lookup the rules need, in one pass over each table.

    The "inverted indexes" below map a piece of evidence to the Amazon records
    containing it — the same idea a book index uses, letting us jump straight
    to the relevant records instead of scanning all 22,074 every time.
    """
    columns = attribute_columns(table_a)

    a_text = {r[ID_COLUMN]: record_text(r, columns) for _, r in table_a.iterrows()}
    b_text = {r[ID_COLUMN]: record_text(r, columns) for _, r in table_b.iterrows()}

    a_tokens = {k: set(word_tokens(v)) for k, v in a_text.items()}
    b_tokens = {k: set(word_tokens(v)) for k, v in b_text.items()}
    a_ngrams = {k: char_ngrams(v) for k, v in a_text.items()}
    b_ngrams = {k: char_ngrams(v) for k, v in b_text.items()}

    # How many records contain each word, counting each record once however
    # many times the word occurs in it, pooled over both tables.
    doc_frequency = collections.Counter()
    for tokens in list(a_tokens.values()) + list(b_tokens.values()):
        doc_frequency.update(tokens)

    a_brands = _harvest_brands(table_a, a_tokens, table_a, table_b)
    b_brands = _harvest_brands(table_b, b_tokens, table_a, table_b)

    index = BlockingIndex(
        a_tokens=a_tokens, b_tokens=b_tokens,
        a_ngrams=a_ngrams, b_ngrams=b_ngrams,
        a_brands=a_brands, b_brands=b_brands,
        token_doc_frequency=doc_frequency,
    )
    index.b_token_index = _invert(b_tokens)
    index.b_ngram_index = _invert(b_ngrams)
    index.b_brand_index = _invert(b_brands)
    return index


def _invert(record_to_items: dict[str, set[str]]) -> dict[str, set[str]]:
    """Turn {record: items} into {item: records}."""
    inverted: dict[str, set[str]] = collections.defaultdict(set)
    for record_id, items in record_to_items.items():
        for item in items:
            inverted[item].add(record_id)
    return inverted


def _known_brand_vocabulary(table_a: pd.DataFrame, table_b: pd.DataFrame) -> set[str]:
    """Every single-word brand name either retailer uses.

    Multi-word brands ("cooler master") are skipped: matching them reliably
    inside a free-text title needs phrase handling that would add complexity
    for a small gain. Single-word brands cover the large majority.
    """
    values = pd.concat([table_a["brand"], table_b["brand"]]).dropna().str.lower()
    return {v for v in values if len(word_tokens(v)) == 1}


def _harvest_brands(
    table: pd.DataFrame,
    tokens: dict[str, set[str]],
    table_a: pd.DataFrame,
    table_b: pd.DataFrame,
) -> dict[str, set[str]]:
    """Find each record's brand, from the column *or* from inside its text.

    This is the cross-field idea from D8 applied to blocking. The corruption
    blanked the ``brand`` column on roughly half the records — but it usually
    moved that value into the title rather than deleting it. Looking for known
    brand names anywhere in the record recovers the brand for about 88% of
    Walmart and 91% of Amazon records whose column is empty.
    """
    vocabulary = _known_brand_vocabulary(table_a, table_b)
    out: dict[str, set[str]] = {}
    for _, row in table.iterrows():
        record_id = row[ID_COLUMN]
        found = set()
        if pd.notna(row["brand"]):
            value = str(row["brand"]).lower()
            if len(word_tokens(value)) == 1:
                found.add(value)
        # Any known brand name appearing among the record's words counts too.
        found |= tokens[record_id] & vocabulary
        out[record_id] = found
    return out


# --- The rules ---------------------------------------------------------------

def _rule_r1(index: BlockingIndex, a_id: str) -> set[str]:
    """Shared word that is rare across the two tables pooled."""
    hits: set[str] = set()
    for token in index.a_tokens[a_id]:
        if index.token_doc_frequency[token] <= R1_MAX_DOC_FREQUENCY:
            hits |= index.b_token_index.get(token, set())
    return hits


def _rule_r2(index: BlockingIndex, a_id: str) -> set[str]:
    """Shared word shaped like a manufacturer part number, at any frequency."""
    hits: set[str] = set()
    for token in index.a_tokens[a_id]:
        if is_identifier_like(token):
            hits |= index.b_token_index.get(token, set())
    return hits


def _rule_r3(index: BlockingIndex, a_id: str) -> set[str]:
    """Same brand AND at least one other shared word.

    Brand alone is too coarse to be useful on its own, so it acts as a cheap
    partition that a second piece of agreement then narrows.
    """
    same_brand: set[str] = set()
    for brand in index.a_brands[a_id]:
        same_brand |= index.b_brand_index.get(brand, set())

    a_tokens = index.a_tokens[a_id]
    hits = set()
    for b_id in same_brand:
        # "Another" shared word means one that is not itself the brand name.
        shared = (a_tokens & index.b_tokens[b_id]) - index.a_brands[a_id]
        if shared:
            hits.add(b_id)
    return hits


def _rule_r5(index: BlockingIndex, a_id: str) -> set[str]:
    """Shared character sequence that is rare on the Amazon side."""
    hits: set[str] = set()
    for gram in index.a_ngrams[a_id]:
        postings = index.b_ngram_index.get(gram)
        if postings is not None and len(postings) <= R5_MAX_DOC_FREQUENCY:
            hits |= postings
    return hits


def _rule_r4(index: BlockingIndex, a_id: str) -> set[str]:
    """Safety net: the most textually similar Amazon records, however weak.

    Only used for a record that every other rule missed. Without it such a
    record has no candidates at all and therefore cannot possibly be matched —
    a silent, unrecoverable loss. Similarity is the proportion of character
    sequences the two records share.

    Only records sharing at least one sequence are considered, which keeps this
    fast without changing the result: a record sharing nothing would score zero
    anyway.
    """
    a_grams = index.a_ngrams[a_id]
    if not a_grams:
        return set()

    overlap: collections.Counter = collections.Counter()
    for gram in a_grams:
        for b_id in index.b_ngram_index.get(gram, ()):
            overlap[b_id] += 1

    scored = [
        (shared / len(a_grams | index.b_ngrams[b_id]), b_id)
        for b_id, shared in overlap.items()
    ]
    scored.sort(reverse=True)
    return {b_id for _, b_id in scored[:R4_NEIGHBOURS]}


# Applied in this order. R4 runs last and only where the others found nothing.
PRIMARY_RULES = {"R1": _rule_r1, "R2": _rule_r2, "R3": _rule_r3, "R5": _rule_r5}


def generate_candidates(index: BlockingIndex) -> dict[str, set[str]]:
    """Produce the candidate Amazon records for every Walmart record.

    Returns ``{walmart_id: {amazon_id, ...}}``. Which rule produced a pair is
    available via :func:`candidates_by_rule` when that matters for diagnostics.
    """
    by_rule = candidates_by_rule(index)
    combined: dict[str, set[str]] = {}
    for a_id in index.a_tokens:
        hits: set[str] = set()
        for rule in by_rule.values():
            hits |= rule.get(a_id, set())
        combined[a_id] = hits
    return combined


def candidates_by_rule(index: BlockingIndex) -> dict[str, dict[str, set[str]]]:
    """Same as :func:`generate_candidates`, but keeping each rule separate."""
    result: dict[str, dict[str, set[str]]] = {
        name: {a_id: fn(index, a_id) for a_id in index.a_tokens}
        for name, fn in PRIMARY_RULES.items()
    }

    # R4 only fires where nothing else did.
    rescued: dict[str, set[str]] = {}
    for a_id in index.a_tokens:
        if not any(result[name][a_id] for name in PRIMARY_RULES):
            rescued[a_id] = _rule_r4(index, a_id)
    result["R4"] = rescued
    return result


# --- Reporting ---------------------------------------------------------------

def report(index: BlockingIndex) -> dict[str, set[str]]:
    """Generate candidates and print a label-free summary of the result.

    Every figure here is a count. None of it consults the labelled data, in
    line with the no-peek policy — so this says how *reachable* records are,
    never how *correct* the pairs are.
    """
    by_rule = candidates_by_rule(index)
    combined = {
        a_id: set().union(*(r.get(a_id, set()) for r in by_rule.values()))
        for a_id in index.a_tokens
    }

    n_a, n_b = len(index.a_tokens), len(index.b_tokens)
    full = n_a * n_b

    print("=" * 78)
    print("BLOCKING RESULT")
    print("=" * 78)
    print(f"  Walmart records {n_a:,}  x  Amazon records {n_b:,}  =  {full:,} possible pairs")
    print(f"  settings: R1 DF<={R1_MAX_DOC_FREQUENCY}  R5 DF<={R5_MAX_DOC_FREQUENCY}  "
          f"R4 neighbours={R4_NEIGHBOURS}")

    print(f"\n  {'rule':<8} {'pairs':>10} {'unique to rule':>15} {'A records reached':>19}")
    for name in ("R1", "R2", "R3", "R5", "R4"):
        rule = by_rule[name]
        pairs = sum(len(v) for v in rule.values())
        others = {
            (a, b)
            for other, r in by_rule.items() if other != name
            for a, bs in r.items() for b in bs
        }
        mine = {(a, b) for a, bs in rule.items() for b in bs}
        reached = sum(1 for v in rule.values() if v)
        print(f"  {name:<8} {pairs:>10,} {len(mine - others):>15,} {reached:>19,}")

    total = sum(len(v) for v in combined.values())
    covered = sum(1 for v in combined.values() if v)
    reached_b = len(set().union(*combined.values())) if total else 0
    sizes = sorted(len(v) for v in combined.values())

    print(f"\n  {'TOTAL':<8} {total:>10,} candidate pairs")
    print(f"  reduction from {full:,}          : {100 * (1 - total / full):.4f}%")
    print(f"  Walmart records with >=1 candidate : {covered:,}/{n_a:,} "
          f"({covered / n_a * 100:.2f}%)   orphans: {n_a - covered}")
    print(f"  Amazon records reachable           : {reached_b:,}/{n_b:,} "
          f"({reached_b / n_b * 100:.1f}%)")
    print(f"  candidates per Walmart record      : median {sizes[len(sizes) // 2]:,}  "
          f"p99 {sizes[int(0.99 * len(sizes))]:,}  max {sizes[-1]:,}")
    print("\n  NOTE: these are reachability counts, not accuracy. Whether the correct")
    print("  partner is among the candidates cannot be known without the labelled")
    print("  data, which stays sealed until the final evaluation (D14).")
    return combined


if __name__ == "__main__":
    table_a, table_b = load_source_tables()
    report(build_index(table_a, table_b))
