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

- **No self-labelling either.** Do not hand-judge pairs to create a feedback
  signal — not 40, not 4 — even though doing so would never open a sealed file.
  Writing our own answer key defeats the purpose as thoroughly as reading the
  supplied one. This rules out learned blocking schemes of the `dedupe`/Zingg
  kind, tuning thresholds by eye, and any model trained on judgements we
  produced (including a language model standing in for a human judge). See
  [D19](docs/DECISIONS.md#d19--no-self-labelling-we-will-not-create-our-own-answer-key-either).
  The line: reasoning about the data's *structure* is fine; judging whether a
  specific pair is a match, and feeding that back into a design choice, is not.

If a proposed step would touch labelled data — or would manufacture a
substitute for it — stop and say so rather than running it.

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
system handles genuinely uncertain cases**. Rather than forcing every pair into
a binary verdict, the matcher may abstain — the established name for this is
**selective prediction**, and the standard way to report it is a
**risk-coverage curve**. Abstained pairs are routed for review, with sparing AI
escalation. Use that vocabulary rather than invented terms like "unsure band"
(see [D22](docs/DECISIONS.md#d22--how-the-two-systems-will-be-compared)).

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

**Decisions recorded: D1–D25.** Several supersede earlier ones — D14 replaced
D6 and voided the D9 baseline result; D17 and D18 changed settings first stated
in D16; D23 corrected how R3 had been described throughout. When two entries
disagree, the higher number wins.

## Blocking — complete

**Finalised, implemented in `src/blocking.py`, and fully documented.** Produces
**564,450 candidate pairs** from 56,376,996 possible (98.9988% reduction), with
**every record on both sides reachable** — no Walmart and no Amazon record is
excluded by construction.

The five rules, with their live settings:

| Rule | Matches on | Setting |
| --- | --- | --- |
| R1 | A shared word that is uncommon **on the Amazon side** | DF ≤ 100 |
| R2 | A shared part-number-shaped word (letters + digits) | length ≥ 5 |
| R3 | A shared brand-vocabulary term **plus two** other shared words | ≥ 2 words |
| R5 | A shared rare 5-character sequence. Word boundaries are collapsed **only where a digit sits next to them**, so split part numbers survive while ordinary words are not welded together | Amazon DF ≤ 50 |
| R4 | Nearest neighbours, **in both directions**, only for records nothing else reached | 100 neighbours |

Notes that matter for anyone reading the code:

- **R4 is kept, not dropped.** An earlier judgement that it was redundant was
  made while R5 was still broken; once the R5 noise was fixed that redundancy
  disappeared. It now runs **symmetrically** — rescuing stranded Amazon records
  as well as Walmart ones ([D17](docs/DECISIONS.md#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap))
  — with a **short-sequence fallback tier** (4-grams, then 3-grams) for records
  sharing no 5-gram with anything ([D20](docs/DECISIONS.md#d20--a-last-resort-tier-for-records-with-no-five-character-overlap)).
  With R3 included it currently rescues nobody, and is retained deliberately as
  a guarantee against a future threshold change reintroducing unreachable
  records.
- **R3 is not brand agreement**, despite its name. The brand vocabulary
  includes ordinary words such as `case` and `digital`, and records pick up
  brands they merely mention. See [D23](docs/DECISIONS.md#d23--correcting-how-r3-is-described)
  before reasoning about it.
- The rule definitions **are** now recorded — in
  [D16](docs/DECISIONS.md#d16--final-blocking-design-five-rules-and-the-thresholds-behind-them),
  [D17](docs/DECISIONS.md#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap)
  and [D23](docs/DECISIONS.md#d23--correcting-how-r3-is-described). An earlier
  version of this section said they were written down nowhere and told sessions
  to ask rather than read. That is no longer true.

Also done: a summary of what blocking discarded
([D21](docs/DECISIONS.md#d21--summarise-what-blocking-discards-rather-than-logging-it),
regenerated into `docs/blocking_diagnostics.json`), and a fixed
blocking↔matching interface contract in `src/interfaces.py`
([D22](docs/DECISIONS.md#d22--how-the-two-systems-will-be-compared)).

## Matching — designed, approved in part, **not yet built**

No matcher code exists. Splink is the engine. Approved so far:

- **Field plan.** `title` is the primary comparison; three derived array
  columns carry cross-field evidence (identifier tokens, brand terms, rare
  tokens); `price` included loosely; `category` **dropped** as a field-to-field
  comparison (the two retailers' taxonomies barely overlap — 55 categories
  versus 592, only 15 shared); `modelno` folded into the identifier tokens
  rather than compared as a column.
- **Conflicting-evidence design.** Multi-level comparisons rather than binary,
  missing values contributing **zero** weight rather than counting as
  disagreement, and expectation-maximisation learning the weights.
- **Integration path.** Splink cannot be handed an arbitrary pair list
  directly, so each record carries an array of the pair-keys it belongs to and
  blocking explodes that array. Tested at full scale: reproduces all 564,450
  pairs exactly, in about 30 seconds. Two gotchas: records with no candidates
  need an **empty** array (a shared placeholder silently pairs them with each
  other), and table aliases must be named so Walmart sorts first, or Splink
  returns the sides swapped.
- **Identifier token split.** Separate rare and common identifier arrays, since
  Splink's array comparison cannot weight by term frequency. For **matching
  only**, the definition is broadened to include long pure-numeric tokens.
  **Blocking's R2 definition is unchanged** — altering it would invalidate every
  measured blocking figure.
- **`probability_two_random_records_match` = 2.0e-05**, derived label-free and
  to be sensitivity-tested across [1e-05, 4e-05] at final evaluation
  ([D25](docs/DECISIONS.md#d25--the-prior-probability-that-two-random-records-match)).

**Still open, to settle before or during the build:**

1. **EM training blocking rules** — `estimate_parameters_using_expectation_maximisation`
   takes its own rules, separate from prediction. Not yet designed.
2. **The `title` comparison method.** Jaro-Winkler is built for short strings
   like names; product titles run ~100 characters, so token-based similarity is
   probably right. Undecided.
3. The DF ≤ 5 cutoff separating rare from common identifiers is inherited from
   blocking and untuned for matching.
4. Price comparison bands are unspecified.
5. **Clarification, not a question:** Splink's native term-frequency adjustment
   does not work on array comparisons. The rare/common split **is** the
   term-frequency mechanism for those columns.

## After matching

Selective prediction and review routing are designed but not built, and depend
on match scores existing ([D24](docs/DECISIONS.md#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai)):
the review interface shows evidence but never a recommendation, AI-only review
is measured for real, human-only review is modelled across a stated range of
assumed accuracies.

A **second, embedding-based system** follows, for comparison against the
classical one ([D22](docs/DECISIONS.md#d22--how-the-two-systems-will-be-compared)).
Labels stay sealed until both are finished, then one evaluation covers both.

73 tests currently pass.

Remember that under rule 5 every design choice is justified from data structure
only — no checking rules or thresholds against known matches.
