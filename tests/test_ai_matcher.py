"""Tests for the AI matcher.

No test makes a network call. The shuffle path is pinned because it failed
silently once: the record is indexed by unique_id, so the id is the Series name
rather than a column, and only the reordered prompts raised.

Run with:  pytest
"""

import pandas as pd
import pytest

from src.ai_matcher import ORDERINGS, PROMPT, Judgement, render


def record(rid="A_1"):
    return pd.Series({"title": "maxell couleur ear buds purple 190238",
                      "brand": "maxell", "modelno": None,
                      "price": "16.18", "category": "headphones"}, name=rid)


def candidates(n=4):
    return pd.DataFrame([
        {"unique_id": f"B_{i}", "title": f"candidate product {i}", "brand": "acme",
         "modelno": f"m{i}", "price": f"{10+i}.00", "category": "headphones"}
        for i in range(n)])


def test_a_reordered_prompt_renders_without_raising():
    """The id lives on the Series name, not in a column."""
    for order in ORDERINGS:
        assert "maxell" in render(record(), candidates(), ["title", "brand"], order)


def test_reordering_actually_changes_the_prompt():
    plain = render(record(), candidates(8), ["title"], "")
    assert any(render(record(), candidates(8), ["title"], o) != plain
               for o in ORDERINGS if o)


def test_the_same_order_is_reproducible():
    a = render(record(), candidates(8), ["title"], "#b")
    b = render(record(), candidates(8), ["title"], "#b")
    assert a == b


def test_different_records_shuffle_differently():
    a = render(record("A_1"), candidates(8), ["title"], "#b")
    b = render(record("A_2"), candidates(8), ["title"], "#b")
    assert a.replace("A_2", "A_1") != a or b != a


def test_every_candidate_survives_a_reorder():
    out = render(record(), candidates(6), ["title"], "#c")
    for i in range(6):
        assert f"B_{i}" in out


def test_the_prompt_asks_for_the_distinguishing_attribute_first():
    """D37: no rule over token sets can see the token that decides identity,
    so the model is pointed at it explicitly."""
    out = render(record(), candidates(), ["title"], "")
    assert "distinguishing_attribute" in out
    assert out.index("name the attribute") < out.index("Then decide")


def test_no_classical_score_reaches_the_prompt():
    """Ranking is by embedding similarity; match weight must not leak in."""
    out = render(record(), candidates(), ["title", "brand", "price"], "")
    for leaked in ("bits", "match_probability", "match weight"):
        assert leaked not in out


def test_all_three_outcomes_are_offered():
    out = render(record(), candidates(), ["title"], "")
    for o in ("match", "none_of_these", "cannot_tell"):
        assert o in out


def test_the_judgement_key_ignores_the_id_unless_it_matched():
    assert Judgement("none_of_these", "B_9", "").key() == ("none_of_these", None)
    assert Judgement("match", "B_9", "").key() == ("match", "B_9")
