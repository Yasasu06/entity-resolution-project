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
- **Describe measurements, do not pass verdicts on the work.** A finding that
  reveals a limitation stays on the page in full, with its real numbers, and is
  written in the language of measurement rather than self-assessment. The line
  falls between the two: *"identified a match on 36.7% of records where none
  existed"* is a measurement and stays; *"the reviewer did badly"* is a verdict
  and does not. By the same rule *"wrong partner chosen"* stays, because it
  names a category in the error decomposition, and the prediction ledger's
  *"three failed"* stays, because reporting the three that were wrong is the
  reason the ledger is worth reading. What gets rewritten is phrasing that
  judges rather than reports — *falls short*, *weakness*, *modestly* — since it
  adds no information the numbers do not already carry.

  **This is not permission to soften a finding.** Nothing is removed, no figure
  is omitted, and the site is never gentler than the decision log. The
  constraint is on adjectives, not on evidence.

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

## 3. Label-feedback boundary and disclosure

Earlier exploration used train/validation labels before D14 adopted a stricter
policy. From that point through the original evaluation, later blocking,
matching and threshold decisions were developed without further label feedback.
The original pre-registered policy scored **59.46% F1**. D41 and D46 then made
label-informed policy changes; D54 records that the historical **61.46% F1**
run was unseeded. D55 fixes `u` sampling at seed 0 and reports the current
reproducible **61.47% F1** run over 974 accepts. See [D14](DECISIONS.md#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)
for the earlier exposure and its quarantine.

- This includes checks that resemble ordinary due diligence. *"How many known
  true matches survive this blocking step?"* is a peek: if a rule is kept or
  dropped based on that number, the answer key has shaped the design.
- It includes reporting label counts or match percentages for a split.
  Describing the answer key is still using the answer key.
- The later pre-evaluation blocking rules, comparison logic and original
  thresholds were justified from the **structure of the data** — row counts,
  column names, missing-value rates,
  token frequency distributions, the documented corruption mechanism, and
  published benchmark totals. Never from label feedback.
- The loader refuses to open a labeled split without
  `unlock_final_evaluation=True`, and the baseline requires
  `--unlock-final-evaluation`. Tests check the default guard, while some tests
  explicitly unlock and read train/validation labels. The guard makes access
  deliberate; it cannot establish that a split has never been read.
- Parts of [`ASSESSMENT.md`](ASSESSMENT.md) predate this policy and are
  **label-derived and quarantined** — they are flagged in that file and must not
  be used as design input. D14 lists exactly what is contaminated and what is
  safe.
- **No self-labeling for the original design.** Pairs were not hand-judged to
  create feedback for pre-evaluation blocking or matching choices.
  Writing a new answer key defeats the purpose as thoroughly as reading the
  supplied one. This rules out learned blocking schemes of the `dedupe`/Zingg
  kind, tuning thresholds by eye, and any model trained on judgements produced
  within the project (including a language model standing in for a human
  judge). See [D19](DECISIONS.md#d19--no-self-labelling-the-project-does-not-create-its-own-answer-key).
  The line: reasoning about the data's *structure* is permitted; judging
  whether a specific pair is a match, and feeding that back into a design
  choice, is not.

Post-evaluation label use and human judgments are recorded as such. The
60-record owner review study in D51 does not establish an operating review
service or independent-reviewer agreement.

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

A system demonstrating **entity resolution** — matching product listings across
retailers that refer to the same real-world item, with no shared ID.

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

**Decisions recorded: D1–D55.** Several supersede earlier ones — D14 replaced
D6 and voided the D9 baseline result; D17 and D18 changed settings first stated
in D16; D23 corrected how R3 had been described throughout; D29 added a fourth
training round to the three set out in D26. When two entries disagree, the
higher number wins, and the superseded entry carries a dated note pointing
forward to whatever replaced it, so the correction is visible from either end.

**A new entry and the counts that describe it move in the same commit.** The
entry total and the highest entry number are stated in three places outside the
log: the count above, the line in `README.md` that links to the log, and the
record row in `site/src/components/Method.jsx`. All of them are updated in the
commit that adds the entry, so the log and its description are never out of step,
including briefly. The same applies to the test total and the pre-registration
section count where those appear.

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

Implemented in `src/matcher.py`. The seed-0 local rerun scored all 564,450
candidate pairs with Splink in about 185 seconds without pair-label training:
u was estimated by seeded random sampling over 50 million pairs, followed by
four expectation-maximisation sessions and prediction. Every model parameter
is estimated; none is imputed.

In the earlier unseeded analysis, scores were strongly bimodal — 93.3% below
0.01 and 0.8% above 0.99, with a sparse middle for the abstention band.

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
- **`probability_two_random_records_match` = 2.0e-05**, derived without label
  feedback during D14 design. D39 later found that this prior implied about
  1,128 matches against 962 actual, while the model's posterior mass implied
  12,941 ([D25](DECISIONS.md#d25--the-prior-probability-that-two-random-records-match),
  [D39](DECISIONS.md)).

**Build observations and remaining questions:**

1. **Two price levels collapsed.** "Within 10%" and "Within 20%" learned
   essentially the same weight, +1.33 and +1.32 bits, so the 10% boundary
   carries no information and the two could be merged
   ([D30](DECISIONS.md#d30--comparing-prices-by-relative-difference)).
2. **`m` probabilities do not perfectly normalise.** They should sum to 1
   within a comparison; `rare_tokens` sums to 1.0725 and `title` to 0.9541,
   because separate EM sessions estimate different levels against different
   populations and Splink does not renormalise across them
   ([D29](DECISIONS.md#d29--a-fourth-training-round-and-a-lesson-about-which-statistic-governs)).
3. **The λ tension was resolved at the original evaluation.** The prior
   implied roughly 1,128 matches against 962 actual; the model's summed scores
   implied 12,941. Its score values are not calibrated match probabilities
   ([D39](DECISIONS.md)).
4. The DF ≤ 5 cutoff separating rare from common identifiers is inherited from
   blocking and remains untuned for matching.
5. **Clarification, not a question:** Splink's native term-frequency adjustment
   does not work on array comparisons. The rare/common split **is** the
   term-frequency mechanism for those columns.

### After matching

Selective prediction and review routing are implemented. A local JSON queue
and terminal tool support review; one owner reviewer completed 60 distinct
records in D51. Full-queue outcomes are projections, and no operational review
service or feedback into production accepts is established. The site is a
static interactive demo over a committed snapshot.

D43 ran an embedding and model **component-swap experiment** over the classical
candidate set. It was declined; an independent embedding blocker and complete
second pipeline were not built. Its 1,416 accepts were 42.4547% more than the
994 classical accepts at the time, or 45.8290% more than the later historical
D46 policy's 971 accepts. These comparisons use different denominators.

The original policy's 59.46% F1, historical unseeded D46's 61.46% F1 and the
current seed-0 policy's 61.47% F1 must be reported separately.

368 tests currently pass.
