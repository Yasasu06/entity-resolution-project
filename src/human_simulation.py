"""The human-only review arm, modelled rather than observed.

⚠️ **ASSUMPTION — a model, not an observation.** No human reviews these records.
Reviewer accuracy is a supplied input, and the results are a sensitivity
analysis across a declared range, not a measurement. This is
[D24](../docs/DECISIONS.md)'s position: of the three approaches to handling
abstained pairs, only the AI arm can honestly be measured here.

Everything below was fixed in ``docs/PRE_REGISTRATION.md`` section 6.4 before it
was written.

**This module never opens a labelled file.** Truth is passed in as an argument,
so the module is fully testable with invented labels and cannot itself breach
the seal. The caller supplies real labels once, at final evaluation.

**It cannot produce a number before unsealing**, because simulating a reviewer
who is right 90% of the time requires knowing what right is.

**The display ceiling is reported separately, not folded into accuracy.** A
reviewer can only choose among the candidates D33 displays. Where the true
partner was truncated away, a reviewer of *any* accuracy answers wrongly - they
would correctly say "none of these" given what they saw, and be scored wrong.
That ceiling is set by this project's display rule, not by human fallibility,
and it is the honest measurement of what D33's choice of ten extra candidates
cost.
"""

import random

# Fixed in section 6.4. A single invented figure would hide how much the
# conclusion depends on it; a range makes that dependence visible.
ACCURACIES = (0.80, 0.90, 0.95, 1.00)

MATCH = "match"
NONE_OF_THESE = "none_of_these"


def displayed_candidates(item: dict) -> list[str]:
    """Every Amazon id the reviewer can actually see for this record."""
    return [m["amazon_id"] for block in item["candidate_blocks"] for m in block["members"]]


def correct_outcome(item: dict, truth: dict[str, set[str]]) -> tuple[str, str | None]:
    """What a perfect reviewer would answer, given only what is on screen.

    If the true partner is not displayed, the correct answer *from the screen* is
    "none of these" - which the answer key will score as wrong. That gap is the
    display ceiling, and it belongs to the interface rather than to the reviewer.
    """
    partners = truth.get(item["walmart_id"], set())
    for amazon_id in displayed_candidates(item):
        if amazon_id in partners:
            return (MATCH, amazon_id)
    return (NONE_OF_THESE, None)


def is_reachable(item: dict, truth: dict[str, set[str]]) -> bool:
    """True when a true partner exists and is on screen, so a reviewer could
    possibly get it right."""
    partners = truth.get(item["walmart_id"], set())
    if not partners:
        return True          # "none of these" is correct and is answerable
    return bool(partners & set(displayed_candidates(item)))


def display_ceiling(items: list[dict], truth: dict[str, set[str]]) -> dict:
    """The best accuracy any reviewer could achieve against the answer key."""
    reachable = sum(is_reachable(i, truth) for i in items)
    total = len(items)
    return {
        "items": total,
        "reachable": reachable,
        "unreachable": total - reachable,
        "ceiling": reachable / total if total else 0.0,
    }


def simulate(
    items: list[dict], truth: dict[str, set[str]], accuracy: float, seed: int = 0
) -> dict[str, tuple[str, str | None]]:
    """One reviewer's decisions at a given accuracy.

    With probability ``accuracy`` the reviewer returns the correct answer for
    what is on screen. Otherwise they choose **uniformly** among the displayed
    candidates and "none of these".

    Uniform is deliberate (section 6.4). Weighting the error by match score would
    smuggle the classical system's opinion into the arm that is supposed to be
    independent of it, and would flatter the comparison in a way no reader could
    detect from the result.
    """
    rng = random.Random(seed)
    decisions = {}
    for item in items:
        shown = displayed_candidates(item)
        if rng.random() < accuracy:
            decisions[item["walmart_id"]] = correct_outcome(item, truth)
        else:
            choice = rng.choice([*shown, None])
            decisions[item["walmart_id"]] = (
                (MATCH, choice) if choice is not None else (NONE_OF_THESE, None))
    return decisions


def score(
    decisions: dict[str, tuple[str, str | None]], truth: dict[str, set[str]]
) -> dict:
    """Score decisions against the answer key."""
    correct = tp = fp = fn = 0
    for record_id, (kind, amazon_id) in decisions.items():
        partners = truth.get(record_id, set())
        if kind == MATCH:
            if amazon_id in partners:
                correct += 1; tp += 1
            else:
                fp += 1
                if partners:
                    fn += 1
        else:
            if partners:
                fn += 1
            else:
                correct += 1
    n = len(decisions)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "decisions": n,
        "accuracy": correct / n if n else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0,
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
    }


def sweep(items: list[dict], truth: dict[str, set[str]], seed: int = 0) -> dict:
    """The full sensitivity analysis, with the ceiling reported alongside."""
    return {
        "display_ceiling": display_ceiling(items, truth),
        "by_accuracy": {a: score(simulate(items, truth, a, seed), truth)
                        for a in ACCURACIES},
    }
