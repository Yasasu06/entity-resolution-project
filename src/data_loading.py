"""The single, canonical way to load raw benchmark data into this project.

Every notebook and script should load data through this module rather than
calling ``pd.read_csv`` directly. That gives us one place where the awkward
details of the raw files are handled, so a fix here fixes them everywhere.

The most important of those details:

**Both source tables number their rows from zero.** ``tableA.csv`` has records
with ``id`` 0, 1, 2, ... and so does ``tableB.csv``. If those raw IDs were fed
into a matching engine as-is, record ``0`` from Walmart and record ``0`` from
Amazon would look like the same identifier, and results would be silently
wrong — no error, just quietly nonsensical output. To prevent that, every
record gets a prefixed identifier that is unique across both tables:

    tableA row 0  ->  "A_0"
    tableB row 0  ->  "B_0"

This module is the only place that prefixing happens, so it cannot be
forgotten.

Typical use::

    from src.data_loading import load_source_tables

    table_a, table_b = load_source_tables()

The labelled pair files are **sealed** under this project's strict no-peek
policy and cannot be loaded without an explicit override. Design work uses the
source tables only. See docs/DECISIONS.md (D14).
"""

from pathlib import Path

import pandas as pd

# Project root, derived from this file's location so imports work regardless of
# the directory a notebook or script happens to be run from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# The primary dataset for this project. See docs/DECISIONS.md for why.
DEFAULT_DATASET = "dirty_walmart_amazon"

# Prefixes that make record identifiers unique across the two source tables.
TABLE_A_PREFIX = "A"
TABLE_B_PREFIX = "B"

# Splink expects the identifier column to be called "unique_id" by default, so
# we adopt that name here rather than renaming things later.
ID_COLUMN = "unique_id"

# The labelled pair files that ship with the benchmark.
#
# STRICT NO-PEEK POLICY: every labelled split is sealed.
#
# Not just "test" — train and valid too. No labelled answers are consulted at
# any point while the system is being designed and built. That includes checks
# that feel like harmless due diligence, such as "how many known matches
# survive my blocking rules?" — that is still using the answer key to validate
# a design choice, and it is not permitted until the end.
#
# Loading any of these requires passing unlock_final_evaluation=True, which
# exists to make the single, final, one-time evaluation a deliberate act that
# cannot happen by accident. See docs/DECISIONS.md (D14).
ROUTINE_SPLITS = ()
SEALED_SPLITS = ("train", "valid", "test")


def _dataset_dir(dataset: str) -> Path:
    """Return the directory for a dataset, with a helpful error if missing."""
    path = RAW_DATA_DIR / dataset
    if not path.is_dir():
        available = sorted(p.name for p in RAW_DATA_DIR.iterdir() if p.is_dir())
        raise FileNotFoundError(
            f"No dataset directory {path}. Available datasets: {available}"
        )
    return path


def _load_table(path: Path, prefix: str) -> pd.DataFrame:
    """Load one source table and give its records globally unique identifiers.

    Values are read as strings (``dtype=str``) so that nothing is silently
    reinterpreted. Left to its own devices pandas would turn a model number
    like ``1163641`` into an integer and a price like ``59.0`` into a float,
    which loses leading zeros and changes how values compare as text. Since
    this project matches records *as text*, preserving them exactly matters.
    """
    frame = pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,  # don't invent NaN from strings like "NA" or "null"
        na_values=[""],         # a genuinely empty cell is the only missing value
    )

    if "id" not in frame.columns:
        raise ValueError(f"{path} has no 'id' column; got {list(frame.columns)}")

    # Build the prefixed identifier, then drop the raw 'id'. Keeping both around
    # invites using the wrong one by mistake.
    frame.insert(0, ID_COLUMN, prefix + "_" + frame["id"].astype(str))
    frame = frame.drop(columns=["id"])

    # A sanity check rather than an assumption: if the raw file ever contained
    # duplicate ids, the prefixed ids would collide too and matching would be
    # subtly wrong. Better to fail loudly here than to debug it downstream.
    duplicates = frame[ID_COLUMN].duplicated().sum()
    if duplicates:
        raise ValueError(f"{path} produced {duplicates} duplicate ids after prefixing")

    return frame


def load_source_tables(dataset: str = DEFAULT_DATASET) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the two tables being matched, with globally unique identifiers.

    Returns ``(table_a, table_b)``. Both have a ``unique_id`` column and share
    the same set of attribute columns.
    """
    directory = _dataset_dir(dataset)
    table_a = _load_table(directory / "tableA.csv", TABLE_A_PREFIX)
    table_b = _load_table(directory / "tableB.csv", TABLE_B_PREFIX)

    # The benchmark guarantees both tables share a schema. Verify rather than
    # trust: a mismatch would break field-to-field comparisons later.
    if list(table_a.columns) != list(table_b.columns):
        raise ValueError(
            "tableA and tableB have different columns:\n"
            f"  A: {list(table_a.columns)}\n"
            f"  B: {list(table_b.columns)}"
        )

    return table_a, table_b


def load_labelled_pairs(
    split: str,
    dataset: str = DEFAULT_DATASET,
    unlock_final_evaluation: bool = False,
) -> pd.DataFrame:
    """Load one split of labelled pairs, with identifiers matching the tables.

    The raw files reference records by their *raw* ids, so those are translated
    into the same prefixed identifiers that :func:`load_source_tables` produces.

    Returns a frame with columns ``unique_id_l``, ``unique_id_r``, ``label``,
    where ``label`` is 1 for "same real-world entity" and 0 for "different".

    **Every split is sealed.** Loading any of them raises unless
    ``unlock_final_evaluation=True`` is passed explicitly. This is not a
    formality — it is the mechanism that enforces the project's strict no-peek
    policy. See docs/DECISIONS.md (D14).
    """
    all_splits = ROUTINE_SPLITS + SEALED_SPLITS
    if split not in all_splits:
        raise ValueError(f"Unknown split {split!r}; expected one of {all_splits}")

    if split in SEALED_SPLITS and not unlock_final_evaluation:
        raise ValueError(
            f"The '{split}' split is SEALED. This project uses a strict no-peek "
            f"policy: no labelled answers (train, valid or test) may be consulted "
            f"until the entire pipeline is built, at which point there is one "
            f"single final evaluation.\n\n"
            f"This includes checks that feel like ordinary due diligence, such as "
            f"measuring how many known matches survive a blocking rule. That is "
            f"still tuning a design choice against the answer key.\n\n"
            f"Design decisions must come from the structure of the source tables "
            f"(see load_source_tables), not from labels.\n\n"
            f"If this genuinely is the final evaluation, pass "
            f"unlock_final_evaluation=True explicitly."
        )

    path = _dataset_dir(dataset) / f"{split}.csv"
    pairs = pd.read_csv(path)

    expected = {"ltable_id", "rtable_id", "label"}
    if not expected.issubset(pairs.columns):
        raise ValueError(f"{path} is missing columns; got {list(pairs.columns)}")

    # Translate raw ids into the prefixed form used everywhere else. 'l' (left)
    # refers to tableA and 'r' (right) to tableB.
    return pd.DataFrame({
        "unique_id_l": TABLE_A_PREFIX + "_" + pairs["ltable_id"].astype(str),
        "unique_id_r": TABLE_B_PREFIX + "_" + pairs["rtable_id"].astype(str),
        "label": pairs["label"].astype(int),
    })


def attribute_columns(table: pd.DataFrame) -> list[str]:
    """Return the matchable attribute columns, i.e. everything but the id."""
    return [c for c in table.columns if c != ID_COLUMN]


if __name__ == "__main__":
    # Running this file directly gives a quick confirmation that loading works.
    a, b = load_source_tables()
    print(f"tableA: {len(a):,} rows   tableB: {len(b):,} rows")
    print(f"attributes: {attribute_columns(a)}")
    print(f"first ids  A: {list(a[ID_COLUMN].head(3))}   B: {list(b[ID_COLUMN].head(3))}")
    print(f"\nlabelled splits {SEALED_SPLITS} are SEALED — no-peek policy (D14).")
    print("Design work uses the source tables above only.")
