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

## 3. Never silently substitute data

**If something cannot be obtained or verified, say so clearly. Never fill the
gap.**

- No placeholder, synthetic, mock, or randomly generated data standing in for
  real data.
- No swapping in an alternate dataset or source without saying so **first** and
  getting agreement.
- When a source is used, state exactly where it came from, and verify it
  against published figures where possible rather than trusting it.
- A clearly reported failure is a better outcome than a quietly filled gap.

## 4. Dataset scope

- **Primary: Walmart-Amazon₂ (dirty)** — `data/raw/dirty_walmart_amazon/`.
  The system is built and evaluated on this.
- **Secondary: DBLP-ACM₂ (dirty)** — `data/raw/dirty_dblp_acm/`. A comparison
  and contrast case only, not the main focus.
- **Company (textual): deliberately deferred.** Evaluated and consciously set
  aside — network-blocked *and* too large for GitHub's file limit. This is a
  settled decision, not an open task; see [`docs/DATASETS.md`](docs/DATASETS.md)
  for the full reasoning. Do not re-investigate it or treat it as an oversight.

## 5. Project context

A portfolio project demonstrating **entity resolution** — matching records
across sources that refer to the same real-world company, with no shared ID.

Aimed at Forward Deployed Engineer roles, so the emphasis is on engineering
judgement, not just model accuracy. The distinguishing focus is **how the
system handles genuinely uncertain cases**: routing an explicit "unsure" band to
human review, with sparing AI escalation, rather than forcing every pair into a
binary match/no-match verdict.

**Splink** is the intended core matching engine.

## 6. Repository conventions

- Raw data in `data/raw/` is **never** edited in place. It is committed
  deliberately so the project is reproducible from a single clone.
- Reusable code lives in `src/`; exploration in `notebooks/`; written decisions
  and findings in `docs/`.
- Record significant decisions in `docs/` with the reasoning, so the repo
  explains *why*, not just *what*.
