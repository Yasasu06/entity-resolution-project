"""Splink comparisons: how two records are scored against each other.

A comparison takes one piece of evidence and sorts a record pair into one of
several *levels* - exact agreement, close agreement, weak agreement, and so on.
Splink then learns, from the data, how much each level is worth. The job here
is to define sensible levels; the weights are not set by hand.

Levels are always multi-valued rather than agree/disagree, so that "close but
not identical" carries its own learned weight instead of being forced into one
of two buckets.

Nothing here reads labelled data. Thresholds come from the distribution of
similarity across candidate pairs, never from how well they separate known
matches. See docs/DECISIONS.md (D27).
"""

from splink.comparison_library import CustomComparison

# Similarity cuts for the title comparison, placed against the measured
# distribution of word-level Jaccard across all 564,450 candidate pairs rather
# than at round numbers. p99 is 0.350 and p95 is 0.226, so these separate the
# top ~0.07%, ~1% and ~8% of pairs respectively. See docs/DECISIONS.md (D27).
TITLE_HIGH = 0.6
TITLE_MEDIUM = 0.35
TITLE_LOW = 0.2

def word_jaccard_sql(left_column: str, right_column: str) -> str:
    """SQL for word-level Jaccard: shared words over all distinct words.

    Built as a function of the column names so that the expression used by the
    comparison is the same one exercised by the tests, rather than a copy that
    can drift from it.

    Written with the inclusion-exclusion identity
    ``|A union B| = |A| + |B| - |A intersect B|`` because DuckDB has no
    ``list_union``, and because this avoids materialising the union list at all.
    The token lists are built distinct and sorted upstream, so the identity
    holds exactly.

    ``DOUBLE`` rather than ``FLOAT``: single precision introduces errors around
    3e-8, enough to move a pair sitting exactly on a threshold into the wrong
    level. Measured against the same calculation in Python, double precision
    agrees exactly across all 564,450 candidate pairs; single precision did not.

    ``NULLIF`` guards the case where both titles tokenise to nothing, yielding
    NULL so the null level catches it rather than a division error.
    """
    intersect = f"array_length(list_intersect({left_column}, {right_column}))"
    return (
        f"{intersect}::DOUBLE "
        f"/ NULLIF(array_length({left_column}) + array_length({right_column}) "
        f"- {intersect}, 0)"
    )


_TITLE_JACCARD = word_jaccard_sql('"title_tokens_l"', '"title_tokens_r"')


def title_comparison() -> CustomComparison:
    """Compare titles by the proportion of words they share.

    **Why not Splink's built-in string comparisons.** ``JaccardAtThresholds``
    calls DuckDB's ``jaccard()``, which compares *character* sets, not words -
    ``jaccard('cat', 'act')`` is 1.0. Across these titles it saturates: measured
    over the candidate set its 5th percentile is 0.484 and its 95th is 0.788, so
    the whole population sits inside a band of 0.30 and barely discriminates.
    Jaro-Winkler is worse suited still, being built for short strings and
    weighting a shared prefix heavily; titles here run to a median of 73 and 84
    characters and the two retailers reorder words freely, so a prefix bonus
    rewards an accident of word order.

    **Why not ``ArrayIntersectAtSizes``.** It grades on the raw count of shared
    words, which scales with title length: candidate pairs whose Walmart title
    runs to 25 words or more show a median overlap of 3 words against 1 word for
    titles of 10 words or fewer, while their normalised similarity is nearly
    identical (0.070 against 0.059). Unnormalised counts would systematically
    favour verbose listings - and Amazon titles reach 857 characters.

    Dividing by the size of the union removes that bias, which is the whole
    reason for the custom SQL.
    """
    return CustomComparison(
        output_column_name="title",
        comparison_description="Title, by proportion of shared words",
        comparison_levels=[
            {
                "sql_condition": '"title_tokens_l" IS NULL OR "title_tokens_r" IS NULL',
                "label_for_charts": "Null",
                "is_null_level": True,
            },
            {
                # Vanishingly rare - 5 pairs in the whole candidate set - so
                # agreement here should carry far more weight than merely close
                # agreement, and gets its own level to hold it.
                "sql_condition": '"title_tokens_l" = "title_tokens_r"',
                "label_for_charts": "Exact token-set match",
            },
            {
                "sql_condition": f"({_TITLE_JACCARD}) >= {TITLE_HIGH}",
                "label_for_charts": f"Jaccard >= {TITLE_HIGH}",
            },
            {
                "sql_condition": f"({_TITLE_JACCARD}) >= {TITLE_MEDIUM}",
                "label_for_charts": f"Jaccard >= {TITLE_MEDIUM}",
            },
            {
                "sql_condition": f"({_TITLE_JACCARD}) >= {TITLE_LOW}",
                "label_for_charts": f"Jaccard >= {TITLE_LOW}",
            },
            {
                "sql_condition": "ELSE",
                "label_for_charts": f"Jaccard < {TITLE_LOW}, or no overlap",
            },
        ],
    )


# Relative-difference bands for price, placed against the measured distribution
# over candidate pairs where both sides carry a usable price. The 5th and 10th
# percentiles of that distribution are 0.023 and 0.109, so the two tight bands
# isolate genuine agreement rather than slicing into the bulk - whose median
# pair differs by 62%. See docs/DECISIONS.md (D30).
PRICE_TIGHT = 0.02
PRICE_CLOSE = 0.10
PRICE_LOOSE = 0.20


def relative_price_difference_sql(left_column: str, right_column: str) -> str:
    """SQL for ``|a - b| / max(a, b)``: the gap as a share of the larger price.

    Relative rather than absolute, because a five pound difference means
    something entirely different on a ten pound cable and a thousand pound
    television.

    Dividing by the larger of the two keeps the result within 0 to 1 and
    symmetric, so the order of the arguments cannot change the answer. Both
    values are guaranteed positive upstream - anything at or below zero is
    parsed to NULL - so the denominator cannot be zero, but GREATEST is wrapped
    in NULLIF regardless rather than relying on that invariant holding forever.
    """
    return (
        f"abs({left_column} - {right_column}) "
        f"/ NULLIF(GREATEST({left_column}, {right_column}), 0)"
    )


_PRICE_DIFFERENCE = relative_price_difference_sql('"price_value_l"', '"price_value_r"')


def price_comparison() -> CustomComparison:
    """Compare prices by how far apart they are, in proportion.

    Price is weak evidence here and is expected to stay weak: the two retailers
    price independently, and only 21.1% of candidate pairs carry a usable price
    on both sides at all. Among those that do, the median pair differs by 62%.

    It is included because a near-identical price on an expensive item is worth
    something, and because letting the model learn how little price agreement is
    worth is more honest than asserting in advance that it is worthless. The
    null level means the 78.9% of pairs without two usable prices contribute
    nothing rather than counting against the pair.
    """
    return CustomComparison(
        output_column_name="price",
        comparison_description="Price, by relative difference",
        comparison_levels=[
            {
                "sql_condition": '"price_value_l" IS NULL OR "price_value_r" IS NULL',
                "label_for_charts": "Null",
                "is_null_level": True,
            },
            {
                "sql_condition": '"price_value_l" = "price_value_r"',
                "label_for_charts": "Exact match",
            },
            {
                "sql_condition": f"({_PRICE_DIFFERENCE}) <= {PRICE_TIGHT}",
                "label_for_charts": f"Within {PRICE_TIGHT:.0%}",
            },
            {
                "sql_condition": f"({_PRICE_DIFFERENCE}) <= {PRICE_CLOSE}",
                "label_for_charts": f"Within {PRICE_CLOSE:.0%}",
            },
            {
                "sql_condition": f"({_PRICE_DIFFERENCE}) <= {PRICE_LOOSE}",
                "label_for_charts": f"Within {PRICE_LOOSE:.0%}",
            },
            {
                "sql_condition": "ELSE",
                "label_for_charts": f"More than {PRICE_LOOSE:.0%} apart",
            },
        ],
    )
