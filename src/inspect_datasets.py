"""Print a structural summary of each raw benchmark dataset.

This is a *look, don't touch* script. It reads the CSVs in ``data/raw/`` and
reports what is in them — filenames, sizes, columns, row counts, label balance,
and the first few rows exactly as stored. It deliberately performs no cleaning,
normalisation, or matching, so that the summary describes the real data.

Run it with the project virtual environment active::

    python src/inspect_datasets.py
"""

from pathlib import Path

import pandas as pd

# Repository root, derived from this file's location so the script works no
# matter which directory it is invoked from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# The two source tables being matched. Every labeled pair points at one row in
# each of these.
SOURCE_TABLES = ("tableA.csv", "tableB.csv")

# The labeled pair files. Together these form the full set of judged pairs;
# the benchmark ships them pre-split so results are comparable across papers.
PAIR_FILES = ("train.csv", "valid.csv", "test.csv")


def human_size(num_bytes: int) -> str:
    """Format a byte count as a short human-readable string."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} GB"  # pragma: no cover - unreachable, keeps mypy happy


def describe_source_table(path: Path) -> pd.DataFrame:
    """Report the structure and contents of one source table."""
    # dtype=str keeps every value exactly as written in the file. Without it
    # pandas would silently coerce things like IDs and prices, which would
    # hide the formatting inconsistencies we are specifically looking for.
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])

    print(f"\n  --- {path.name}  ({human_size(path.stat().st_size)}) ---")
    print(f"  rows: {len(frame):,}    columns: {len(frame.columns)}")
    print(f"  column names: {list(frame.columns)}")

    # Missing values matter a lot in entity resolution: an absent attribute is
    # a comparison you simply cannot make.
    print("\n  missing values per column:")
    for column in frame.columns:
        missing = int(frame[column].isna().sum())
        pct = (missing / len(frame) * 100) if len(frame) else 0.0
        print(f"    {column:<16} {missing:>7,} missing  ({pct:5.1f}%)")

    print("\n  first 5 rows, exactly as stored:")
    with pd.option_context(
        "display.max_columns", None,
        "display.width", 200,
        "display.max_colwidth", 60,
    ):
        print(frame.head(5).to_string(index=False))

    return frame


def describe_pair_files(dataset_dir: Path) -> None:
    """Report row counts and label balance across the train/valid/test splits."""
    print("\n  --- labeled pairs ---")

    total_rows = 0
    total_matches = 0

    for filename in PAIR_FILES:
        path = dataset_dir / filename
        if not path.exists():
            print(f"  {filename:<12} MISSING")
            continue

        pairs = pd.read_csv(path)
        matches = int((pairs["label"] == 1).sum())
        total_rows += len(pairs)
        total_matches += matches

        print(
            f"  {filename:<12} {human_size(path.stat().st_size):>10}  "
            f"columns={list(pairs.columns)}  "
            f"rows={len(pairs):>6,}  matches={matches:>5,}  "
            f"non-matches={len(pairs) - matches:>6,}"
        )

    match_pct = (total_matches / total_rows * 100) if total_rows else 0.0
    print(
        f"  {'TOTAL':<12} {'':>10}  "
        f"rows={total_rows:>6,}  matches={total_matches:>5,}  "
        f"({match_pct:.1f}% of pairs are matches)"
    )

    # Show the first few labeled pairs so the ID-referencing structure is
    # visible: each row names a row in tableA and a row in tableB, plus a verdict.
    first_split = dataset_dir / PAIR_FILES[0]
    if first_split.exists():
        print(f"\n  first 5 rows of {PAIR_FILES[0]}, exactly as stored:")
        print(pd.read_csv(first_split).head(5).to_string(index=False))


def describe_dataset(dataset_dir: Path) -> None:
    """Print a full report for one dataset directory."""
    print("\n" + "=" * 78)
    print(f"DATASET: {dataset_dir.name}")
    print("=" * 78)

    files = sorted(p for p in dataset_dir.iterdir() if p.is_file())
    print("\n  files received:")
    for path in files:
        print(f"    {path.name:<14} {human_size(path.stat().st_size):>10}")

    for filename in SOURCE_TABLES:
        path = dataset_dir / filename
        if path.exists():
            describe_source_table(path)
        else:
            print(f"\n  --- {filename} MISSING ---")

    describe_pair_files(dataset_dir)


def main() -> None:
    if not RAW_DATA_DIR.exists():
        raise SystemExit(f"No raw data directory found at {RAW_DATA_DIR}")

    dataset_dirs = sorted(p for p in RAW_DATA_DIR.iterdir() if p.is_dir())
    if not dataset_dirs:
        raise SystemExit(f"No dataset directories found under {RAW_DATA_DIR}")

    for dataset_dir in dataset_dirs:
        describe_dataset(dataset_dir)


if __name__ == "__main__":
    main()
