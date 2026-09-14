"""Tests for the blocking/matching contract.

The contract exists so the classical and embedding systems stay swappable. Its
value is entirely in being enforced — a contract nothing checks is a comment.
These tests check that each violation it is meant to catch actually raises.

Run with:  pytest
"""

import pandas as pd
import pytest

from src.blocking import ClassicalBlocker, to_candidate_frame
from src.interfaces import (
    CANDIDATE_COLUMNS,
    LEFT_ID,
    RIGHT_ID,
    SCORE_COLUMNS,
    Blocker,
    Matcher,
    validate_candidates,
    validate_scores,
)
from tests.test_blocking import make_table


def tables():
    a = make_table([{"title": "acme alpha"}, {"title": "zeta beta"}], "A")
    b = make_table([{"title": "acme alpha"}, {"title": "zeta beta"}], "B")
    return a, b


def candidates(pairs):
    return pd.DataFrame(
        [(l, r, "R1") for l, r in pairs], columns=CANDIDATE_COLUMNS
    )


# --- the candidate contract ---------------------------------------------------

def test_a_well_formed_candidate_set_passes():
    a, b = tables()
    validate_candidates(candidates([("A_0", "B_0"), ("A_1", "B_1")]), a, b)


def test_missing_columns_are_rejected():
    a, b = tables()
    bad = pd.DataFrame([("A_0", "B_0")], columns=[LEFT_ID, RIGHT_ID])  # no 'rules'
    with pytest.raises(ValueError, match="missing required columns"):
        validate_candidates(bad, a, b)


def test_unknown_identifiers_are_rejected():
    """A typo'd or stale id would otherwise score against nothing, silently."""
    a, b = tables()
    with pytest.raises(ValueError, match="not in table A"):
        validate_candidates(candidates([("A_999", "B_0")]), a, b)
    with pytest.raises(ValueError, match="not in table B"):
        validate_candidates(candidates([("A_0", "B_999")]), a, b)


def test_sides_cannot_be_swapped():
    """Passing Amazon ids as the left side must fail rather than half-work."""
    a, b = tables()
    with pytest.raises(ValueError, match="not in table A"):
        validate_candidates(candidates([("B_0", "A_0")]), a, b)


def test_duplicate_pairs_are_rejected():
    """A duplicate would be scored twice and counted twice."""
    a, b = tables()
    with pytest.raises(ValueError, match="duplicate"):
        validate_candidates(candidates([("A_0", "B_0"), ("A_0", "B_0")]), a, b)


def test_empty_candidate_set_is_rejected():
    a, b = tables()
    with pytest.raises(ValueError, match="empty"):
        validate_candidates(candidates([]), a, b)


# --- the score contract -------------------------------------------------------

def scores(rows):
    return pd.DataFrame(rows, columns=SCORE_COLUMNS)


def test_a_well_formed_score_set_passes():
    cand = candidates([("A_0", "B_0"), ("A_1", "B_1")])
    validate_scores(scores([("A_0", "B_0", 0.9), ("A_1", "B_1", 0.1)]), cand)


def test_a_matcher_must_score_every_candidate():
    """Dropping pairs would look like precision but is actually missing work."""
    cand = candidates([("A_0", "B_0"), ("A_1", "B_1")])
    with pytest.raises(ValueError, match="did not score"):
        validate_scores(scores([("A_0", "B_0", 0.9)]), cand)


def test_a_matcher_may_not_invent_pairs():
    cand = candidates([("A_0", "B_0")])
    with pytest.raises(ValueError, match="invented"):
        validate_scores(
            scores([("A_0", "B_0", 0.9), ("A_1", "B_1", 0.5)]), cand
        )


@pytest.mark.parametrize("bad_probability", [-0.1, 1.5])
def test_probabilities_must_lie_between_zero_and_one(bad_probability):
    cand = candidates([("A_0", "B_0")])
    with pytest.raises(ValueError, match="between 0 and 1"):
        validate_scores(scores([("A_0", "B_0", bad_probability)]), cand)


def test_missing_probabilities_are_rejected():
    cand = candidates([("A_0", "B_0")])
    with pytest.raises(ValueError, match="missing values"):
        validate_scores(scores([("A_0", "B_0", None)]), cand)


# --- the classical blocker honours the contract -------------------------------

def test_classical_blocker_satisfies_the_protocol():
    """The swap test later depends on this being structurally true."""
    assert isinstance(ClassicalBlocker(), Blocker)
    assert not isinstance(ClassicalBlocker(), Matcher)


def test_classical_blocker_output_validates():
    a, b = tables()
    frame = ClassicalBlocker().generate_candidates(a, b)
    validate_candidates(frame, a, b)
    assert list(frame.columns) == CANDIDATE_COLUMNS


def test_provenance_records_every_rule_that_proposed_a_pair():
    """Which rules agreed is what makes a later disagreement explainable."""
    by_rule = {
        "R1": {"A_0": {"B_0"}},
        "R5": {"A_0": {"B_0"}},
        "R2": {"A_0": {"B_1"}},
    }
    frame = to_candidate_frame(by_rule).set_index([LEFT_ID, RIGHT_ID])
    assert frame.loc[("A_0", "B_0"), "rules"] == "R1+R5"
    assert frame.loc[("A_0", "B_1"), "rules"] == "R2"


def test_candidate_frame_is_sorted_for_reproducibility():
    """A stable order makes reruns byte-identical and diffs meaningful."""
    by_rule = {"R1": {"A_1": {"B_1"}, "A_0": {"B_2", "B_0"}}}
    frame = to_candidate_frame(by_rule)
    assert list(zip(frame[LEFT_ID], frame[RIGHT_ID])) == [
        ("A_0", "B_0"), ("A_0", "B_2"), ("A_1", "B_1"),
    ]
