"""The contract between the blocking stage and the matching stage.

This project will eventually contain **two** complete entity resolution
systems — one classical and rule-based, one built on embeddings — so that they
can be compared. The comparison is only meaningful if their parts can be
swapped: classical blocking with the embedding matcher, and the reverse. That
tells us which *component* drives any difference in results, rather than
leaving us with two black boxes and one number each.

Swapping only works if both systems agree on what passes between the stages.
This module defines that agreement, and is written before either system is
finished precisely so neither can quietly grow a shape the other cannot accept.

**The contract, in one line:** blocking produces a table of candidate pairs;
matching consumes that table and produces the same pairs with a score attached.

```
    table A ──┐
              ├──►  Blocker  ──►  candidate pairs  ──►  Matcher  ──►  scored pairs
    table B ──┘                  (this contract)
```

The pitfall this exists to prevent is **coupling**. If a blocker computed
embeddings and its matcher silently reused them, the two would be welded
together and could never be swapped — and we would not find out until the very
end, with both systems built. Passing nothing between the stages but this
table keeps them genuinely independent.

Nothing here touches labelled data. Candidate pairs and scores are derived
from the source tables only, per docs/DECISIONS.md (D14).
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Generated files live here. Unlike data/raw/, this directory is NOT committed:
# everything in it is reproducible by rerunning the pipeline, which is the same
# reasoning that led us not to store discarded pairs (D21).
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# The two identifier columns. These names match those returned by
# data_loading.load_labelled_pairs, so the final evaluation can join candidates
# and scores against the answer key without renaming anything.
LEFT_ID = "unique_id_l"
RIGHT_ID = "unique_id_r"

# What a blocker must produce. 'rules' records which rule or method proposed
# the pair — not needed to match, but it is what makes a disagreement between
# two systems explainable rather than merely visible.
CANDIDATE_COLUMNS = [LEFT_ID, RIGHT_ID, "rules"]

# What a matcher must produce. 'match_probability' is a calibrated probability
# in [0, 1]; the three-way decision (match / unsure / non-match) is made later
# by applying thresholds, never inside the matcher itself.
SCORE_COLUMNS = [LEFT_ID, RIGHT_ID, "match_probability"]


@runtime_checkable
class Blocker(Protocol):
    """Anything that turns two tables into a shortlist of pairs worth scoring."""

    name: str

    def generate_candidates(
        self, table_a: pd.DataFrame, table_b: pd.DataFrame
    ) -> pd.DataFrame:
        """Return a frame with :data:`CANDIDATE_COLUMNS`."""
        ...


@runtime_checkable
class Matcher(Protocol):
    """Anything that attaches a match probability to each candidate pair."""

    name: str

    def score(
        self,
        candidates: pd.DataFrame,
        table_a: pd.DataFrame,
        table_b: pd.DataFrame,
    ) -> pd.DataFrame:
        """Return a frame with :data:`SCORE_COLUMNS`, one row per candidate."""
        ...


def validate_candidates(
    candidates: pd.DataFrame,
    table_a: pd.DataFrame,
    table_b: pd.DataFrame,
    id_column: str = "unique_id",
) -> None:
    """Check a candidate frame against the contract, raising on any violation.

    Called at the boundary between stages so that a mistake surfaces where it
    was made. Without this, a malformed frame would flow downstream and produce
    plausible-looking but wrong results — the failure mode this project keeps
    guarding against.
    """
    missing = [c for c in CANDIDATE_COLUMNS if c not in candidates.columns]
    if missing:
        raise ValueError(f"candidates missing required columns: {missing}")

    if candidates.empty:
        raise ValueError("candidate set is empty — blocking produced nothing")

    # Identifiers must refer to records that actually exist.
    valid_a, valid_b = set(table_a[id_column]), set(table_b[id_column])
    unknown_left = set(candidates[LEFT_ID]) - valid_a
    unknown_right = set(candidates[RIGHT_ID]) - valid_b
    if unknown_left:
        raise ValueError(f"{len(unknown_left)} left ids are not in table A, "
                         f"e.g. {sorted(unknown_left)[:3]}")
    if unknown_right:
        raise ValueError(f"{len(unknown_right)} right ids are not in table B, "
                         f"e.g. {sorted(unknown_right)[:3]}")

    # A duplicated pair would be scored twice and counted twice.
    duplicates = candidates.duplicated(subset=[LEFT_ID, RIGHT_ID]).sum()
    if duplicates:
        raise ValueError(f"{duplicates} duplicate candidate pairs")


def validate_scores(scores: pd.DataFrame, candidates: pd.DataFrame) -> None:
    """Check a score frame against the contract.

    A matcher must score every candidate it was given and invent none of its
    own. Silently dropping pairs would look like good precision while actually
    being missing work.
    """
    missing = [c for c in SCORE_COLUMNS if c not in scores.columns]
    if missing:
        raise ValueError(f"scores missing required columns: {missing}")

    given = set(zip(candidates[LEFT_ID], candidates[RIGHT_ID]))
    returned = set(zip(scores[LEFT_ID], scores[RIGHT_ID]))
    if returned - given:
        raise ValueError(f"matcher invented {len(returned - given)} pairs it was not given")
    if given - returned:
        raise ValueError(f"matcher did not score {len(given - returned)} of its candidates")

    probabilities = scores["match_probability"]
    if probabilities.isna().any():
        raise ValueError("match_probability contains missing values")
    if not ((probabilities >= 0) & (probabilities <= 1)).all():
        raise ValueError("match_probability must lie between 0 and 1")


def candidate_path(system_name: str) -> Path:
    """Where a given system's candidate pairs are written."""
    return PROCESSED_DIR / f"candidates_{system_name}.csv"


def save_candidates(candidates: pd.DataFrame, system_name: str) -> Path:
    """Write a candidate set to disk so the matching stage can pick it up.

    Persisting between stages means the expensive blocking step runs once, and
    that the exact pairs a matcher saw can be inspected afterwards rather than
    only existing inside one process.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = candidate_path(system_name)
    candidates.to_csv(path, index=False)
    return path


def load_candidates(system_name: str) -> pd.DataFrame:
    """Read back a candidate set written by :func:`save_candidates`."""
    path = candidate_path(system_name)
    if not path.exists():
        raise FileNotFoundError(
            f"No candidate set at {path}. Generate it first, e.g. "
            f"`python -m src.blocking`."
        )
    return pd.read_csv(path, dtype={LEFT_ID: str, RIGHT_ID: str, "rules": str})
