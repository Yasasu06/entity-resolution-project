# Entity Resolution

**[Read the project site →](https://yasasu06.github.io/entity-resolution-project/)**

A system for **entity resolution**: deciding when two product listings from
different retailers refer to the same real-world item, when there is no shared
ID to join on.

Built without reading a single label. Every threshold, every design decision and
every expected failure was written down, committed and independently timestamped
*before* the answer key was opened once, at the end. Eight of those predictions
held, three failed, and the record of both is the point.

## The problem

One retailer lists `maxell couleur series ear buds purple maxell 190238`. The
other lists `new-purple couleur series ear buds de6235 headphones`. Same
earbuds. Four words in common out of thirteen, catalogue numbers that disagree
completely because each shop keeps its own, and a 30% price gap. A person sees
one product. A database sees two unrelated rows.

That is the problem this project explores: comparing records across sources and
deciding *same entity* or *different entity* — and, where the evidence genuinely
doesn't support a confident answer, saying so rather than guessing.

## What we predicted blind, and what was true

Every design decision was made, and every threshold fixed, **before any labelled
data was read** — committed to git and independently timestamped first. Then the
labels were opened once.

| Claim made blind | Reality | |
| --- | --- | :-: |
| Blocking retains essentially every true match | **99.90%** recall (961 of 962) | ✅ |
| The prior implies about **1,128** matches exist | **962** actual | ✅ |
| "Confidently different" is our most exposed claim | **0.5%** wrong (2 of 369) | ✅ |
| Picking the top tied candidate is near a coin flip | **66.3%** vs **53.4%** chance | ✅ |
| An independent AI judge put ~**31%** of accepts wrong | **43%** were — it was too generous | ❌ |

Eight predictions held, three failed, one was registered in advance as
unknowable. **[The full table, misses included →](docs/PREDICTIONS_VS_REALITY.md)**

The headline result is mixed and the record says so: the system reaches **61.46% F1**
(61.17% precision, 61.75% recall, over 971 auto-accepted records) against a five-line
heuristic's 54.46%, and its unattended output is **not** deployable. What the project
demonstrates is that every material weakness was found, measured and published
*before* the answer key was opened.

Every figure here carries a 95% bootstrap interval, because the project
withdrew an entire experiment over one and then reported its own headline bare
([D48](docs/DECISIONS.md#d48--every-reported-figure-gets-an-interval-and-one-claim-does-not-survive-it)).
The headline is **61.46 [58.95, 64.07]**; the margin over the heuristic, paired
on the same records, is **+7.22 [+4.34, +10.17]**.

Scored instead under the benchmark's own protocol — its candidate pairs, the
test split alone, no one-to-one constraint — the same matcher reaches **51.38
[46.61, 56.20]**, against published figures of 37.40 for Magellan, 53.80 for
DeepMatcher and 85.69 for Ditto, each of which trains on 60% of the labels
where this trains on none. That is **clearly above Magellan, clearly below
Ditto, and statistically indistinguishable from DeepMatcher**
([D44](docs/DECISIONS.md#d44--the-system-measured-under-the-benchmarks-own-protocol-and-a-threshold-that-does-not-transfer)).

## Status

| Stage | Status |
| --- | --- |
| Dataset selection & verification | ✅ Done |
| Data loading, sealing of labelled data | ✅ Done |
| **Blocking** (candidate pair generation) | ✅ Done — 564,450 candidates from 56.4M possible pairs, 100% record reachability on both sides |
| Blocking diagnostics (what was discarded, and why) | ✅ Done |
| Blocking ↔ matching interface contract | ✅ Done |
| **Matching** (Splink probabilistic scoring) | ✅ Done — all 564,450 pairs scored, unsupervised, in ~157s |
| **Selective prediction** / review-band design | ✅ Done — rule pre-registered (6.0-bit threshold, 1.0-bit margin, −3.5-bit floor) and implemented; 971 records auto-accepted, 1,214 queued for review |
| **Review interface** | ✅ Built — working demo over 120 real records on the [project site](https://yasasu06.github.io/entity-resolution-project/); the full 1,214-record queue is generated but unreviewed |
| **Human review** of the queued records | 🔜 Not started — no human has worked the queue; the human-only arm is modelled, not observed ([D24](docs/DECISIONS.md#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai)) |
| Second system (embedding-based), for comparison | ✅ Done, and **declined** — the component swap scored **66.86% F1**, over five points above the headline, and was rejected because the gain came from accepting 42% more pairs rather than better judgement. The error class it existed to fix grew from 342 to 590, which [section 11.7](docs/PRE_REGISTRATION.md) had fixed in advance as the condition for not building further ([D43](docs/DECISIONS.md#d43--the-component-swap-a-better-f1-a-failed-mechanism-and-no-second-system)) |
| **Final evaluation** against sealed labels | ✅ Done — one pass, 20 September 2026; F1 was 59.46% at that point ([D39](docs/DECISIONS.md), [D40](docs/DECISIONS.md)) |
| Post-evaluation improvement | ✅ Mutual-best-match check added ([D41](docs/DECISIONS.md)), superseding the figure above. **Current: F1 61.46%, precision 61.17%, recall 61.75%, 971 accepted** ([D46](docs/DECISIONS.md#d46--a-tie-is-not-a-preference-the-reciprocity-test-was-settled-by-record-id))**.** Label-informed, unlike everything above the [boundary](docs/PRE_UNSEAL.md) |

Every design decision — including several corrected mid-project on new
evidence — is recorded with its reasoning in
[`docs/DECISIONS.md`](docs/DECISIONS.md) (52 entries). That log,
not this README, is the authoritative account of what has actually been built
and why.

## What's here

| Path | Purpose |
| --- | --- |
| `data/raw/` | Benchmark datasets exactly as downloaded — never edited by hand |
| `data/processed/` | Generated pipeline outputs (candidate pairs, etc.) — not committed; regenerable from `data/raw/` |
| `notebooks/` | Jupyter notebooks for exploration |
| `src/` | Reusable Python code — data loading and label sealing, text normalisation, blocking rules and diagnostics, the blocking/matching interface contract, derived features, comparison definitions, the Splink matcher, the review queue, the quantity veto, the AI escalation arm, the modelled human reviewer, and both token-overlap baselines, and bootstrap confidence intervals |
| `tests/` | Automated tests (358 passing) covering the code in `src/`, run on every push by CI |
| `docs/` | Decision log, the pre-registered decision rule, the label-free boundary and its timestamp proof, dataset provenance |
| `site/` | The project site: Vite, React, Tailwind and Motion, built and deployed by GitHub Actions |

## Data

The datasets come from the Magellan / DeepMatcher entity-matching benchmark
collection produced by the [AnHai Doan research group at UW–Madison](https://github.com/anhaidgroup/deepmatcher/blob/master/Datasets.md).

Each dataset follows the same layout:

- `tableA.csv`, `tableB.csv` — the two source tables being matched
- `train.csv`, `valid.csv`, `test.csv` — labeled pairs referencing those tables
  by ID, with a `label` column (`1` = same entity, `0` = different)

Two datasets are included:

- **Walmart-Amazon₂ (dirty)** — the **primary** dataset. Product listings from
  two retailers, deliberately corrupted by the benchmark authors so attribute
  values sit in the wrong fields. Chosen because it is genuinely hard: matching
  and non-matching pairs overlap heavily in text similarity, only 9.4% of
  labeled pairs are matches, and its most decisive field is missing from most
  rows.
- **DBLP-ACM₂ (dirty)** — a **secondary** contrast case. Same corruption, but
  much easier to match, which makes it useful for comparison.

A third dataset (Company) was evaluated and deliberately deferred.

See [`docs/DATASETS.md`](docs/DATASETS.md) for provenance, verified row counts,
and the reasoning behind those choices, and [`docs/ASSESSMENT.md`](docs/ASSESSMENT.md)
for the data-driven comparison that selected the primary dataset.

Raw data CSVs are intentionally committed to this repository so the project is
reproducible from a single clone.

## Setup

```bash
python3 -m venv .venv          # create an isolated Python environment
source .venv/bin/activate      # start using it
pip install -r requirements.txt

nbstripout --install           # strip notebook outputs on commit (one-off, per clone)
```

The `nbstripout` step configures a local git setting, which a clone does not
inherit — so it needs running once after cloning. See
[`docs/DECISIONS.md`](docs/DECISIONS.md) (D12) for why.

## Running things

Every stage writes to `data/processed/`, which is not committed and is
regenerable from `data/raw/`. The order matters: each step below reads what the
one above it wrote.

```bash
python src/inspect_datasets.py       # structural summary of the raw tables
python -m src.blocking               # 56.4M possible pairs -> 564,450 candidates
python -m src.blocking_diagnostics   # what blocking discarded, and why
python -m src.matcher                # train by EM and score every candidate (~157s)
python -m src.review_queue           # accept / review / different, and the queue
python -m src.baseline_fair          # the token-overlap baseline, same candidates
```

Checks that read nothing and write nothing:

```bash
python -m src.data_loading           # confirm the tables load and are sealed
python -m src.features               # confirm derived columns build
pytest                               # the test suite (307 tests)
```

These need an OpenAI API key in a gitignored `.env`, and cost money:

```bash
python -m src.embeddings             # embed records, build the top-30 shortlists
python -m src.ai_escalation          # the AI review arm (docs/PRE_REGISTRATION.md s6)
```

These read the answer key and so sit below the
[boundary](docs/PRE_UNSEAL.md). They are the final evaluation, not development:

```bash
python -m src.baseline_token_overlap # the sealed baseline
python -m src.uncertainty            # bootstrap intervals on every reported figure
```

## What this project demonstrates

The work is finished. These are the outcomes it was built to produce:

- **Blocking reduces 56.4 million possible pairs to 564,450 candidates**
  (98.9988% reduction) while keeping **100% of records on both sides reachable**
  — no Walmart record and no Amazon record is excluded by construction, a
  guarantee most published blocking work doesn't report.
- **Real iteration on evidence, not just a first pass.** A normalisation bug
  in the character-sequence blocking rule was found and fixed after measuring
  that 79% of its candidates were meaningless artifacts of collapsing
  whitespace ([D15](docs/DECISIONS.md#d15--fixing-how-text-is-split-for-n-gram-blocking));
  a "same brand" rule was found to only loosely match brands and was
  re-documented rather than silently left inaccurate
  ([D23](docs/DECISIONS.md#d23--correcting-how-r3-is-described)).
- **A strict no-peek policy**, enforced in code (not just by convention): the
  labelled answer key cannot be loaded without an explicit override, and
  several design decisions were deliberately made *without* checking them
  against ground truth — stricter than how some real practitioners work, and
  recorded as a conscious trade-off ([D14](docs/DECISIONS.md#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)).
- **Design choices backed by research, not intuition** — e.g. the decision on
  how to handle low-confidence pairs (human-only, AI-only, or AI-assisted
  review) was made only after checking what the human-AI collaboration
  literature actually shows, including a correction to an earlier claim of
  novelty ([D24](docs/DECISIONS.md#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai)).
- **A better result was measured and declined.** An embedding-and-model rewrite
  of the matcher scored **66.86% F1**, over five points above the headline. It
  was rejected because the gain came from accepting 46% more pairs rather than
  from better judgement, and the error class it existed to fix grew from 342 to
  590 — a stopping condition fixed in writing before the experiment ran
  ([D43](docs/DECISIONS.md#d43--the-component-swap-a-better-f1-a-failed-mechanism-and-no-second-system)).
- **Claims are withdrawn when the evidence does not carry them.** Every figure
  now has a 95% bootstrap interval. One published comparison did not survive
  its own: the system was said to sit 2.42 points below DeepMatcher, and the
  interval contains DeepMatcher's figure, so the ranking was withdrawn
  ([D48](docs/DECISIONS.md#d48--every-reported-figure-gets-an-interval-and-one-claim-does-not-survive-it)).
- **Corrections run in both directions.** A denominator error in the baseline's
  recall was found and fixed; it had run against this project throughout,
  and correcting it roughly doubled the measured margin over the baseline
  ([D45](docs/DECISIONS.md#d45--correcting-d39-the-baselines-best-point-was-measured-on-the-wrong-denominator));
  49 decision entries record what changed and why, each superseded entry
  pointing forward to whatever replaced it.

## No-peek policy

Labelled data (`train`, `valid` and `test`) is **sealed**. Nothing in this
project consults the answers until the whole pipeline is built, at which point
there is one single evaluation. This is enforced in code, not by convention —
the loader refuses to open a labelled split without an explicit override. See
[`docs/DECISIONS.md`](docs/DECISIONS.md) (D14) for the reasoning and the
trade-off being accepted.

## Decisions

Every significant decision on this project — and the reasoning behind it — is
recorded in [`docs/DECISIONS.md`](docs/DECISIONS.md), written to be readable
with no prior context. On a project like this the reasoning matters as much as
the code.

### Pre-registration

The final decision rule — its exact thresholds, the logic that applies them, and
every measurement that will be taken once the labels are unsealed — is fixed in
advance in
[`docs/PRE_REGISTRATION.md`](docs/PRE_REGISTRATION.md), dated and committed
before any labelled data was read. Once labels are visible it is impossible to
demonstrate, even in good faith, that a threshold was not adjusted to improve
the result. Writing the rule down first is what makes the final number a
result rather than a claim.

## License

[MIT](LICENSE)
