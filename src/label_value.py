"""What a few dozen labels are worth, measured.

Pre-registered in docs/PRE_REGISTRATION.md section 13. D19 rejected
self-labelling, conceded that active learning from 30-40 pairs is standard
practice that works, and deferred this comparison until the strict build was
complete. It is complete.

**Only the m-probabilities change.** ``u`` comes from random sampling over the
whole space, needs no labels, and is kept. The comparisons, the blocking and
the candidate set are untouched.

**The EM-trained m values are stripped first.** Splink leaves a level's m
alone when the labels never exercise it, so starting from the trained model
would give a "40 labels" system that was still part expectation-maximisation
on the levels the labels missed. Untrained levels fall back to Splink's
defaults instead, which is what makes k genuinely mean k.

This reads the answer key and sits below the boundary in docs/PRE_UNSEAL.md.

Run with ``python -m src.label_value``.
"""

import copy
import json

import numpy as np
import pandas as pd

from src.interfaces import LEFT_ID, PROCESSED_DIR, RIGHT_ID

K_VALUES = (0, 10, 20, 40, 80, 160, 320, 576)
N_DRAWS = 20                       # random-draw arm, section 13.4
SEED = 0
RESULT_PATH = PROCESSED_DIR / "label_value.json"

PUBLISHED = {"Magellan": 37.40, "DeepMatcher": 53.80, "Ditto": 85.69}
LABEL_FREE_F1 = 51.38              # k = 0, the pre-registered operating point


def strip_m(model: dict) -> dict:
    """Remove every EM-estimated m, keeping u.

    Without this the experiment measures labels *plus* whatever EM already
    knew about the levels the labels did not reach.
    """
    out = copy.deepcopy(model)
    for comparison in out["comparisons"]:
        for level in comparison["comparison_levels"]:
            level.pop("m_probability", None)
    return out


def acquisition_order(train: pd.DataFrame, bits: pd.Series) -> pd.DataFrame:
    """The order an annotator inspects pairs in, best-scoring first.

    The ranking comes from the **label-free** model. Ranking by anything that
    had seen these labels would make the cost column fiction (section 13.8).
    """
    ordered = train.assign(bits=bits.to_numpy()).sort_values(
        ["bits", LEFT_ID, RIGHT_ID], ascending=[False, True, True])
    ordered["confirmed"] = ordered["label"].cumsum()
    return ordered.reset_index(drop=True)


def budget_for(ordered: pd.DataFrame, k: int) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """The first k confirmed matches, **every pair inspected to find them**, and the count.

    The inspected set is returned because the threshold is selected from it and
    from nothing else. Selecting on the whole training split instead would
    spend all 6,144 labels while reporting a budget of twelve, which is the
    error this signature exists to prevent.
    """
    if k == 0:
        empty = ordered.iloc[:0]
        return empty, empty, 0
    reached = ordered.index[ordered["confirmed"] >= k]
    if not len(reached):
        return ordered[ordered["label"] == 1], ordered, len(ordered)
    stop = int(reached[0])
    seen = ordered.iloc[:stop + 1]
    return seen[seen["label"] == 1], seen, stop + 1


def best_threshold(bits: np.ndarray, labels: np.ndarray) -> float:
    """The bit threshold maximising F1 on the data given.

    Selected on train and charged to the label budget (section 13.4). D44
    showed a threshold in bits is not portable, so carrying 6.0 across a
    changed m would blame miscalibration on supervision.
    """
    best, best_f1 = 0.0, -1.0
    for threshold in np.unique(np.round(bits, 2)):
        predicted = bits >= threshold
        tp = int((predicted & (labels == 1)).sum())
        if not tp:
            continue
        denominator = int(predicted.sum()) + int((labels == 1).sum())
        score = 2 * tp / denominator
        if score > best_f1:
            best, best_f1 = float(threshold), score
    return best


def f1_at(bits: np.ndarray, labels: np.ndarray, threshold: float) -> float:
    predicted = bits >= threshold
    tp = int((predicted & (labels == 1)).sum())
    denominator = int(predicted.sum()) + int((labels == 1).sum())
    return 2 * tp / denominator * 100 if denominator else 0.0


def _linker(settings, tables, aliases):
    from splink import DuckDBAPI, Linker
    return Linker(tables, settings, DuckDBAPI(), input_table_aliases=aliases)


def score_with_labels(settings_path, tables, aliases, matches: pd.DataFrame,
                      tag: str) -> pd.DataFrame:
    """Estimate m from ``matches`` alone, then score every pair."""
    from src.matcher import AMAZON_ALIAS, WALMART_ALIAS
    linker = _linker(settings_path, tables, aliases)
    if len(matches):
        labels = pd.DataFrame({
            "source_dataset_l": WALMART_ALIAS,
            "unique_id_l": matches[LEFT_ID].to_numpy(),
            "source_dataset_r": AMAZON_ALIAS,
            "unique_id_r": matches[RIGHT_ID].to_numpy()})
        registered = linker.table_management.register_table(
            labels, f"lbl_{tag}", overwrite=True)
        linker.training.estimate_m_from_pairwise_labels(registered)
    scored = linker.inference.predict().as_pandas_dataframe()
    out = scored[["unique_id_l", "unique_id_r", "match_probability"]].rename(
        columns={"unique_id_l": LEFT_ID, "unique_id_r": RIGHT_ID})
    p = out["match_probability"].clip(1e-12, 1 - 1e-12)
    out["bits"] = np.log2(p / (1 - p))
    return out


def main() -> None:
    import warnings

    from src.data_loading import load_labelled_pairs, load_source_tables
    from src.features import add_features
    from src.matcher import AMAZON_ALIAS, WALMART_ALIAS, attach_pair_keys
    from src.review_queue import SCORES_PATH, match_weight

    warnings.filterwarnings("ignore")
    train = load_labelled_pairs("train", unlock_final_evaluation=True).rename(
        columns={"unique_id_l": LEFT_ID, "unique_id_r": RIGHT_ID})
    test = load_labelled_pairs("test", unlock_final_evaluation=True).rename(
        columns={"unique_id_l": LEFT_ID, "unique_id_r": RIGHT_ID})
    print(f"train {len(train):,} pairs / {int(train.label.sum())} matches   "
          f"test {len(test):,} pairs / {int(test.label.sum())} matches")

    # the label-free ranking the annotator works down
    free = pd.read_csv(SCORES_PATH)
    free["bits"] = match_weight(free["match_probability"])
    ranked = train.merge(free[[LEFT_ID, RIGHT_ID, "bits"]], on=[LEFT_ID, RIGHT_ID],
                         how="left")
    ranked["bits"] = ranked["bits"].fillna(-np.inf)
    ordered = acquisition_order(ranked.drop(columns="bits"), ranked["bits"])

    settings = strip_m(json.load(open(PROCESSED_DIR / "model_classical.json")))
    settings_path = str(PROCESSED_DIR / "_u_only.json")
    json.dump(settings, open(settings_path, "w"))

    raw_a, raw_b = load_source_tables()
    ta, tb = add_features(raw_a.copy(), raw_b.copy())
    every = pd.concat([train, test])[[LEFT_ID, RIGHT_ID]]
    tables = list(attach_pair_keys(ta, tb, every))
    aliases = [WALMART_ALIAS, AMAZON_ALIAS]

    key = lambda d: set(zip(d[LEFT_ID], d[RIGHT_ID]))
    train_keys, test_keys = key(train), key(test)
    truth = {(l, r) for l, r, y in
             zip(pd.concat([train, test])[LEFT_ID], pd.concat([train, test])[RIGHT_ID],
                 pd.concat([train, test])["label"]) if y == 1}

    def evaluate(scored, budget_keys):
        """Threshold from the inspected pairs only; F1 on test.

        ``budget_keys`` is exactly what the annotator looked at. Anything
        outside it has not been paid for and may not inform the threshold.
        """
        scored = scored.copy()
        pair = list(zip(scored[LEFT_ID], scored[RIGHT_ID]))
        scored["y"] = [int(p in truth) for p in pair]
        inspected = scored[[p in budget_keys for p in pair]]
        if len(inspected) and inspected["y"].sum():
            threshold = best_threshold(inspected["bits"].to_numpy(),
                                       inspected["y"].to_numpy())
        else:
            threshold = 6.0                      # nothing paid for, so nothing learned
        te_ = scored[[p in test_keys for p in pair]]
        return threshold, f1_at(te_["bits"].to_numpy(), te_["y"].to_numpy(), threshold)

    results = {"ranked": [], "draws": {}}
    all_matches = train[train.label == 1]
    rng = np.random.default_rng(SEED)

    for k in K_VALUES:
        matches, seen, spent = budget_for(ordered, k)
        if k == 0:
            results["ranked"].append({"k": 0, "labels_spent": 0,
                                      "threshold": 6.0, "f1": LABEL_FREE_F1})
            print(f"  k={k:>4}  labels {0:>5}   F1 {LABEL_FREE_F1:6.2f}  (pre-registered)")
        else:
            seen_keys = set(zip(seen[LEFT_ID], seen[RIGHT_ID]))
            scored = score_with_labels(settings_path, tables, aliases, matches, f"r{k}")
            threshold, score = evaluate(scored, seen_keys)
            results["ranked"].append({"k": k, "labels_spent": int(spent),
                                      "threshold": threshold, "f1": round(score, 2)})
            print(f"  k={k:>4}  labels {spent:>5}   F1 {score:6.2f}   "
                  f"threshold {threshold:6.2f}")

        if k and k < len(all_matches):
            scores = []
            for d in range(N_DRAWS):
                drawn = all_matches.sample(n=k, random_state=int(rng.integers(1 << 30)))
                dkeys = set(zip(drawn[LEFT_ID], drawn[RIGHT_ID]))
                s = score_with_labels(settings_path, tables, aliases, drawn, f"d{k}_{d}")
                scores.append(evaluate(s, dkeys)[1])
            results["draws"][str(k)] = {
                "median": round(float(np.median(scores)), 2),
                "lo": round(float(np.percentile(scores, 2.5)), 2),
                "hi": round(float(np.percentile(scores, 97.5)), 2)}
            r = results["draws"][str(k)]
            print(f"         random draws  median {r['median']:6.2f}  "
                  f"[{r['lo']:.2f}, {r['hi']:.2f}]")

    results["published"] = PUBLISHED
    RESULT_PATH.write_text(json.dumps(results, indent=2))
    print(f"\n  written to {RESULT_PATH.name}")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# POST-HOC ARM -- NOT PRE-REGISTERED
#
# Section 13.3 fixed the crude top-ranked acquisition and called it "the honest
# floor: a real tool would do better". The floor turned out to be a hole: at 44
# labels the annotator has seen four negatives, and a threshold cannot be
# learned from a sample that is almost entirely accepts.
#
# This arm asks what a competent query strategy is worth. It queries the pairs
# nearest the current decision boundary, which is what dedupe and Zingg
# actually do, and what starves the other arm of negatives by construction.
#
# It was added after seeing the pre-registered result and is reported as such.
# ---------------------------------------------------------------------------

ROUNDS = 4


def uncertainty_budget(scored: pd.DataFrame, labelled: set, threshold: float,
                       pool: set, n: int) -> list:
    """The n unlabelled pairs whose scores sit closest to the current boundary."""
    keys = list(zip(scored[LEFT_ID], scored[RIGHT_ID]))
    available = [(abs(b - threshold), k) for k, b in zip(keys, scored["bits"])
                 if k in pool and k not in labelled]
    available.sort(key=lambda x: x[0])
    return [k for _, k in available[:n]]
