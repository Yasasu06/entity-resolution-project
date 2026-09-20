"""Building the human review queue from the matcher's scores.

The matcher scores every candidate pair. This module turns those scores into
three outcomes per Walmart record - accept, review, or confidently different -
and writes the review items out as an artefact a person could work through.

The rule and every display choice were fixed in advance and are not decided
here. This module implements them:

* the thresholds, and the one-to-one constraint, from ``docs/PRE_REGISTRATION.md``
* record-level review and the "none of these" outcome, from D31
* unordered presentation of tied candidates, from D32
* how many candidates are shown, and how truncation is disclosed, from D33

**Scores are handled in bits, not probabilities.** Match weight,
``log2(p / (1 - p))``, is the model's natural scale. Above 0.99 the probability
scale compresses so hard that clearly separated candidates look identical, which
is how an earlier reading of this data put the tie rate at 62% when it was 18%.
A within-record difference in bits is also exactly invariant to the prior, which
makes it the most trustworthy quantity available here (D31).

**No labelled data is read.** Everything below derives from the source tables
and the matcher's scores (D14).

Run with ``python -m src.review_queue``.
"""

import json
import random
import zlib

import numpy as np
import pandas as pd

from src.data_loading import attribute_columns, load_source_tables
from src.interfaces import LEFT_ID, PROCESSED_DIR, RIGHT_ID
from src.matcher import SCORES_PATH

# --- the decision rule, from PRE_REGISTRATION.md ------------------------------

# A record's best candidate must reach this to be accepted without review.
ACCEPT_BITS = 6.0
# ... and must beat its runner-up by more than this. Below it the two are not
# meaningfully distinguishable and picking between them is a coin flip (D31).
MARGIN_BITS = 1.0
# Below this, no candidate is credible and the record is confidently different.
FLOOR_BITS = -3.5

# --- display, from D32 and D33 ------------------------------------------------

# Candidates within this of each other are tied *for display* and are shown
# unordered. Deliberately tighter than MARGIN_BITS, which answers a different
# question: 0.05 sits just above the 0.0389-bit quantum that separates an absent
# rare_identifier_tokens from a present-but-non-overlapping one (D32).
DISPLAY_TIE_BITS = 0.05
# Shown after the top tie group, which is always shown whole (D33).
EXTRA_CANDIDATES = 10

QUEUE_PATH = PROCESSED_DIR / "review_queue_classical.json"
ACCEPTED_PATH = PROCESSED_DIR / "accepted_classical.csv"

ACCEPT = "accept"
REVIEW_TIED = "review_tied"
REVIEW_UNSURE = "review_unsure"
DIFFERENT = "confidently_different"

# What a reviewer may answer. "none of these" is not a fallback: some records
# genuinely have no correct partner among their candidates, and an interface
# that forced a choice would manufacture errors rather than record the truth
# (D31).
REVIEW_OUTCOMES = ["match", "none_of_these", "cannot_tell"]


def match_weight(probability: pd.Series) -> pd.Series:
    """Convert a match probability to match weight in bits."""
    p = probability.clip(1e-15, 1 - 1e-15)
    return np.log2(p / (1 - p))


def rank_candidates(scores: pd.DataFrame) -> pd.DataFrame:
    """Sort by record then descending score, and number each record's candidates."""
    ranked = scores.sort_values([LEFT_ID, "bits"], ascending=[True, False]).copy()
    ranked["rank"] = ranked.groupby(LEFT_ID).cumcount()
    return ranked


def assign_outcomes(ranked: pd.DataFrame) -> pd.DataFrame:
    """One row per Walmart record: its best candidate, its margin, its outcome.

    A record contributes at most one predicted match. That one-to-one constraint
    is part of the rule, not an implementation detail - it is where most of the
    measured gain over a plain score threshold came from.
    """
    best = ranked[ranked["rank"] == 0].set_index(LEFT_ID)
    runner_up = ranked[ranked["rank"] == 1].set_index(LEFT_ID)["bits"]
    # A record with a single candidate has no runner-up, so nothing can tie it.
    margin = (best["bits"] - runner_up.reindex(best.index)).fillna(np.inf)

    out = pd.DataFrame({
        "best_candidate": best[RIGHT_ID],
        "best_bits": best["bits"],
        "best_probability": best["match_probability"],
        "margin_bits": margin,
    })
    confident = out["best_bits"] >= ACCEPT_BITS
    out["outcome"] = np.where(
        confident & (out["margin_bits"] > MARGIN_BITS), ACCEPT,
        np.where(confident, REVIEW_TIED,
                 np.where(out["best_bits"] >= FLOOR_BITS, REVIEW_UNSURE, DIFFERENT)))
    return out


def tie_groups(bits: list[float]) -> list[int]:
    """Group a record's candidates into tied sets, best first.

    A candidate joins the current group while it is within DISPLAY_TIE_BITS of
    that group's leader. Grouping against the leader rather than the previous
    member stops a long chain of small steps collapsing into one group.
    """
    groups, index, leader = [], 0, bits[0]
    for value in bits:
        if leader - value > DISPLAY_TIE_BITS + 1e-9:
            index += 1
            leader = value
        groups.append(index)
    return groups


def _shuffled(items: list, record_id: str) -> list:
    """Shuffle deterministically, seeded by the record id.

    Tied candidates carry no real order, so any order shown is arbitrary. Left
    in score order it would track Amazon table position, and position bias would
    then push reviewers systematically toward whichever record happened to sort
    first - turning an artefact into a bias correlated with the data, inside the
    judgements being collected to evaluate the system. Seeding keeps the queue
    reproducible while decorrelating it from the table (D32).
    """
    shuffled = list(items)
    random.Random(zlib.crc32(record_id.encode())).shuffle(shuffled)
    return shuffled


def _record_fields(row: pd.Series, columns: list[str]) -> dict:
    return {c: (None if pd.isna(row[c]) else row[c]) for c in columns}


def build_review_items(
    ranked: pd.DataFrame,
    outcomes: pd.DataFrame,
    table_a: pd.DataFrame,
    table_b: pd.DataFrame,
) -> list[dict]:
    """Assemble one review item per record needing review.

    The unit is the record together with its candidates, never a single pair:
    "is this pair a match?" cannot be answered alone. A reviewer can only judge
    it by seeing the alternatives - which is how one notices that none of eleven
    memory cards is the 512MB one being looked for (D31).
    """
    columns = attribute_columns(table_a)
    left = table_a.set_index("unique_id")
    right = table_b.set_index("unique_id")
    needs_review = outcomes[outcomes["outcome"].isin([REVIEW_TIED, REVIEW_UNSURE])]

    # Only candidates above the floor are worth a reviewer's attention at all.
    shown_pool = ranked[ranked["bits"] >= FLOOR_BITS]
    by_record = dict(list(shown_pool.groupby(LEFT_ID)))

    items = []
    for record_id, summary in needs_review.iterrows():
        candidates = by_record[record_id]
        groups = tie_groups(list(candidates["bits"]))
        candidates = candidates.assign(group=groups)

        # The top tie group is shown whole; EXTRA_CANDIDATES follow it (D33).
        top = candidates[candidates["group"] == 0]
        rest = candidates[candidates["group"] > 0].head(EXTRA_CANDIDATES)
        displayed = pd.concat([top, rest])

        blocks = []
        for group_index, block in displayed.groupby("group", sort=True):
            true_size = int((candidates["group"] == group_index).sum())
            members = [
                {
                    "amazon_id": row[RIGHT_ID],
                    "bits": round(float(row["bits"]), 4),
                    "match_probability": float(row["match_probability"]),
                    **_record_fields(right.loc[row[RIGHT_ID]], columns),
                }
                for _, row in block.iterrows()
            ]
            tied = len(members) > 1
            blocks.append({
                "tied": tied,
                # Tied members have no meaningful order, so no rank numerals are
                # emitted for them and the order shown is the seeded shuffle.
                "members": _shuffled(members, record_id) if tied else members,
                "shown": len(members),
                "true_size": true_size,
                # Without this a truncated group is an arbitrary subset of an
                # unordered set, presented as though it were a shortlist (D33).
                "truncated": len(members) < true_size,
            })

        items.append({
            "walmart_id": record_id,
            "walmart": _record_fields(left.loc[record_id], columns),
            "reason": summary["outcome"],
            "best_bits": round(float(summary["best_bits"]), 4),
            "margin_bits": (None if np.isinf(summary["margin_bits"])
                            else round(float(summary["margin_bits"]), 4)),
            "candidate_blocks": blocks,
            "total_candidates_above_floor": int(len(candidates)),
            "allowed_outcomes": REVIEW_OUTCOMES,
            "decision": None,
        })
    return items


def main() -> None:
    scores = pd.read_csv(SCORES_PATH)
    scores["bits"] = match_weight(scores["match_probability"])
    table_a, table_b = load_source_tables()

    ranked = rank_candidates(scores)
    outcomes = assign_outcomes(ranked)

    counts = outcomes["outcome"].value_counts()
    total = len(outcomes)
    print(f"{len(scores):,} scored pairs over {total:,} Walmart records\n")
    for name in (ACCEPT, REVIEW_TIED, REVIEW_UNSURE, DIFFERENT):
        n = int(counts.get(name, 0))
        print(f"  {name:<24} {n:>6,} records  ({n / total:6.1%})")

    accepted = outcomes[outcomes["outcome"] == ACCEPT]
    pairs = pd.DataFrame({
        LEFT_ID: accepted.index,
        RIGHT_ID: accepted["best_candidate"].to_numpy(),
        "match_probability": accepted["best_probability"].to_numpy(),
    })
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(ACCEPTED_PATH, index=False)

    items = build_review_items(ranked, outcomes, table_a, table_b)
    QUEUE_PATH.write_text(json.dumps(items, indent=2))

    shown = sum(b["shown"] for i in items for b in i["candidate_blocks"])
    truncated = sum(1 for i in items for b in i["candidate_blocks"] if b["truncated"])
    per_item = [sum(b["shown"] for b in i["candidate_blocks"]) for i in items]
    print(f"\n  accepted pairs written to   {ACCEPTED_PATH.name}  ({len(pairs):,})")
    print(f"  review queue written to     {QUEUE_PATH.name}  ({len(items):,} items)")
    print(f"  candidates shown            {shown:,}  "
          f"(median {int(np.median(per_item))}, max {max(per_item)} per item)")
    print(f"  tie groups shown truncated  {truncated:,}  (each labelled with its true size)")


if __name__ == "__main__":
    main()
