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
