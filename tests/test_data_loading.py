"""Tests for the canonical data loader.

These guard the properties that would cause silent, hard-to-spot wrongness if
they ever broke — the kind of bug that produces plausible-looking output rather
than an error message.

Run them with:  pytest
"""

import pandas as pd
import pytest

from src.data_loading import (
    ID_COLUMN,
    attribute_columns,
    load_labelled_pairs,
    load_source_tables,
)


def test_identifiers_do_not_collide_across_tables():
    """The whole reason the loader exists: A_0 and B_0 must stay distinct.

    Both raw files number their rows from 0. Without prefixing, record 0 from
    one table and record 0 from the other would be indistinguishable, and
    matching results would be quietly meaningless.
    """
    table_a, table_b = load_source_tables()
    overlap = set(table_a[ID_COLUMN]) & set(table_b[ID_COLUMN])
    assert not overlap, f"identifiers collide across tables: {sorted(overlap)[:5]}"


def test_identifiers_are_prefixed_and_unique():
    table_a, table_b = load_source_tables()

    assert table_a[ID_COLUMN].str.startswith("A_").all()
    assert table_b[ID_COLUMN].str.startswith("B_").all()

    assert table_a[ID_COLUMN].is_unique
    assert table_b[ID_COLUMN].is_unique


def test_raw_id_column_is_removed():
    """Keeping both 'id' and 'unique_id' would invite using the wrong one."""
    table_a, table_b = load_source_tables()
    assert "id" not in table_a.columns
    assert "id" not in table_b.columns


def test_both_tables_share_a_schema():
    """Field-to-field comparison later depends on this holding."""
    table_a, table_b = load_source_tables()
    assert list(table_a.columns) == list(table_b.columns)
    assert attribute_columns(table_a) == ["title", "category", "brand", "modelno", "price"]


def test_values_are_preserved_as_text():
    """Numeric-looking values must not be silently reinterpreted.

    If pandas parsed these as numbers, a model number like '0012' would become
    12 and stop matching its counterpart in the other table.
    """
    table_a, _ = load_source_tables()
    non_null_prices = table_a["price"].dropna()
    assert non_null_prices.map(type).eq(str).all()


def test_labelled_pairs_reference_real_records():
    """Every labelled pair must point at records that actually exist.

    A mismatch here would mean the id translation is wrong — pairs would
    silently score against nothing.
    """
    table_a, table_b = load_source_tables()
    ids_a = set(table_a[ID_COLUMN])
    ids_b = set(table_b[ID_COLUMN])

    for split in ("train", "valid"):
        pairs = load_labelled_pairs(split)
        assert set(pairs["unique_id_l"]).issubset(ids_a), f"{split}: unknown left ids"
        assert set(pairs["unique_id_r"]).issubset(ids_b), f"{split}: unknown right ids"


def test_labels_are_binary():
    for split in ("train", "valid"):
        labels = load_labelled_pairs(split)["label"]
        assert set(labels.unique()).issubset({0, 1})


def test_split_sizes_match_the_published_benchmark():
    """Verify against the benchmark's published figures rather than trusting.

    Walmart-Amazon_2 ships 10,242 pairs with 962 matches in total, split
    6,144 / 2,049 / 2,049. Since 'test' is sealed we check the two splits we
    are allowed to touch, and confirm the remainder adds up.
    """
    train = load_labelled_pairs("train")
    valid = load_labelled_pairs("valid")

    assert (len(train), int(train["label"].sum())) == (6144, 576)
    assert (len(valid), int(valid["label"].sum())) == (2049, 193)

    # Whatever is left must account for the published totals exactly.
    assert 10242 - len(train) - len(valid) == 2049
    assert 962 - int(train["label"].sum()) - int(valid["label"].sum()) == 193


def test_test_split_is_sealed_by_default():
    """The sealed split must be blocked unless explicitly unlocked.

    This is the guard that stops the final honest evaluation from being
    accidentally spent during development.
    """
    with pytest.raises(ValueError, match="sealed"):
        load_labelled_pairs("test")


def test_unknown_split_is_rejected():
    with pytest.raises(ValueError, match="Unknown split"):
        load_labelled_pairs("nonexistent")


def test_source_tables_have_expected_shape():
    """Row counts from the benchmark, verified earlier against its publication."""
    table_a, table_b = load_source_tables()
    assert len(table_a) == 2554
    assert len(table_b) == 22074


def test_missing_values_are_real_nulls():
    """Empty cells must be NaN, not the string 'nan' or 'NA'."""
    table_a, _ = load_source_tables()
    assert table_a["brand"].isna().any()
    assert not (table_a["brand"].dropna() == "nan").any()
    assert pd.notna(table_a["title"]).all(), "title is never missing in this dataset"
