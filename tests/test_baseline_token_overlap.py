"""Tests for the token-overlap baseline.

The baseline exists to give the real system a number to beat, so a defect in it
is not harmless: an accidentally weak baseline would flatter the real system,
and an accidentally strong one would understate it. Neither would raise.

The most important test here is not about scoring at all. It is that the module
**does not read labelled data unless explicitly unlocked** — the guard standing
between this project and an accidental peek (D14). Nothing in this file opens a
labelled split; where labels are needed they are invented in the test.

Run with:  pytest
"""

import pandas as pd
import pytest

import src.baseline_token_overlap as baseline
from src.baseline_token_overlap import (
    choose_threshold,
    evaluate,
    jaccard,
    record_tokens,
    score_pairs,
    tokenise,
)


# --- the seal -----------------------------------------------------------------

def test_the_baseline_does_not_read_labels_unless_unlocked(monkeypatch, capsys):
    """The guard that keeps the no-peek policy honest.

    Without the flag the module must decline to run and must not touch a
    labelled split. Monkeypatching the loader to raise means any attempt to
    read one fails the test rather than quietly succeeding.
    """
    def refuse(*args, **kwargs):
        raise AssertionError("labelled data was read without unlocking")

    monkeypatch.setattr(baseline, "load_labelled_pairs", refuse)
    monkeypatch.setattr(baseline, "load_source_tables", refuse)

    baseline.main()  # no flag

    out = capsys.readouterr().out
    assert "SEALED" in out
    assert "did not run" in out


def test_the_superseded_result_is_not_presented_as_live(capsys):
    """D9's F1 = 0.381 was voided by D14; the module must say so, not report it."""
    baseline.main()
    out = capsys.readouterr().out
    assert "SUPERSEDED" in out
    assert "0.381" in out, "the old number is kept as history, clearly marked"


# --- tokenising ---------------------------------------------------------------

def test_tokenise_lowercases_and_splits_on_punctuation():
    assert tokenise("Kingston DataTraveler 8GB, USB-3.0") == {
        "kingston", "datatraveler", "8gb", "usb", "3", "0"}


def test_tokenise_returns_a_set_so_repeats_do_not_count():
    assert tokenise("blue blue blue widget") == {"blue", "widget"}


def test_tokenise_of_empty_text_is_empty():
    assert tokenise("") == set()


def test_missing_attributes_do_not_become_the_token_nan():
    """A literal "nan" token would be shared by every incomplete record, making
    unrelated products look similar to each other."""
    table = pd.DataFrame({
        "unique_id": ["A_0"],
        "title": ["wooden bench"],
        "brand": [None],
        "modelno": [float("nan")],
        "price": [None],
        "category": [None],
    })
    assert record_tokens(table)["A_0"] == {"wooden", "bench"}


def test_record_tokens_combines_every_attribute():
    table = pd.DataFrame({
        "unique_id": ["A_0"],
        "title": ["widget"], "brand": ["acme"], "modelno": ["xy900"],
        "price": ["12.50"], "category": ["tools"],
    })
    assert record_tokens(table)["A_0"] == {
        "widget", "acme", "xy900", "12", "50", "tools"}


# --- the similarity -----------------------------------------------------------

def test_jaccard_of_identical_sets_is_one():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_of_disjoint_sets_is_zero():
    assert jaccard({"a"}, {"b"}) == 0.0


def test_jaccard_is_intersection_over_union():
    # shared: a, b   union: a, b, c, d, e
    assert jaccard({"a", "b", "c"}, {"a", "b", "d", "e"}) == pytest.approx(2 / 5)


def test_jaccard_is_symmetric():
    left, right = {"a", "b", "c"}, {"b", "c", "d"}
    assert jaccard(left, right) == jaccard(right, left)


def test_jaccard_of_two_empty_sets_is_zero_not_undefined():
    """Both records having no usable text is not evidence that they match."""
    assert jaccard(set(), set()) == 0.0


def test_score_pairs_looks_each_record_up_by_id():
    tokens_a = pd.Series([{"a", "b"}, {"z"}], index=["A_0", "A_1"])
    tokens_b = pd.Series([{"a", "b"}, {"q"}], index=["B_0", "B_1"])
    pairs = pd.DataFrame({"unique_id_l": ["A_0", "A_1"], "unique_id_r": ["B_0", "B_1"]})
    assert score_pairs(pairs, tokens_a, tokens_b).tolist() == [1.0, 0.0]


# --- the metrics --------------------------------------------------------------

def test_evaluate_on_a_hand_worked_example():
    #            scores: 0.9  0.8  0.2  0.1
    #            labels:   1    0    1    0      threshold 0.5
    # predicted match: the first two -> tp=1, fp=1, fn=1
    labels = pd.Series([1, 0, 1, 0])
    scores = pd.Series([0.9, 0.8, 0.2, 0.1])
    r = evaluate(labels, scores, 0.5)
    assert (r["true_positives"], r["false_positives"], r["false_negatives"]) == (1, 1, 1)
    assert r["precision"] == pytest.approx(0.5)
    assert r["recall"] == pytest.approx(0.5)
    assert r["f1"] == pytest.approx(0.5)


def test_a_threshold_nothing_reaches_scores_zero_rather_than_dividing_by_zero():
    r = evaluate(pd.Series([1, 0]), pd.Series([0.1, 0.2]), 0.9)
    assert r["precision"] == 0.0 and r["recall"] == 0.0 and r["f1"] == 0.0


def test_perfect_separation_scores_one():
    labels = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.9, 0.8, 0.1, 0.0])
    r = evaluate(labels, scores, 0.5)
    assert r["precision"] == 1.0 and r["recall"] == 1.0 and r["f1"] == 1.0


def test_the_threshold_boundary_is_inclusive():
    """'>= threshold' - a pair scoring exactly the threshold is a match."""
    r = evaluate(pd.Series([1]), pd.Series([0.5]), 0.5)
    assert r["true_positives"] == 1


def test_choose_threshold_finds_the_separating_point():
    labels = pd.Series([1, 1, 0, 0])
    scores = pd.Series([0.80, 0.70, 0.30, 0.20])
    best = choose_threshold(labels, scores)
    assert best["f1"] == 1.0
    assert 0.30 < best["threshold"] <= 0.70


def test_choose_threshold_reports_the_threshold_it_picked():
    labels = pd.Series([1, 0])
    scores = pd.Series([0.6, 0.1])
    best = choose_threshold(labels, scores)
    assert evaluate(labels, scores, best["threshold"])["f1"] == best["f1"]
