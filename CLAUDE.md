# Project rules

Standing instructions for this repository. These persist across sessions and
apply unless Yasaswi explicitly says otherwise in a given session.

## 1. Commit attribution

**Yasaswi is the sole author of every commit.**

- Do **not** add a `Co-Authored-By` trailer of any kind.
- Do **not** add session links, `Claude-Session:` lines, or any other
  AI/assistant attribution to commit messages, PR descriptions, or code
  comments.
- Git identity for this repo is `Yasaswi <yasaswishops@gmail.com>`.

This holds unless Yasaswi explicitly asks for attribution in a given session.

## 2. This is a learning project — explain, don't just execute

Yasaswi is relatively new to **Python, SQL, Git, and Docker**. The goal is
understanding, not just working code.

- Write clean, readable code with comments explaining *why*, not just *what*.
  Prefer an obvious approach over a clever one.
- Explain significant steps in **plain language a non-technical person could
  follow** — what a command does, why this approach over an alternative, and
  what the output means. Do not perform meaningful steps silently.
- Flag concepts worth understanding rather than assuming familiarity (e.g. what
  a virtual environment is for, why history rewrites need a force-push).
- Favour explicitness over magic and terseness.

## 3. Work in small, reviewable chunks — pause for confirmation

**Do not complete several steps and report them together.** Yasaswi reviews
each explanation carefully before responding, and large multi-part updates are
hard to review and approve properly.

- Do **one** meaningful chunk of work, then stop and report it.
- Pause for explicit confirmation after each design decision, before acting
  on it. A design that has been described is not a design that has been
  approved — wait for the word.
- Keep reports proportionate to the chunk. Depth of thinking should stay
  high; the *size of each delivery* is what shrinks.
- This is about pacing, not scope. Keep surfacing everything worth flagging —
  just introduce it a piece at a time rather than all at once.
- This applies to documents and explanations too, not only to code. Prefer one
  focused piece over a bundled multi-part deliverable.

If a task seems to need many steps, propose the sequence and let Yasaswi
approve it before starting, rather than working through it unprompted.

## 4. Never silently substitute data

**If something cannot be obtained or verified, say so clearly. Never fill the
gap.**

- No placeholder, synthetic, mock, or randomly generated data standing in for
  real data.
- No swapping in an alternate dataset or source without saying so **first** and
  getting agreement.
- When a source is used, state exactly where it came from, and verify it
  against published figures where possible rather than trusting it.
- A clearly reported failure is a better outcome than a quietly filled gap.

## 5. Strict no-peek on all labelled data

**No labelled answers — `train`, `valid` *or* `test` — are consulted for any
purpose until the entire system is built.** Then one single evaluation is run,
once. See [D14](docs/DECISIONS.md#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)
for the full reasoning and the trade-off being accepted deliberately.

- This includes checks that feel like ordinary due diligence. *"How many of the
  962 known true matches survive my blocking step?"* is a peek: if a rule is
  kept or dropped based on that number, the answer key has shaped the design.
- It includes reporting label counts or match percentages for a split.
  Describing the answer key is still using the answer key.
- Blocking rules, comparison logic and thresholds are all justified from the
  **structure of the data** — row counts, column names, missing-value rates,
  token frequency distributions, the documented corruption mechanism, and
  published benchmark totals. Never from label feedback.
- It is enforced in code, not by memory: `src/data_loading.py` refuses to open
  a labelled split without `unlock_final_evaluation=True`, the baseline refuses
  to run without `--unlock-final-evaluation`, and a test asserts all three
  splits are sealed by default. **Do not weaken or work around these guards.**
- Parts of [`docs/ASSESSMENT.md`](docs/ASSESSMENT.md) predate this rule and are
  **label-derived and quarantined** — they are flagged in that file and must not
  be used as design input. D14 lists exactly what is contaminated and what is
  safe.

If a proposed step would touch labelled data, stop and say so rather than
running it.

## 6. Dataset scope

- **Primary: Walmart-Amazon₂ (dirty)** — `data/raw/dirty_walmart_amazon/`.
  The system is built and evaluated on this.
- **Secondary: DBLP-ACM₂ (dirty)** — `data/raw/dirty_dblp_acm/`. A comparison
  and contrast case only, not the main focus.
- **Company (textual): deliberately deferred.** Evaluated and consciously set
  aside — network-blocked *and* too large for GitHub's file limit. This is a
  settled decision, not an open task; see [`docs/DATASETS.md`](docs/DATASETS.md)
  for the full reasoning. Do not re-investigate it or treat it as an oversight.

## 7. Project context

A portfolio project demonstrating **entity resolution** — matching records
across sources that refer to the same real-world company, with no shared ID.

Aimed at Forward Deployed Engineer roles, so the emphasis is on engineering
judgement, not just model accuracy. The distinguishing focus is **how the
system handles genuinely uncertain cases**: routing an explicit "unsure" band to
human review, with sparing AI escalation, rather than forcing every pair into a
binary match/no-match verdict.

**Splink** is the intended core matching engine.

## 8. Repository conventions

- Raw data in `data/raw/` is **never** edited in place. It is committed
  deliberately so the project is reproducible from a single clone.
- Reusable code lives in `src/`; exploration in `notebooks/`; written decisions
  and findings in `docs/`.
- Record significant decisions in `docs/` with the reasoning, so the repo
  explains *why*, not just *what*.

---

# Current project state

*Unlike the rules above, this section goes stale. Update it as the work moves.
Where it disagrees with [`docs/DECISIONS.md`](docs/DECISIONS.md), the decision
log wins.*

**Decisions recorded:** D1–D14. The most recent, D14 (strict no-peek),
supersedes D6 and invalidates the live status of the D9 baseline result.

**Blocking design — in progress.** Status as stated by Yasaswi on 2026-09-12:

- **R1, R2, R3 — approved.**
- **R5 — being fixed.** It currently matches across word boundaries — tokens
  glued together across a boundary — which is reported to produce roughly **79%
  noise**. The fix is to make it respect word boundaries. Instructions for that
  fix are coming separately.
- **R4 — pending re-verification.** R4 appeared redundant against the other
  rules, but that judgement was made while R5 was still unfixed. Re-check
  whether R4 is genuinely redundant **after** the R5 fix lands, then decide to
  keep or drop it.

> ⚠️ **The rule definitions themselves are not recorded anywhere in this
> repository** — not in `docs/`, not in `src/`, not in git history. Only the
> status above is written down. Do **not** reconstruct, guess, or re-derive what
> R1–R5 match on. Ask Yasaswi for the current definitions, and write them into
> `docs/DECISIONS.md` as a numbered decision — **after** the R5 fix lands.
>
> Writing them up is **deliberately deferred until then**, so the rules are
> documented accurately once rather than recorded now and immediately
> corrected. This is a settled decision, not an oversight. Do not pre-empt it.

Remember that under rule 5 the blocking design is justified from data structure
only — no checking rules against known matches.
