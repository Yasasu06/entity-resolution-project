"""Confidence intervals for the figures this project reports.

Every headline number here is a statistic of one sample: 2,554 Walmart records
drawn once from a benchmark. Reported bare, `61.46%` invites the reading that a
system scoring 61.0% would be worse, which the data does not support.

The project already holds this standard. The stability gate in
docs/PRE_REGISTRATION.md section 11.4 was **withdrawn** rather than reported,
because its interval straddled the floor it was meant to clear. That reasoning
was never turned on the headline.

**The resampling unit is the Walmart record, not the pair.** A record's
candidates, its accept decision and its true partners are one dependent bundle:
resampling pairs would treat them as independent evidence and give intervals
that are too narrow. For the benchmark protocol (D44) the unit is the pair,
because there each pair is judged alone.

**Intervals are percentile bootstrap**, which needs no assumption about the
shape of the sampling distribution. This matters for F1, a ratio of ratios with
no closed-form standard error.

Nothing here changes a decision. It reports how much of what is claimed the
evidence actually carries.
"""

import numpy as np

N_BOOT = 2000
ALPHA = 0.05
SEED = 0       # fixed: an interval that moves between runs is not a measurement


def f1(true_positives: int, predicted: int, actual: int) -> float:
    """F1 as a percentage, zero where it is undefined rather than NaN."""
    if not predicted or not actual:
        return 0.0
    precision = true_positives / predicted
    recall = true_positives / actual
    if not (precision + recall):
        return 0.0
    return 2 * precision * recall / (precision + recall) * 100


def bootstrap(units: list, statistic, n_boot: int = N_BOOT, alpha: float = ALPHA,
              seed: int = SEED) -> dict:
    """Percentile interval for ``statistic`` over resamples of ``units``.

    ``statistic`` takes a sample of units and returns a number, or None where
    the resample cannot produce one. Those are dropped and counted rather than
    silently treated as zero.
    """
    rng = np.random.default_rng(seed)
    index = np.arange(len(units))
    arr = np.asarray(units, dtype=object)
    values, dropped = [], 0
    for _ in range(n_boot):
        sample = arr[rng.choice(index, size=len(index), replace=True)]
        value = statistic(sample)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            dropped += 1
            continue
        values.append(value)
    if not values:
        raise ValueError("every resample was undefined; check the statistic")
    lo, hi = np.percentile(values, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"point": statistic(arr), "lo": float(lo), "hi": float(hi),
            "n_boot": len(values), "dropped": dropped}


def paired_bootstrap(units: list, statistic_a, statistic_b, n_boot: int = N_BOOT,
                     alpha: float = ALPHA, seed: int = SEED) -> dict:
    """Interval for ``a - b`` measured on the *same* resample each time.

    Pairing is what makes a small difference testable. Two systems evaluated on
    one set of records share every quirk of that set, so the difference is far
    better determined than either figure alone: D46's +0.52 point gain sits
    inside intervals for the two systems that overlap almost completely.
    """
    rng = np.random.default_rng(seed)
    index = np.arange(len(units))
    arr = np.asarray(units, dtype=object)
    diffs = []
    for _ in range(n_boot):
        sample = arr[rng.choice(index, size=len(index), replace=True)]
        a, b = statistic_a(sample), statistic_b(sample)
        if a is None or b is None:
            continue
        diffs.append(a - b)
    lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"point": statistic_a(arr) - statistic_b(arr),
            "lo": float(lo), "hi": float(hi),
            "favours_a": float(np.mean(np.asarray(diffs) > 0)),
            "significant": bool(lo > 0 or hi < 0)}


def contains(interval: dict, value: float) -> bool:
    """Whether a published figure lies inside an interval.

    A figure inside it is **not distinguishable** from the measurement. D44
    claimed the system sits 2.42 points below DeepMatcher's published 53.80 on
    a split of 2,049 pairs; 53.80 is inside the interval, so the ordering was
    never established (D48).
    """
    return interval["lo"] <= value <= interval["hi"]


def fmt(interval: dict, places: int = 2) -> str:
    """``61.46 [58.95, 64.07]`` -- the form every reported figure should take."""
    return (f"{interval['point']:.{places}f} "
            f"[{interval['lo']:.{places}f}, {interval['hi']:.{places}f}]")


# ---------------------------------------------------------------------------
# The project's own figures
#
# This reads the answer key and therefore sits below the boundary in
# docs/PRE_UNSEAL.md. It changes no threshold and no decision; it reports how
# much the evidence carries.
# ---------------------------------------------------------------------------

BENCHMARK_PUBLISHED = {"Magellan": 37.40, "DeepMatcher": 53.80, "Ditto": 85.69}
RESULT_PATH = None      # set in main(), kept out of import time


def _accepted(path) -> dict:
    import pandas as pd
    d = pd.read_csv(path)
    return dict(zip(d["unique_id_l"], d["unique_id_r"]))


def _record_statistic(accepted: dict, partners: dict):
    """F1 over a resample of Walmart records, per true pair."""
    def statistic(sample):
        tp = sum(1 for w in sample if w in accepted
                 and accepted[w] in partners.get(w, ()))
        predicted = sum(1 for w in sample if w in accepted)
        actual = sum(len(partners.get(w, ())) for w in sample)
        if not predicted or not actual:
            return None
        return f1(tp, predicted, actual)
    return statistic


def main() -> None:
    import collections
    import json

    import pandas as pd

    from src.data_loading import load_labelled_pairs
    from src.interfaces import LEFT_ID, PROCESSED_DIR, load_candidates

    labelled = pd.concat([load_labelled_pairs(s, unlock_final_evaluation=True)
                          for s in ("train", "valid", "test")])
    matches = labelled[labelled["label"] == 1]
    partners = collections.defaultdict(set)
    for left, right in zip(matches["unique_id_l"], matches["unique_id_r"]):
        partners[left].add(right)

    records = sorted(set(load_candidates("classical")[LEFT_ID]))
    system = _record_statistic(_accepted(PROCESSED_DIR / "accepted_classical.csv"), partners)
    baseline = _record_statistic(_accepted(PROCESSED_DIR / "accepted_baseline.csv"), partners)

    out = {
        "system": bootstrap(records, system),
        "baseline": bootstrap(records, baseline),
        "gap": paired_bootstrap(records, system, baseline),
    }
    print(f"resampling {len(records):,} Walmart records, {N_BOOT:,} draws\n")
    print(f"  system F1    {fmt(out['system'])}")
    print(f"  baseline F1  {fmt(out['baseline'])}")
    g = out["gap"]
    print(f"  gap          {g['point']:+.2f} [{g['lo']:+.2f}, {g['hi']:+.2f}]  "
          f"{'significant' if g['significant'] else 'within noise'}")

    bench = PROCESSED_DIR / "benchmark_predictions.csv"
    if bench.exists():
        d = pd.read_csv(bench)
        rows = list(zip(d["predicted"].astype(bool), d["label"].astype(int)))

        def bench_stat(sample):
            pred = np.array([bool(p) for p, _ in sample])
            lab = np.array([int(l) for _, l in sample])
            tp = int((pred & (lab == 1)).sum())
            if not pred.sum() or not (lab == 1).sum():
                return None
            return f1(tp, int(pred.sum()), int((lab == 1).sum()))

        out["benchmark"] = bootstrap(rows, bench_stat)
        print(f"\n  benchmark F1 {fmt(out['benchmark'])}  "
              f"({len(rows):,} pairs, the pair is the unit here)")
        for name, published in BENCHMARK_PUBLISHED.items():
            inside = contains(out["benchmark"], published)
            out.setdefault("benchmark_vs", {})[name] = {
                "published": published, "distinguishable": not inside}
            print(f"    vs {name:<12}{published:>6}  "
                  f"{'NOT distinguishable' if inside else 'distinguishable'}")
    else:
        print(f"\n  {bench.name} absent; benchmark interval skipped")

    (PROCESSED_DIR / "uncertainty.json").write_text(json.dumps(out, indent=2))
    print(f"\n  written to uncertainty.json")


if __name__ == "__main__":
    main()
