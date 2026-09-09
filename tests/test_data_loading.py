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


def test_all_labelled_splits_are_sealed_by_default():
    """The strict no-peek policy must be enforced in code, not by memory.

    Every labelled split — train and valid as well as test — is off limits
    while the system is being designed. This is the guard that makes an
    accidental peek impossible rather than merely discouraged.
    """
    for split in ("train", "valid", "test"):
        with pytest.raises(ValueError, match="SEALED"):
            load_labelled_pairs(split)


def test_sealed_splits_open_only_with_explicit_unlock():
    """The final evaluation must still be possible — just never by accident."""
    pairs = load_labelled_pairs("train", unlock_final_evaluation=True)
    assert {"unique_id_l", "unique_id_r", "label"} == set(pairs.columns)
    assert len(pairs) > 0


def test_unlocked_pairs_reference_real_records():
    """When finally unlocked, pair ids must resolve against the source tables.

    Uses the explicit unlock, since verifying the id translation is a property
    of the loader rather than a peek at the answers.
    """
    table_a, table_b = load_source_tables()
    ids_a = set(table_a[ID_COLUMN])
    ids_b = set(table_b[ID_COLUMN])

    for split in ("train", "valid"):
        pairs = load_labelled_pairs(split, unlock_final_evaluation=True)
        assert set(pairs["unique_id_l"]).issubset(ids_a), f"{split}: unknown left ids"
        assert set(pairs["unique_id_r"]).issubset(ids_b), f"{split}: unknown right ids"
        assert set(pairs["label"].unique()).issubset({0, 1})


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
