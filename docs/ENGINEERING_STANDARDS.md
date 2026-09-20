# Engineering standards

Standing constraints for this repository. They describe how the system is
built and why, and apply to any change made to it.

## 1. Code and documentation style

- Comments explain **why**, not what. The code already states what it does.
- Prefer an obvious implementation over a clever one. Where the two conflict,
  legibility wins.
- Favour explicitness over implicit behaviour.
- **Write in neutral third person.** Code comments, documentation, decision
  entries and commit messages describe the system and the reasoning behind it,
  not a narrator working on it. No first-person narrative, no personal framing,
  no commentary on who did what or how the work felt. This applies from the
  first draft — it is a writing standard, not something corrected afterwards.

## 2. Never silently substitute data

**If something cannot be obtained or verified, that is stated plainly. The gap
is never filled.**

- No placeholder, synthetic, mock, or randomly generated data standing in for
  real data.
- No alternate dataset or source is swapped in without that substitution being
  stated and agreed first.
- When a source is used, its exact origin is recorded, and it is verified
  against published figures where possible rather than trusted.
- A clearly reported failure is a better outcome than a quietly filled gap.

## 3. Strict no-peek on all labelled data

**No labelled answers — `train`, `valid` *or* `test` — are consulted for any
purpose until the entire system is built.** Then one single evaluation is run,
once. See [D14](DECISIONS.md#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)
for the full reasoning and the trade-off accepted deliberately.

- This includes checks that resemble ordinary due diligence. *"How many known
  true matches survive this blocking step?"* is a peek: if a rule is kept or
  dropped based on that number, the answer key has shaped the design.
- It includes reporting label counts or match percentages for a split.
  Describing the answer key is still using the answer key.
- Blocking rules, comparison logic and thresholds are all justified from the
  **structure of the data** — row counts, column names, missing-value rates,
  token frequency distributions, the documented corruption mechanism, and
  published benchmark totals. Never from label feedback.
- It is enforced in code, not by convention: `src/data_loading.py` refuses to
  open a labelled split without `unlock_final_evaluation=True`, the baseline
  refuses to run without `--unlock-final-evaluation`, and a test asserts all
  three splits are sealed by default. **These guards are not to be weakened or
  worked around.**
- Parts of [`ASSESSMENT.md`](ASSESSMENT.md) predate this policy and are
  **label-derived and quarantined** — they are flagged in that file and must not
  be used as design input. D14 lists exactly what is contaminated and what is
  safe.
- **No self-labelling either.** Pairs are not hand-judged to create a feedback
  signal — not 40, not 4 — even though doing so would never open a sealed file.
  Writing a new answer key defeats the purpose as thoroughly as reading the
  supplied one. This rules out learned blocking schemes of the `dedupe`/Zingg
  kind, tuning thresholds by eye, and any model trained on judgements produced
  within the project (including a language model standing in for a human
  judge). See [D19](DECISIONS.md#d19--no-self-labelling-the-project-does-not-create-its-own-answer-key).
  The line: reasoning about the data's *structure* is permitted; judging
  whether a specific pair is a match, and feeding that back into a design
  choice, is not.

Any step that would touch labelled data — or manufacture a substitute for it —
stops, and the conflict is stated rather than resolved silently.

## 4. Dataset scope

- **Primary: Walmart-Amazon₂ (dirty)** — `data/raw/dirty_walmart_amazon/`.
  The system is built and evaluated on this.
- **Secondary: DBLP-ACM₂ (dirty)** — `data/raw/dirty_dblp_acm/`. A comparison
  and contrast case only, not the main focus.
- **Company (textual): deliberately deferred.** Evaluated and consciously set
  aside — network-blocked *and* too large for GitHub's file limit. This is a
  settled decision, not an open task; see [`DATASETS.md`](DATASETS.md) for the
  full reasoning. It is not to be re-investigated or treated as an oversight.

## 5. Project context

A system demonstrating **entity resolution** — matching records across sources
that refer to the same real-world company, with no shared ID.

The emphasis is on engineering judgement, not just model accuracy. The
distinguishing focus is **how the system handles genuinely uncertain cases**.
Rather than forcing every pair into a binary verdict, the matcher may abstain —
the established name for this is **selective prediction**, and the standard way
to report it is a **risk-coverage curve**. Abstained pairs are routed for
review, with sparing AI escalation. That vocabulary is used in preference to
invented terms such as "unsure band"
(see [D22](DECISIONS.md#d22--how-the-two-systems-will-be-compared)).

**Splink** is the intended core matching engine.

## 6. Repository conventions

- Raw data in `data/raw/` is **never** edited in place. It is committed
  deliberately so the project is reproducible from a single clone.
- Reusable code lives in `src/`; exploration in `notebooks/`; written decisions
  and findings in `docs/`.
- Significant decisions are recorded in `docs/` with their reasoning, so the
  repository explains *why*, not just *what*.
- **Archives are exported from the tracked tree, never zipped from the working
  directory.** Use `git archive --format=zip HEAD -o project.zip` or an
  equivalent clean-tree export. A directory zip would sweep in the virtual
  environment (~408 MB), generated intermediates under `data/processed/`, the
  full `.git` history, and any untracked local files — none of which belong in
  a distributed copy.

---

## Current project state

*Unlike the rules above, this section goes stale. Update it as the work moves.
Where it disagrees with [`DECISIONS.md`](DECISIONS.md), the decision
log wins.*

**Decisions recorded: D1–D40.** Several supersede earlier ones — D14 replaced
D6 and voided the D9 baseline result; D17 and D18 changed settings first stated
in D16; D23 corrected how R3 had been described throughout; D29 added a fourth
training round to the three set out in D26. When two entries disagree, the
higher number wins.

### Blocking — complete

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
  as well as Walmart ones ([D17](DECISIONS.md#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap))
  — with a **short-sequence fallback tier** (4-grams, then 3-grams) for records
  sharing no 5-gram with anything ([D20](DECISIONS.md#d20--a-last-resort-tier-for-records-with-no-five-character-overlap)).
  With R3 included it currently rescues nobody, and is retained deliberately as
  a guarantee against a future threshold change reintroducing unreachable
  records.
- **R3 is not brand agreement**, despite its name. The brand vocabulary
  includes ordinary words such as `case` and `digital`, and records pick up
  brands they merely mention. See [D23](DECISIONS.md#d23--correcting-how-r3-is-described)
  before reasoning about it.
- The rule definitions **are** now recorded — in
  [D16](DECISIONS.md#d16--final-blocking-design-five-rules-and-the-thresholds-behind-them),
  [D17](DECISIONS.md#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap)
  and [D23](DECISIONS.md#d23--correcting-how-r3-is-described). An earlier
  version of this section said they were written down nowhere and told sessions
  to ask rather than read. That is no longer true.

Also done: a summary of what blocking discarded
([D21](DECISIONS.md#d21--summarise-what-blocking-discards-rather-than-logging-it),
regenerated into `blocking_diagnostics.json`), and a fixed
blocking↔matching interface contract in `src/interfaces.py`
([D22](DECISIONS.md#d22--how-the-two-systems-will-be-compared)).

### Matching — complete

Implemented in `src/matcher.py`. Scores all 564,450 candidate pairs with Splink,
unsupervised, in about 157 seconds: u estimated by random sampling over 50
million pairs, four expectation-maximisation sessions, then prediction. Every
model parameter is estimated; none is imputed.

Scores are strongly bimodal — 93.3% below 0.01 and 0.8% above 0.99, with a
sparse middle that the abstention band can sit in.

Settled during the build:

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
  ([D25](DECISIONS.md#d25--the-prior-probability-that-two-random-records-match)).

**Open items carried forward:**

1. **Two price levels collapsed.** "Within 10%" and "Within 20%" learned
   essentially the same weight, +1.33 and +1.32 bits, so the 10% boundary
   carries no information and the two could be merged
   ([D30](DECISIONS.md#d30--comparing-prices-by-relative-difference)).
2. **`m` probabilities do not perfectly normalise.** They should sum to 1
   within a comparison; `rare_tokens` sums to 1.0725 and `title` to 0.9541,
   because separate EM sessions estimate different levels against different
   populations and Splink does not renormalise across them
   ([D29](DECISIONS.md#d29--a-fourth-training-round-and-a-lesson-about-which-statistic-governs)).
3. **The λ tension.** 4,454 pairs score at or above 0.99 against a prior
   implying roughly 1,128 matches. Either the prior is low or the model is
   overconfident; only the sensitivity check at final evaluation can tell
   ([D25](DECISIONS.md#d25--the-prior-probability-that-two-random-records-match)).
4. The DF ≤ 5 cutoff separating rare from common identifiers is inherited from
   blocking and remains untuned for matching.
5. **Clarification, not a question:** Splink's native term-frequency adjustment
   does not work on array comparisons. The rare/common split **is** the
   term-frequency mechanism for those columns.

### After matching

Selective prediction and review routing are designed but not built, and depend
on match scores existing ([D24](DECISIONS.md#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai)):
the review interface shows evidence but never a recommendation, AI-only review
is measured for real, human-only review is modelled across a stated range of
assumed accuracies.

A **second, embedding-based system** follows, for comparison against the
classical one ([D22](DECISIONS.md#d22--how-the-two-systems-will-be-compared)).
Labels stay sealed until both are finished, then one evaluation covers both.

73 tests currently pass.

Under the no-peek policy above, every design choice is justified from data
structure only — no checking rules or thresholds against known matches.
