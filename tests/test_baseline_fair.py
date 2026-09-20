"""Tests for the comparable baseline.

Every label here is invented. The module takes truth as an argument and never
opens a labelled file, so the whole thing is testable before the seal lifts.

Run with:  pytest
"""

import pandas as pd
import pytest

from src.baseline_fair import (
    THRESHOLD,
    decide,
    evaluate,
    precision_recall_curve,
    score_candidates,
)
from src.interfaces import LEFT_ID, RIGHT_ID
from tests.test_blocking import make_table


def candidates(pairs):
    return pd.DataFrame(pairs, columns=[LEFT_ID, RIGHT_ID])


# --- scoring ------------------------------------------------------------------

def test_identical_records_score_one():
    a = make_table([{"title": "kingston datatraveler 8gb"}], "A")
    b = make_table([{"title": "kingston datatraveler 8gb"}], "B")
    assert score_candidates(candidates([("A_0", "B_0")]), a, b).iloc[0] == 1.0


def test_unrelated_records_score_low():
    a = make_table([{"title": "wooden garden bench"}], "A")
    b = make_table([{"title": "kingston usb flash drive"}], "B")
    assert score_candidates(candidates([("A_0", "B_0")]), a, b).iloc[0] == 0.0


# --- the decision rule --------------------------------------------------------

def _setup():
    a = make_table([{"title": "alpha beta gamma"}, {"title": "delta epsilon"}], "A")
    b = make_table([{"title": "alpha beta gamma"},      # perfect for A_0
                    {"title": "alpha beta zeta"},       # close for A_0
                    {"title": "totally unrelated"}], "B")
    c = candidates([("A_0", "B_0"), ("A_0", "B_1"), ("A_1", "B_2")])
    return a, b, c, score_candidates(c, a, b)


def test_only_the_best_candidate_per_record_is_kept():
    """The one-to-one constraint, mirroring the system's."""
    a, b, c, s = _setup()
    out = decide(c, s, threshold=0.1)
    assert out[LEFT_ID].tolist() == ["A_0"] or set(out[LEFT_ID]) <= {"A_0", "A_1"}
    assert out[out[LEFT_ID] == "A_0"][RIGHT_ID].tolist() == ["B_0"]
    assert out[LEFT_ID].is_unique


def test_a_record_below_the_threshold_is_not_accepted():
    a, b, c, s = _setup()
    assert "A_1" not in set(decide(c, s, threshold=0.9)[LEFT_ID])


def test_raising_the_threshold_never_accepts_more():
    a, b, c, s = _setup()
    assert len(decide(c, s, 0.9)) <= len(decide(c, s, 0.1))


def test_the_pre_registered_threshold_is_the_default():
    assert THRESHOLD == 0.34


# --- evaluation, with invented labels -----------------------------------------

def test_a_correct_acceptance_is_a_true_positive():
    acc = pd.DataFrame({LEFT_ID: ["A_0"], RIGHT_ID: ["B_0"], "similarity": [0.9]})
    r = evaluate(acc, {"A_0": {"B_0"}}, {"A_0"})
    assert r["true_positives"] == 1 and r["precision"] == 1.0 and r["recall"] == 1.0


def test_the_wrong_partner_is_a_false_positive_and_a_miss():
    acc = pd.DataFrame({LEFT_ID: ["A_0"], RIGHT_ID: ["B_1"], "similarity": [0.9]})
    r = evaluate(acc, {"A_0": {"B_0"}}, {"A_0"})
    assert r["false_positives"] == 1 and r["false_negatives"] == 1
    assert r["precision"] == 0.0


def test_a_record_the_baseline_declined_still_counts_against_recall():
    """Otherwise abstaining would look like precision for free."""
    acc = pd.DataFrame({LEFT_ID: [], RIGHT_ID: [], "similarity": []})
    r = evaluate(acc, {"A_0": {"B_0"}, "A_1": {"B_1"}}, {"A_0", "A_1"})
    assert r["false_negatives"] == 2 and r["recall"] == 0.0


def test_a_record_with_no_true_partner_does_not_inflate_recall():
    acc = pd.DataFrame({LEFT_ID: ["A_0"], RIGHT_ID: ["B_0"], "similarity": [0.9]})
    r = evaluate(acc, {"A_0": {"B_0"}, "A_1": set()}, {"A_0", "A_1"})
    assert r["recall"] == 1.0


def test_the_curve_spans_thresholds_and_is_monotone_in_acceptance():
    a, b, c, s = _setup()
    curve = precision_recall_curve(c, s, {"A_0": {"B_0"}}, {"A_0", "A_1"}, steps=10)
    assert len(curve) == 9
    accepted = [r["accepted"] for r in curve]
    assert accepted == sorted(accepted, reverse=True)
