"""Recording a real human reviewer working the queue.

[D24](../docs/DECISIONS.md) modelled the human arm and never observed it. D51
records one owner's actual judgements on the historical unseeded queue; its
full-queue figures are projections from that sample.

**The three stages are separated on purpose, and the separation is the point.**

``build_sample`` reads the answer key, because stratifying on whether a true
partner is shown requires knowing. The sample omits partner IDs and labels but
retains ``stratum_hidden`` for later scoring. That metadata reveals whether a
true partner is shown, so the sample file itself is not truth-free.

``run_session`` reads only that file. Its terminal display hides the stratum
metadata and gives no feedback of any sort while the session runs.

``score_session`` reads the log and the answer key afterwards.

**Why stratify.** In D51's historical 1,214-record queue, only 210 have their
true partner shown; for the other 1,004 the answer is "none of these". A reviewer who
always answered "none of these" would score 82.7%, so a single accuracy figure
is uninterpretable. Recall and the false-match rate are measured separately, on
the two strata, and any population figure is reweighted back to 17.3 / 82.7.

**What the reviewer is not shown.** The bucket a record came from is hidden, so
"this one was tied" cannot anchor the judgement. The model's match weight is
hidden too: showing it would measure whether the reviewer agrees with the model
rather than whether the reviewer can find the match. Candidate ordering and the
display cap are left exactly as the queue defines them in D32 and D33. This
local terminal study does not establish an operating review service.

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
    """Draw a stratified sample for a blinded terminal review.

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
    """Reject direct answer-key fields from the sample by *key*.

    This does not reject ``stratum_hidden``, which is truth-derived metadata
    needed for later scoring and must stay hidden by the terminal display.

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
# Stage 2: the session. This stage does not load the answer key.
#
# Nothing here imports src.data_loading. The sample file does carry
# truth-derived stratum metadata, but the terminal display does not show it.
# ---------------------------------------------------------------------------

def render(item: dict, position: int, total: int) -> str:
    """One record and its candidates, as a terminal page.

    ``position`` is the place in the running order, not the record's ``seq``.
    The two diverge after truncate_sample, which keeps original seq values so
    that an existing log still joins, leaving gaps. Displaying seq showed
    "70 of 69" to a reviewer partway through a 69-record session.
    """
    def fields(rec, keys=FIELDS):
        parts = [f"{k}: {rec[k]}" for k in keys if rec.get(k) not in (None, "")]
        return "\n      ".join(parts)

    out = [f"\n{'='*78}", f" {position} of {total}", "=" * 78,
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
    # position in the running order, which is not seq once the sample has been
    # truncated: seq stays stable so an existing log keeps joining
    position = {it["seq"]: n for n, it in enumerate(items, 1)}
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
            writer(render(item, position[item["seq"]], len(items)))
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
        # Headline is the rate over all stratum-B records: an abstention is a
        # real outcome of the review tier, not a record to divide away. The
        # decided-only rate sits beside it because it answers the sharper
        # question and because reporting only the lower of two defensible
        # figures would be a choice made after seeing which was lower.
        # Pre-registration section 14.5, amended 27 September 2026.
        "false_match_rate": {
            "n": b["n"], "false_matches": b["false_match"],
            "rate": rate(b["false_match"], b["n"]),
            "rate_decided_only": rate(b["false_match"], b["n"] - b["unsure"]),
            "decided": b["n"] - b["unsure"], "unsure": b["unsure"]},
        "abstention_rate": {
            "stratum_a": rate(a["unsure"], a["n"]),
            "stratum_b": rate(b["unsure"], b["n"]),
            "overall": rate(a["unsure"] + b["unsure"], a["n"] + b["n"])},
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


def truncate_sample(per_stratum: int, sample_path=SAMPLE_PATH, log_path=LOG_PATH,
                    seed: int = SEED) -> dict:
    """Cut the sample to ``per_stratum`` records each, keeping what is done.

    Pre-registration 14.3 committed to 60 per stratum and was amended to 30 on
    27 September 2026, after 20 presentations had been scored. The amendment
    states that plainly, including that the interim result was favourable.

    Records already reviewed are kept and counted, so the reduction only ever
    removes unseen presentations. Repeats are redrawn from the retained set at
    the same 15% proportion.
    """
    sample = json.loads(sample_path.read_text())
    done = completed(log_path)
    distinct = [i for i in sample["items"] if i["repeat_of"] is None]

    kept, counts = [], {"A": 0, "B": 0}
    for item in sorted(distinct, key=lambda i: i["seq"]):
        stratum = item["stratum_hidden"]
        if counts[stratum] < per_stratum:
            kept.append(item)
            counts[stratum] += 1
    dropped_done = [s for s in done if s not in {i["seq"] for i in kept}]
    assert not dropped_done, f"reduction would discard reviewed records {dropped_done}"

    n_repeats = round(per_stratum * 2 * 0.15)
    rng = random.Random(seed + per_stratum)
    tail = max(i["seq"] for i in kept)
    repeats = []
    for n, src in enumerate(rng.sample(kept, min(n_repeats, len(kept))), 1):
        clone = dict(src)
        clone["seq"] = tail + n
        clone["repeat_of"] = src["seq"]
        repeats.append(clone)

    sample.update({"per_stratum": per_stratum, "repeats": len(repeats),
                   "presentations": len(kept) + len(repeats),
                   "items": kept + repeats,
                   "reduced_from": {"per_stratum": 60, "presentations": 138,
                                    "after_presentations_seen": len(done)}})
    sample_path.write_text(json.dumps(sample, indent=1))
    assert_no_answer(sample)
    return {"kept": len(kept), "per_stratum": counts, "repeats": len(repeats),
            "presentations": sample["presentations"],
            "already_done": len(done), "still_to_review": sample["presentations"] - len(done)}
