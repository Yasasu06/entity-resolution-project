"""A deliberately simple baseline, to give the real system a number to beat.

The idea is about as unsophisticated as record matching gets:

1. Mash all of a record's attribute values together into one bag of words.
2. Measure how many words two records share, as a proportion of all the
   distinct words across both (this ratio is called *Jaccard similarity*).
3. Call the pair a match if that score is above some threshold.

No learning, no probabilities, no per-field logic — it does not even know which
attribute a word came from. That is the point. If a sophisticated system cannot
comfortably beat this, the sophistication is not earning its keep.

Establishing a weak baseline first is standard practice for a reason: it is very
easy to build something complicated and *feel* like it works, without ever
checking whether a five-line heuristic would have done just as well.

**Which evaluation is this?**
This scores the benchmark's own pre-selected pairs — the ~10,242 curated pairs
that ship with the dataset. It measures the *decision step only*, on a set where
9.4% of pairs are matches. It is NOT the full-pipeline evaluation over all
~56.4 million possible pairs, where genuine matches are about 0.0017% of the
space. Those two numbers are not comparable, and this project reports them
separately. See docs/DECISIONS.md.

**SEALED — this does not run during development.**
Under the project's strict no-peek policy (docs/DECISIONS.md D14) no labelled
data is consulted until the entire pipeline is built. This script scores
against labels, so it belongs to the single final evaluation pass at the end
of the project, alongside the real system.

An earlier result from this script (F1 = 0.381 on valid) was computed under a
looser rule that has since been superseded. It is retained in the decision log
as history, not as a live number, and will be recomputed at the final
evaluation.

Run it, as that final evaluation only::

    python -m src.baseline_token_overlap --unlock-final-evaluation
"""

import re

import pandas as pd

from src.data_loading import (
    ID_COLUMN,
    attribute_columns,
    load_labelled_pairs,
    load_source_tables,
)

# Splits words on anything that is not a letter or digit, so "1tb", "usb",
# "3.0" and "ph3100u-1e3s" break apart in a predictable way.
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenise(text: str) -> set[str]:
    """Turn a record's text into a set of lowercase word-ish tokens.

    A *set* is used rather than a list because this baseline only cares whether
    a word is present, not how many times it appears.
    """
    return set(TOKEN_PATTERN.findall(str(text).lower()))


def record_tokens(table: pd.DataFrame) -> pd.Series:
    """Build one token set per record, from all its attributes combined.

    Missing values are skipped rather than turned into the literal word "nan",
    which would otherwise become a token that every incomplete record shares.
    """
    columns = attribute_columns(table)

    def combine(row: pd.Series) -> set[str]:
        parts = [str(v) for v in row[columns] if pd.notna(v)]
        return tokenise(" ".join(parts))

    return pd.Series(table.apply(combine, axis=1).values, index=table[ID_COLUMN])


def jaccard(left: set[str], right: set[str]) -> float:
    """Proportion of shared tokens: |intersection| / |union|. 0.0 to 1.0."""
    if not left and not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def score_pairs(pairs: pd.DataFrame, tokens_a: pd.Series, tokens_b: pd.Series) -> pd.Series:
    """Compute a similarity score for every labelled pair."""
    return pd.Series(
        [
            jaccard(tokens_a[left], tokens_b[right])
            for left, right in zip(pairs["unique_id_l"], pairs["unique_id_r"])
        ],
        index=pairs.index,
    )


def evaluate(labels: pd.Series, scores: pd.Series, threshold: float) -> dict[str, float]:
    """Score predictions at one threshold.

    - **precision** — of the pairs we called matches, how many really were.
      Low precision means we waste people's time with false alarms.
    - **recall** — of the real matches, how many we found.
      Low recall means we silently miss real duplicates.
    - **F1** — their harmonic mean, a single number balancing the two.
    """
    predicted = scores >= threshold
    actual = labels == 1

    true_positives = int((predicted & actual).sum())
    false_positives = int((predicted & ~actual).sum())
    false_negatives = int((~predicted & actual).sum())

    precision = true_positives / (true_positives + false_positives) if predicted.any() else 0.0
    recall = true_positives / (true_positives + false_negatives) if actual.any() else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def choose_threshold(labels: pd.Series, scores: pd.Series) -> dict[str, float]:
    """Pick the threshold with the best F1, by trying many candidates.

    Deliberately a brute-force sweep: it is obvious, fast enough at this scale,
    and easy to reason about.
    """
    candidates = [i / 200 for i in range(1, 200)]  # 0.005 to 0.995
    return max(
        (evaluate(labels, scores, t) for t in candidates),
        key=lambda r: r["f1"],
    )


def _print_result(name: str, result: dict[str, float], n_pairs: int, n_matches: int) -> None:
    print(f"\n  {name}  ({n_pairs:,} pairs, {n_matches:,} real matches)")
    print(f"    threshold        {result['threshold']:.3f}")
    print(f"    precision        {result['precision']:.3f}"
          f"   (of pairs called a match, this share really were)")
    print(f"    recall           {result['recall']:.3f}"
          f"   (of real matches, this share were found)")
    print(f"    F1               {result['f1']:.3f}")
    print(f"    true positives   {result['true_positives']:,}")
    print(f"    false positives  {result['false_positives']:,}")
    print(f"    false negatives  {result['false_negatives']:,}")


def main(unlock_final_evaluation: bool = False) -> None:
    # SEALED under the strict no-peek policy (docs/DECISIONS.md D14). This
    # script consults labelled answers, so it may only run as part of the single
    # final evaluation at the end of the project — not during development.
    if not unlock_final_evaluation:
        print(__doc__.strip().splitlines()[0])
        print(
            "\nThis baseline is SEALED and did not run.\n\n"
            "It scores against labelled answers, and this project uses a strict\n"
            "no-peek policy: no labelled data (train, valid or test) is consulted\n"
            "until the whole pipeline is built and the single final evaluation\n"
            "is run.\n\n"
            "The previously recorded result (F1 = 0.381 on valid) was computed\n"
            "under an earlier, looser rule and is SUPERSEDED — see D9 and D14 in\n"
            "docs/DECISIONS.md. It will be recomputed at the final evaluation,\n"
            "as part of one honest pass alongside the real system.\n\n"
            "To run it as that final evaluation:\n"
            "    python -m src.baseline_token_overlap --unlock-final-evaluation"
        )
        return

    table_a, table_b = load_source_tables()
    tokens_a = record_tokens(table_a)
    tokens_b = record_tokens(table_b)

    train = load_labelled_pairs("train", unlock_final_evaluation=True)
    valid = load_labelled_pairs("valid", unlock_final_evaluation=True)

    train_scores = score_pairs(train, tokens_a, tokens_b)
    valid_scores = score_pairs(valid, tokens_a, tokens_b)

    print("=" * 74)
    print("DUMB BASELINE — token overlap (Jaccard) on all attributes combined")
    print("=" * 74)
    print("\n  Evaluation scope: the benchmark's OWN curated pairs (decision step only).")
    print("  This is NOT the full ~56.4M-pair pipeline evaluation. Not comparable.")

    # The threshold is chosen using train only; valid is untouched until it is
    # used once, for reporting. This mirrors how the real system will be tuned.
    best = choose_threshold(train["label"], train_scores)
    _print_result("TRAIN (threshold chosen here)", best,
                  len(train), int(train["label"].sum()))

    held_out = evaluate(valid["label"], valid_scores, best["threshold"])
    _print_result("VALID (held out — the number that counts)", held_out,
                  len(valid), int(valid["label"].sum()))

    print("\n  test.csv was NOT read. It stays sealed for one final evaluation.")
    print("\n  This is the number the real system must beat:"
          f"  F1 = {held_out['f1']:.3f} on valid.\n")


if __name__ == "__main__":
    import sys
    main(unlock_final_evaluation="--unlock-final-evaluation" in sys.argv)
