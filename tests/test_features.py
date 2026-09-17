"""Tests for the derived comparison columns.

These pin the properties the matcher depends on: that evidence is gathered
from the whole record rather than from the column it nominally belongs to,
that rarity splits the identifier tokens as intended, and that the columns are
deterministic.

Run with:  pytest
"""

import pandas as pd

from src.features import (
    FEATURE_COLUMNS,
    RARE_IDENTIFIER_MAX_DF,
    add_features,
    is_identifier_shaped,
    pooled_document_frequency,
)
from tests.test_blocking import make_table


def test_identifier_shape_accepts_mixed_and_pure_numeric():
    """Matching accepts both forms; blocking's R2 accepts only the mixed one."""
    assert is_identifier_shaped("ph3100u")      # letters and digits
    assert is_identifier_shaped("1163641")      # all digits, long enough


def test_identifier_shape_rejects_short_and_wordlike():
    for token in ("usb", "a1", "black", "1080"):
        assert not is_identifier_shaped(token), token


def test_rarity_is_pooled_across_both_tables():
    """A token counted only within one table would look rare by accident."""
    a = make_table([{"title": "widget alpha"}], "A")
    b = make_table([{"title": "widget beta"}, {"title": "widget gamma"}], "B")
    freq = pooled_document_frequency(a, b)
    assert freq["widget"] == 3, "should count across both tables, not one"
    assert freq["alpha"] == 1


def test_evidence_is_gathered_from_anywhere_in_the_record():
    """The point of these columns: a value counts wherever the corruption left it."""
    in_column = make_table([{"title": "some widget", "modelno": "ph3100u"}], "A")
    in_title = make_table([{"title": "some widget ph3100u"}], "B")
    a, b = add_features(in_column, in_title)
    assert "ph3100u" in a["rare_identifier_tokens"][0]
    assert "ph3100u" in b["rare_identifier_tokens"][0], "must be found inside the title too"


def test_identifier_tokens_split_by_rarity():
    """A token in many records is a specification, not a part number."""
    common = [{"title": f"device {i} 1080p zz{i}kk"} for i in range(RARE_IDENTIFIER_MAX_DF + 3)]
    a = make_table([{"title": "device 1080p rr7788vv"}], "A")
    b = make_table(common, "B")
    a2, _ = add_features(a, b)
    assert "1080p" in a2["common_identifier_tokens"][0], "frequent -> common bucket"
    assert "rr7788vv" in a2["rare_identifier_tokens"][0], "infrequent -> rare bucket"
    assert "1080p" not in a2["rare_identifier_tokens"][0]


# --- absence must not be mistaken for disagreement ----------------------------

def test_absent_evidence_is_none_not_an_empty_list():
    """None becomes SQL NULL, which Splink scores as no evidence.

    An empty list is NOT null in SQL, so it would fall through to the final
    comparison level and collect the weight for *disagreement* - the opposite
    meaning. See docs/DECISIONS.md (D28).
    """
    a = make_table([{"title": "plain words only"}], "A")
    b = make_table([{"title": "other plain words"}], "B")
    a2, _ = add_features(a, b)
    assert a2["rare_identifier_tokens"][0] is None, "no identifiers -> None, not []"
    assert a2["common_identifier_tokens"][0] is None
    assert a2["brand_terms"][0] is None, "no brand terms -> None, not []"


def test_present_evidence_is_still_a_list():
    a = make_table([{"title": "acme widget ph3100u", "brand": "acme"}], "A")
    b = make_table([{"title": "acme widget ph3100u", "brand": "acme"}], "B")
    a2, _ = add_features(a, b)
    assert a2["rare_identifier_tokens"][0] == ["ph3100u"]
    assert isinstance(a2["brand_terms"][0], list)


def test_conflict_and_absence_are_distinguishable():
    """The distinction the fix exists to preserve.

    Two records with *different* brands disagree, and both sides stay non-empty
    so the comparison reaches the disagreement level. A record with *no* brand
    says nothing, and becomes null. These must not collapse into one case.
    """
    a = make_table([{"title": "sony camera", "brand": "sony"}], "A")
    b = make_table([
        {"title": "canon camera", "brand": "canon"},   # conflict
        {"title": "generic camera"},                   # absence
    ], "B")
    a2, b2 = add_features(a, b)

    # conflict: both sides carry brand terms, they simply do not overlap
    assert a2["brand_terms"][0] is not None
    assert b2["brand_terms"][0] is not None
    assert not (set(a2["brand_terms"][0]) & set(b2["brand_terms"][0]))

    # absence: nothing to say about brand at all
    assert b2["brand_terms"][1] is None


def test_title_tokens_are_none_only_when_a_title_has_no_words():
    a = make_table([{"title": "real words here"}, {"title": "---"}], "A")
    a2, _ = add_features(a, make_table([{"title": "other"}], "B"))
    assert a2["title_tokens"][0] is not None
    assert a2["title_tokens"][1] is None, "punctuation-only title has no tokens"


def test_all_feature_columns_are_added_to_both_tables():
    a, b = add_features(make_table([{"title": "acme alpha 2gb"}], "A"),
                        make_table([{"title": "acme beta 4gb"}], "B"))
    for frame in (a, b):
        for name in FEATURE_COLUMNS:
            assert name in frame.columns
            value = frame[name][0]
            assert value is None or isinstance(value, list)


def test_columns_are_sorted_and_deterministic():
    """Reproducible output keeps the pipeline diffable between runs."""
    tables = (make_table([{"title": "zeta alpha mike 9x8y7z"}], "A"),
              make_table([{"title": "zeta alpha mike"}], "B"))
    first_a, _ = add_features(*tables)
    second_a, _ = add_features(*tables)
    for name in FEATURE_COLUMNS:
        value = first_a[name][0]
        if value is not None:
            assert value == sorted(value), f"{name} must be sorted"
        assert value == second_a[name][0], f"{name} must be deterministic"


def test_original_columns_are_left_untouched():
    """Features are added; nothing about the source record is modified."""
    a_in = make_table([{"title": "acme alpha", "brand": "acme"}], "A")
    a_out, _ = add_features(a_in, make_table([{"title": "other"}], "B"))
    for column in a_in.columns:
        assert list(a_out[column]) == list(a_in[column])


def test_features_never_read_labelled_data():
    import inspect
    import src.features as features
    source = inspect.getsource(features)
    assert "load_labelled_pairs" not in source
    assert "unlock_final_evaluation" not in source
