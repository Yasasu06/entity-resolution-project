"""Tests for the modelled human reviewer.

Every label here is invented in the test. The module takes truth as an argument
and never opens a labelled file, which is what makes it testable at all before
the seal is lifted.

Run with:  pytest
"""

import pytest

from src.human_simulation import (
    ACCURACIES,
    MATCH,
    NONE_OF_THESE,
    correct_outcome,
    display_ceiling,
    displayed_candidates,
    is_reachable,
    score,
    simulate,
    sweep,
)


def item(record_id="A_0", shown=("B_0", "B_1", "B_2")):
    return {
        "walmart_id": record_id,
        "candidate_blocks": [{
            "tied": len(shown) > 1,
            "members": [{"amazon_id": s, "title": f"t{s}"} for s in shown],
            "shown": len(shown), "true_size": len(shown), "truncated": False,
        }],
    }


# --- what a perfect reviewer can and cannot do --------------------------------

def test_the_displayed_candidates_are_read_from_every_block():
    it = item(shown=("B_0",))
    it["candidate_blocks"].append(
        {"tied": False, "members": [{"amazon_id": "B_9"}], "shown": 1,
         "true_size": 1, "truncated": False})
    assert displayed_candidates(it) == ["B_0", "B_9"]


def test_a_perfect_reviewer_picks_the_true_partner_when_it_is_shown():
    assert correct_outcome(item(), {"A_0": {"B_1"}}) == (MATCH, "B_1")


def test_none_of_these_is_correct_when_no_partner_exists():
    assert correct_outcome(item(), {"A_0": set()}) == (NONE_OF_THESE, None)


def test_a_truncated_away_partner_forces_a_wrong_answer():
    """The display ceiling: the reviewer answers correctly for what is on
    screen, and the answer key still scores it wrong."""
    it = item(shown=("B_0", "B_1"))
    truth = {"A_0": {"B_99"}}                 # the real partner was cut
    assert correct_outcome(it, truth) == (NONE_OF_THESE, None)
    assert not is_reachable(it, truth)


def test_a_record_with_no_true_partner_is_still_reachable():
    """'None of these' is answerable, so such records do not cap the ceiling."""
    assert is_reachable(item(), {"A_0": set()})


def test_the_ceiling_counts_records_whose_partner_is_off_screen():
    items = [item("A_0", ("B_0",)), item("A_1", ("B_5",)), item("A_2", ("B_9",))]
    truth = {"A_0": {"B_0"}, "A_1": {"B_77"}, "A_2": set()}
    c = display_ceiling(items, truth)
    assert c == {"items": 3, "reachable": 2, "unreachable": 1, "ceiling": pytest.approx(2/3)}


# --- the reviewer model -------------------------------------------------------

def test_a_perfect_reviewer_is_right_on_everything_reachable():
    items = [item(f"A_{i}") for i in range(30)]
    truth = {f"A_{i}": {"B_1"} for i in range(30)}
    assert score(simulate(items, truth, 1.00), truth)["accuracy"] == 1.0


def test_a_less_accurate_reviewer_does_worse():
    items = [item(f"A_{i}") for i in range(400)]
    truth = {f"A_{i}": {"B_1"} for i in range(400)}
    good = score(simulate(items, truth, 0.95, seed=1), truth)["accuracy"]
    poor = score(simulate(items, truth, 0.80, seed=1), truth)["accuracy"]
    assert good > poor


def test_the_simulation_is_reproducible_for_a_seed():
    items = [item(f"A_{i}") for i in range(50)]
    truth = {f"A_{i}": {"B_2"} for i in range(50)}
    assert simulate(items, truth, 0.8, seed=7) == simulate(items, truth, 0.8, seed=7)


def test_a_different_seed_gives_a_different_draw():
    items = [item(f"A_{i}") for i in range(80)]
    truth = {f"A_{i}": {"B_2"} for i in range(80)}
    assert simulate(items, truth, 0.8, seed=1) != simulate(items, truth, 0.8, seed=2)


def test_errors_can_land_on_none_of_these_as_well_as_a_candidate():
    """The error model is uniform over the displayed candidates *and* the
    'none of these' option, not over candidates alone."""
    items = [item(f"A_{i}") for i in range(300)]
    truth = {f"A_{i}": {"B_0"} for i in range(300)}
    kinds = {d[0] for d in simulate(items, truth, 0.0, seed=3).values()}
    assert kinds == {MATCH, NONE_OF_THESE}


def test_errors_are_not_weighted_towards_any_candidate():
    """Uniform choice keeps the arm independent of the classical system, which
    a score-weighted error model would not."""
    items = [item(f"A_{i}", ("B_0", "B_1", "B_2")) for i in range(900)]
    truth = {f"A_{i}": {"B_9"} for i in range(900)}      # never correct
    picked = [d[1] for d in simulate(items, truth, 0.0, seed=5).values()]
    counts = [picked.count(c) for c in ("B_0", "B_1", "B_2", None)]
    assert min(counts) > 0.5 * max(counts), counts       # roughly even


# --- scoring ------------------------------------------------------------------

def test_scoring_counts_a_wrong_partner_as_both_a_false_positive_and_a_miss():
    s = score({"A_0": (MATCH, "B_1")}, {"A_0": {"B_2"}})
    assert s["false_positives"] == 1 and s["false_negatives"] == 1
    assert s["true_positives"] == 0


def test_a_correct_abstention_counts_as_accurate_but_not_a_true_positive():
    s = score({"A_0": (NONE_OF_THESE, None)}, {"A_0": set()})
    assert s["accuracy"] == 1.0 and s["true_positives"] == 0


def test_a_missed_partner_is_a_false_negative():
    s = score({"A_0": (NONE_OF_THESE, None)}, {"A_0": {"B_1"}})
    assert s["false_negatives"] == 1 and s["accuracy"] == 0.0


def test_the_sweep_covers_the_declared_range_and_reports_the_ceiling():
    items = [item(f"A_{i}") for i in range(20)]
    truth = {f"A_{i}": {"B_1"} for i in range(20)}
    out = sweep(items, truth)
    assert tuple(out["by_accuracy"]) == ACCURACIES
    assert out["display_ceiling"]["ceiling"] == 1.0
