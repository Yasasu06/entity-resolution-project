"""Recording a real human reviewer working the queue.

[D24](../docs/DECISIONS.md) modelled the human arm and never observed it. This
records one reviewer's actual judgements so the modelled estimate can be
replaced with a measurement.

**The three stages are separated on purpose, and the separation is the point.**

``build_sample`` reads the answer key, because stratifying on whether a true
partner is shown requires knowing. It writes a sample file that contains **no
truth field of any kind**, and a test asserts that.

``run_session`` reads only that file. It cannot reveal an answer because it has
no access to one, and it gives no feedback of any sort while the session runs.

``score_session`` reads the log and the answer key afterwards.

**Why stratify.** Only 210 of the 1,214 queued records have their true partner
shown; for the other 1,004 the correct answer is "none of these". A reviewer who
always answered "none of these" would score 82.7%, so a single accuracy figure
is uninterpretable. Recall and the false-match rate are measured separately, on
the two strata, and any population figure is reweighted back to 17.3 / 82.7.

**What the reviewer is not shown.** The bucket a record came from is hidden, so
"this one was tied" cannot anchor the judgement. The model's match weight is
hidden too: showing it would measure whether the reviewer agrees with the model
rather than whether the reviewer can find the match. Candidate ordering and the
display cap are left exactly as the queue defines them, because those are fixed
in D32 and D33 and are the production interface.

This reads the answer key in two of its three stages and therefore sits below
the boundary in docs/PRE_UNSEAL.md.
"""

import json
import random
import time

from src.interfaces import PROCESSED_DIR

QUEUE_PATH = PROCESSED_DIR / "review_queue_classical.json"
SAMPLE_PATH = PROCESSED_DIR / "human_review_sample.json"
LOG_PATH = PROCESSED_DIR / "human_review_log.jsonl"

# The site's review tool ships the answer key to the browser for 120 cards, 71
# of which are queued records. Any of those the owner has opened is no longer a
# blind judgement, so the whole overlap is excluded.
REVEALED_PATH = "site/public/data.json"

SEED = 20260927

# A record cannot take five minutes of genuine comparison: the largest shows 14
# candidates. Anything longer means the session was left open, and the trial run
# proved it silently: one record absorbed a 9.9-hour overnight shutdown and
# dragged the mean from 12.5 seconds to 2,404. The judgement is kept, because
# the reviewer did answer it; only the timing is discarded.
INTERRUPTED_SECONDS = 300
FIELDS = ("title", "brand", "modelno", "category", "price")
OUTCOME_NONE = "none_of_these"
OUTCOME_UNSURE = "cannot_tell"


def revealed_ids(path=REVEALED_PATH) -> set:
    """Records whose answers have already been shown by the site's tool."""
    try:
        cards = json.loads(open(path).read())["cards"]
    except (OSError, KeyError, json.JSONDecodeError):
        return set()
    return {c["id"] for c in cards}


def shown_ids(item: dict) -> list:
    return [m["amazon_id"] for b in item["candidate_blocks"] for m in b["members"]]


def strip_for_review(item: dict) -> dict:
    """The item as the reviewer sees it: no bucket, no scores, no answer.

    Ordering and the display cap are preserved, because those are the interface
    fixed in D32 and D33 rather than incidental presentation.
    """
    return {
        "walmart_id": item["walmart_id"],
        "walmart": {k: item["walmart"].get(k) for k in FIELDS},
        "blocks": [
            {"tied": b["tied"], "truncated": b["truncated"], "true_size": b["true_size"],
             "members": [{"amazon_id": m["amazon_id"],
                          **{k: m.get(k) for k in FIELDS}} for m in b["members"]]}
            for b in item["candidate_blocks"]
        ],
        "allowed_outcomes": item["allowed_outcomes"],
    }


# ---------------------------------------------------------------------------
# Stage 1: build the sample. This stage reads the answer key.
# ---------------------------------------------------------------------------

def build_sample(per_stratum: int = 60, repeats: int = 18, seed: int = SEED,
                 queue_path=QUEUE_PATH, out_path=SAMPLE_PATH) -> dict:
    """Draw a stratified sample and write it without any answer.

    Stratum A: the true partner is among the candidates shown.
    Stratum B: it is not, so the correct answer is "none of these".

    Within each stratum records are drawn proportionally across the four queue
    buckets, so the bucket mix can be reported even though per-bucket rates will
    be too thin to claim precision on.
    """
    import collections

    from src.data_loading import load_labelled_pairs
    import pandas as pd

    labelled = pd.concat([load_labelled_pairs(s, unlock_final_evaluation=True)
                          for s in ("train", "valid", "test")])
    matches = labelled[labelled["label"] == 1]
    partners = collections.defaultdict(set)
    for left, right in zip(matches["unique_id_l"], matches["unique_id_r"]):
        partners[left].add(right)

    queue = json.loads(queue_path.read_text())
    excluded = revealed_ids()
    pool = [i for i in queue if i["walmart_id"] not in excluded]

    strata = {"A": [], "B": []}
    for item in pool:
        found = partners.get(item["walmart_id"], set()) & set(shown_ids(item))
        strata["A" if found else "B"].append(item)

    rng = random.Random(seed)
    picked = []
    for name, items in strata.items():
        by_bucket = collections.defaultdict(list)
        for i in items:
            by_bucket[i["reason"]].append(i)
        want = min(per_stratum, len(items))
        # proportional allocation, largest remainder, so small buckets are not
        # silently rounded out of the sample
        shares = {b: len(v) / len(items) * want for b, v in by_bucket.items()}
        alloc = {b: int(s) for b, s in shares.items()}
        while sum(alloc.values()) < want:
            b = max(shares, key=lambda k: shares[k] - alloc[k])
            alloc[b] += 1
            shares[b] -= 1e-9
        for bucket, n in alloc.items():
            chosen = rng.sample(by_bucket[bucket], min(n, len(by_bucket[bucket])))
            picked += [(name, i) for i in chosen]

    rng.shuffle(picked)
    order = [{"seq": n, "stratum_hidden": s, "repeat_of": None, **strip_for_review(i)}
             for n, (s, i) in enumerate(picked, 1)]

    # the repeat set: re-presented late, unmarked, to measure self-consistency
    repeat_src = rng.sample(order, min(repeats, len(order)))
    tail = len(order)
    for n, src in enumerate(repeat_src, 1):
        clone = dict(src)
        clone["seq"] = tail + n
        clone["repeat_of"] = src["seq"]
        order.append(clone)

    payload = {
        "seed": seed, "per_stratum": per_stratum, "repeats": len(repeat_src),
        "pool": len(pool), "excluded_revealed": len(set(i["walmart_id"] for i in queue) & excluded),
        "stratum_sizes": {k: len(v) for k, v in strata.items()},
        "presentations": len(order), "items": order,
    }
    out_path.write_text(json.dumps(payload, indent=1))
    assert_no_answer(json.loads(out_path.read_text()))
    return payload


BANNED_KEYS = frozenset({"truth", "truth_shown", "truthshown", "label", "labels",
                         "correct", "is_match", "answer", "gold", "y"})


def assert_no_answer(node, path="") -> None:
    """Fail if any *key* in the sample could carry an answer.

    Keys, not substrings. The first version of this check scanned the serialised
    file for the word "label" and fired on 270 records: this is a product
    catalogue, and Avery label sheets and binders with label holders are
    products. A guard that cries wolf on the data it protects is worse than no
    guard, because the next person disables it.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            assert key.lower() not in BANNED_KEYS, f"sample leaks an answer at {path}/{key}"
            assert_no_answer(value, f"{path}/{key}")
    elif isinstance(node, list):
        for n, value in enumerate(node):
            assert_no_answer(value, f"{path}[{n}]")


# ---------------------------------------------------------------------------
# Stage 2: the session. This stage has no access to the answer key.
#
# Nothing here imports src.data_loading, and the sample file it reads carries
# no truth field. The tool cannot reveal an answer because it does not have one.
# ---------------------------------------------------------------------------

def render(item: dict, n: int, total: int) -> str:
    """One record and its candidates, as a terminal page."""
    def fields(rec, keys=FIELDS):
        parts = [f"{k}: {rec[k]}" for k in keys if rec.get(k) not in (None, "")]
        return "\n      ".join(parts)

    out = [f"\n{'='*78}", f" {n} of {total}", "=" * 78,
           "\n  WALMART", f"      {fields(item['walmart'])}", "\n  CANDIDATES"]
    idx = 0
    for block in item["blocks"]:
        if block["tied"]:
            note = f"  [{block['true_size']} candidates the model cannot separate"
            note += ", list truncated]" if block["truncated"] else "]"
            out.append(note)
        for member in block["members"]:
            idx += 1
            out.append(f"\n   [{idx}] {fields(member)}")
    out.append(f"\n{'-'*78}")
    out.append("  number = that candidate    n = none of these    ? = cannot tell")
    out.append("  s = skip (recorded as skipped)    q = save and stop")
    return "\n".join(out)


def parse_choice(raw: str, n_candidates: int) -> str | None:
    """Map a keystroke to an outcome, or None if it is not understood."""
    raw = raw.strip().lower()
    if raw == "n":
        return OUTCOME_NONE
    if raw == "?":
        return OUTCOME_UNSURE
    if raw == "s":
        return "skipped"
    if raw == "q":
        return "quit"
    if raw.isdigit() and 1 <= int(raw) <= n_candidates:
        return f"pick:{int(raw)}"
    return None


def completed(log_path=LOG_PATH) -> set:
    """Presentation sequence numbers already recorded, so a session resumes."""
    if not log_path.exists():
        return set()
    done = set()
    for line in log_path.read_text().splitlines():
        if line.strip():
            done.add(json.loads(line)["seq"])
    return done


def run_session(sample_path=SAMPLE_PATH, log_path=LOG_PATH, limit=None,
                reader=input, writer=print) -> dict:
    """Present records and record judgements. No scoring, no feedback."""
    sample = json.loads(sample_path.read_text())
    items = sample["items"]
    done = completed(log_path)
    pending = [i for i in items if i["seq"] not in done]
    if limit is not None:
        pending = pending[:limit]

    writer(f"\n  {len(done)} already recorded, {len(pending)} to go in this run.")
    writer("  No feedback is given during the session. Scoring happens afterwards.")

    recorded, stopped = 0, None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as fh:
        for n, item in enumerate(pending, 1):
            ids = [m["amazon_id"] for b in item["blocks"] for m in b["members"]]
            writer(render(item, item["seq"], len(items)))
            started = time.time()
            while True:
                choice = parse_choice(reader("  > "), len(ids))
                if choice is None:
                    writer("  not understood")
                    continue
                break
            elapsed = round(time.time() - started, 2)
            if choice == "quit":
                stopped = "reviewer stopped"
                break
            outcome, picked = choice, None
            if choice.startswith("pick:"):
                outcome, picked = "match", ids[int(choice.split(":")[1]) - 1]
            interrupted = elapsed > INTERRUPTED_SECONDS
            fh.write(json.dumps({
                "seq": item["seq"], "walmart_id": item["walmart_id"],
                "repeat_of": item["repeat_of"], "outcome": outcome,
                "picked": picked, "seconds": elapsed,
                "interrupted": interrupted,
                "n_candidates": len(ids)}) + "\n")
            if interrupted:
                writer("  (that record's timing is marked interrupted and will "
                       "not count toward the pace; the answer is kept)")
            fh.flush()
            recorded += 1
    return {"recorded": recorded, "stopped": stopped,
            "remaining": len(items) - len(completed(log_path))}


# ---------------------------------------------------------------------------
# Stage 3: scoring. This stage reads the answer key, after the session.
# ---------------------------------------------------------------------------

POPULATION_RECOVERABLE = 210 / 1214      # 17.3%, the weight for reweighting


def score_session(sample_path=SAMPLE_PATH, log_path=LOG_PATH) -> dict:
    """Recall on the recoverable stratum, false-match rate on the other.

    A single accuracy figure is deliberately not the headline: answering "none
    of these" every time scores 82.7% on this queue, so accuracy cannot separate
    a reviewer who is discriminating from one who is simply always saying no.
    """
    import collections

    from src.data_loading import load_labelled_pairs
    import pandas as pd

    labelled = pd.concat([load_labelled_pairs(s, unlock_final_evaluation=True)
                          for s in ("train", "valid", "test")])
    matches = labelled[labelled["label"] == 1]
    partners = collections.defaultdict(set)
    for left, right in zip(matches["unique_id_l"], matches["unique_id_r"]):
        partners[left].add(right)

    sample = json.loads(sample_path.read_text())
    by_seq = {i["seq"]: i for i in sample["items"]}
    rows = [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]

    first = [r for r in rows if by_seq[r["seq"]]["repeat_of"] is None]
    strata = {"A": {"n": 0, "found": 0, "wrong_pick": 0, "unsure": 0},
              "B": {"n": 0, "false_match": 0, "unsure": 0}}
    for r in first:
        item = by_seq[r["seq"]]
        s = item["stratum_hidden"]
        strata[s]["n"] += 1
        if r["outcome"] == OUTCOME_UNSURE:
            strata[s]["unsure"] += 1
        elif s == "A":
            if r["outcome"] == "match":
                if r["picked"] in partners.get(r["walmart_id"], set()):
                    strata["A"]["found"] += 1
                else:
                    strata["A"]["wrong_pick"] += 1
        elif r["outcome"] == "match":
            strata["B"]["false_match"] += 1

    def rate(k, n):
        return round(k / n * 100, 2) if n else None

    a, b = strata["A"], strata["B"]
    # self-consistency, the single-reviewer analogue of D34's control
    seen, repeats, agree = {}, 0, 0
    for r in rows:
        item = by_seq[r["seq"]]
        key = (r["outcome"], r["picked"])
        if item["repeat_of"] is None:
            seen[r["seq"]] = key
        elif item["repeat_of"] in seen:
            repeats += 1
            agree += seen[item["repeat_of"]] == key

    timed = [r for r in rows if not r.get("interrupted")
             and r["seconds"] <= INTERRUPTED_SECONDS]
    secs = [r["seconds"] for r in timed]
    import statistics as st
    return {
        "presentations_recorded": len(rows),
        "recall_on_recoverable": {"n": a["n"], "found": a["found"],
                                  "rate": rate(a["found"], a["n"]),
                                  "wrong_candidate": a["wrong_pick"], "unsure": a["unsure"]},
        "false_match_rate": {"n": b["n"], "false_matches": b["false_match"],
                             "rate": rate(b["false_match"], b["n"]), "unsure": b["unsure"]},
        "self_consistency": {"repeats": repeats, "agreed": agree,
                             "rate": rate(agree, repeats)},
        "seconds_per_record": {"median": round(st.median(secs), 1) if secs else None,
                               "mean": round(st.mean(secs), 1) if secs else None,
                               "total_minutes": round(sum(secs) / 60, 1) if secs else None,
                               "timed": len(secs),
                               "excluded_interrupted": len(rows) - len(secs)},
        "note": ("Stratified, so these two rates are not a population accuracy. "
                 "Any population figure must reweight to 17.3% recoverable."),
    }
