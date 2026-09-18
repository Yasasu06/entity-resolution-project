"""Tests for the Splink comparisons.

The title comparison is custom SQL, so these check it computes what it claims
and sorts pairs into the intended levels. The SQL is exercised through DuckDB
rather than re-implemented in Python, so a change to the expression is caught
rather than mirrored.

Run with:  pytest
"""

import duckdb
import pytest

from src.comparisons import (
    PRICE_CLOSE,
    PRICE_LOOSE,
    PRICE_TIGHT,
    price_comparison,
    relative_price_difference_sql,
    TITLE_HIGH,
    TITLE_LOW,
    TITLE_MEDIUM,
    title_comparison,
    word_jaccard_sql,
)

def jaccard(left: list[str], right: list[str]):
    """Evaluate the real comparison expression against two token lists.

    Uses ``word_jaccard_sql`` rather than a copy of the SQL, so that changing
    the expression breaks these tests instead of silently diverging from them.
    """
    con = duckdb.connect()
    expression = word_jaccard_sql("l", "r")
    return con.execute(
        f"SELECT {expression} FROM (SELECT ? AS l, ? AS r)", [left, right]
    ).fetchone()[0]


# --- the similarity expression ------------------------------------------------

def test_identical_token_sets_score_one():
    assert jaccard(["a", "b", "c"], ["a", "b", "c"]) == 1.0


def test_disjoint_token_sets_score_zero():
    assert jaccard(["a", "b"], ["c", "d"]) == 0.0


def test_partial_overlap_is_normalised_by_the_union():
    # 2 shared of 4 distinct
    assert jaccard(["a", "b", "c"], ["b", "c", "d"]) == pytest.approx(0.5)


def test_word_order_does_not_matter():
    """Retailers reorder freely, so the measure must be order-independent."""
    assert jaccard(["sling", "pack", "sumdex"], ["sumdex", "pack", "sling"]) == 1.0


def test_length_does_not_inflate_similarity():
    """The failure mode ArrayIntersectAtSizes has: raw counts favour long titles.

    Both pairs share two words. The verbose pair must not score higher.
    """
    short = jaccard(["a", "b"], ["a", "b"])
    verbose = jaccard(["a", "b"] + [f"x{i}" for i in range(20)],
                      ["a", "b"] + [f"y{i}" for i in range(20)])
    assert verbose < short
    assert verbose == pytest.approx(2 / 42)


def test_empty_token_sets_yield_null_not_an_error():
    """Guarded by NULLIF so the null level catches it instead of dividing by zero."""
    assert jaccard([], []) is None


def test_one_side_empty_scores_zero():
    assert jaccard(["a", "b"], []) == 0.0


# --- the comparison structure -------------------------------------------------

def test_levels_are_ordered_and_complete():
    levels = title_comparison().get_comparison("duckdb").comparison_levels
    labels = [l.label_for_charts for l in levels]
    assert labels[0] == "Null"
    assert labels[1] == "Exact token-set match"
    assert labels[-1].startswith(f"Jaccard < {TITLE_LOW}")
    assert len(levels) == 6, "null + exact + three bands + catch-all"


def test_thresholds_descend():
    """Splink evaluates levels in order, so they must go strongest first."""
    assert TITLE_HIGH > TITLE_MEDIUM > TITLE_LOW


def test_first_level_is_flagged_as_null():
    """A null comparison must contribute no evidence, not count as disagreement."""
    levels = title_comparison().get_comparison("duckdb").comparison_levels
    assert levels[0].is_null_level


def test_comparison_uses_double_precision():
    """Single precision moved pairs sitting on a threshold into the wrong level."""
    import inspect
    import src.comparisons as comparisons
    assert "::DOUBLE" in inspect.getsource(comparisons)
    assert "::FLOAT" not in inspect.getsource(comparisons)


# --- price -------------------------------------------------------------------

def price_difference(left, right):
    """Evaluate the real price expression, not a copy of it."""
    con = duckdb.connect()
    expression = relative_price_difference_sql("l", "r")
    return con.execute(
        f"SELECT {expression} FROM (SELECT ?::DOUBLE AS l, ?::DOUBLE AS r)",
        [left, right],
    ).fetchone()[0]


def test_identical_prices_are_zero_apart():
    assert price_difference(49.99, 49.99) == 0.0


def test_difference_is_relative_not_absolute():
    """Five pounds means something different on a cable and a television."""
    cable = price_difference(10.0, 15.0)       # 5 apart on a small price
    television = price_difference(1000.0, 1005.0)  # 5 apart on a large one
    assert cable > television
    assert cable == pytest.approx(1 / 3)


def test_measure_is_symmetric():
    """Argument order must not change the answer."""
    assert price_difference(40.0, 50.0) == price_difference(50.0, 40.0)


def test_difference_stays_within_zero_and_one():
    for a, b in ((1.0, 1000.0), (1000.0, 1.0), (5.0, 5.01)):
        value = price_difference(a, b)
        assert 0.0 <= value <= 1.0


def test_missing_price_yields_null():
    """A pair without two usable prices must contribute nothing."""
    assert price_difference(None, 20.0) is None
    assert price_difference(20.0, None) is None


def test_price_thresholds_ascend():
    assert PRICE_TIGHT < PRICE_CLOSE < PRICE_LOOSE


def test_price_levels_are_ordered_with_a_null_level_first():
    levels = price_comparison().get_comparison("duckdb").comparison_levels
    assert levels[0].is_null_level
    assert [l.label_for_charts for l in levels][1] == "Exact match"
    assert len(levels) == 6


def test_zero_and_negative_prices_are_treated_as_missing():
    """A zero price reads as absent data, not as a free product (D28, D30)."""
    from src.features import parse_price
    assert parse_price(0) is None
    assert parse_price(-5) is None
    assert parse_price("not a price") is None
    assert parse_price(None) is None
    assert parse_price("19.99") == 19.99
