"""The AI matcher: classical blocking, AI ranking, AI decision.

D22 built the blocking/matching contract so the stages could be swapped rather
than leaving two whole systems and one number each. This is that swap, fixed in
docs/PRE_REGISTRATION.md section 11.

**The classical system supplies the candidate set and nothing else.** The
shortlist is ranked by embedding similarity, not by match weight, so the model
does not inherit the classical ranking and get tested on re-ranking a shortlist
the classical system already chose. No Splink score reaches the prompt.

**The prompt asks what distinguishes the products before asking whether they
match.** D37 established that the classical comparisons cannot see the token
that decides identity, and that no rule over token sets can be given that
ability. Asking for the distinguishing attribute directs the model at exactly
that token, rather than inviting a holistic similarity judgement.

**The three outcomes map straight onto the three buckets**, so there is no
threshold to set and nothing to tune after the fact.

This is not label-free work. It exists because the answer key showed that most
wrong accepts are records with no partner at all. The design is fixed in advance;
the claim is weaker than system one's and is stated as such.

Run with ``python -m src.ai_matcher``.
"""

import json
import random
from dataclasses import dataclass, field

import pandas as pd

from src.ai_escalation import Response, Responder, parse_decision, require_api_key
from src.data_loading import attribute_columns, load_source_tables
from src.embeddings import SHORTLIST_PATH
from src.interfaces import PROCESSED_DIR

MODEL = "gpt-5.4-mini-2026-03-17"
TEMPERATURE = 0
MAX_TOKENS = 512

ORDERINGS = ("", "#b", "#c")       # stability: three shortlist orders
CONTROL = ""                        # plus a repeat of the first

RESULTS_PATH = PROCESSED_DIR / "ai_matcher_results.json"
STABILITY_PATH = PROCESSED_DIR / "ai_matcher_stability.json"

PROMPT = """\
You are matching product listings between two retailers. Decide whether the
Walmart listing below refers to the same real-world product as any one of the
Amazon listings.

WALMART LISTING
{walmart}

CANDIDATE AMAZON LISTINGS
{candidates}

Work in two steps.

First, for the candidates that look closest, name the attribute that decides
whether they are the same product: storage capacity, physical dimensions,
colour, model or part number, pack quantity, or product variant. Two listings
differing on any of these are different products, however similar the rest of
the description.

Then decide. Exactly one candidate may be the same product, or none may.

Respond with JSON only:
{{"distinguishing_attribute": "<what decides it, or null>",
 "decision": "match" | "none_of_these" | "cannot_tell",
 "amazon_id": "<id, or null>",
 "reasoning": "<one or two sentences>"}}

Choose "cannot_tell" only where the listings lack the information needed to
decide, not where the decision is merely difficult."""


@dataclass
class Judgement:
    decision: str
    amazon_id: str | None
    reasoning: str
    attribute: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    raw: str = field(default="", repr=False)

    def key(self) -> tuple[str, str | None]:
        return (self.decision, self.amazon_id if self.decision == "match" else None)


def _fields(row: pd.Series, columns: list[str]) -> str:
    return "\n".join(f"  {c}: {row[c]}" for c in columns if pd.notna(row[c]))


def render(record: pd.Series, candidates: pd.DataFrame, columns: list[str],
           order: str = "") -> str:
    """The prompt for one record and its shortlist.

    The shortlist arrives in embedding-similarity order, which is real
    information and is kept for the measured run. ``order`` reshuffles it, which
    is how the stability check separates a genuine judgement from one driven by
    where a candidate happened to sit.
    """
    rows = list(candidates.itertuples(index=False))
    if order:
        # the record is indexed by unique_id, so the id is the Series name,
        # not a column; record["unique_id"] raises and only on the shuffle path
        random.Random(str(record.name) + order).shuffle(rows)
    rendered = "\n".join(
        f"- id: {r.unique_id}\n" + _fields(pd.Series(r._asdict()), columns)
        for r in rows)
    return PROMPT.format(walmart=_fields(record, columns), candidates=rendered)


def judge(record, candidates, columns, responder: Responder, order: str = "") -> Judgement:
    reply = responder(render(record, candidates, columns, order))
    decision, amazon_id, reasoning = parse_decision(reply.text)
    attribute = None
    try:
        import re
        payload = json.loads(re.search(r"\{.*\}", reply.text, re.S).group(0))
        attribute = payload.get("distinguishing_attribute")
    except Exception:
        pass
    return Judgement(decision, amazon_id, reasoning, attribute,
                     reply.input_tokens, reply.output_tokens, reply.text)


def openai_responder() -> Responder:
    require_api_key()
    from openai import OpenAI
    client = OpenAI()

    def respond(prompt: str) -> Response:
        try:
            r = client.chat.completions.create(
                model=MODEL, messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE, max_completion_tokens=MAX_TOKENS)
        except Exception as exc:
            if "no credits remaining" in str(exc) or "insufficient_quota" in str(exc):
                raise CreditsExhausted(str(exc)[:160]) from exc
            raise
        return Response(text=r.choices[0].message.content or "",
                        input_tokens=r.usage.prompt_tokens,
                        output_tokens=r.usage.completion_tokens)
    return respond


def load_inputs():
    table_a, table_b = load_source_tables()
    columns = attribute_columns(table_a)
    shortlists = json.loads(SHORTLIST_PATH.read_text())
    return table_a.set_index("unique_id"), table_b.set_index("unique_id"), columns, shortlists


def shortlist_frame(table_b, ids: list[str]) -> pd.DataFrame:
    return table_b.loc[ids].reset_index()

class CreditsExhausted(RuntimeError):
    """The account ran out of credit mid-run.

    Worth its own type because the first stability run did not stop: it kept
    calling, recorded 225 identical failures, and those failures then counted as
    agreement in the gate. A run that cannot continue should end, not fill its
    results with errors that look like data.
    """


def stability(runs: dict[str, list[Judgement | None]], floor: float = 0.60) -> dict:
    """Score the gate over records whose calls all returned.

    Calls that never reached the model are excluded rather than treated as
    answers. Counting a failed call as a decision makes identical failures look
    like unanimous agreement, which is how the first run reported 72% when the
    figure over completed records was 61.1%.
    """
    complete = {w: v for w, v in runs.items()
                if all(j is not None for j in v[:len(ORDERINGS)])}
    n = len(complete)
    unanimous = sum(1 for v in complete.values()
                    if len({j.key() for j in v[:len(ORDERINGS)]}) == 1)
    with_control = {w: v for w, v in runs.items() if all(j is not None for j in v)}
    flips = sum(1 for v in with_control.values() if v[-1].key() != v[0].key())
    rate = unanimous / n if n else 0.0
    # a wide interval at this sample size is itself a result; report it
    half = 1.96 * ((rate * (1 - rate) / n) ** 0.5) if n else 0.0
    return {
        "records_attempted": len(runs),
        "records_complete": n,
        "records_dropped": len(runs) - n,
        "unanimous": unanimous,
        "unanimous_rate": rate,
        "ci95": [max(0.0, rate - half), min(1.0, rate + half)],
        "control_flips": flips,
        "control_flip_rate": flips / len(with_control) if with_control else 0.0,
        "floor": floor,
        "passes": rate - half >= floor,
        "inconclusive": rate >= floor > rate - half,
    }


# ---------------------------------------------------------------------------
# Running the experiment under a fixed budget
#
# The first stability run had neither of the safeguards below. It met HTTP 429
# partway through, kept calling, and recorded 225 failures that a later gate
# read as agreement. The work already paid for was not recoverable because
# nothing had been written down. Both problems are addressed here: spend is
# checked before each call rather than discovered after it, and every record is
# on disk the moment it completes.
# ---------------------------------------------------------------------------

PRICE_IN = 0.75 / 1_000_000     # gpt-5.4-mini-2026-03-17, verified 26 Sep 2026
PRICE_OUT = 4.50 / 1_000_000
SPEND_CEILING = 4.60            # against $5.00 available and not extensible
LARGEST_PROMPT = 2_768          # exact local token count over all 2,554 prompts

CHECKPOINT_PATH = PROCESSED_DIR / "ai_matcher_checkpoint.jsonl"


class BudgetExhausted(RuntimeError):
    """The ceiling would be crossed by the next call, so it is not made.

    Distinct from CreditsExhausted: that is the account refusing, discovered
    after the money is gone. This is the run refusing, before it is.
    """


class Ledger:
    """Cumulative spend, checked before a call rather than after it."""

    def __init__(self, ceiling: float = SPEND_CEILING):
        self.ceiling = ceiling
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0
        self.max_call = 0.0

    @property
    def spent(self) -> float:
        return self.input_tokens * PRICE_IN + self.output_tokens * PRICE_OUT

    @property
    def worst_case_next(self) -> float:
        """The largest a single call can cost: longest prompt, full output.

        The static figure is the exact local token count of the longest prompt
        in the population, but it is an assumption about the future and the
        ceiling must not depend on it being right. Any call that costs more
        than assumed raises the reserve for every call after it, so the
        guarantee survives an estimate that turns out to be wrong.
        """
        return max(LARGEST_PROMPT * PRICE_IN + MAX_TOKENS * PRICE_OUT,
                   self.max_call)

    def check(self) -> None:
        if self.spent + self.worst_case_next > self.ceiling:
            raise BudgetExhausted(
                f"${self.spent:.2f} spent over {self.calls:,} calls; the next "
                f"call could cost ${self.worst_case_next:.4f} and the ceiling "
                f"is ${self.ceiling:.2f}")

    def add(self, judgement: "Judgement") -> None:
        self.input_tokens += judgement.input_tokens
        self.output_tokens += judgement.output_tokens
        self.calls += 1
        self.max_call = max(self.max_call,
                            judgement.input_tokens * PRICE_IN
                            + judgement.output_tokens * PRICE_OUT)


def _row(record_id: str, j: "Judgement") -> str:
    return json.dumps({"unique_id": record_id, "decision": j.decision,
                       "amazon_id": j.amazon_id, "attribute": j.attribute,
                       "reasoning": j.reasoning,
                       "input_tokens": j.input_tokens,
                       "output_tokens": j.output_tokens}, sort_keys=True)


def load_checkpoint(path=CHECKPOINT_PATH, ledger: Ledger | None = None) -> dict:
    """Re-read completed records, and re-seed the ledger with what they cost.

    Seeding matters: a resumed run that started its ledger at zero would spend
    the whole ceiling again.
    """
    done: dict[str, dict] = {}
    if not path.exists():
        return done
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        done[row["unique_id"]] = row          # last write wins
    if ledger is not None:
        for row in done.values():
            ledger.input_tokens += row["input_tokens"]
            ledger.output_tokens += row["output_tokens"]
            ledger.calls += 1
            ledger.max_call = max(ledger.max_call,
                                  row["input_tokens"] * PRICE_IN
                                  + row["output_tokens"] * PRICE_OUT)
    return done


def run_experiment(responder: Responder, limit: int | None = None,
                   ledger: Ledger | None = None, checkpoint=CHECKPOINT_PATH,
                   inputs=None, progress=None) -> dict:
    """One call per record, checkpointed, stopping before the ceiling.

    Returns the results gathered plus why the run ended. A budget or credit
    stop is a normal outcome, not an exception to the caller: the partial
    result is on disk either way and resuming is the same call again.
    """
    table_a, table_b, columns, shortlists = inputs or load_inputs()
    ledger = ledger if ledger is not None else Ledger()
    results = load_checkpoint(checkpoint, ledger)

    pending = [r for r in sorted(shortlists) if r not in results]
    if limit is not None:
        pending = pending[:limit]

    stopped = None
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint.open("a") as fh:
        for n, rid in enumerate(pending, 1):
            try:
                ledger.check()
                j = judge(table_a.loc[rid], shortlist_frame(table_b, shortlists[rid]),
                          columns, responder)
            except (BudgetExhausted, CreditsExhausted) as exc:
                stopped = f"{type(exc).__name__}: {exc}"
                break
            ledger.add(j)
            results[rid] = json.loads(_row(rid, j))
            fh.write(_row(rid, j) + "\n")
            fh.flush()
            if progress and n % progress == 0:
                print(f"  {n:,}/{len(pending):,}  ${ledger.spent:.2f}", flush=True)

    return {"results": results, "completed": len(results),
            "attempted_this_run": ledger.calls, "spent": round(ledger.spent, 4),
            "stopped": stopped,
            "remaining": len([r for r in shortlists if r not in results])}
