"""Tests for the discarded-pairs diagnostics.

These check that the summary is internally consistent and honest — that the
counts add up, that the sampled taxonomy really only looks at discarded pairs,
and that nothing here reaches for labelled data.

Run with:  pytest
"""

import pandas as pd

from src.blocking import build_index, generate_candidates
from src.blocking_diagnostics import collect
from tests.test_blocking import COLUMNS, make_table


def small_setup():
    a = make_table([
        {"title": "acme alpha widget 2gb", "brand": "acme"},
        {"title": "zeta beta gadget kvr400x64c3a", "brand": "zeta"},
    ], "A")
    b = make_table([
        {"title": "acme alpha widget 2gb", "brand": "acme"},
        {"title": "completely unrelated article here"},
        {"title": "zeta beta gadget kvr400x64c3a", "brand": "zeta"},
        {"title": "another thing entirely different"},
    ], "B")
    index = build_index(a, b)
    return index, generate_candidates(index)


def test_headline_counts_add_up():
    """kept + discarded must equal the full cross product, exactly."""
    index, candidates = small_setup()
    h = collect(index, candidates)["headline"]
    assert h["candidate_pairs"] + h["discarded_pairs"] == h["possible_pairs"]
    assert h["possible_pairs"] == h["walmart_records"] * h["amazon_records"]


def test_reduction_ratio_matches_the_counts():
    index, candidates = small_setup()
    h = collect(index, candidates)["headline"]
    expected = 1 - h["candidate_pairs"] / h["possible_pairs"]
    assert abs(h["reduction_ratio"] - expected) < 1e-6


def test_taxonomy_shares_sum_to_one():
    """Buckets are mutually exclusive, so their shares must account for all of it."""
    index, candidates = small_setup()
    sample = collect(index, candidates)["discarded_sample"]
    if sample["sample_size"]:
        total = sum(c["count"] for c in sample["categories"].values())
        assert total == sample["sample_size"]
        assert abs(sum(c["share"] for c in sample["categories"].values()) - 1.0) < 0.01


def test_no_kept_pair_is_ever_counted_as_discarded():
    """The sampler must reject pairs that blocking actually kept.

    If it did not, the taxonomy would describe the wrong population entirely.
    """
    index, candidates = small_setup()
    report = collect(index, candidates)
    # Every kept pair is excluded by construction, so a dataset where
    # everything is kept must yield an empty sample.
    everything = {a: set(index.b_tokens) for a in index.a_tokens}
    empty = collect(index, everything)["discarded_sample"]
    assert empty["sample_size"] == 0
    assert report["discarded_sample"]["sample_size"] > 0


def test_part_number_bucket_stays_empty():
    """R2 accepts a shared part number at any frequency.

    So a discarded pair sharing one would mean a rule is not doing what it
    claims. The bucket exists to catch exactly that, and must stay empty.
    """
    index, candidates = small_setup()
    categories = collect(index, candidates)["discarded_sample"]["categories"]
    assert "UNEXPECTED_shared_part_number" not in categories


def test_near_miss_counts_are_non_negative():
    index, candidates = small_setup()
    for value in collect(index, candidates)["near_misses"].values():
        assert value >= 0


def test_report_is_deterministic():
    """A fixed seed means the sampled figures must not drift between runs."""
    index, candidates = small_setup()
    assert collect(index, candidates) == collect(index, candidates)


def test_diagnostics_never_read_labelled_data():
    import inspect
    import src.blocking_diagnostics as diagnostics
    source = inspect.getsource(diagnostics)
    assert "load_labelled_pairs" not in source
    assert "unlock_final_evaluation" not in source
