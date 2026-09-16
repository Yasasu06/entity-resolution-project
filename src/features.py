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

Four lists are produced:

- ``rare_identifier_tokens``  - part-number-shaped tokens that are rare
- ``common_identifier_tokens`` - part-number-shaped tokens that are not
- ``brand_terms``             - terms from the harvested brand vocabulary
- ``rare_tokens``             - any uncommon word, whatever its shape

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

FEATURE_COLUMNS = [
    "rare_identifier_tokens",
    "common_identifier_tokens",
    "brand_terms",
    "rare_tokens",
]


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

    def features_for(table: pd.DataFrame) -> dict[str, list[list[str]]]:
        built: dict[str, list[list[str]]] = {name: [] for name in FEATURE_COLUMNS}
        for _, row in table.iterrows():
            tokens = set(word_tokens(record_text(row, columns)))
            identifiers = {t for t in tokens if is_identifier_shaped(t)}
            # Sorted so the columns are deterministic run to run, which keeps
            # the pipeline reproducible and any diff meaningful.
            built["rare_identifier_tokens"].append(
                sorted(t for t in identifiers if frequency[t] <= RARE_IDENTIFIER_MAX_DF))
            built["common_identifier_tokens"].append(
                sorted(t for t in identifiers if frequency[t] > RARE_IDENTIFIER_MAX_DF))
            built["brand_terms"].append(sorted(tokens & brands))
            built["rare_tokens"].append(
                sorted(t for t in tokens if frequency[t] <= RARE_TOKEN_MAX_DF))
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
