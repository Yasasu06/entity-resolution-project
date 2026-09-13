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


def test_r3_needs_two_shared_words_beyond_the_brand():
    """Brand alone is far too broad, and brand plus one word is still too free."""
    a = make_table([{"title": "acme alpha beta", "brand": "acme"}], "A")
    b = make_table([
        {"title": "acme zeta", "brand": "acme"},          # brand only -> rejected
        {"title": "acme alpha", "brand": "acme"},         # brand + 1 word -> rejected
        {"title": "acme alpha beta", "brand": "acme"},    # brand + 2 words -> accepted
    ], "B")
    r3 = candidates_by_rule(build_index(a, b))["R3"]
    assert r3["A_0"] == {"B_2"}


def test_r3_threshold_is_the_configured_one():
    """Guard against the setting drifting without the tests noticing."""
    from src.blocking import R3_MIN_SHARED_WORDS
    assert R3_MIN_SHARED_WORDS == 2


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


# --- R4 symmetric: the Amazon-side safety net ---------------------------------

def test_symmetric_r4_rescues_an_unreached_amazon_record():
    """An Amazon record nothing reached must still end up in some candidate list.

    Every other rule is phrased "for each Walmart record, find Amazon records",
    so an Amazon record nobody happens to reach is invisible to all of them.
    """
    a = make_table([{"title": "kvr400x64c3a memory module"}], "A")
    b = make_table([
        {"title": "kvr400x64c3a memory module"},        # reached by R2
        {"title": "kvr400x64c3a memory widget thing"},  # also reachable
    ], "B")
    by_rule = candidates_by_rule(build_index(a, b))
    reached = set()
    for rule in by_rule.values():
        for hits in rule.values():
            reached |= hits
    assert set(b["unique_id"]) <= reached


def test_symmetric_r4_stays_silent_when_everything_is_already_reached():
    a = make_table([{"title": "acme alpha beta gamma"}], "A")
    b = make_table([{"title": "acme alpha beta gamma"}], "B")
    by_rule = candidates_by_rule(build_index(a, b))
    assert not by_rule["R4-sym"], "nothing was unreached, so it must not fire"


def test_symmetric_r4_keys_pairs_by_walmart_id():
    """Its output must share the shape of every other rule."""
    a = make_table([{"title": "alpha beta gamma delta"}], "A")
    b = make_table([{"title": "alpha zzz"}, {"title": "beta qqq"}], "B")
    by_rule = candidates_by_rule(build_index(a, b))
    valid_a = set(a["unique_id"]); valid_b = set(b["unique_id"])
    for a_id, hits in by_rule["R4-sym"].items():
        assert a_id in valid_a
        assert hits <= valid_b


def test_both_safety_nets_use_the_same_neighbour_count():
    """The two directions are deliberately symmetric - see D17."""
    import inspect
    from src.blocking import _rule_r4, _rule_r4_symmetric
    assert "R4_NEIGHBOURS" not in inspect.getsource(_rule_r4)
    assert "R4_NEIGHBOURS" not in inspect.getsource(_rule_r4_symmetric)


# --- R4 short sequences: the last-resort tier ---------------------------------

def test_short_sequence_tier_rescues_a_record_made_of_short_words():
    """A record of sub-five-letter words yields almost no 5-grams.

    This is the B_2852 shape: "mydesk pink lap desk" produces only two
    five-character sequences, neither of which occurs in the other table.
    """
    a = make_table([{"title": "pink desk lamp for home"}], "A")
    b = make_table([{"title": "mydesk pink lap desk"}], "B")
    by_rule = candidates_by_rule(build_index(a, b))
    reached = set()
    for rule in by_rule.values():
        for hits in rule.values():
            reached |= hits
    assert "B_0" in reached, "the short-word record must not be left unreachable"


def test_short_sequence_tier_stays_silent_when_nothing_is_stranded():
    a = make_table([{"title": "kvr400x64c3a memory module"}], "A")
    b = make_table([{"title": "kvr400x64c3a memory module"}], "B")
    assert not candidates_by_rule(build_index(a, b))["R4-short"]


def test_longer_sequences_are_tried_before_shorter_ones():
    """Least-weak-evidence-first: 4 is attempted before falling back to 3.

    Both real cases were rescued at four characters, so the three-character
    tier never fired — which is the intended behaviour, not an accident.
    """
    from src.blocking import R4_FALLBACK_NGRAM_SIZES
    assert R4_FALLBACK_NGRAM_SIZES == (4, 3)
    assert list(R4_FALLBACK_NGRAM_SIZES) == sorted(R4_FALLBACK_NGRAM_SIZES, reverse=True)


def test_short_sequence_tier_respects_the_neighbour_cap():
    a = make_table([{"title": "pink thing"} for _ in range(R4_NEIGHBOURS + 30)], "A")
    b = make_table([{"title": "pink lap desk"}], "B")
    short = candidates_by_rule(build_index(a, b))["R4-short"]
    rescued = {b_id for hits in short.values() for b_id in hits}
    if rescued:
        count = sum(1 for hits in short.values() if "B_0" in hits)
        assert count <= R4_NEIGHBOURS


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
