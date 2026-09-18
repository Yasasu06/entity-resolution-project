"""Tests for the matcher.

The matcher is the module where a defect is least likely to announce itself: a
broken pair-key join, a transposed side, or a mis-wired comparison all still
produce a full column of plausible-looking probabilities. Nothing raises. These
tests therefore check the plumbing rather than the numbers - that the pairs
scored are exactly the pairs intended, that the sides are the right way round,
and that the model is assembled as designed.

Run with:  pytest
"""

import pandas as pd
import pytest
from splink import DuckDBAPI, Linker

from src.features import add_features
from src.interfaces import LEFT_ID, RIGHT_ID, validate_scores
from src.matcher import (
    AMAZON_ALIAS,
    ARRAY_COMPARISONS,
    PROBABILITY_TWO_RANDOM_RECORDS_MATCH,
    TRAINING_COLUMNS,
    WALMART_ALIAS,
    attach_pair_keys,
    build_settings,
    training_rule,
)
from tests.test_blocking import make_table


def candidates(pairs: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(pairs, columns=[LEFT_ID, RIGHT_ID])


# A token shared by enough records to exceed RARE_IDENTIFIER_MAX_DF, so that the
# common_identifier_tokens column is populated. Without it every value in that
# column is None, and DuckDB types an all-null column as INTEGER rather than a
# list, which makes list_intersect fail. The real tables never hit that - all
# five feature columns carry content on both sides - but a fixture easily can.
SPEC = "1080p"
FILLER = [{"title": f"{SPEC} filler device zz{i}qq", "brand": "acme"} for i in range(8)]


def padded(rows: list[dict], prefix: str) -> pd.DataFrame:
    """Build a table whose derived columns are all non-empty."""
    return make_table(rows + FILLER, prefix)


# --- attach_pair_keys: the known silent-failure surface ------------------------

def test_a_key_is_shared_only_by_the_two_records_in_a_pair():
    """The property the whole mechanism rests on."""
    a = make_table([{"title": "one"}, {"title": "two"}], "A")
    b = make_table([{"title": "three"}, {"title": "four"}], "B")
    a2, b2 = attach_pair_keys(a, b, candidates([("A_0", "B_1")]))

    left = dict(zip(a2["unique_id"], a2["pair_keys"]))
    right = dict(zip(b2["unique_id"], b2["pair_keys"]))
    assert left["A_0"] == ["A_0|B_1"]
    assert right["B_1"] == ["A_0|B_1"]
    # no other record carries that key
    assert left["A_1"] == [] and right["B_0"] == []


def test_records_in_no_candidate_pair_get_an_empty_list():
    """The bug this module already had once.

    An earlier version gave candidate-less records a shared placeholder value.
    Because two such records then held the *same* key, the explode joined them
    to each other and invented a pair that blocking never proposed. An empty
    list produces no join at all, which is the correct behaviour.
    """
    a = make_table([{"title": "stranded one"}, {"title": "paired"}], "A")
    b = make_table([{"title": "stranded two"}, {"title": "paired"}], "B")
    a2, b2 = attach_pair_keys(a, b, candidates([("A_1", "B_1")]))

    stranded_left = dict(zip(a2["unique_id"], a2["pair_keys"]))["A_0"]
    stranded_right = dict(zip(b2["unique_id"], b2["pair_keys"]))["B_0"]
    assert stranded_left == []
    assert stranded_right == []
    # and crucially, they share nothing with each other
    assert not (set(stranded_left) & set(stranded_right))


def test_two_stranded_records_are_never_scored_together():
    """The same bug, asserted end to end rather than on the column.

    This is the test that would have caught it: the earlier placeholder passed
    a column-shape check and only failed when the pairs were counted.
    """
    a = padded([{"title": "alpha widget kx9900z", "brand": "acme"},
                {"title": "shared item kx9900z", "brand": "acme"}], "A")
    b = padded([{"title": "beta gadget kx9900z", "brand": "acme"},
                {"title": "shared item kx9900z", "brand": "acme"}], "B")
    scored = _score(a, b, [("A_1", "B_1")])
    got = set(zip(scored[LEFT_ID], scored[RIGHT_ID]))
    assert got == {("A_1", "B_1")}
    assert ("A_0", "B_0") not in got, "stranded records must not be paired together"


def test_a_record_in_several_pairs_carries_every_key():
    a = make_table([{"title": "one"}], "A")
    b = make_table([{"title": "x"}, {"title": "y"}, {"title": "z"}], "B")
    a2, _ = attach_pair_keys(a, b, candidates([("A_0", "B_0"), ("A_0", "B_2")]))
    assert a2["pair_keys"][0] == ["A_0|B_0", "A_0|B_2"]


def test_source_tables_are_not_mutated():
    """attach_pair_keys copies; the caller's frames must be untouched."""
    a = make_table([{"title": "one"}], "A")
    b = make_table([{"title": "two"}], "B")
    attach_pair_keys(a, b, candidates([("A_0", "B_0")]))
    assert "pair_keys" not in a.columns
    assert "pair_keys" not in b.columns


# --- end-to-end scoring -------------------------------------------------------

def _score(a: pd.DataFrame, b: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """Score a tiny case through the real settings, without training.

    Untrained parameters make the probabilities meaningless, which is fine:
    these tests are about which pairs get scored and how they are shaped, not
    about the values.
    """
    a, b = add_features(a, b)
    a, b = attach_pair_keys(a, b, candidates(pairs))
    linker = Linker([a, b], build_settings(), DuckDBAPI(),
                    input_table_aliases=[WALMART_ALIAS, AMAZON_ALIAS])
    out = linker.inference.predict().as_pandas_dataframe()
    return out.rename(columns={"unique_id_l": LEFT_ID, "unique_id_r": RIGHT_ID})


def test_only_the_candidate_pairs_are_scored():
    """Three by three is nine possible pairs; only the two given may appear."""
    a = padded([{"title": f"walmart item {i} kx9900z", "brand": "acme"} for i in range(3)], "A")
    b = padded([{"title": f"amazon item {i} kx9900z", "brand": "acme"} for i in range(3)], "B")
    wanted = [("A_0", "B_0"), ("A_2", "B_1")]
    scored = _score(a, b, wanted)
    assert sorted(zip(scored[LEFT_ID], scored[RIGHT_ID])) == sorted(wanted)


def test_walmart_is_on_the_left():
    """Splink orders sides by alias; the aliases exist to make this hold.

    Getting this wrong transposes every pair in the output without any error,
    and would silently corrupt the join against the answer key.
    """
    a = padded([{"title": "walmart thing kx9900z", "brand": "acme"}], "A")
    b = padded([{"title": "amazon thing kx9900z", "brand": "acme"}], "B")
    a2, b2 = add_features(a, b)
    a2, b2 = attach_pair_keys(a2, b2, candidates([("A_0", "B_0")]))
    linker = Linker([a2, b2], build_settings(), DuckDBAPI(),
                    input_table_aliases=[WALMART_ALIAS, AMAZON_ALIAS])
    out = linker.inference.predict().as_pandas_dataframe()
    assert out["source_dataset_l"].iloc[0] == WALMART_ALIAS
    assert out["unique_id_l"].iloc[0].startswith("A_")
    assert out["unique_id_r"].iloc[0].startswith("B_")


def test_aliases_sort_walmart_first():
    """The mechanism behind the previous test, asserted directly."""
    assert WALMART_ALIAS < AMAZON_ALIAS


def test_identical_records_score_above_unrelated_ones():
    """The one behavioural check: more agreement must not score lower."""
    a = padded([{"title": "kingston datatraveler 8gb usb dtig3",
                 "brand": "kingston"}], "A")
    b = padded([
        {"title": "kingston datatraveler 8gb usb dtig3", "brand": "kingston"},
        {"title": "wooden garden bench slatted", "brand": "gardenco"},
    ], "B")
    scored = _score(a, b, [("A_0", "B_0"), ("A_0", "B_1")]).set_index(RIGHT_ID)
    assert (scored.loc["B_0", "match_probability"]
            > scored.loc["B_1", "match_probability"])


def test_output_satisfies_the_interface_contract():
    a = padded([{"title": "alpha kx9900z", "brand": "acme"},
                {"title": "beta kx9900z", "brand": "acme"}], "A")
    b = padded([{"title": "alpha kx9900z", "brand": "acme"},
                {"title": "gamma kx9900z", "brand": "acme"}], "B")
    pairs = [("A_0", "B_0"), ("A_1", "B_1")]
    scored = _score(a, b, pairs)
    validate_scores(scored[[LEFT_ID, RIGHT_ID, "match_probability"]], candidates(pairs))


def test_probabilities_stay_within_range():
    a = padded([{"title": "same words here kx9900z", "brand": "acme"},
                {"title": "nothing alike kx9900z", "brand": "acme"}], "A")
    b = padded([{"title": "same words here kx9900z", "brand": "acme"},
                {"title": "utterly different kx9900z", "brand": "acme"}], "B")
    scored = _score(a, b, [("A_0", "B_0"), ("A_1", "B_1")])
    assert scored["match_probability"].between(0, 1).all()


# --- model assembly -----------------------------------------------------------

def settings_dict() -> dict:
    return build_settings().create_settings_dict("duckdb")


def test_every_comparison_is_present_and_in_order():
    names = [c["output_column_name"] for c in settings_dict()["comparisons"]]
    assert names == ["title", *ARRAY_COMPARISONS, "price"]


def test_the_prior_is_the_documented_value():
    """Set from a label-free derivation; a silent change would contradict D25."""
    assert (settings_dict()["probability_two_random_records_match"]
            == PROBABILITY_TWO_RANDOM_RECORDS_MATCH == 2.0e-05)


def test_link_type_is_link_only():
    """These are two separate catalogues, not one table to deduplicate."""
    assert settings_dict()["link_type"] == "link_only"


def test_prediction_blocks_on_the_exploded_pair_key_column():
    rules = settings_dict()["blocking_rules_to_generate_predictions"]
    assert len(rules) == 1
    assert "pair_keys" in rules[0]["blocking_rule"]
    assert rules[0]["arrays_to_explode"] == ["pair_keys"], (
        "prediction relies on the explode to reproduce the candidate set"
    )


def test_training_rules_do_not_explode():
    """Expectation-maximisation rejects exploding rules; prediction accepts them.

    That asymmetry broke the first full run, so it is pinned here rather than
    rediscovered.
    """
    rule = training_rule("rare_tokens")
    assert rule.arrays_to_explode is None, "EM raises on exploding rules"
    assert "list_intersect" in rule.sql_condition


def test_every_comparison_is_estimable_in_some_training_session():
    """Blocking on a column makes it unestimable for that session.

    Each comparison therefore needs at least one session that leaves it free,
    or its parameters are never learned.
    """
    comparisons = [c.output_column_name
                   for c in build_settings().get_settings("duckdb").comparisons]
    for name in comparisons:
        free = [col for col in TRAINING_COLUMNS if col != name]
        assert free, f"{name} is blocked in every training session"


@pytest.mark.parametrize("column", TRAINING_COLUMNS)
def test_training_columns_are_real_comparison_columns(column):
    """A typo here would silently train on a column nothing compares."""
    assert column in ARRAY_COMPARISONS
