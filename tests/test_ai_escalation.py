"""Tests for the AI escalation arm.

No test makes a network call. A mock responder stands in for the API, which is
what allows the whole arm - prompt, parsing, three orderings, the stability
gate, and the recorded result - to be exercised end to end before a key exists.

The test that matters most is that the mock can never stand in *silently*: with
no credentials the module must raise rather than produce invented answers, since
a fabricated result that looks real is worse than no result.

Run with:  pytest
"""

import json
import os
from pathlib import Path

import pytest

import src.ai_escalation as ai
from src.ai_escalation import (
    MIN_UNANIMOUS_AGREEMENT,
    SHUFFLE_SALTS,
    CONTROL_SALT,
    Decision,
    RecordRuns,
    Response,
    judge,
    judge_with_shuffles,
    majority_decision,
    parse_decision,
    render_prompt,
    run,
    stability,
)


def item(record_id="A_0", n_tied=3, truncated=False, true_size=None):
    members = [{"amazon_id": f"B_{i}", "bits": 7.0, "match_probability": 0.99,
                "title": f"widget variant {i}", "brand": "acme",
                "modelno": f"m{i}", "price": "10.00", "category": "tools"}
               for i in range(n_tied)]
    return {
        "walmart_id": record_id,
        "walmart": {"title": "widget variant 2", "brand": "acme",
                    "modelno": "m2", "price": "10.00", "category": "tools"},
        "reason": "review_tied",
        "best_bits": 7.0, "margin_bits": 0.0,
        "candidate_blocks": [{
            "tied": n_tied > 1, "members": members, "shown": len(members),
            "true_size": true_size or len(members), "truncated": truncated,
        }],
        "total_candidates_above_floor": true_size or len(members),
        "allowed_outcomes": ["match", "none_of_these", "cannot_tell"],
        "decision": None,
    }


def replying(*texts):
    """A responder that returns the given texts in order, then repeats the last."""
    calls = []

    def respond(prompt):
        calls.append(prompt)
        text = texts[min(len(calls) - 1, len(texts) - 1)]
        return Response(text=text, input_tokens=100, output_tokens=20)

    respond.calls = calls
    return respond


MATCH = '{"decision": "match", "amazon_id": "B_1", "reasoning": "same model."}'
NONE = '{"decision": "none_of_these", "amazon_id": null, "reasoning": "no match."}'


# --- the guard ----------------------------------------------------------------

def test_the_real_responder_refuses_to_run_without_credentials(monkeypatch):
    """The mock is for tests. It is never a fallback for a missing key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(ai, "ENV_FILE", Path("/nonexistent"))
    with pytest.raises(RuntimeError):
        ai.openai_responder()


def test_the_model_is_the_dated_snapshot_the_amendment_names():
    """A floating alias could be repointed under a pre-registered experiment."""
    assert ai.MODEL == "gpt-5.4-mini-2026-03-17"
    assert ai.TEMPERATURE == 0


def test_a_malformed_reply_is_an_error_not_an_abstention():
    """Turning unparseable output into 'cannot_tell' would hide a broken prompt
    behind a plausible-looking result."""
    with pytest.raises(ValueError):
        parse_decision("I think it's probably the second one.")


# --- the prompt ---------------------------------------------------------------

def test_the_prompt_never_shows_the_model_a_score():
    """Supplying the classical system's scores would anchor the model to the
    tie and destroy the independence the comparison depends on."""
    prompt = render_prompt(item())
    for leaked in ("bits", "match_probability", "0.99", "7.0"):
        assert leaked not in prompt


def test_the_prompt_carries_both_records_and_the_candidate_ids():
    prompt = render_prompt(item(n_tied=2))
    assert "widget variant 2" in prompt
    assert "B_0" in prompt and "B_1" in prompt


def test_the_prompt_uses_no_rank_numerals_for_tied_candidates():
    prompt = render_prompt(item(n_tied=4))
    assert "1." not in prompt and "2." not in prompt


def test_truncation_is_disclosed_to_the_model():
    """The same disclosure D33 requires for a person."""
    prompt = render_prompt(item(n_tied=5, truncated=True, true_size=221))
    assert "showing 5 of 221" in prompt


def test_the_schema_and_the_three_outcomes_are_in_the_prompt():
    prompt = render_prompt(item())
    for outcome in ("match", "none_of_these", "cannot_tell"):
        assert outcome in prompt


def test_different_orderings_produce_different_prompts():
    """If they did not, the stability check would measure nothing."""
    prompts = {render_prompt(item(n_tied=8), salt) for salt in SHUFFLE_SALTS}
    assert len(prompts) > 1


def test_ordering_is_reproducible_for_a_given_run():
    assert render_prompt(item(n_tied=8), "#run2") == render_prompt(item(n_tied=8), "#run2")


# --- parsing ------------------------------------------------------------------

def test_a_valid_match_is_parsed():
    assert parse_decision(MATCH) == ("match", "B_1", "same model.")


def test_none_of_these_carries_no_candidate():
    assert parse_decision(NONE)[:2] == ("none_of_these", None)


def test_json_surrounded_by_prose_is_still_read():
    assert parse_decision(f"Here is my answer:\n{MATCH}\nHope that helps.")[0] == "match"


def test_an_unknown_decision_is_rejected():
    with pytest.raises(ValueError):
        parse_decision('{"decision": "probably", "amazon_id": "B_1"}')


def test_a_match_without_a_candidate_is_rejected():
    with pytest.raises(ValueError):
        parse_decision('{"decision": "match", "amazon_id": null, "reasoning": ""}')


def test_a_candidate_named_alongside_an_abstention_is_discarded():
    assert parse_decision(
        '{"decision": "cannot_tell", "amazon_id": "B_1", "reasoning": ""}')[1] is None


# --- judging ------------------------------------------------------------------

def test_judging_records_the_token_cost():
    d = judge(item(), replying(MATCH))
    assert (d.input_tokens, d.output_tokens) == (100, 20)


def test_each_record_is_judged_once_per_ordering_plus_a_control():
    responder = replying(MATCH)
    record = judge_with_shuffles(item(n_tied=6), responder)
    assert len(record.orderings) == len(SHUFFLE_SALTS)
    assert len(responder.calls) == len(SHUFFLE_SALTS) + 1, "the control is a fourth call"
    assert len(set(responder.calls)) > 1, "the orderings must actually differ"


def test_the_control_repeats_the_first_ordering_exactly():
    """Only then is a disagreement attributable to sampling rather than order."""
    responder = replying(MATCH)
    judge_with_shuffles(item(n_tied=6), responder)
    assert CONTROL_SALT == SHUFFLE_SALTS[0]
    assert responder.calls[-1] == responder.calls[0]


# --- stability ----------------------------------------------------------------

def _runs(keys, control=None):
    orderings = [Decision(d, a, "") for d, a in keys]
    ctrl = Decision(*control, "") if control else orderings[0]
    return {"A_0": RecordRuns(orderings=orderings, control=ctrl)}


def test_three_identical_answers_are_unanimous():
    gate = stability(_runs([("match", "B_1")] * 3), {"A_0": item()})
    assert gate["unanimous"] == 1 and gate["unanimous_rate"] == 1.0


def test_one_differing_answer_breaks_unanimity():
    gate = stability(_runs([("match", "B_1"), ("match", "B_2"), ("match", "B_1")]),
                     {"A_0": item()})
    assert gate["unanimous"] == 0


def test_abstentions_agree_regardless_of_named_candidate():
    """'none of these' names no candidate, so it cannot disagree with itself."""
    gate = stability(_runs([("none_of_these", None)] * 3), {"A_0": item()})
    assert gate["unanimous"] == 1


def _same(key, n=3):
    d = Decision(*key, "")
    return RecordRuns(orderings=[d] * n, control=d)


def test_the_gate_fails_below_the_floor():
    runs = {f"A_{i}": _same(("match", f"B_{i % 2}")) for i in range(10)}
    for i in range(6):                       # six of ten made inconsistent
        mixed = [Decision("match", "B_0", ""), Decision("match", "B_1", ""),
                 Decision("match", "B_0", "")]
        runs[f"A_{i}"] = RecordRuns(orderings=mixed, control=mixed[0])
    gate = stability(runs, {k: item(k, n_tied=20) for k in runs})
    assert gate["unanimous_rate"] == pytest.approx(0.4)
    assert not gate["meets_floor"] and not gate["passes"]


def test_the_gate_requires_beating_chance_as_well_as_the_floor():
    """A record with few options agrees often by luck; the floor alone would
    let that through."""
    runs = {f"A_{i}": _same(("match", "B_0")) for i in range(10)}
    tiny = {k: item(k, n_tied=1) for k in runs}          # 1 candidate + 2 outcomes
    gate = stability(runs, tiny)
    assert gate["expected_rate_by_chance"] == pytest.approx(1 / 9)
    assert gate["passes"], "perfect agreement should still pass"
    assert gate["floor"] == MIN_UNANIMOUS_AGREEMENT


def test_majority_wins_when_the_orderings_disagree():
    decisions = [Decision("match", "B_1", ""), Decision("match", "B_2", ""),
                 Decision("match", "B_1", "")]
    assert majority_decision(decisions).amazon_id == "B_1"


# --- end to end ---------------------------------------------------------------

def test_the_whole_arm_runs_against_a_mock():
    items = [item("A_0", n_tied=3), item("A_1", n_tied=2)]
    results, gate = run(items, replying(MATCH))
    assert set(results) == {"A_0", "A_1"}
    assert results["A_0"]["decision"] == "match"
    assert results["A_0"]["unanimous"] is True
    assert len(results["A_0"]["runs"]) == len(SHUFFLE_SALTS)
    assert results["A_0"]["input_tokens"] == 400      # three orderings plus control
    assert gate["records"] == 2
    json.dumps(results)                                # must be serialisable


def test_a_disagreeing_arm_is_recorded_as_not_unanimous():
    responder = replying(MATCH, NONE, MATCH)
    results, _ = run([item("A_0", n_tied=3)], responder)
    assert results["A_0"]["unanimous"] is False
    assert results["A_0"]["decision"] == "match"       # two of three


# --- credentials --------------------------------------------------------------

def test_the_env_file_is_parsed_without_overriding_the_shell(tmp_path, monkeypatch):
    """An exported key wins, so a stale file cannot silently replace it."""
    env = tmp_path / ".env"
    env.write_text('# a comment\n\nOPENAI_API_KEY="from-file"\nOTHER=plain\n')
    monkeypatch.setenv("OPENAI_API_KEY", "from-shell")
    monkeypatch.delenv("OTHER", raising=False)

    found = ai.load_env_file(env)

    assert found == {"OPENAI_API_KEY": "from-file", "OTHER": "plain"}
    assert os.environ["OPENAI_API_KEY"] == "from-shell"   # shell wins
    assert os.environ["OTHER"] == "plain"                 # file fills the gap


def test_a_missing_env_file_is_not_an_error(tmp_path):
    assert ai.load_env_file(tmp_path / "absent") == {}


def test_the_untouched_placeholder_counts_as_no_key(monkeypatch):
    """A forgotten placeholder must fail clearly, not as an auth error later."""
    monkeypatch.setenv("OPENAI_API_KEY", ai.PLACEHOLDER_KEY)
    monkeypatch.setattr(ai, "ENV_FILE", Path("/nonexistent"))
    with pytest.raises(RuntimeError, match="not set"):
        ai.require_api_key()


def test_a_real_looking_key_is_accepted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-value")
    monkeypatch.setattr(ai, "ENV_FILE", Path("/nonexistent"))
    assert ai.require_api_key() == "sk-test-value"


# --- the same-ordering control ------------------------------------------------

def test_a_flip_against_the_control_is_counted_as_sampling_noise():
    """The control saw an identical prompt, so a disagreement cannot be
    position bias - there was no change in position."""
    runs = _runs([("match", "B_1")] * 3, control=("match", "B_2"))
    gate = stability(runs, {"A_0": item()})
    assert gate["control_flips"] == 1
    assert gate["control_flip_rate"] == 1.0
    assert gate["unanimous_rate"] == 1.0, "the orderings still agreed among themselves"


def test_a_stable_control_reports_no_noise():
    gate = stability(_runs([("match", "B_1")] * 3), {"A_0": item()})
    assert gate["control_flips"] == 0 and gate["control_flip_rate"] == 0.0


def test_the_control_does_not_by_itself_fail_the_gate():
    """It caps how much instability can be blamed on presentation; it is
    reported alongside rather than used to disqualify."""
    runs = {f"A_{i}": _runs([("match", "B_1")] * 3, control=("match", "B_2"))["A_0"]
            for i in range(10)}
    gate = stability(runs, {k: item(k) for k in runs})
    assert gate["control_flip_rate"] == 1.0
    assert gate["passes"], "the gate turns on the orderings, not the control"


def test_the_control_outcome_is_recorded_per_record():
    results, gate = run([item("A_0", n_tied=3)], replying(MATCH))
    assert results["A_0"]["control_flipped"] is False
    assert results["A_0"]["control"]["decision"] == "match"
    assert "control_flip_rate" in gate
