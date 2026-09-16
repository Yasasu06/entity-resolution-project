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
