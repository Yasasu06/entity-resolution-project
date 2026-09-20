"""Tests for the quantity veto.

The veto exists to catch a failure the matcher cannot see: a near-miss differing
only in a capacity or a dimension. Its value depends entirely on firing when
values genuinely conflict and staying silent otherwise, so both directions are
pinned here.

Run with:  pytest
"""

import pandas as pd
import pytest

from src.quantity_veto import conflicts, quantities, record_quantities


# --- extraction ---------------------------------------------------------------

def test_storage_is_normalised_across_units():
    """1tb and 1024gb are the same quantity and must not look like a conflict."""
    assert quantities("1tb drive")["storage"] == quantities("1024gb drive")["storage"]


def test_a_capacity_is_found_with_or_without_a_space():
    assert quantities("32gb card")["storage"] == quantities("32 gb card")["storage"]


def test_several_quantities_in_one_text_are_all_kept():
    gb = 1024.0 ** 2          # the family's base unit is kb
    assert quantities("16gb and 32gb bundle")["storage"] == {16 * gb, 32 * gb}


def test_length_and_power_are_separate_families():
    q = quantities("20 inch 750w monitor")
    assert q["length"] == {20.0} and q["power"] == {750.0}


def test_text_with_no_quantity_yields_nothing():
    assert quantities("wooden garden bench") == {}


def test_a_unit_inside_a_word_is_not_a_quantity():
    """'in' must not match the 'in' of 'wireless in-ear'."""
    assert "length" not in quantities("3 inline connectors")


def test_quantities_are_read_from_every_attribute_not_just_the_title():
    row = pd.Series({"title": "memory card", "brand": "edge",
                     "modelno": "pe-512mb-x", "price": None, "category": None})
    assert record_quantities(row, ["title", "brand", "modelno", "price", "category"]) \
        == {"storage": {512 * 1024.0}}


# --- the veto decision --------------------------------------------------------

def test_different_capacities_conflict():
    assert conflicts(quantities("512mb card"), quantities("32gb card"))


def test_the_same_capacity_does_not_conflict():
    assert not conflicts(quantities("32gb card"), quantities("32 gb memory card"))


def test_equivalent_units_do_not_conflict():
    assert not conflicts(quantities("1tb drive"), quantities("1024gb drive"))


def test_silence_is_never_a_conflict():
    """Absence of evidence is not evidence of disagreement (D28)."""
    assert not conflicts(quantities("32gb card"), quantities("memory card"))
    assert not conflicts({}, {})


def test_a_shared_value_among_several_is_not_a_conflict():
    """A bundle listing one of the same capacities is not a contradiction."""
    assert not conflicts(quantities("16gb and 32gb"), quantities("32gb"))


def test_families_are_compared_independently():
    """Matching capacity but differing size is still a conflict."""
    assert conflicts(quantities("32gb 20 inch"), quantities("32gb 24 inch"))


def test_a_conflict_in_any_family_is_enough():
    assert conflicts(quantities("750w"), quantities("500w"))


def test_different_families_never_interact():
    """20 inches and 20 watts are not the same quantity, but nor do they clash."""
    assert not conflicts(quantities("20 inch"), quantities("20w"))
