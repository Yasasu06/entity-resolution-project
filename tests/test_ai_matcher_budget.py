"""Tests for the spend ceiling and the checkpoint.

No test makes a network call. These exist because the run they guard cannot be
repeated: the credit is fixed at $5.00 and is not extensible. A bug that wastes
calls here is not a failing test, it is a run that cannot be finished.

Run with:  pytest
"""

import json

import pandas as pd
import pytest

from src.ai_escalation import Response
from src.ai_matcher import (
    MAX_TOKENS, BudgetExhausted, CreditsExhausted, Ledger, load_checkpoint,
    run_experiment)


def _inputs(n=6):
    """A stand-in for load_inputs(), so no data files are touched."""
    table_a = pd.DataFrame([{"unique_id": f"A_{i}", "title": f"walmart {i}",
                             "brand": "acme"} for i in range(n)]).set_index("unique_id")
    table_b = pd.DataFrame([{"unique_id": f"B_{i}", "title": f"amazon {i}",
                             "brand": "acme"} for i in range(n)]).set_index("unique_id")
    shortlists = {f"A_{i}": [f"B_{i}"] for i in range(n)}
    return table_a, table_b, ["title", "brand"], shortlists


def responder(in_tok=1000, out_tok=100, fail_after=None):
    calls = {"n": 0}

    def respond(prompt):
        calls["n"] += 1
        if fail_after is not None and calls["n"] > fail_after:
            raise CreditsExhausted("no credits remaining")
        return Response(text='{"decision": "none_of_these", "distinguishing_attribute": "brand"}',
                        input_tokens=in_tok, output_tokens=out_tok)

    respond.calls = calls
    return respond


# --- the ceiling ----------------------------------------------------------

def test_the_ceiling_is_checked_before_the_call_not_after():
    """A ledger already at the limit refuses without spending anything."""
    led = Ledger(ceiling=0.01)
    led.input_tokens = 100_000          # $0.075, over a $0.01 ceiling
    with pytest.raises(BudgetExhausted):
        led.check()


def test_the_reserve_is_the_worst_a_single_call_can_cost():
    led = Ledger()
    assert led.worst_case_next == pytest.approx(2768 * 0.75e-6 + MAX_TOKENS * 4.5e-6)


def test_a_run_stops_at_the_ceiling_and_never_crosses_it(tmp_path):
    cp = tmp_path / "c.jsonl"
    r = responder(in_tok=1_000_000)     # $0.75 a call
    out = run_experiment(r, ledger=Ledger(ceiling=2.0), checkpoint=cp,
                         inputs=_inputs(n=6))
    assert out["spent"] <= 2.0
    assert out["stopped"].startswith("BudgetExhausted")
    assert r.calls["n"] == 2            # a third would have reserved past 2.0


def test_the_ceiling_holds_across_a_resume(tmp_path):
    """The second run must not start its ledger at zero."""
    cp = tmp_path / "c.jsonl"
    inp = _inputs(n=6)
    run_experiment(responder(in_tok=1_000_000), ledger=Ledger(ceiling=2.0),
                   checkpoint=cp, inputs=inp)
    r2 = responder(in_tok=1_000_000)
    out = run_experiment(r2, ledger=Ledger(ceiling=2.0), checkpoint=cp, inputs=inp)
    assert r2.calls["n"] == 0           # the budget was already gone
    assert out["spent"] <= 2.0


# --- the checkpoint -------------------------------------------------------

def test_every_completed_record_is_on_disk_immediately(tmp_path):
    cp = tmp_path / "c.jsonl"
    run_experiment(responder(), checkpoint=cp, inputs=_inputs(n=4))
    rows = [json.loads(x) for x in cp.read_text().splitlines()]
    assert len(rows) == 4
    assert {r["unique_id"] for r in rows} == {f"A_{i}" for i in range(4)}


def test_per_call_tokens_are_recorded(tmp_path):
    """The first run kept only totals, so the distribution was unrecoverable."""
    cp = tmp_path / "c.jsonl"
    run_experiment(responder(in_tok=1234, out_tok=56), checkpoint=cp, inputs=_inputs(n=2))
    row = json.loads(cp.read_text().splitlines()[0])
    assert row["input_tokens"] == 1234 and row["output_tokens"] == 56


def test_a_resumed_run_skips_what_is_already_done(tmp_path):
    cp = tmp_path / "c.jsonl"
    inp = _inputs(n=6)
    run_experiment(responder(fail_after=3), checkpoint=cp, inputs=inp)
    r2 = responder()
    out = run_experiment(r2, checkpoint=cp, inputs=inp)
    assert r2.calls["n"] == 3           # only the three that never ran
    assert out["completed"] == 6 and out["remaining"] == 0


def test_credit_exhaustion_stops_the_run_rather_than_recording_failures(tmp_path):
    """The first stability run kept calling and stored 225 failures as data."""
    cp = tmp_path / "c.jsonl"
    r = responder(fail_after=2)
    out = run_experiment(r, checkpoint=cp, inputs=_inputs(n=6))
    assert out["stopped"].startswith("CreditsExhausted")
    assert out["completed"] == 2
    assert r.calls["n"] == 3            # the failing call, then no more
    assert len(cp.read_text().splitlines()) == 2


def test_the_ledger_is_reseeded_from_the_checkpoint(tmp_path):
    cp = tmp_path / "c.jsonl"
    run_experiment(responder(in_tok=1000, out_tok=100), checkpoint=cp, inputs=_inputs(n=3))
    led = Ledger()
    load_checkpoint(cp, led)
    assert led.calls == 3 and led.input_tokens == 3000 and led.output_tokens == 300


def test_an_absent_checkpoint_is_an_empty_start(tmp_path):
    assert load_checkpoint(tmp_path / "nope.jsonl") == {}


def test_a_call_dearer_than_assumed_raises_the_reserve(tmp_path):
    """The ceiling must not depend on LARGEST_PROMPT being a true maximum.

    Written after the two tests above failed: with a fixed reserve, calls
    costing more than assumed walked straight through the ceiling.
    """
    led = Ledger(ceiling=2.0)
    assert led.worst_case_next < 0.01            # the static assumption
    run_experiment(responder(in_tok=1_000_000), ledger=led, checkpoint=tmp_path / "c.jsonl",
                   inputs=_inputs(n=6))
    assert led.worst_case_next > 0.74            # corrected by observation
    assert led.spent <= 2.0
