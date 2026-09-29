"""Tests for the human-review recording tool.

The terminal review display hides answers and truth-derived stratum metadata.
The sample file retains ``stratum_hidden`` for later scoring, so it is not
truth-free. Tests below check the display fields and the guard against direct
answer-key fields separately.

Run with:  pytest
"""

import json

import pytest

from src.human_review import (FIELDS, OUTCOME_NONE, OUTCOME_UNSURE, completed,
                              parse_choice, render, revealed_ids, shown_ids,
                              strip_for_review)


def _item(n_members=3, tied=False):
    return {
        "walmart_id": "A_1", "reason": "review_tied",
        "walmart": {"title": "a thing", "brand": "acme", "modelno": "m1",
                    "category": "cat", "price": "9.99"},
        "candidate_blocks": [{
            "tied": tied, "shown": n_members, "true_size": n_members, "truncated": False,
            "members": [{"amazon_id": f"B_{i}", "bits": 9.5, "match_probability": 0.99,
                         "title": f"candidate {i}", "brand": "acme", "modelno": f"m{i}",
                         "category": "cat", "price": "8.00"} for i in range(n_members)]}],
        "allowed_outcomes": ["match", OUTCOME_NONE, OUTCOME_UNSURE],
    }


# --- what the reviewer is and is not shown ------------------------------------

def test_the_model_score_is_withheld():
    """Showing it would measure agreement with the model, not the judgement."""
    out = strip_for_review(_item())
    blob = json.dumps(out)
    assert "bits" not in blob and "match_probability" not in blob


def test_the_queue_bucket_is_withheld():
    """'This one was tied' would anchor the answer."""
    assert "reason" not in json.dumps(strip_for_review(_item()))


def test_candidate_identity_and_order_are_preserved():
    out = strip_for_review(_item(4))
    assert [m["amazon_id"] for m in out["blocks"][0]["members"]] == ["B_0", "B_1", "B_2", "B_3"]


def test_the_tie_flag_and_truncation_survive():
    """D32 and D33 fix these as part of the interface, not as decoration."""
    out = strip_for_review(_item(tied=True))
    assert out["blocks"][0]["tied"] is True
    assert "truncated" in out["blocks"][0] and "true_size" in out["blocks"][0]


def test_every_display_field_is_carried():
    out = strip_for_review(_item())
    assert set(out["walmart"]) == set(FIELDS)


# --- the keystrokes -----------------------------------------------------------

def test_a_number_selects_that_candidate():
    assert parse_choice("2", 3) == "pick:2"


def test_the_three_outcomes_map_correctly():
    assert parse_choice("n", 3) == OUTCOME_NONE
    assert parse_choice("?", 3) == OUTCOME_UNSURE


def test_an_out_of_range_number_is_refused_rather_than_clamped():
    assert parse_choice("4", 3) is None
    assert parse_choice("0", 3) is None


def test_junk_is_refused():
    assert parse_choice("", 3) is None and parse_choice("yes", 3) is None


# --- rendering ----------------------------------------------------------------

def test_the_page_numbers_candidates_from_one():
    page = render(strip_for_review(_item(3)), 1, 10)
    assert "[1]" in page and "[3]" in page and "[4]" not in page


def test_a_tie_is_announced_without_naming_the_bucket():
    page = render(strip_for_review(_item(2, tied=True)), 1, 10)
    assert "cannot separate" in page
    assert "review_tied" not in page


def test_empty_fields_are_omitted_rather_than_shown_as_none():
    item = _item()
    item["walmart"]["brand"] = None
    page = render(strip_for_review(item), 1, 10)
    assert "None" not in page


# --- resuming -----------------------------------------------------------------

def test_an_absent_log_means_nothing_is_done(tmp_path):
    assert completed(tmp_path / "nope.jsonl") == set()


def test_recorded_sequences_are_read_back(tmp_path):
    p = tmp_path / "log.jsonl"
    p.write_text('{"seq": 1}\n\n{"seq": 5}\n')
    assert completed(p) == {1, 5}


# --- the exclusion ------------------------------------------------------------

def test_the_revealed_set_is_read_from_the_site_bundle():
    """71 of these overlap the queue and must not be sampled."""
    assert len(revealed_ids()) == 120


def test_a_missing_site_bundle_does_not_silently_pass(tmp_path):
    """Returning an empty set would let contaminated records into the sample,
    so the caller must be able to tell the difference."""
    assert revealed_ids(tmp_path / "absent.json") == set()


def test_shown_ids_flattens_every_block():
    item = _item(2)
    item["candidate_blocks"].append(dict(item["candidate_blocks"][0]))
    assert len(shown_ids(item)) == 4


# --- the leak guard -----------------------------------------------------------

def test_the_guard_catches_an_answer_key_field():
    from src.human_review import assert_no_answer
    with pytest.raises(AssertionError, match="leaks an answer"):
        assert_no_answer({"items": [{"walmart_id": "A_1", "truth": ["B_2"]}]})


def test_the_guard_reports_where_the_leak_is():
    from src.human_review import assert_no_answer
    with pytest.raises(AssertionError, match=r"/items\[0\]/label"):
        assert_no_answer({"items": [{"label": 1}]})


def test_a_product_called_a_label_is_not_a_leak():
    """270 queued records are Avery label sheets. The first version of this
    guard scanned for the substring and fired on all of them."""
    from src.human_review import assert_no_answer
    assert_no_answer({"items": [{"walmart": {"title": "avery 5692 laser cd dvd labels"}}]})


# --- interrupted timings ------------------------------------------------------

def test_a_long_gap_is_flagged_not_averaged_in():
    """The trial had one record absorb a 9.9-hour shutdown, which moved the
    mean from 12.5 seconds to 2,404 without anything looking wrong."""
    from src.human_review import INTERRUPTED_SECONDS
    assert INTERRUPTED_SECONDS == 300
    assert 35815.6 > INTERRUPTED_SECONDS and 80.9 < INTERRUPTED_SECONDS


def test_the_judgement_survives_an_interrupted_timing():
    """Only the clock is unreliable after a gap. The reviewer still answered."""
    import inspect
    from src import human_review
    src = inspect.getsource(human_review.run_session)
    assert '"interrupted": interrupted' in src
    assert '"outcome": outcome' in src


# --- abstentions (pre-registration 14.5, amended 27 September 2026) -----------

def test_the_headline_false_match_rate_counts_every_record():
    """3 false matches among 10 records is 30%, not 50% of the 6 decided."""
    from src.human_review import score_session
    import inspect
    src = inspect.getsource(score_session)
    assert '"rate": rate(b["false_match"], b["n"])' in src


def test_the_decided_only_rate_is_reported_beside_it():
    """Publishing only the lower of two defensible figures would be a choice
    made after seeing which was lower."""
    from src.human_review import score_session
    import inspect
    assert "rate_decided_only" in inspect.getsource(score_session)


def test_abstention_is_a_measure_not_a_discard():
    """D24 modelled a uniform error rate with no abstention at all."""
    from src.human_review import score_session
    import inspect
    src = inspect.getsource(score_session)
    assert '"abstention_rate"' in src and "stratum_a" in src and "stratum_b" in src


# --- reducing the sample (14.3, amended 27 September 2026) --------------------

def _sample_file(tmp_path, n_each=6):
    import json
    items = []
    for s in range(n_each * 2):
        items.append({"seq": s + 1, "stratum_hidden": "A" if s % 2 == 0 else "B",
                      "repeat_of": None, "walmart_id": f"A_{s}", "walmart": {},
                      "blocks": [], "allowed_outcomes": []})
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"items": items, "per_stratum": n_each, "repeats": 0,
                             "presentations": len(items)}))
    return p


def test_reducing_never_discards_a_reviewed_record(tmp_path):
    from src.human_review import truncate_sample
    s = _sample_file(tmp_path, 6)
    log = tmp_path / "l.jsonl"
    log.write_text("\n".join(f'{{"seq": {i}}}' for i in range(1, 5)) + "\n")
    out = truncate_sample(2, s, log)
    assert out["already_done"] == 4
    assert out["per_stratum"] == {"A": 2, "B": 2}


def test_reducing_refuses_rather_than_dropping_reviewed_work(tmp_path):
    """A cut small enough to orphan a scored record must fail loudly."""
    from src.human_review import truncate_sample
    s = _sample_file(tmp_path, 6)
    log = tmp_path / "l.jsonl"
    log.write_text("\n".join(f'{{"seq": {i}}}' for i in range(1, 11)) + "\n")
    with pytest.raises(AssertionError, match="discard reviewed records"):
        truncate_sample(2, s, log)


def test_the_reduction_is_recorded_in_the_sample(tmp_path):
    import json
    from src.human_review import truncate_sample
    s = _sample_file(tmp_path, 6)
    log = tmp_path / "l.jsonl"; log.write_text("")
    truncate_sample(3, s, log)
    meta = json.loads(s.read_text())["reduced_from"]
    assert meta["per_stratum"] == 60 and meta["presentations"] == 138


def test_repeats_stay_proportional_when_the_sample_shrinks(tmp_path):
    from src.human_review import truncate_sample
    s = _sample_file(tmp_path, 10)
    log = tmp_path / "l.jsonl"; log.write_text("")
    assert truncate_sample(10, s, log)["repeats"] == 3


# --- the counter -------------------------------------------------------------

def test_the_counter_never_exceeds_the_total_after_truncation(tmp_path):
    """A reviewer saw "70 of 69": render was passed seq, which has gaps once
    truncate_sample keeps original numbering so an existing log still joins."""
    import itertools, json
    from src.human_review import run_session

    items = [{"seq": s, "stratum_hidden": "A", "repeat_of": None,
              "walmart_id": f"A_{s}", "walmart": {"title": "t"},
              "blocks": [{"tied": False, "truncated": False, "true_size": 1,
                          "members": [{"amazon_id": "B_1", "title": "c"}]}],
              "allowed_outcomes": []} for s in (1, 5, 70)]          # deliberate gaps
    s = tmp_path / "s.json"
    s.write_text(json.dumps({"items": items, "presentations": len(items)}))

    pages = []
    script = itertools.cycle(["n"])
    run_session(s, tmp_path / "l.jsonl", reader=lambda _: next(script),
                writer=lambda *a: pages.append(" ".join(str(x) for x in a)))
    shown = [p for p in pages if " of 3" in p]
    assert len(shown) == 3
    for n, page in enumerate(shown, 1):
        assert f" {n} of 3" in page, f"expected position {n}, got: {page.splitlines()[1]}"
