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

    from src.data_loading import load_source_tables, load_labelled_pairs

    table_a, table_b = load_source_tables()
    train = load_labelled_pairs("train")
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
# IMPORTANT: "test" is deliberately excluded from routine use. It is sealed
# until one final evaluation at the end of the project, so that the headline
# number is honest and not the product of repeated peeking. Loading it requires
# passing allow_test=True, which exists purely to make that an explicit,
# deliberate act rather than an accident.
ROUTINE_SPLITS = ("train", "valid")
SEALED_SPLITS = ("test",)


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
    allow_test: bool = False,
) -> pd.DataFrame:
    """Load one split of labelled pairs, with identifiers matching the tables.

    The raw files reference records by their *raw* ids, so those are translated
    into the same prefixed identifiers that :func:`load_source_tables` produces.

    Returns a frame with columns ``unique_id_l``, ``unique_id_r``, ``label``,
    where ``label`` is 1 for "same real-world entity" and 0 for "different".

    Passing ``split="test"`` raises unless ``allow_test=True``. That guard is
    deliberate — see the note on sealed splits at the top of this module.
    """
    if split in SEALED_SPLITS and not allow_test:
        raise ValueError(
            f"The '{split}' split is sealed for a single final evaluation and must "
            f"not be used for development, tuning, or threshold-setting. "
            f"Use one of {ROUTINE_SPLITS} instead. If this really is that final "
            f"evaluation, pass allow_test=True explicitly."
        )

    valid_splits = ROUTINE_SPLITS + SEALED_SPLITS
    if split not in valid_splits:
        raise ValueError(f"Unknown split {split!r}; expected one of {valid_splits}")

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
    for split_name in ROUTINE_SPLITS:
        pairs = load_labelled_pairs(split_name)
        print(f"{split_name:>6}: {len(pairs):,} pairs, {int(pairs.label.sum()):,} matches")
