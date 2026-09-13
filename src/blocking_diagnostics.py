"""What blocking threw away, summarised — without storing the discarded pairs.

Blocking discards about 55.8 million of 56.4 million possible pairs. A system
that drops 99% of its input should not do so silently: if a real match is lost
here, nothing downstream can recover it, and without some record of what was
excluded there is no way to reason about the loss at all.

**Why a summary rather than a log.** Storing 55.8 million discarded pairs would
cost gigabytes to record something fully regenerable — rerun `src.blocking`
against the untouched raw data and the identical set comes back. What is *not*
regenerable from a glance is a characterisation of what those pairs look like,
which is what this module produces.

**What it reports.**

1. **Headline counts and reduction ratio** — the one standard, label-free
   blocking metric in the literature.
2. **Per-record exclusion spread** — how unevenly the discarding falls across
   Walmart records.
3. **Near-miss counts** — exactly how many more pairs each rule would admit if
   its threshold were loosened one notch. This is the most directly useful
   number here: it says how much is sitting just outside the door, and
   therefore how sensitive the design is to a threshold being slightly wrong.
4. **A sampled taxonomy of why pairs were discarded** — of the pairs thrown
   away, how many shared nothing at all, how many shared only words too common
   to be meaningful, and how many fell just short of a specific rule.

**On standard practice.** Reduction ratio (item 1) is standard. The other two
metrics in the literature — pair completeness and pair quality — both require
the answer key and so cannot be computed under this project's no-peek policy
(docs/DECISIONS.md D14). Items 2 to 4 are not a named standard technique; they
are a design choice for this project, reasoned from the fact that the usual
recall-side metrics are unavailable. See docs/DECISIONS.md (D21).

Nothing here consults labelled data. These figures describe the *shape* of what
was excluded, never whether any excluded pair was a genuine match.

Run with ``python -m src.blocking_diagnostics``.
"""

import collections
import json
import random
from pathlib import Path

from src.blocking import (
    R1_MAX_DOC_FREQUENCY,
    R3_MIN_SHARED_WORDS,
    R5_MAX_DOC_FREQUENCY,
    BlockingIndex,
    build_index,
    generate_candidates,
    is_identifier_like,
)
from src.data_loading import load_source_tables

# How many discarded pairs to inspect for the taxonomy. The discarded space is
# ~55.8 million; a sample this size pins each percentage to well under a tenth
# of a percentage point, which is far finer than any decision needs.
SAMPLE_SIZE = 100_000

# Fixed so the reported figures are reproducible run to run.
RANDOM_SEED = 20260913

# One notch looser than each live threshold, for the near-miss counts.
R1_LOOSENED = 150
R5_LOOSENED = 75
R3_LOOSENED = 1

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "blocking_diagnostics.json"


def _headline(index: BlockingIndex, candidates: dict[str, set[str]]) -> dict:
    n_a, n_b = len(index.a_tokens), len(index.b_tokens)
    possible = n_a * n_b
    kept = sum(len(v) for v in candidates.values())
    return {
        "walmart_records": n_a,
        "amazon_records": n_b,
        "possible_pairs": possible,
        "candidate_pairs": kept,
        "discarded_pairs": possible - kept,
        "reduction_ratio": round(1 - kept / possible, 6),
        "share_discarded": round((possible - kept) / possible, 6),
    }


def _exclusion_spread(index: BlockingIndex, candidates: dict[str, set[str]]) -> dict:
    """How unevenly the discarding falls across Walmart records.

    A record with very few candidates had almost the entire Amazon table thrown
    away against it. That is not wrong in itself — most of it genuinely is
    unrelated — but a record at the extreme is the one most exposed if blocking
    has made a mistake, so it is worth surfacing rather than hiding inside an
    average.
    """
    n_b = len(index.b_tokens)
    discarded = sorted(n_b - len(v) for v in candidates.values())
    n = len(discarded)
    return {
        "per_walmart_record": {
            "min_discarded": discarded[0],
            "median_discarded": discarded[n // 2],
            "p99_discarded": discarded[int(0.99 * n)],
            "max_discarded": discarded[-1],
        },
        "records_keeping_under_50_candidates": sum(1 for d in discarded if n_b - d < 50),
    }


def _near_misses(index: BlockingIndex, candidates: dict[str, set[str]]) -> dict:
    """How many more pairs each rule would admit at a slightly looser setting.

    This is the number that says how exposed the design is to a threshold being
    a little wrong. A rule where loosening changes almost nothing is settled; a
    rule where loosening admits a flood is sitting on a cliff edge.
    """
    kept = {(a, b) for a, bs in candidates.items() for b in bs}

    def extra(pairs: set[tuple[str, str]]) -> int:
        return len(pairs - kept)

    # R1 one notch looser
    r1: set[tuple[str, str]] = set()
    for a_id, tokens in index.a_tokens.items():
        for token in tokens:
            postings = index.b_token_index.get(token)
            if postings is not None and R1_MAX_DOC_FREQUENCY < len(postings) <= R1_LOOSENED:
                r1 |= {(a_id, b) for b in postings}

    # R5 one notch looser
    r5: set[tuple[str, str]] = set()
    for a_id, grams in index.a_ngrams.items():
        for gram in grams:
            postings = index.b_ngram_index.get(gram)
            if postings is not None and R5_MAX_DOC_FREQUENCY < len(postings) <= R5_LOOSENED:
                r5 |= {(a_id, b) for b in postings}

    # R3 with the shared-word requirement dropped back to one
    r3: set[tuple[str, str]] = set()
    for a_id, brands in index.a_brands.items():
        same_brand: set[str] = set()
        for brand in brands:
            same_brand |= index.b_brand_index.get(brand, set())
        for b_id in same_brand:
            shared = (index.a_tokens[a_id] & index.b_tokens[b_id]) - brands
            if R3_LOOSENED <= len(shared) < R3_MIN_SHARED_WORDS:
                r3.add((a_id, b_id))

    return {
        "r1_amazon_df_100_to_150": extra(r1),
        "r3_shared_words_2_to_1": extra(r3),
        "r5_amazon_df_50_to_75": extra(r5),
        "any_of_the_three": extra(r1 | r3 | r5),
    }


def _sampled_taxonomy(index: BlockingIndex, candidates: dict[str, set[str]]) -> dict:
    """Why discarded pairs were discarded, from a uniform random sample.

    Each sampled pair is placed in the *strongest* category it qualifies for,
    so the buckets are mutually exclusive and read as "the best evidence this
    pair had was ...".
    """
    rng = random.Random(RANDOM_SEED)
    a_ids = list(index.a_tokens)
    b_ids = list(index.b_tokens)

    buckets: collections.Counter = collections.Counter()
    shared_word_counts: collections.Counter = collections.Counter()
    inspected = 0
    attempts = 0
    max_attempts = SAMPLE_SIZE * 5

    while inspected < SAMPLE_SIZE and attempts < max_attempts:
        attempts += 1
        a_id = rng.choice(a_ids)
        b_id = rng.choice(b_ids)
        if b_id in candidates[a_id]:
            continue                      # this pair was kept, not discarded
        inspected += 1

        a_tokens, b_tokens = index.a_tokens[a_id], index.b_tokens[b_id]
        shared = a_tokens & b_tokens
        shared_word_counts[min(len(shared), 5)] += 1

        brands_agree = bool(index.a_brands[a_id] & index.b_brands[b_id])
        shared_beyond_brand = shared - index.a_brands[a_id]
        shared_grams = index.a_ngrams[a_id] & index.b_ngrams[b_id]

        if not shared and not shared_grams:
            buckets["shared_nothing_at_all"] += 1
        elif any(is_identifier_like(t) for t in shared):
            # Should be impossible: R2 accepts these at any frequency.
            buckets["UNEXPECTED_shared_part_number"] += 1
        elif brands_agree and shared_beyond_brand:
            buckets["brand_agreed_but_too_few_other_words"] += 1
        elif shared:
            buckets["shared_only_words_too_common"] += 1
        else:
            buckets["shared_only_sequences_too_common"] += 1

    total = max(inspected, 1)
    return {
        "sample_size": inspected,
        "categories": {
            name: {"count": count, "share": round(count / total, 4)}
            for name, count in buckets.most_common()
        },
        "shared_word_count_distribution": {
            (f"{k}+" if k == 5 else str(k)): round(v / total, 4)
            for k, v in sorted(shared_word_counts.items())
        },
    }


def collect(index: BlockingIndex, candidates: dict[str, set[str]]) -> dict:
    """Assemble every diagnostic into one plain dictionary."""
    return {
        "settings": {
            "r1_max_amazon_doc_frequency": R1_MAX_DOC_FREQUENCY,
            "r3_min_shared_words": R3_MIN_SHARED_WORDS,
            "r5_max_amazon_doc_frequency": R5_MAX_DOC_FREQUENCY,
        },
        "headline": _headline(index, candidates),
        "exclusion_spread": _exclusion_spread(index, candidates),
        "near_misses": _near_misses(index, candidates),
        "discarded_sample": _sampled_taxonomy(index, candidates),
        "note": (
            "Summary only. The discarded pairs themselves are not stored: they are "
            "fully regenerable by rerunning src.blocking against the untouched raw "
            "data. No labelled data was consulted (see docs/DECISIONS.md D14, D21)."
        ),
    }


def render(report: dict) -> None:
    """Print the report in a readable form."""
    h, s, n, d = (report["headline"], report["exclusion_spread"],
                  report["near_misses"], report["discarded_sample"])

    print("=" * 78)
    print("BLOCKING DIAGNOSTICS — what was discarded")
    print("=" * 78)
    print(f"\n  possible pairs   {h['possible_pairs']:>12,}")
    print(f"  kept             {h['candidate_pairs']:>12,}")
    print(f"  discarded        {h['discarded_pairs']:>12,}   "
          f"({h['share_discarded'] * 100:.2f}% of the space)")
    print(f"  reduction ratio  {h['reduction_ratio']:>12.6f}   (the standard metric)")

    print("\n  --- how the discarding falls across Walmart records ---")
    p = s["per_walmart_record"]
    print(f"    pairs discarded per record: min {p['min_discarded']:,}  "
          f"median {p['median_discarded']:,}  max {p['max_discarded']:,}")
    print(f"    records left with fewer than 50 candidates: "
          f"{s['records_keeping_under_50_candidates']:,}")

    print("\n  --- near misses: extra pairs if a threshold were loosened one notch ---")
    print(f"    R1  Amazon-DF 100 -> 150 : {n['r1_amazon_df_100_to_150']:>9,} more pairs")
    print(f"    R3  shared words 2 -> 1  : {n['r3_shared_words_2_to_1']:>9,} more pairs")
    print(f"    R5  Amazon-DF 50 -> 75   : {n['r5_amazon_df_50_to_75']:>9,} more pairs")
    print(f"    any of the three         : {n['any_of_the_three']:>9,} more pairs")

    print(f"\n  --- what discarded pairs look like ({d['sample_size']:,} sampled) ---")
    for name, stats in d["categories"].items():
        print(f"    {name:<42} {stats['share'] * 100:>6.2f}%  ({stats['count']:,})")
    print("\n    shared words per discarded pair:")
    for k, share in d["shared_word_count_distribution"].items():
        print(f"      {k:>2} shared words : {share * 100:>6.2f}%")

    print("\n  Summary only — the discarded pairs are regenerable by rerunning")
    print("  src.blocking. No labelled data consulted.")


def main() -> None:
    table_a, table_b = load_source_tables()
    index = build_index(table_a, table_b)
    candidates = generate_candidates(index)
    report = collect(index, candidates)
    render(report)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n  written to {OUTPUT_PATH.relative_to(OUTPUT_PATH.parent.parent)}")


if __name__ == "__main__":
    main()
