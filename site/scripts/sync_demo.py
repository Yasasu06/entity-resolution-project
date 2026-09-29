"""Refresh the fixed 120-card demo from a completed local matcher run.

The card IDs and their original seeded draw stay fixed. This script updates
their decisions, visible review candidates, and answer keys from the generated
artifacts. Run from any directory with ``python3 site/scripts/sync_demo.py``.
Use ``--check`` to compare the committed snapshot with those artifacts.
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "site/public/data.json"
PROCESSED = ROOT / "data/processed"
RAW = ROOT / "data/raw/dirty_walmart_amazon"
FIELDS = ("title", "category", "brand", "modelno", "price")


def rows(path):
    with path.open(newline="") as handle:
        yield from csv.DictReader(handle)


def positives():
    truth = defaultdict(set)
    for split in ("train", "valid", "test"):
        for row in rows(RAW / f"{split}.csv"):
            if row["label"] == "1":
                truth[f"A_{row['ltable_id']}"].add(f"B_{row['rtable_id']}")
    return truth


def displayed_blocks(item):
    """Keep interface fields and ordering, excluding model scores."""
    return [
        {
            "tied": block["tied"],
            "members": [
                {"amazon_id": member["amazon_id"],
                 **{field: member.get(field) for field in FIELDS}}
                for member in block["members"]
            ],
            "shown": block["shown"],
            "true_size": block["true_size"],
            "truncated": block["truncated"],
        }
        for block in item["candidate_blocks"]
    ]


def make_snapshot(existing):
    accepted = {}
    for row in rows(PROCESSED / "accepted_classical.csv"):
        left, right = row["unique_id_l"], row["unique_id_r"]
        if left in accepted:
            raise ValueError(f"duplicate accepted record: {left}")
        accepted[left] = right

    queue_items = json.loads((PROCESSED / "review_queue_classical.json").read_text())
    queue = {item["walmart_id"]: item for item in queue_items}
    if len(queue) != len(queue_items) or set(queue) & set(accepted):
        raise ValueError("duplicate or overlapping accepted/review records")

    # Reuse the pipeline's own display rules for every card, including accepts
    # that have no persisted queue item. The fake review outcome affects only
    # whether build_review_items renders the card; scores and display stay real.
    sys.path.insert(0, str(ROOT))
    import pandas as pd
    from src.data_loading import load_source_tables
    from src.review_queue import (REVIEW_UNSURE, assign_outcomes,
                                  build_review_items, match_weight,
                                  rank_candidates)

    scores = pd.read_csv(PROCESSED / "scores_classical.csv")
    scores["bits"] = match_weight(scores["match_probability"])
    ranked = rank_candidates(scores)
    ids = [card["id"] for card in existing["cards"]]
    summaries = assign_outcomes(ranked).loc[ids].copy()
    summaries["outcome"] = REVIEW_UNSURE
    table_a, table_b = load_source_tables()
    rendered = {
        item["walmart_id"]: item
        for item in build_review_items(ranked, summaries, table_a, table_b)
    }
    for left, item in queue.items():
        if left in rendered and displayed_blocks(item) != displayed_blocks(rendered[left]):
            raise ValueError(f"{left}: generated display disagrees with current queue artifact")

    truth = positives()
    n_left = sum(1 for _ in rows(RAW / "tableA.csv"))
    n_right = sum(1 for _ in rows(RAW / "tableB.csv"))
    n_candidates = sum(1 for _ in rows(PROCESSED / "candidates_classical.csv"))
    run = json.loads((PROCESSED / "run_classical.json").read_text())
    if run["candidate_pairs"] != n_candidates or run["dataset"] != RAW.name:
        raise ValueError("matcher run metadata disagrees with the candidate data")
    true_pairs = {(left, right) for left, rights in truth.items() for right in rights}
    correct = sum((left, right) in true_pairs for left, right in accepted.items())
    precision = 100 * correct / len(accepted)
    recall = 100 * correct / len(true_pairs)
    f1 = 200 * correct / (len(accepted) + len(true_pairs))

    cards = []
    drift = {"display": [], "outcome": [], "pick": [], "ai_cleared": []}
    for old in existing["cards"]:
        card = dict(old)
        left = card["id"]
        display = rendered[left]
        card["walmart"] = {field: display["walmart"].get(field) for field in FIELDS}
        card["blocks"] = displayed_blocks(display)
        if left in queue:
            item = queue[left]
            card["outcome"] = item["reason"]
            card["systemPick"] = None
            card["systemBest"] = max(
                (m for block in display["candidate_blocks"] for m in block["members"]),
                key=lambda m: m["bits"],
            )["amazon_id"]
            # The saved AI decision was made on the old shortlist. Retain it
            # only if that shortlist and its outcome still describe this card.
            old_ids = [m["amazon_id"] for b in old["blocks"] for m in b["members"]]
            new_ids = [m["amazon_id"] for b in card["blocks"] for m in b["members"]]
            if old["outcome"] != card["outcome"] or old_ids != new_ids:
                card["ai"] = None
        elif left in accepted:
            pick = accepted[left]
            shown = {m["amazon_id"] for b in card["blocks"] for m in b["members"]}
            if pick not in shown:
                raise ValueError(f"{left}: accepted partner {pick} absent from saved display")
            card["outcome"] = "accept"
            card["systemPick"] = pick
            card["systemBest"] = pick
            card["ai"] = None
        else:
            raise ValueError(f"{left}: fixed demo card has no accepted/review outcome")
        shown = {m["amazon_id"] for b in card["blocks"] for m in b["members"]}
        card["truth"] = sorted(truth.get(left, ()))
        card["truthShown"] = [right for right in card["truth"] if right in shown]
        if card["blocks"] != old["blocks"]:
            drift["display"].append(left)
        if card["outcome"] != old["outcome"]:
            drift["outcome"].append(left)
        if card["systemPick"] != old["systemPick"]:
            drift["pick"].append(left)
        if old["ai"] is not None and card["ai"] is None:
            drift["ai_cleared"].append(left)
        cards.append(card)

    counts = Counter(card["outcome"] for card in cards)
    old_sample = existing["stats"]["sample"]
    stats = {
        "records": n_left,
        "candidates": n_candidates,
        "crossProduct": n_left * n_right,
        "withPartner": len(truth),
        "trueMatches": len(true_pairs),
        "accepted": len(accepted),
        "queue": len(queue),
        "different": n_left - len(accepted) - len(queue),
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1": round(f1, 2),
        "uSampleSeed": run["u_sample_seed"],
        "originalF1": 59.46,
        "blockingRecall": 99.9,
        "byReason": dict(sorted(Counter(item["reason"] for item in queue_items).items())),
        "sample": {
            "n": len(cards),
            "seed": old_sample["seed"],
            "drawQuota": old_sample.get("drawQuota", old_sample.get("quota")),
            "actual": dict(sorted(counts.items())),
        },
    }
    return {"stats": stats, "cards": cards}, drift


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    existing = json.loads(SNAPSHOT.read_text())
    updated, drift = make_snapshot(existing)
    if args.check:
        if existing != updated:
            raise SystemExit("demo snapshot differs from current local artifacts; run sync_demo.py")
        print("Demo snapshot agrees with current local artifacts.")
    else:
        SNAPSHOT.write_text(json.dumps(updated, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(f"Refreshed {len(updated['cards'])} demo cards: {updated['stats']}")
        print(f"Changes against the prior snapshot: {drift}")


if __name__ == "__main__":
    main()
