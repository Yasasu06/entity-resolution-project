"""Tests for the embedding step.

No test makes a network call. The ordering test exists because the failure it
guards is silent: an embedding attached to the wrong record produces a
plausible shortlist built from another product's meaning, with no error.

Run with:  pytest
"""

import numpy as np
import pandas as pd
import pytest

from src.embeddings import EMBED_DIMS, SHORTLIST, build_shortlists, embed_all, record_text
from src.interfaces import LEFT_ID, RIGHT_ID


class _Datum:
    def __init__(self, index, embedding):
        self.index, self.embedding = index, embedding


class _Client:
    """Returns one unit vector per input, in a chosen order."""

    def __init__(self, shuffle=False):
        self.shuffle = shuffle
        self.embeddings = self

    def create(self, model, input, dimensions):
        data = []
        for i, text in enumerate(input):
            v = np.zeros(dimensions, dtype=float)
            v[int(text)] = 1.0          # the text IS its own index, so mix-ups show
            data.append(_Datum(i, v.tolist()))
        if self.shuffle:
            data = data[::-1]
        return type("R", (), {"data": data})


# --- the ordering guarantee ---------------------------------------------------

def test_embeddings_follow_request_order_when_the_api_does():
    m = embed_all([str(i) for i in range(5)], _Client())
    assert [int(np.argmax(row)) for row in m] == [0, 1, 2, 3, 4]


def test_embeddings_are_reordered_when_the_api_returns_them_shuffled():
    """The bug this guards: response order is not promised to match input."""
    m = embed_all([str(i) for i in range(5)], _Client(shuffle=True))
    assert [int(np.argmax(row)) for row in m] == [0, 1, 2, 3, 4], \
        "each embedding must return to its own record"


def test_rows_are_unit_length():
    m = embed_all([str(i) for i in range(4)], _Client())
    assert np.allclose(np.linalg.norm(m, axis=1), 1.0)


# --- record text --------------------------------------------------------------

def test_record_text_skips_missing_attributes():
    row = pd.Series({"title": "a thing", "brand": None, "price": "9.99"})
    assert record_text(row, ["title", "brand", "price"]) == "title: a thing | price: 9.99"


def test_record_text_is_stable_in_column_order():
    row = pd.Series({"title": "x", "brand": "y"})
    assert record_text(row, ["title", "brand"]) != record_text(row, ["brand", "title"])


# --- shortlists ---------------------------------------------------------------

def _emb(vectors):
    m = np.asarray(vectors, dtype=float)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def test_the_shortlist_is_ordered_by_cosine_similarity():
    cands = pd.DataFrame({LEFT_ID: ["A_0"]*3, RIGHT_ID: ["B_0", "B_1", "B_2"]})
    a = _emb([[1.0, 0.0]])
    b = _emb([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])   # worst, middle, best
    out = build_shortlists(cands, ["A_0"], ["B_0", "B_1", "B_2"], a, b)
    assert out["A_0"] == ["B_2", "B_1", "B_0"]


def test_only_candidates_are_considered_never_the_whole_table():
    """This re-ranks the classical candidate set, it does not retrieve."""
    cands = pd.DataFrame({LEFT_ID: ["A_0"], RIGHT_ID: ["B_1"]})
    a = _emb([[1.0, 0.0]])
    b = _emb([[1.0, 0.0], [0.0, 1.0]])   # B_0 is a perfect match but not a candidate
    out = build_shortlists(cands, ["A_0"], ["B_0", "B_1"], a, b)
    assert out["A_0"] == ["B_1"]


def test_the_shortlist_is_capped():
    n = SHORTLIST + 15
    cands = pd.DataFrame({LEFT_ID: ["A_0"]*n, RIGHT_ID: [f"B_{i}" for i in range(n)]})
    a = _emb([[1.0, 0.0]])
    b = _emb([[1.0, i / n] for i in range(n)])
    out = build_shortlists(cands, ["A_0"], [f"B_{i}" for i in range(n)], a, b)
    assert len(out["A_0"]) == SHORTLIST


def test_every_record_with_candidates_gets_a_shortlist():
    cands = pd.DataFrame({LEFT_ID: ["A_0", "A_1"], RIGHT_ID: ["B_0", "B_1"]})
    e = _emb([[1.0, 0.0], [0.0, 1.0]])
    out = build_shortlists(cands, ["A_0", "A_1"], ["B_0", "B_1"], e, e)
    assert set(out) == {"A_0", "A_1"}
