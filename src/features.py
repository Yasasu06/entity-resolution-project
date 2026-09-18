"""Derived columns the matcher compares records on.

The benchmark's corruption moved attribute values into `title` and blanked the
column they came from, so comparing `brand` to `brand` or `modelno` to
`modelno` fails on most pairs: measured across candidate pairs, those columns
are populated on *both* sides only 16-25% of the time, while `title` is always
present.

The response is to stop comparing columns and start comparing evidence
gathered from the whole record. Each function below extracts one kind of
evidence from wherever it happens to sit, producing a list that two records can
be compared on by set intersection.

Five lists are produced:

- ``title_tokens``            - the words of the title alone
- ``rare_identifier_tokens``  - part-number-shaped tokens that are rare
- ``common_identifier_tokens`` - part-number-shaped tokens that are not
- ``brand_terms``             - terms from the harvested brand vocabulary
- ``rare_tokens``             - any uncommon word, whatever its shape

``title_tokens`` is the exception to the gather-from-everywhere rule above: it
holds the title and nothing else, because the title comparison is deliberately
title-against-title. Evidence from the other columns reaches the model through
the four lists that follow it. Using the same tokeniser as everywhere else
means ``1TB`` and ``1 tb`` reduce to the same tokens on both sides.

Rarity is judged by **document frequency pooled across both tables** - how many
records in total contain the token. That differs from blocking rule R1, which
counts on the Amazon side only, and the difference is deliberate: R1's cutoff
controls how many candidates a word drags in, which is a question about cost,
whereas here the question is how *informative* agreement on a token is, which
is a property of the token across the whole corpus. See docs/DECISIONS.md
(D16, D18, D26).

Nothing here reads labelled data. Every threshold is derived from token
frequency in the source tables, per D14.
"""

import collections

import pandas as pd

from src.blocking import _known_brand_vocabulary, record_text
from src.data_loading import ID_COLUMN, attribute_columns
from src.text_normalisation import word_tokens

# A token is "identifier shaped" if it is long enough and either mixes letters
# with digits (``ph3100u``) or is entirely digits (``1163641``). Blocking's R2
# requires the mixed form only; matching accepts both, because a long pure
# number is very often a manufacturer code and the candidate set is already
# fixed by the time this runs, so a looser test costs nothing. R2 itself is
# unchanged - see docs/DECISIONS.md (D26).
IDENTIFIER_MIN_LENGTH = 5

# An identifier token appearing in more than this many records is treated as a
# specification rather than a part number: '1080p' and '500gb' pass the shape
# test but say almost nothing about which product a record describes.
RARE_IDENTIFIER_MAX_DF = 5

# A plain word appearing in at most this many records counts as rare enough to
# be worth comparing on.
RARE_TOKEN_MAX_DF = 20

# A numeric price, or None. Kept separate from FEATURE_COLUMNS because it is a
# single value rather than a list of evidence.
PRICE_COLUMN = "price_value"

FEATURE_COLUMNS = [
    "title_tokens",
    "rare_identifier_tokens",
    "common_identifier_tokens",
    "brand_terms",
    "rare_tokens",
]


def parse_price(raw: object) -> float | None:
    """Return a usable price, or ``None`` where there is not one.

    Anything that will not parse becomes None, and so does any price at or
    below zero. A zero price in this data reads as an absent value rather than
    a free product, and a relative difference measured against zero is
    undefined in any case. Treating those as missing rather than as a price of
    nought follows the same principle as the array columns: absence is not
    evidence of disagreement. See docs/DECISIONS.md (D28, D30).
    """
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _absent_if_empty(values: set[str]) -> list[str] | None:
    """Return a sorted list, or ``None`` when there is nothing to report.

    The distinction matters more than it looks. Splink treats a NULL comparison
    as *no evidence* and gives it zero weight, but an **empty list is not
    NULL** - ``[] IS NULL`` is false in SQL, so an empty list falls through to
    the final level and collects the weight for *disagreement*.

    Those are opposite meanings. A record carrying no brand term has nothing to
    say about brand; it is not evidence against a match. On this dataset the
    difference is severe, because the benchmark's corruption is what emptied
    these fields: scoring absence as disagreement would penalise records
    precisely for having been corrupted. Measured before the correction,
    97.61% of candidate pairs were being scored as disagreeing on
    ``common_identifier_tokens``, a field most records simply do not have.

    Genuine conflict is unaffected. Two records that both carry brand terms
    which happen not to overlap still produce two non-empty lists, an empty
    intersection, and the disagreement level - which is correct. Only true
    absence becomes NULL. See docs/DECISIONS.md (D28).
    """
    return sorted(values) if values else None


def is_identifier_shaped(token: str) -> bool:
    """Does this token look like a manufacturer code?

    Accepts both ``elplp12`` (letters and digits) and ``1163641`` (all digits),
    provided the token is long enough that the resemblance is unlikely to be
    accidental.
    """
    if len(token) < IDENTIFIER_MIN_LENGTH:
        return False
    if token.isdigit():
        return True
    return any(c.isalpha() for c in token) and any(c.isdigit() for c in token)


def pooled_document_frequency(
    table_a: pd.DataFrame, table_b: pd.DataFrame
) -> collections.Counter:
    """Count how many records across both tables contain each token.

    Each record contributes at most once per token, however many times the
    token occurs in it, so a single verbose title cannot make a word look
    common.
    """
    columns = attribute_columns(table_a)
    frequency: collections.Counter = collections.Counter()
    for table in (table_a, table_b):
        for _, row in table.iterrows():
            frequency.update(set(word_tokens(record_text(row, columns))))
    return frequency


def add_features(
    table_a: pd.DataFrame, table_b: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return both tables with the four comparison columns attached.

    Both tables are processed together because rarity is a property of the
    corpus, not of one side: a token counted only within Walmart would look
    rare simply because Walmart is the smaller table.
    """
    columns = attribute_columns(table_a)
    frequency = pooled_document_frequency(table_a, table_b)
    brands = _known_brand_vocabulary(table_a, table_b)

    def features_for(table: pd.DataFrame) -> dict[str, list]:
        built: dict[str, list] = {name: [] for name in FEATURE_COLUMNS}
        built[PRICE_COLUMN] = []
        for _, row in table.iterrows():
            tokens = set(word_tokens(record_text(row, columns)))
            # Title only - see the note on title_tokens in the module docstring.
            built["title_tokens"].append(
                _absent_if_empty(set(word_tokens(str(row["title"])))))
            identifiers = {t for t in tokens if is_identifier_shaped(t)}
            # Sorted so the columns are deterministic run to run, which keeps
            # the pipeline reproducible and any diff meaningful.
            built["rare_identifier_tokens"].append(_absent_if_empty(
                {t for t in identifiers if frequency[t] <= RARE_IDENTIFIER_MAX_DF}))
            built["common_identifier_tokens"].append(_absent_if_empty(
                {t for t in identifiers if frequency[t] > RARE_IDENTIFIER_MAX_DF}))
            built["brand_terms"].append(_absent_if_empty(tokens & brands))
            built["rare_tokens"].append(_absent_if_empty(
                {t for t in tokens if frequency[t] <= RARE_TOKEN_MAX_DF}))
            built[PRICE_COLUMN].append(parse_price(row["price"]))
        return built

    out = []
    for table in (table_a, table_b):
        enriched = table.copy()
        for name, values in features_for(table).items():
            enriched[name] = values
        out.append(enriched)
    return out[0], out[1]


if __name__ == "__main__":
    from src.data_loading import load_source_tables

    a, b = add_features(*load_source_tables())
    print(f"{'column':<28} {'Walmart non-empty':>18} {'Amazon non-empty':>17}")
    for name in FEATURE_COLUMNS:
        pa = sum(1 for v in a[name] if v) / len(a) * 100
        pb = sum(1 for v in b[name] if v) / len(b) * 100
        print(f"{name:<28} {pa:>17.1f}% {pb:>16.1f}%")
