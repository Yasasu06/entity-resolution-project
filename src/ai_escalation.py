"""The AI-only review arm: escalating the queued records to a language model.

D24 splits human review into three approaches and measures exactly one of them.
This is that one. The model decides each queued record on its own, and those
decisions are scored against the answer key at final evaluation - making this
the project's headline result, and the answer to D7's question: how much of the
review queue can the AI clear, at what cost?

Everything about this arm was fixed in ``docs/PRE_REGISTRATION.md`` section 6
before it was run, including the prompt below. Nothing here decides anything.

Three things are worth knowing before reading the code.

**The model sees no scores.** The point of escalation is resolving what string
overlap cannot - 512MB against 32GB, smoke grey against hot pink. Supplying the
classical system's scores would anchor the model to the tie and destroy the
independence the comparison depends on. It gets record text only, exactly the
evidence a human reviewer would see under D33's display rule.

**Every record is judged three times, under three different orderings.** A
language model is exposed to position bias just as a person is. If its answer
changes when the candidates are shuffled, the judgement is being driven by
presentation rather than evidence. This check needs **no labels**, so it runs
before unsealing and can disqualify the arm before its accuracy is ever quoted.

**The mock responder is for tests only.** It is never a fallback for missing
credentials: without a key this module raises rather than quietly producing
invented answers, because a fabricated result that looks real is worse than no
result at all.

Run with ``python -m src.ai_escalation`` once ANTHROPIC_API_KEY is set.
"""

import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from src.interfaces import PROCESSED_DIR
from src.review_queue import QUEUE_PATH, REVIEW_OUTCOMES, REVIEW_TIED, _shuffled

# --- fixed in PRE_REGISTRATION.md section 6 -----------------------------------

MODEL = "claude-opus-5"
TEMPERATURE = 0
MAX_TOKENS = 512

# Three runs, three orderings. The salts only need to differ from each other.
SHUFFLE_SALTS = ("", "#run2", "#run3")

# The disqualification floor. Below this, two decisions in five turn on the
# order candidates happened to be displayed in, and reporting them as a measured
# result would misrepresent them. Recorded in advance as a judgement, not a
# measurement.
MIN_UNANIMOUS_AGREEMENT = 0.60

PROMPT_TEMPLATE = """\
You are matching product listings between two retailers. Decide whether the
Walmart listing below refers to the same real-world product as any one of the
Amazon listings.

WALMART LISTING
{walmart}

CANDIDATE AMAZON LISTINGS
{candidates}

Exactly one candidate may refer to the same product, or none may. Attributes
such as storage capacity, physical dimensions, colour, model number and product
variant distinguish otherwise similar products: two listings differing on any of
these are different products even when their descriptions are otherwise nearly
identical.

Respond with JSON only:
{{"decision": "match" | "none_of_these" | "cannot_tell",
 "amazon_id": "<id, or null>",
 "reasoning": "<one or two sentences>"}}

Choose "cannot_tell" only where the listings lack the information needed to
decide, not where the decision is merely difficult."""

FIELDS = ["title", "brand", "modelno", "price", "category"]

RESULTS_PATH = PROCESSED_DIR / "ai_escalation_classical.json"
STABILITY_PATH = PROCESSED_DIR / "ai_stability_classical.json"


@dataclass
class Response:
    """One model reply, with what it cost."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


# A responder takes a prompt and returns a Response. Keeping this pluggable is
# what lets the whole arm be tested end to end without a network call.
Responder = Callable[[str], Response]


@dataclass
class Decision:
    decision: str
    amazon_id: str | None
    reasoning: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: str = field(default="", repr=False)

    def key(self) -> tuple[str, str | None]:
        """What must agree across runs for the judgement to count as stable."""
        return (self.decision, self.amazon_id if self.decision == "match" else None)


# --- rendering ----------------------------------------------------------------

def _fields(record: dict) -> str:
    return "\n".join(f"  {f}: {record.get(f)}" for f in FIELDS
                     if record.get(f) not in (None, ""))


def render_candidates(item: dict, salt: str) -> str:
    """Render the candidate blocks as the reviewer sees them.

    No scores and no rank numerals. Tied members are reshuffled per run, which
    is the whole basis of the stability check. A truncated group states its true
    size, so the model is told when it is seeing a sample rather than a
    shortlist - the same disclosure D33 requires for a person.
    """
    lines = []
    for block in item["candidate_blocks"]:
        members = block["members"]
        if block["tied"]:
            members = _shuffled(members, item["walmart_id"], salt)
            note = f"  [{len(members)} listings the evidence cannot separate"
            if block["truncated"]:
                note += f"; showing {block['shown']} of {block['true_size']}"
            lines.append(note + "]")
        for member in members:
            lines.append(f"- id: {member['amazon_id']}")
            lines.append(_fields(member))
    return "\n".join(lines)


def render_prompt(item: dict, salt: str = "") -> str:
    return PROMPT_TEMPLATE.format(
        walmart=_fields(item["walmart"]), candidates=render_candidates(item, salt))


# --- parsing ------------------------------------------------------------------

def parse_decision(text: str) -> tuple[str, str | None, str]:
    """Pull the decision out of a reply, rejecting anything off-schema.

    A reply that cannot be parsed is an error, not a "cannot_tell": silently
    converting malformed output into a valid-looking abstention would hide a
    broken prompt behind a plausible result.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object in reply: {text[:120]!r}")
    payload = json.loads(match.group(0))

    decision = payload.get("decision")
    if decision not in REVIEW_OUTCOMES:
        raise ValueError(f"decision {decision!r} is not one of {REVIEW_OUTCOMES}")
    amazon_id = payload.get("amazon_id")
    if decision == "match" and not amazon_id:
        raise ValueError("decision 'match' without an amazon_id")
    if decision != "match":
        amazon_id = None
    return decision, amazon_id, str(payload.get("reasoning", ""))


def judge(item: dict, responder: Responder, salt: str = "") -> Decision:
    reply = responder(render_prompt(item, salt))
    decision, amazon_id, reasoning = parse_decision(reply.text)
    return Decision(decision, amazon_id, reasoning,
                    reply.input_tokens, reply.output_tokens, reply.text)


def judge_with_shuffles(item: dict, responder: Responder) -> list[Decision]:
    """Judge one record once per ordering."""
    return [judge(item, responder, salt) for salt in SHUFFLE_SALTS]


# --- stability ----------------------------------------------------------------

def _options(item: dict) -> int:
    """How many answers were available: every shown candidate, plus the two
    outcomes that name no candidate."""
    shown = sum(block["shown"] for block in item["candidate_blocks"])
    return shown + 2


def stability(runs: dict[str, list[Decision]], items: dict[str, dict]) -> dict:
    """Measure how often the three orderings agreed, and against what chance.

    Agreement alone is not enough: a record with two candidates would agree
    often by luck. The comparison is therefore against the agreement expected
    from choosing uniformly at random among that record's own options.
    """
    unanimous, expected = 0, 0.0
    for record_id, decisions in runs.items():
        keys = {d.key() for d in decisions}
        unanimous += len(keys) == 1
        k = _options(items[record_id])
        # probability that three uniform draws from k options all coincide
        expected += 1 / (k * k)

    n = len(runs)
    rate = unanimous / n if n else 0.0
    chance = expected / n if n else 0.0
    return {
        "records": n,
        "unanimous": unanimous,
        "unanimous_rate": rate,
        "expected_rate_by_chance": chance,
        "floor": MIN_UNANIMOUS_AGREEMENT,
        "beats_chance": rate > chance,
        "meets_floor": rate >= MIN_UNANIMOUS_AGREEMENT,
        "passes": rate >= MIN_UNANIMOUS_AGREEMENT and rate > chance,
    }


def majority_decision(decisions: list[Decision]) -> Decision:
    """The answer given most often across orderings; ties go to the first run."""
    counts = Counter(d.key() for d in decisions)
    best, _ = counts.most_common(1)[0]
    return next(d for d in decisions if d.key() == best)


# --- the real responder -------------------------------------------------------

def anthropic_responder() -> Responder:
    """Build a responder backed by the real API.

    Raises if the SDK or the key is missing. It deliberately does not fall back
    to anything: an arm that quietly produced invented answers would be worse
    than one that did not run.
    """
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "the 'anthropic' package is not installed; add it to requirements.txt"
        ) from exc
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set; this arm cannot run")

    client = anthropic.Anthropic()

    def respond(prompt: str) -> Response:
        reply = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        return Response(
            text="".join(block.text for block in reply.content
                         if getattr(block, "type", None) == "text"),
            input_tokens=reply.usage.input_tokens,
            output_tokens=reply.usage.output_tokens,
        )

    return respond


# --- running ------------------------------------------------------------------

def run(items: list[dict], responder: Responder) -> tuple[dict, dict]:
    """Judge every item three times and summarise stability."""
    runs = {item["walmart_id"]: judge_with_shuffles(item, responder) for item in items}
    by_id = {item["walmart_id"]: item for item in items}

    results = {}
    for record_id, decisions in runs.items():
        chosen = majority_decision(decisions)
        results[record_id] = {
            "decision": chosen.decision,
            "amazon_id": chosen.amazon_id,
            "reasoning": chosen.reasoning,
            "unanimous": len({d.key() for d in decisions}) == 1,
            "runs": [{"decision": d.decision, "amazon_id": d.amazon_id} for d in decisions],
            "input_tokens": sum(d.input_tokens for d in decisions),
            "output_tokens": sum(d.output_tokens for d in decisions),
        }
    return results, stability(runs, by_id)


def load_queue(tied_only: bool = True) -> list[dict]:
    """The validation slice is the tied records; the full arm is all of them."""
    items = json.loads(QUEUE_PATH.read_text())
    return [i for i in items if i["reason"] == REVIEW_TIED] if tied_only else items


def main(tied_only: bool = True) -> None:
    items = load_queue(tied_only)
    print(f"{len(items):,} records, {len(SHUFFLE_SALTS)} orderings each "
          f"= {len(items) * len(SHUFFLE_SALTS):,} calls to {MODEL}")

    results, gate = run(items, anthropic_responder())

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    STABILITY_PATH.write_text(json.dumps(gate, indent=2))

    tokens_in = sum(r["input_tokens"] for r in results.values())
    tokens_out = sum(r["output_tokens"] for r in results.values())
    print(f"\n  unanimous across orderings  {gate['unanimous']:,} of {gate['records']:,} "
          f"({gate['unanimous_rate']:.1%})")
    print(f"  expected by chance          {gate['expected_rate_by_chance']:.1%}")
    print(f"  floor                       {gate['floor']:.0%}")
    print(f"  stability gate              {'PASSED' if gate['passes'] else 'FAILED'}")
    print(f"\n  tokens                      {tokens_in:,} in, {tokens_out:,} out")
    print(f"  results written to          {RESULTS_PATH.name}")
    if not gate["passes"]:
        print("\n  The arm did not pass. Per the pre-registration this is reported")
        print("  as the finding; its accuracy is not presented as a headline result.")


if __name__ == "__main__":
    main()
