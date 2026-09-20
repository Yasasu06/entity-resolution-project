"""Tests for the review queue.

The queue is an artefact a person acts on, so its failures are quiet ones: a
mislabelled truncation or a tie shown in score order looks perfectly normal and
misleads the reviewer rather than raising. These tests pin the properties the
decisions actually turn on - that the top tie group is never cut, that every
truncation is disclosed, that tied candidates are not in score order, and that
a record contributes at most one accepted pair.

Run with:  pytest
"""

import numpy as np
import pandas as pd
import pytest

from src.interfaces import LEFT_ID, RIGHT_ID
from src.review_queue import (
    ACCEPT,
    REVIEW_QUANTITY,
    apply_quantity_veto,
    ACCEPT_BITS,
    DIFFERENT,
    DISPLAY_TIE_BITS,
    EXTRA_CANDIDATES,
    FLOOR_BITS,
    MARGIN_BITS,
    REVIEW_OUTCOMES,
    REVIEW_TIED,
    REVIEW_UNSURE,
    _shuffled,
    assign_outcomes,
    build_review_items,
    match_weight,
    rank_candidates,
    tie_groups,
)
from tests.test_blocking import make_table


def scores_from_bits(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """Build a score table from bits, inverting the weight to a probability."""
    bits = np.array([b for _, _, b in rows], dtype=float)
    return pd.DataFrame({
        LEFT_ID: [l for l, _, _ in rows],
        RIGHT_ID: [r for _, r, _ in rows],
        "match_probability": 1 / (1 + 2.0**-bits),
        "bits": bits,
    })


# --- the bits conversion ------------------------------------------------------

def test_match_weight_round_trips():
    """Even odds is 0 bits; 2:1 odds is 1 bit; the thresholds land where stated."""
    p = pd.Series([0.5, 2 / 3, 0.984615, 0.081210])
    assert match_weight(p).tolist() == pytest.approx([0.0, 1.0, 6.0, -3.5], abs=1e-3)


def test_match_weight_survives_the_extremes():
    """Probabilities of exactly 0 or 1 must not produce infinities."""
    assert np.isfinite(match_weight(pd.Series([0.0, 1.0]))).all()


# --- outcome assignment -------------------------------------------------------

def test_the_four_outcomes_are_assigned_at_the_documented_boundaries():
    s = scores_from_bits([
        ("A_0", "B_0", 8.0), ("A_0", "B_1", 2.0),        # clear winner -> accept
        ("A_1", "B_0", 8.0), ("A_1", "B_1", 7.5),        # within margin -> tied
        ("A_2", "B_0", 3.0), ("A_2", "B_1", -1.0),       # below accept -> unsure
        ("A_3", "B_0", -9.0), ("A_3", "B_1", -12.0),     # below floor -> different
    ])
    out = assign_outcomes(rank_candidates(s))
    assert out.loc["A_0", "outcome"] == ACCEPT
    assert out.loc["A_1", "outcome"] == REVIEW_TIED
    assert out.loc["A_2", "outcome"] == REVIEW_UNSURE
    assert out.loc["A_3", "outcome"] == DIFFERENT


def test_a_record_exactly_on_the_accept_threshold_is_accepted():
    """The rule is 'at or above', so the boundary belongs to accept."""
    s = scores_from_bits([("A_0", "B_0", ACCEPT_BITS), ("A_0", "B_1", -5.0)])
    assert assign_outcomes(rank_candidates(s)).loc["A_0", "outcome"] == ACCEPT


def test_a_margin_exactly_at_the_threshold_is_a_tie():
    """The rule requires the margin to *exceed* MARGIN_BITS, not equal it."""
    s = scores_from_bits([("A_0", "B_0", 8.0), ("A_0", "B_1", 8.0 - MARGIN_BITS)])
    assert assign_outcomes(rank_candidates(s)).loc["A_0", "outcome"] == REVIEW_TIED


def test_a_record_exactly_on_the_floor_is_reviewed_not_discarded():
    s = scores_from_bits([("A_0", "B_0", FLOOR_BITS), ("A_0", "B_1", -20.0)])
    assert assign_outcomes(rank_candidates(s)).loc["A_0", "outcome"] == REVIEW_UNSURE


def test_a_single_candidate_cannot_be_tied():
    """With no runner-up the margin is infinite, so a strong single candidate
    is accepted rather than being treated as ambiguous."""
    s = scores_from_bits([("A_0", "B_0", 9.0)])
    out = assign_outcomes(rank_candidates(s))
    assert np.isinf(out.loc["A_0", "margin_bits"])
    assert out.loc["A_0", "outcome"] == ACCEPT


def test_each_record_yields_at_most_one_accepted_pair():
    """The one-to-one constraint, which carried most of the measured gain."""
    s = scores_from_bits([("A_0", "B_0", 9.0), ("A_0", "B_1", 8.9),
                          ("A_0", "B_2", 1.0), ("A_1", "B_3", 12.0)])
    out = assign_outcomes(rank_candidates(s))
    assert len(out) == 2, "one row per record, not per pair"
    assert out.loc["A_0", "outcome"] == REVIEW_TIED   # 0.1 bits apart


# --- tie grouping -------------------------------------------------------------

def test_candidates_within_the_epsilon_form_one_group():
    assert tie_groups([10.0, 10.0 - DISPLAY_TIE_BITS / 2, 5.0]) == [0, 0, 1]


def test_grouping_is_against_the_leader_not_the_previous_member():
    """Otherwise a chain of small steps collapses into a single false group.

    Each step here is inside the epsilon, but the last value is far below the
    first and must not be presented as tied with it.
    """
    step = DISPLAY_TIE_BITS * 0.9
    chain = [10.0 - i * step for i in range(6)]
    groups = tie_groups(chain)
    assert groups[0] == 0
    assert groups[-1] > 0, "a long chain must not become one group"


def test_a_single_candidate_is_its_own_group():
    assert tie_groups([3.0]) == [0]


# --- the seeded shuffle -------------------------------------------------------

def test_the_shuffle_is_deterministic_for_a_record():
    items = list(range(20))
    assert _shuffled(items, "A_7") == _shuffled(items, "A_7")


def test_different_records_get_different_orders():
    items = list(range(30))
    orders = {tuple(_shuffled(items, f"A_{i}")) for i in range(12)}
    assert len(orders) > 1, "every record receiving one order defeats the purpose"


def test_the_shuffle_does_not_leave_input_order_intact():
    """Score order would track Amazon table position, which is the bias D32
    exists to break. A stable 'shuffle' would silently reintroduce it."""
    items = list(range(40))
    assert any(_shuffled(items, f"A_{i}") != items for i in range(8))


def test_the_shuffle_preserves_membership():
    items = list(range(25))
    assert sorted(_shuffled(items, "A_3")) == items


# --- the assembled review items -----------------------------------------------

def _items(rows, n_amazon=30):
    a = make_table([{"title": f"walmart {i}"} for i in range(4)], "A")
    b = make_table([{"title": f"amazon {i}"} for i in range(n_amazon)], "B")
    ranked = rank_candidates(scores_from_bits(rows))
    return build_review_items(ranked, assign_outcomes(ranked), a, b)


def test_only_records_needing_review_become_items():
    rows = [("A_0", "B_0", 9.0), ("A_0", "B_1", 1.0),      # accept
            ("A_1", "B_2", 3.0), ("A_1", "B_3", 1.0),      # unsure
            ("A_2", "B_4", -9.0)]                          # different
    assert [i["walmart_id"] for i in _items(rows)] == ["A_1"]


def test_the_top_tie_group_is_never_truncated():
    """The guarantee D33 rests on: it holds by construction, at any group size."""
    rows = [("A_0", f"B_{i}", 7.0) for i in range(25)]
    item = _items(rows)[0]
    top = item["candidate_blocks"][0]
    assert top["tied"] and top["shown"] == 25 and not top["truncated"]


def test_a_truncated_group_is_labelled_with_its_true_size():
    """An unlabelled truncation is an arbitrary subset of an unordered set."""
    rows = [("A_0", "B_0", 3.0)] + [("A_0", f"B_{i}", 1.0) for i in range(1, 26)]
    blocks = _items(rows)[0]["candidate_blocks"]
    lower = blocks[1]
    assert lower["truncated"]
    assert lower["shown"] == EXTRA_CANDIDATES
    assert lower["true_size"] == 25


def test_no_more_than_the_extra_allowance_follows_the_top_group():
    # every candidate stays above the floor, so the allowance is what binds
    rows = [("A_0", "B_0", 3.0)] + [("A_0", f"B_{i}", 1.0 - i * 0.1) for i in range(1, 26)]
    item = _items(rows)[0]
    beyond = sum(b["shown"] for b in item["candidate_blocks"][1:])
    assert beyond == EXTRA_CANDIDATES


def test_candidates_below_the_floor_are_never_shown():
    rows = [("A_0", "B_0", 3.0), ("A_0", "B_1", FLOOR_BITS - 0.1), ("A_0", "B_2", -20.0)]
    shown = {m["amazon_id"] for b in _items(rows)[0]["candidate_blocks"] for m in b["members"]}
    assert shown == {"B_0"}


def test_a_tied_block_is_not_in_score_order_when_large_enough():
    """Tied members carry no order; emitting them sorted would imply one."""
    rows = [("A_0", f"B_{i}", 3.0) for i in range(20)]
    members = _items(rows)[0]["candidate_blocks"][0]["members"]
    assert [m["amazon_id"] for m in members] != [f"B_{i}" for i in range(20)]


def test_every_item_offers_none_of_these():
    """Some records have no correct partner; forcing a choice invents errors."""
    rows = [("A_0", "B_0", 3.0), ("A_0", "B_1", 2.0)]
    item = _items(rows)[0]
    assert "none_of_these" in item["allowed_outcomes"] == REVIEW_OUTCOMES
    assert item["decision"] is None, "a fresh item must carry no decision"


def test_the_item_records_why_it_needs_review():
    rows = [("A_0", "B_0", 9.0), ("A_0", "B_1", 8.9),     # tied at the top
            ("A_1", "B_2", 3.0), ("A_1", "B_3", -1.0)]    # merely unsure
    reasons = {i["walmart_id"]: i["reason"] for i in _items(rows)}
    assert reasons == {"A_0": REVIEW_TIED, "A_1": REVIEW_UNSURE}


# --- the quantity veto, wired in ----------------------------------------------

def test_a_quantity_conflict_is_refused_auto_acceptance():
    """The matcher cannot see 512MB against 32GB; the veto can (D37)."""
    a = make_table([{"title": "edge proshot 512mb compact flash card"}], "A")
    b = make_table([{"title": "edge proshot 32gb compact flash card"}], "B")
    s = scores_from_bits([("A_0", "B_0", 12.0)])
    outcomes = assign_outcomes(rank_candidates(s))
    assert outcomes.loc["A_0", "outcome"] == ACCEPT      # accepted on score alone
    vetoed = apply_quantity_veto(outcomes, a, b)
    assert vetoed.loc["A_0", "outcome"] == REVIEW_QUANTITY


def test_matching_quantities_are_left_accepted():
    a = make_table([{"title": "edge proshot 32gb compact flash card"}], "A")
    b = make_table([{"title": "edge proshot 32 gb compactflash memory card"}], "B")
    s = scores_from_bits([("A_0", "B_0", 12.0)])
    out = apply_quantity_veto(assign_outcomes(rank_candidates(s)), a, b)
    assert out.loc["A_0", "outcome"] == ACCEPT


def test_the_veto_never_touches_records_that_were_not_accepted():
    """It refuses acceptance; it cannot promote or reclassify anything else."""
    a = make_table([{"title": "widget 512mb"}], "A")
    b = make_table([{"title": "widget 32gb"}], "B")
    s = scores_from_bits([("A_0", "B_0", 1.0)])          # below the accept bar
    out = apply_quantity_veto(assign_outcomes(rank_candidates(s)), a, b)
    assert out.loc["A_0", "outcome"] == REVIEW_UNSURE


def test_a_silent_record_is_not_a_conflict():
    """Absence of a stated quantity is not disagreement (D28)."""
    a = make_table([{"title": "edge proshot 32gb card"}], "A")
    b = make_table([{"title": "edge proshot memory card"}], "B")
    s = scores_from_bits([("A_0", "B_0", 12.0)])
    out = apply_quantity_veto(assign_outcomes(rank_candidates(s)), a, b)
    assert out.loc["A_0", "outcome"] == ACCEPT
