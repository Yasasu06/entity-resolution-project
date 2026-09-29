"""Reciprocity evaluated within bounded arrival windows.

Pre-registered as [D52](../docs/DECISIONS.md). The trained model, the
thresholds and the veto order are reused unchanged; the only thing that varies
is how many other records the reciprocity stage can see.

**Why reciprocity is the stage that varies.** Three of the four stages in the
decision rule read a single record at a time: the accept threshold, the margin
against the runner-up, and the quantity veto. ``reciprocal_best`` groups by the
Amazon identifier and asks whether a candidate's own highest-scoring Walmart
record is the record under consideration, which reads across records. A window
bounds how many of those other records are available to it.

**Each window is evaluated independently.** A deployment that had emitted a pair
could not withdraw it when a later record arrived. This measurement re-evaluates
each window in isolation and does not model that constraint. It is a property of
the design, stated in D52 under a scope condition.

No retraining and no parameter changes. Run with ``python -m src.stream``.
"""

import json

import pandas as pd

from src.interfaces import LEFT_ID, PROCESSED_DIR
from src.review_queue import (ACCEPT, SCORES_PATH, apply_quantity_veto,
                              apply_reciprocity_veto, assign_outcomes,
                              match_weight, rank_candidates)

WINDOWS = (1, 10, 25, 100, 250, 500, 1000, 2554)
RESULT_PATH = PROCESSED_DIR / "stream_windows.json"

# The seeded full-batch run's figures. D52's earlier unseeded curve remains a
# historical measurement in the decision log.
BATCH_F1, BATCH_ACCEPTED = 61.47, 974


def arrival_order(ranked: pd.DataFrame) -> list:
    """Record identifiers in the order they arrive.

    Sorted rather than shuffled so a rerun reproduces the same windows. The
    order is a property of the measurement and is fixed here rather than left
    to the order rows happen to sit in a file.
    """
    return sorted(ranked[LEFT_ID].unique())


def windowed_outcomes(ranked: pd.DataFrame, base: pd.DataFrame,
                      window: int, order: list) -> pd.DataFrame:
    """Apply the reciprocity stage within consecutive windows of ``window``.

    At window 1 the stage has no other record to compare against and leaves the
    outcomes as the record-at-a-time stages produced them.
    """
    if window <= 1:
        return base.copy()
    out = base.copy()
    for start in range(0, len(order), window):
        members = set(order[start:start + window])
        rows = out[out.index.isin(members)]
        if rows.empty:
            continue
        out.loc[rows.index] = apply_reciprocity_veto(
            rows, ranked[ranked[LEFT_ID].isin(members)])
    return out


def evaluate(outcomes: pd.DataFrame, truth: set, total_true: int) -> dict:
    """Precision, recall, F1 and accepted count for one window size."""
    accepted = outcomes[outcomes["outcome"] == ACCEPT]
    pairs = list(zip(accepted.index, accepted["best_candidate"]))
    tp = sum(1 for pair in pairs if pair in truth)
    precision = tp / len(pairs) if pairs else 0.0
    recall = tp / total_true if total_true else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accepted": len(pairs), "true_positives": tp,
            "precision": round(precision * 100, 2), "recall": round(recall * 100, 2),
            "f1": round(f1 * 100, 2)}


def measure(windows=WINDOWS) -> list:
    """The curve: one row per window size."""
    from src.data_loading import load_labelled_pairs, load_source_tables

    scores = pd.read_csv(SCORES_PATH)
    scores["bits"] = match_weight(scores["match_probability"])
    table_a, table_b = load_source_tables()
    ranked = rank_candidates(scores)
    base = apply_quantity_veto(assign_outcomes(ranked), table_a, table_b)
    order = arrival_order(ranked)

    labelled = pd.concat([load_labelled_pairs(s, unlock_final_evaluation=True)
                          for s in ("train", "valid", "test")])
    matches = labelled[labelled["label"] == 1]
    truth = set(zip(matches["unique_id_l"], matches["unique_id_r"]))

    rows = []
    for window in windows:
        outcomes = windowed_outcomes(ranked, base, window, order)
        rows.append({"window": window, **evaluate(outcomes, truth, len(truth))})
    # The difference is taken against the full-batch row of this same run
    # rather than the published constant, so the column carries no rounding
    # artifact from comparing a computed figure against a rounded one.
    batch = max(rows, key=lambda r: r["window"])["f1"]
    for row in rows:
        row["f1_difference_from_batch"] = round(row["f1"] - batch, 2)
    return rows


def main() -> None:
    rows = measure()
    print(f"{'window':>8}{'accepted':>10}{'precision':>11}{'recall':>9}"
          f"{'F1':>8}{'vs batch':>10}")
    for row in rows:
        print(f"{row['window']:>8}{row['accepted']:>10,}{row['precision']:>10.2f}%"
              f"{row['recall']:>8.2f}%{row['f1']:>8.2f}"
              f"{row['f1_difference_from_batch']:>+10.2f}")
    RESULT_PATH.write_text(json.dumps(
        {"batch_f1": BATCH_F1, "batch_accepted": BATCH_ACCEPTED, "rows": rows}, indent=1))
    print(f"\n  written to {RESULT_PATH.name}")


if __name__ == "__main__":
    main()
