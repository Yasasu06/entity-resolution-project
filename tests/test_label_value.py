"""Tests for the label-value experiment (pre-registration section 13).

No test makes a network call and none builds a Splink model. These cover the
parts that decide whether the experiment means anything: that EM's m values are
genuinely removed, that the label budget is counted honestly, and that the
annotator's ranking never sees a label.

The budget test exists because the first run of this experiment got it wrong.
It selected the threshold on all 6,144 training labels while reporting a budget
of twelve, which inflated every point on the curve.

Run with:  pytest
"""

import numpy as np
import pandas as pd
import pytest

from src.interfaces import LEFT_ID, RIGHT_ID
from src.label_value import (acquisition_order, best_threshold, budget_for,
                             f1_at, strip_m)


def _model():
    return {"comparisons": [
        {"output_column_name": "title", "comparison_levels": [
            {"label_for_charts": "Null", "u_probability": None},
            {"label_for_charts": "Exact", "m_probability": 0.4, "u_probability": 1e-7},
            {"label_for_charts": "Else", "m_probability": 0.6, "u_probability": 0.99}]}]}


def test_every_m_is_removed_and_every_u_kept():
    """Left in place, EM's m would make a 'k=40' model part EM (section 13.2)."""
    levels = strip_m(_model())["comparisons"][0]["comparison_levels"]
    assert all("m_probability" not in lv for lv in levels)
    assert [lv.get("u_probability") for lv in levels] == [None, 1e-7, 0.99]


def test_stripping_does_not_mutate_the_original():
    model = _model()
    strip_m(model)
    assert model["comparisons"][0]["comparison_levels"][1]["m_probability"] == 0.4


def _train(labels, bits):
    return (pd.DataFrame({LEFT_ID: [f"A_{i}" for i in range(len(labels))],
                          RIGHT_ID: [f"B_{i}" for i in range(len(labels))],
                          "label": labels}),
            pd.Series(bits, dtype=float))


def test_the_queue_is_ordered_by_score_not_by_label():
    """Ordering by label would be the annotator seeing the answers."""
    train, bits = _train([0, 1, 0, 1], [9.0, 1.0, 8.0, 2.0])
    order = acquisition_order(train, bits)
    assert order["label"].tolist() == [0, 0, 1, 1]
    assert order["bits"].tolist() == [9.0, 8.0, 2.0, 1.0]


def test_confirmed_counts_matches_found_so_far():
    train, bits = _train([1, 0, 1], [9.0, 8.0, 7.0])
    assert acquisition_order(train, bits)["confirmed"].tolist() == [1, 1, 2]


def test_the_budget_counts_every_pair_inspected_not_just_the_matches():
    train, bits = _train([1, 0, 0, 1], [9.0, 8.0, 7.0, 6.0])
    matches, seen, spent = budget_for(acquisition_order(train, bits), 2)
    assert len(matches) == 2
    assert spent == 4, "four pairs were seen to confirm two matches"


def test_the_inspected_set_is_returned_so_the_threshold_can_be_charged_for():
    """The error this guards: tuning on all of train while reporting twelve."""
    train, bits = _train([1, 0, 0, 1], [9.0, 8.0, 7.0, 6.0])
    _, seen, spent = budget_for(acquisition_order(train, bits), 2)
    assert len(seen) == spent == 4
    assert set(seen["label"]) == {0, 1}, "negatives are paid for and usable too"


def test_no_labels_are_spent_at_k_zero():
    train, bits = _train([1, 0], [9.0, 8.0])
    matches, seen, spent = budget_for(acquisition_order(train, bits), 0)
    assert len(matches) == 0 and len(seen) == 0 and spent == 0


def test_asking_for_more_matches_than_exist_spends_the_whole_pool():
    train, bits = _train([1, 0, 1], [9.0, 8.0, 7.0])
    matches, seen, spent = budget_for(acquisition_order(train, bits), 99)
    assert len(matches) == 2 and spent == 3 and len(seen) == 3


def test_the_threshold_separates_a_separable_sample():
    bits = np.array([-5.0, -4.0, 6.0, 7.0])
    labels = np.array([0, 0, 1, 1])
    assert f1_at(bits, labels, best_threshold(bits, labels)) == pytest.approx(100.0)


def test_f1_is_zero_when_nothing_is_predicted():
    assert f1_at(np.array([1.0, 2.0]), np.array([1, 1]), 99.0) == 0.0


def test_the_threshold_is_chosen_on_the_data_given_not_a_fixed_6_bits():
    """Supervised m shifts every weight, so 6.0 is the wrong point (D44)."""
    bits = np.array([20.0, 21.0, 30.0, 31.0])
    labels = np.array([0, 0, 1, 1])
    assert best_threshold(bits, labels) > 21.0
