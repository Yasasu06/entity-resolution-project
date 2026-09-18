"""The classical matcher: scoring candidate pairs with Splink.

Blocking produced 564,450 candidate pairs. This module scores each one,
producing a calibrated probability that the two records describe the same
product. Deciding what to do with those probabilities - accept, reject, or
abstain and route for review - happens later and is deliberately separate.

The model is **unsupervised**. Splink learns how much each kind of agreement is
worth from the data itself, using expectation-maximisation, without ever seeing
a labelled pair. That is a requirement of this project rather than a
convenience: see docs/DECISIONS.md (D6, D14).

Three things are worth knowing before reading the code.

**Candidates are injected through a pair-key column.** Splink normally
generates pairs from its own blocking rules, but this project's blocking is too
specific to express that way and a pair it failed to reproduce could never be
matched. Instead every record carries a list of the pair-keys it belongs to.
Two records share a key only if they are a candidate pair, so exploding that
list reproduces the candidate set exactly. See D22.

**Training blocks are separate from the prediction block.** Each EM session
blocks on one derived column, which fixes that column at agreement and makes it
unestimable for that session - so three sessions are run, each leaving the
others free. See D26.

**Absent evidence is null, not disagreement.** The derived columns emit NULL
where a record has nothing to say, so that a missing field contributes no
weight rather than counting against the pair. See D28.

Run with ``python -m src.matcher``.
"""

import collections
import time

import pandas as pd
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
from splink.blocking_rule_library import CustomRule
from splink.comparison_library import ArrayIntersectAtSizes

from src.comparisons import title_comparison
from src.data_loading import ID_COLUMN, load_source_tables
from src.features import add_features
from src.interfaces import (
    LEFT_ID,
    PROCESSED_DIR,
    RIGHT_ID,
    load_candidates,
    validate_scores,
)

# The prior probability that two randomly chosen records describe the same
# product. Derived without labels and sensitivity-tested at final evaluation;
# the reasoning is in docs/DECISIONS.md (D25).
PROBABILITY_TWO_RANDOM_RECORDS_MATCH = 2.0e-05

# Table aliases. Splink orders the two sides of a pair by alias, so these are
# named to put Walmart on the left, matching the interface contract, rather
# than swapping the columns back afterwards.
WALMART_ALIAS = "a_walmart"
AMAZON_ALIAS = "b_amazon"

# Intersection sizes for each array comparison, chosen from the measured
# distribution across candidate pairs. The identifier columns get a single
# level because sharing two rare identifiers happens in 30 pairs out of
# 564,450 - too rare for a separate level to be estimable.
ARRAY_COMPARISONS = {
    "rare_identifier_tokens": [1],
    "common_identifier_tokens": [1],
    "brand_terms": [2, 1],
    "rare_tokens": [2, 1],
}

# Each EM session blocks on one column, which makes that column unestimable for
# the session. Ordered most-concentrated first so the broader sessions start
# from better estimates. See D26.
#
# common_identifier_tokens was added after the first full run, which left the
# no-overlap level of rare_tokens untrained: the other three blocks all select
# on something that is itself a rare token, so none of them ever contained a
# pair without rare-token overlap - while 93.2% of pairs at prediction time
# have exactly that. This block is dominated by high-frequency specification
# tokens such as '1080p', which sit outside rare_tokens, and 87% of its pairs
# have no rare-token overlap. See D29.
TRAINING_COLUMNS = [
    "rare_identifier_tokens",
    "common_identifier_tokens",
    "rare_tokens",
    "brand_terms",
]

# How many random pairs to draw when estimating u. Larger is more accurate and
# slower; this is enough to see every comparison level that occurs at a
# workable rate.
U_SAMPLE_PAIRS = 50_000_000


def training_rule(column: str) -> CustomRule:
    """Block on records sharing at least one value in ``column``.

    Written as an explicit join condition rather than
    ``block_on(..., arrays_to_explode=...)`` because **expectation-maximisation
    does not accept exploding rules** - it raises "Exploding blocking rules are
    not supported for the function you have called". Prediction accepts them,
    which is why the pair-key mechanism works there and this does not.

    The condition expresses the same block, evaluated as a join predicate
    instead of an explode. It is quick in practice: the smallest session
    converges in around seven seconds.
    """
    return CustomRule(
        f'array_length(list_intersect(l."{column}", r."{column}")) >= 1'
    )

SCORES_PATH = PROCESSED_DIR / "scores_classical.csv"


def attach_pair_keys(
    table_a: pd.DataFrame, table_b: pd.DataFrame, candidates: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Give every record the list of candidate pairs it belongs to.

    A key is built from both identifiers, so only the two members of a
    candidate pair can ever share one. Records in no candidate pair get an
    empty list rather than a placeholder: a shared placeholder would make every
    such record match every other one.
    """
    left: dict[str, list[str]] = collections.defaultdict(list)
    right: dict[str, list[str]] = collections.defaultdict(list)
    for a_id, b_id in zip(candidates[LEFT_ID], candidates[RIGHT_ID]):
        key = f"{a_id}|{b_id}"
        left[a_id].append(key)
        right[b_id].append(key)

    a = table_a.copy()
    b = table_b.copy()
    a["pair_keys"] = [left.get(i, []) for i in a[ID_COLUMN]]
    b["pair_keys"] = [right.get(i, []) for i in b[ID_COLUMN]]
    return a, b


def build_settings() -> SettingsCreator:
    """The model: what is compared, and how pairs are generated."""
    comparisons = [title_comparison()] + [
        ArrayIntersectAtSizes(column, sizes)
        for column, sizes in ARRAY_COMPARISONS.items()
    ]
    return SettingsCreator(
        link_type="link_only",
        comparisons=comparisons,
        blocking_rules_to_generate_predictions=[
            block_on("pair_keys", arrays_to_explode=["pair_keys"])
        ],
        probability_two_random_records_match=PROBABILITY_TWO_RANDOM_RECORDS_MATCH,
        retain_intermediate_calculation_columns=True,
    )


def train(linker: Linker) -> None:
    """Estimate the model's parameters, using no labelled data.

    ``u`` values - how often a kind of agreement happens *between non-matching
    records* - come from random sampling across the whole space, which is the
    right population for that question. ``m`` values - how often it happens
    between genuine matches - come from expectation-maximisation on blocks
    enriched for matches.
    """
    print("  estimating u by random sampling ...", flush=True)
    started = time.time()
    linker.training.estimate_u_using_random_sampling(max_pairs=U_SAMPLE_PAIRS)
    print(f"    done in {time.time() - started:.1f}s")

    for column in TRAINING_COLUMNS:
        print(f"  EM session, blocked on {column} ...", flush=True)
        started = time.time()
        linker.training.estimate_parameters_using_expectation_maximisation(
            training_rule(column)
        )
        print(f"    done in {time.time() - started:.1f}s")


def main() -> None:
    overall = time.time()
    print("loading data and building features ...", flush=True)
    table_a, table_b = add_features(*load_source_tables())
    candidates = load_candidates("classical")
    table_a, table_b = attach_pair_keys(table_a, table_b, candidates)
    print(f"  {len(table_a):,} Walmart, {len(table_b):,} Amazon, "
          f"{len(candidates):,} candidate pairs")

    linker = Linker(
        [table_a, table_b],
        build_settings(),
        DuckDBAPI(),
        input_table_aliases=[WALMART_ALIAS, AMAZON_ALIAS],
    )

    print("\ntraining ...", flush=True)
    train(linker)

    print("\nscoring candidate pairs ...", flush=True)
    started = time.time()
    scored = linker.inference.predict().as_pandas_dataframe()
    print(f"  scored {len(scored):,} pairs in {time.time() - started:.1f}s")

    # Splink orders the sides by alias; confirm rather than assume, so a
    # renamed alias cannot silently transpose the output.
    left_source = scored["source_dataset_l"].iloc[0]
    if left_source != WALMART_ALIAS:
        raise RuntimeError(
            f"expected Walmart on the left, found {left_source!r}. "
            f"Check the table aliases."
        )

    out = scored[["unique_id_l", "unique_id_r", "match_probability"]].copy()
    out = out.rename(columns={"unique_id_l": LEFT_ID, "unique_id_r": RIGHT_ID})
    validate_scores(out, candidates)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.sort_values([LEFT_ID, RIGHT_ID], ignore_index=True).to_csv(SCORES_PATH, index=False)
    print(f"  written to {SCORES_PATH.relative_to(SCORES_PATH.parent.parent.parent)}")
    print(f"\ntotal wall clock: {time.time() - overall:.1f}s")

    linker.misc.save_model_to_json(
        str(PROCESSED_DIR / "model_classical.json"), overwrite=True
    )


if __name__ == "__main__":
    main()
