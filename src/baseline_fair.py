"""The baseline, made comparable to the real system.

The original baseline in ``baseline_token_overlap`` is kept, but it cannot be
compared with the system it is meant to be a baseline *for*. Two reasons, both
recorded in ``docs/PRE_REGISTRATION.md`` section 7:

* **It was supervised and the system was not.** It chose its threshold by
  maximising F1 on ``train`` labels. The matcher never saw a label.
* **It scored different pairs.** It ran on the benchmark's curated set - the
  decision step alone - while the system runs the full pipeline over 564,450
  candidates.

This module fixes both. It runs the same deliberately unsophisticated similarity
over the **same candidate set**, emits **one match per Walmart record** as the
system does, and accepts at a threshold set **without any label**.

The baseline gains the structural treatment the system had and none of the
sophistication, which is what isolates the contribution of the probabilistic
model.

**Everything except the evaluation runs now.** Scoring and deciding touch no
labelled data; only precision and recall need the answer key, and truth is
passed in as an argument so this module never opens a sealed file.

Run with ``python -m src.baseline_fair``.
"""

import pandas as pd

from src.baseline_token_overlap import jaccard, record_tokens
from src.data_loading import load_source_tables
from src.interfaces import LEFT_ID, PROCESSED_DIR, RIGHT_ID, load_candidates

# Fixed in section 7.3 by equal coverage: at 0.34 the baseline accepts 1,055
# records against the system's 1,072, the nearest achievable point. Comparing at
# matched coverage stops either system buying precision by abstaining more, and
# needs no label to set.
THRESHOLD = 0.34

ACCEPTED_PATH = PROCESSED_DIR / "accepted_baseline.csv"


def score_candidates(
    candidates: pd.DataFrame, table_a: pd.DataFrame, table_b: pd.DataFrame
) -> pd.Series:
    """Jaccard similarity over all attributes, for every candidate pair."""
    tokens_a, tokens_b = record_tokens(table_a), record_tokens(table_b)
    return pd.Series(
        [jaccard(tokens_a[l], tokens_b[r])
         for l, r in zip(candidates[LEFT_ID], candidates[RIGHT_ID])],
        index=candidates.index,
    )


def decide(candidates: pd.DataFrame, scores: pd.Series,
           threshold: float = THRESHOLD) -> pd.DataFrame:
    """One accepted pair per Walmart record, its best candidate, above threshold.

    The one-to-one constraint mirrors the system's. Without it the two would
    produce different shapes of output and could not be compared at all.
    """
    scored = candidates.assign(similarity=scores.to_numpy())
    best = (scored.sort_values([LEFT_ID, "similarity"], ascending=[True, False])
                  .groupby(LEFT_ID, as_index=False).first())
    return best[best["similarity"] >= threshold].reset_index(drop=True)


def evaluate(accepted: pd.DataFrame, truth: dict[str, set[str]],
             population: set[str]) -> dict:
    """Precision, recall and F1 against the answer key.

    ``population`` is every Walmart record the system could have matched, so
    that records the baseline declined still count against recall.
    """
    tp = sum(1 for _, r in accepted.iterrows()
             if r[RIGHT_ID] in truth.get(r[LEFT_ID], set()))
    fp = len(accepted) - tp
    total_true = sum(1 for w in population if truth.get(w))
    fn = total_true - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / total_true if total_true else 0.0
    return {
        "accepted": len(accepted), "true_positives": tp,
        "false_positives": fp, "false_negatives": fn,
        "precision": precision, "recall": recall,
        "f1": (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0,
    }


def precision_recall_curve(
    candidates: pd.DataFrame, scores: pd.Series, truth: dict[str, set[str]],
    population: set[str], steps: int = 50,
) -> list[dict]:
    """The whole trade-off, not one point on it.

    Section 7.5 requires this alongside the headline: it is what stops a single
    threshold being cherry-picked. If the baseline beats the system somewhere
    else on this curve, the curve says so and that is reported.
    """
    out = []
    for i in range(1, steps):
        t = i / steps
        row = evaluate(decide(candidates, scores, t), truth, population)
        row["threshold"] = t
        out.append(row)
    return out


def main() -> None:
    table_a, table_b = load_source_tables()
    candidates = load_candidates("classical")
    scores = score_candidates(candidates, table_a, table_b)
    accepted = decide(candidates, scores)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    accepted.to_csv(ACCEPTED_PATH, index=False)
    print(f"{len(candidates):,} candidate pairs scored by token overlap")
    print(f"  threshold                 {THRESHOLD}")
    print(f"  records accepted          {len(accepted):,} of "
          f"{candidates[LEFT_ID].nunique():,} with candidates")
    print(f"  similarity of accepts     median {accepted['similarity'].median():.3f}, "
          f"min {accepted['similarity'].min():.3f}")
    print(f"  written to                {ACCEPTED_PATH.name}")
    print("\n  Precision and recall need the answer key and are computed once, at")
    print("  final evaluation. This module never opens a labelled file.")


if __name__ == "__main__":
    main()
