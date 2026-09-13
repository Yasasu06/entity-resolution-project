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
  Rarity is judged by how many *Amazon* records hold the word.
- **R2 — a shared part-number-shaped word.** A token mixing letters and digits
  (``ph3100u``, ``elplp12``) is almost always a manufacturer part number, which
  is close to decisive evidence.
- **R3 — the same brand, plus one other shared word.** Brand alone is far too
  broad (the "hp" block holds 318 Amazon records), but combined with any second
  shared word it narrows sharply.
- **R5 — a shared rare character sequence.** Catches part numbers the two
  retailers punctuate differently, which word-level rules miss entirely. See
  ``text_normalisation`` and docs/DECISIONS.md (D15).
- **R4 — a last-resort safety net, in both directions.** Any Walmart record
  that *still* has no candidate is matched to its nearest Amazon records by
  text similarity. The same is then done in reverse for any Amazon record no
  Walmart record reached — because every other rule is phrased as "for each
  Walmart record, find Amazon records", and that phrasing cannot see an Amazon
  record nothing happened to reach.

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

# R1: ignore a word once it appears in more than this many *Amazon* records.
# Counted on the Amazon side only, because that is what determines how many
# candidates the word actually pulls in — the number of Walmart records holding
# it costs nothing. See docs/DECISIONS.md (D18).
R1_MAX_DOC_FREQUENCY = 100

# R2: what counts as "part-number shaped" — at least this long, and containing
# both a letter and a digit.
R2_MIN_IDENTIFIER_LENGTH = 5

# R3: how many shared words beyond the brand name are required. One is too
# weak — brand plus a single common word ("black", "usb") matches far too
# freely. Measured: requiring two cuts the candidate set by a third while
# keeping every Walmart record reachable.
R3_MIN_SHARED_WORDS = 2

# R5: ignore a character sequence once it appears in more than this many
# *Amazon* records. Counted on the Amazon side only, because that is what
# determines how many candidates the sequence actually pulls in.
R5_MAX_DOC_FREQUENCY = 50

# R4: how many nearest neighbours to offer a record that nothing else reached.
# Chosen to be close to the median number of candidates a normal record gets,
# so a rescued record is neither starved nor flooded. The same count is used in
# both directions — see docs/DECISIONS.md (D17) for why the Amazon side is not
# given a smaller allowance.
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
    b_token_index: dict[str, set[str]] = field(default_factory=dict)
    b_ngram_index: dict[str, set[str]] = field(default_factory=dict)
    b_brand_index: dict[str, set[str]] = field(default_factory=dict)
    # Needed only by the Amazon-side safety net, which searches in reverse.
    a_ngram_index: dict[str, set[str]] = field(default_factory=dict)


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

    a_brands = _harvest_brands(table_a, a_tokens, table_a, table_b)
    b_brands = _harvest_brands(table_b, b_tokens, table_a, table_b)

    index = BlockingIndex(
        a_tokens=a_tokens, b_tokens=b_tokens,
        a_ngrams=a_ngrams, b_ngrams=b_ngrams,
        a_brands=a_brands, b_brands=b_brands,
    )
    index.b_token_index = _invert(b_tokens)
    index.b_ngram_index = _invert(b_ngrams)
    index.b_brand_index = _invert(b_brands)
    index.a_ngram_index = _invert(a_ngrams)
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
    """Shared word that appears in few Amazon records.

    "Few" is counted on the Amazon side alone. The size of a word's Amazon
    posting list *is* its cost — it is exactly how many candidates the word
    contributes — so that list is both the filter and the answer, and there is
    no separate frequency table to fall out of step with it.
    """
    hits: set[str] = set()
    for token in index.a_tokens[a_id]:
        postings = index.b_token_index.get(token)
        if postings is not None and len(postings) <= R1_MAX_DOC_FREQUENCY:
            hits |= postings
    return hits


def _rule_r2(index: BlockingIndex, a_id: str) -> set[str]:
    """Shared word shaped like a manufacturer part number, at any frequency."""
    hits: set[str] = set()
    for token in index.a_tokens[a_id]:
        if is_identifier_like(token):
            hits |= index.b_token_index.get(token, set())
    return hits


def _rule_r3(index: BlockingIndex, a_id: str) -> set[str]:
    """Same brand AND at least ``R3_MIN_SHARED_WORDS`` other shared words.

    Brand alone is far too coarse to use by itself — the "hp" block holds 318
    Amazon records — so it acts as a cheap partition that further agreement
    then narrows. Requiring two other shared words rather than one is what
    keeps this rule from dominating the whole candidate set.
    """
    same_brand: set[str] = set()
    for brand in index.a_brands[a_id]:
        same_brand |= index.b_brand_index.get(brand, set())

    a_tokens = index.a_tokens[a_id]
    hits = set()
    for b_id in same_brand:
        # "Another" shared word means one that is not itself the brand name.
        shared = (a_tokens & index.b_tokens[b_id]) - index.a_brands[a_id]
        if len(shared) >= R3_MIN_SHARED_WORDS:
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


def _nearest_neighbours(
    query_grams: set[str],
    target_ngram_index: dict[str, set[str]],
    target_grams: dict[str, set[str]],
) -> set[str]:
    """The most textually similar records from the other table.

    Similarity is the proportion of character sequences the two records share
    (shared / total distinct across both). Only records sharing at least one
    sequence are scored, which keeps this fast without changing the answer — a
    record sharing nothing would score zero regardless.

    Written once and used in both directions, so the Walmart-side and
    Amazon-side safety nets cannot drift apart.
    """
    if not query_grams:
        return set()

    overlap: collections.Counter = collections.Counter()
    for gram in query_grams:
        for record_id in target_ngram_index.get(gram, ()):
            overlap[record_id] += 1

    scored = [
        (shared / len(query_grams | target_grams[record_id]), record_id)
        for record_id, shared in overlap.items()
    ]
    scored.sort(reverse=True)
    return {record_id for _, record_id in scored[:R4_NEIGHBOURS]}


def _rule_r4(index: BlockingIndex, a_id: str) -> set[str]:
    """Safety net, Walmart side: nearest Amazon records for a stranded record.

    Only used for a Walmart record that every other rule missed. Without it
    such a record has no candidates at all and therefore cannot possibly be
    matched — a silent, unrecoverable loss.
    """
    return _nearest_neighbours(index.a_ngrams[a_id], index.b_ngram_index, index.b_ngrams)


def _rule_r4_symmetric(index: BlockingIndex, b_id: str) -> set[str]:
    """Safety net, Amazon side: nearest Walmart records for an unreached record.

    The mirror image of :func:`_rule_r4`, and it exists because every other
    rule is written as "for each Walmart record, find Amazon records". That
    phrasing has a blind spot: an Amazon record that no Walmart record happens
    to reach is just as unmatchable as a stranded Walmart record, and nothing
    else in the design notices.

    See docs/DECISIONS.md (D17), including why the affected records turned out
    not to be the harmless leftovers they were first assumed to be.
    """
    return _nearest_neighbours(index.b_ngrams[b_id], index.a_ngram_index, index.a_ngrams)


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

    # R4 only fires where nothing else did, on the Walmart side.
    rescued: dict[str, set[str]] = {}
    for a_id in index.a_tokens:
        if not any(result[name][a_id] for name in PRIMARY_RULES):
            rescued[a_id] = _rule_r4(index, a_id)
    result["R4"] = rescued

    # Then the same check in the other direction. This must run last, because
    # the Walmart-side rescue above can itself make Amazon records reachable,
    # and there is no point rescuing a record that is already covered.
    reached: set[str] = set()
    for rule in result.values():
        for hits in rule.values():
            reached |= hits

    symmetric: dict[str, set[str]] = collections.defaultdict(set)
    for b_id in index.b_tokens:
        if b_id in reached:
            continue
        # Pairs are keyed by Walmart id to match every other rule's shape, so
        # the found neighbours become the keys and this record the value.
        for a_id in _rule_r4_symmetric(index, b_id):
            symmetric[a_id].add(b_id)
    result["R4-sym"] = dict(symmetric)
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
    print(f"  settings: R1 Amazon-DF<={R1_MAX_DOC_FREQUENCY}  "
          f"R3 >={R3_MIN_SHARED_WORDS} shared words  "
          f"R5 Amazon-DF<={R5_MAX_DOC_FREQUENCY}  R4 neighbours={R4_NEIGHBOURS}")

    print(f"\n  {'rule':<8} {'pairs':>10} {'unique to rule':>15} {'A records reached':>19}")
    for name in ("R1", "R2", "R3", "R5", "R4", "R4-sym"):
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
          f"({reached_b / n_b * 100:.2f}%)   unreachable: {n_b - reached_b}")
    print(f"  candidates per Walmart record      : median {sizes[len(sizes) // 2]:,}  "
          f"p99 {sizes[int(0.99 * len(sizes))]:,}  max {sizes[-1]:,}")
    print("\n  NOTE: these are reachability counts, not accuracy. Whether the correct")
    print("  partner is among the candidates cannot be known without the labelled")
    print("  data, which stays sealed until the final evaluation (D14).")
    return combined


if __name__ == "__main__":
    table_a, table_b = load_source_tables()
    report(build_index(table_a, table_b))
