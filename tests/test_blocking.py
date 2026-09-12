"""Tests for the blocking rules.

Most tests here use small hand-built tables. These are *test fixtures* chosen
to exercise one rule at a time — they are not stand-in data for analysis, and
no measurement or reported figure comes from them. Every number quoted in
docs/DECISIONS.md is measured on the real tables.

Run with:  pytest
"""

import pandas as pd
import pytest

from src.blocking import (
    R4_NEIGHBOURS,
    build_index,
    candidates_by_rule,
    generate_candidates,
    is_identifier_like,
    record_text,
)

COLUMNS = ["title", "category", "brand", "modelno", "price"]


def make_table(rows: list[dict], prefix: str) -> pd.DataFrame:
    """Build a table shaped like the real one, with prefixed ids."""
    frame = pd.DataFrame(rows)
    for column in COLUMNS:
        if column not in frame:
            frame[column] = None
    frame.insert(0, "unique_id", [f"{prefix}_{i}" for i in range(len(frame))])
    return frame[["unique_id", *COLUMNS]]


# --- R2's identifier test -----------------------------------------------------

@pytest.mark.parametrize("token", ["ph3100u", "elplp12", "rkpw247015", "kvr400x64c3a"])
def test_part_numbers_are_recognised(token):
    assert is_identifier_like(token)


@pytest.mark.parametrize("token", ["black", "1080", "usb", "hd", "a1"])
def test_plain_words_and_bare_numbers_are_not(token):
    """Needs letters AND digits AND enough length — 'a1' is too short."""
    assert not is_identifier_like(token)


# --- pooling attributes -------------------------------------------------------

def test_record_text_pools_attributes_and_skips_missing():
    row = pd.Series({"title": "Widget XL", "category": None,
                     "brand": "Acme", "modelno": None, "price": "9.99"})
    text = record_text(row, COLUMNS)
    assert text == "widget xl acme 9.99"
    assert "nan" not in text, "missing values must not become the word 'nan'"


# --- R3: brand harvesting and the second-token requirement --------------------

def test_brand_is_recovered_from_the_title_when_the_column_is_blank():
    """The corruption blanked brand but usually left it in the title (D8)."""
    a = make_table([{"title": "acme widget xl", "brand": None}], "A")
    b = make_table([{"title": "widget", "brand": "acme"}], "B")
    index = build_index(a, b)
    assert index.a_brands["A_0"] == {"acme"}, "brand should be found inside the title"


def test_r3_needs_a_second_shared_word_beyond_the_brand():
    """Brand alone must not be enough — that block is far too broad."""
    a = make_table([{"title": "acme alpha", "brand": "acme"}], "A")
    b = make_table([
        {"title": "acme zeta", "brand": "acme"},    # brand only -> rejected
        {"title": "acme alpha", "brand": "acme"},   # brand + 'alpha' -> accepted
    ], "B")
    r3 = candidates_by_rule(build_index(a, b))["R3"]
    assert r3["A_0"] == {"B_1"}


# --- R4: the safety net -------------------------------------------------------

def test_r4_stays_silent_when_other_rules_already_found_something():
    a = make_table([{"title": "kvr400x64c3a memory"}], "A")
    b = make_table([{"title": "kvr400x64c3a memory"}], "B")
    by_rule = candidates_by_rule(build_index(a, b))
    assert by_rule["R2"]["A_0"], "R2 should have matched the part number"
    assert "A_0" not in by_rule["R4"], "R4 must not fire when another rule did"


def test_r4_rescues_a_record_nothing_else_reached():
    """A record with only common words gets nearest neighbours instead of nothing."""
    a = make_table([{"title": "zzzz plain ordinary thing"}], "A")
    b = make_table([{"title": "totally different article"} for _ in range(3)], "B")
    by_rule = candidates_by_rule(build_index(a, b))
    reached = set().union(*(by_rule[r]["A_0"] for r in ("R1", "R2", "R3", "R5")))
    if not reached:
        assert "A_0" in by_rule["R4"]


def test_r4_returns_at_most_the_configured_number_of_neighbours():
    a = make_table([{"title": "commonword"}], "A")
    b = make_table([{"title": "commonword"} for _ in range(R4_NEIGHBOURS + 25)], "B")
    r4 = candidates_by_rule(build_index(a, b))["R4"]
    assert len(r4.get("A_0", set())) <= R4_NEIGHBOURS


# --- whole-pipeline properties ------------------------------------------------

def test_every_walmart_record_gets_an_entry_and_only_valid_amazon_ids():
    a = make_table([{"title": "acme alpha widget"}, {"title": "zeta beta gadget"}], "A")
    b = make_table([{"title": "acme alpha widget"}, {"title": "unrelated"}], "B")
    candidates = generate_candidates(build_index(a, b))
    assert set(candidates) == {"A_0", "A_1"}
    valid = set(b["unique_id"])
    for hits in candidates.values():
        assert hits <= valid


def test_result_is_deterministic():
    """Same input must give the same candidates — no set-ordering surprises."""
    a = make_table([{"title": "acme alpha widget 2gb"}], "A")
    b = make_table([{"title": "acme alpha widget 2gb"}, {"title": "acme other"}], "B")
    first = generate_candidates(build_index(a, b))
    second = generate_candidates(build_index(a, b))
    assert first == second


def test_blocking_never_reads_labelled_data():
    """The rules must depend only on the source tables (D14)."""
    import inspect
    import src.blocking as blocking
    source = inspect.getsource(blocking)
    assert "load_labelled_pairs" not in source
    assert "train.csv" not in source and "valid.csv" not in source
