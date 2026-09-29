"""Tests for the bootstrap intervals.

No test makes a network call and none reads labelled data. The intervals are
seeded, because a confidence interval that moves between runs is not a
measurement (D47).

Run with:  pytest
"""

import numpy as np
import pytest

from src.uncertainty import (bootstrap, contains, f1, fmt, paired_bootstrap)


# --- f1 -----------------------------------------------------------------------

def test_f1_is_the_harmonic_mean_as_a_percentage():
    assert f1(50, 100, 100) == pytest.approx(50.0)
    assert f1(100, 100, 100) == pytest.approx(100.0)


def test_f1_is_zero_where_it_is_undefined_rather_than_nan():
    assert f1(0, 0, 10) == 0.0
    assert f1(0, 10, 0) == 0.0
    assert f1(0, 10, 10) == 0.0


# --- the interval -------------------------------------------------------------

def _mean(sample):
    return float(np.mean([float(x) for x in sample]))


def test_the_interval_brackets_the_point_estimate():
    r = bootstrap(list(range(100)), _mean, n_boot=300)
    assert r["lo"] < r["point"] < r["hi"]


def test_a_constant_sample_has_a_zero_width_interval():
    r = bootstrap([5.0] * 50, _mean, n_boot=100)
    assert r["lo"] == r["hi"] == pytest.approx(5.0)


def test_more_data_gives_a_narrower_interval():
    """The property that makes the interval mean anything."""
    rng = np.random.default_rng(0)
    small = bootstrap(list(rng.normal(size=50)), _mean, n_boot=400)
    large = bootstrap(list(rng.normal(size=5000)), _mean, n_boot=400)
    assert (large["hi"] - large["lo"]) < (small["hi"] - small["lo"])


def test_the_interval_is_reproducible():
    a = bootstrap(list(range(80)), _mean, n_boot=200)
    b = bootstrap(list(range(80)), _mean, n_boot=200)
    assert (a["lo"], a["hi"]) == (b["lo"], b["hi"])


def test_undefined_resamples_are_dropped_and_counted_not_zeroed():
    """Counting them as zero would drag the interval down silently."""
    calls = {"n": 0}

    def sometimes_none(sample):
        calls["n"] += 1
        return None if calls["n"] % 2 else _mean(sample)

    r = bootstrap(list(range(30)), sometimes_none, n_boot=100)
    assert r["dropped"] > 0 and r["n_boot"] + r["dropped"] == 100
    assert r["lo"] > 0, "zeroed resamples would have pulled this below the data"


def test_every_resample_undefined_raises_rather_than_returning_nonsense():
    with pytest.raises(ValueError):
        bootstrap([1, 2, 3], lambda s: None, n_boot=10)


# --- the paired interval ------------------------------------------------------

def test_a_consistent_small_difference_is_detected_when_paired():
    """Unpaired, this difference would vanish into the spread of either arm."""
    rng = np.random.default_rng(1)
    units = list(rng.normal(size=400))
    better = lambda s: _mean(s) + 0.05
    r = paired_bootstrap(units, better, _mean, n_boot=400)
    assert r["significant"] and r["lo"] > 0
    assert r["point"] == pytest.approx(0.05)
    assert r["favours_a"] == 1.0


def test_no_difference_is_reported_as_not_significant():
    rng = np.random.default_rng(2)
    units = list(rng.normal(size=200))
    r = paired_bootstrap(units, _mean, _mean, n_boot=200)
    assert not r["significant"] and r["point"] == pytest.approx(0.0)


# --- reading an interval ------------------------------------------------------

def test_a_published_figure_inside_the_interval_is_not_distinguishable():
    i = {"point": 51.38, "lo": 46.69, "hi": 56.10}
    assert contains(i, 53.80), "DeepMatcher's figure sits inside (D48)"
    assert not contains(i, 37.40) and not contains(i, 85.69)


def test_the_reported_form_carries_the_interval():
    assert fmt({"point": 61.47, "lo": 58.95, "hi": 64.09}) == "61.47 [58.95, 64.09]"
