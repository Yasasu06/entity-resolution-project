# Entity Resolution

**[Read the project site →](https://yasasu06.github.io/entity-resolution-project/)**

A system for **entity resolution**: deciding when two product listings from
different retailers refer to the same real-world item, when there is no shared
ID to join on.

After an early train/validation exploration, the project adopted a stricter
boundary: later blocking and matching rules and the original decision thresholds
were set without label feedback. The original pre-registered policy scored
**59.46% F1**. Later, label-informed decision-rule changes and a fixed random
sampling seed produced the current reproducible **61.47% F1** result. Eight of
the predictions recorded before that evaluation held, three
failed, and one was left open.

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

These predictions and the original decision rule were recorded before the final
evaluation under the stricter boundary adopted in D14. Earlier train/validation
analysis is disclosed there; the project did not begin in total ignorance of
the labels. The original evaluation and later policy changes are separate.

| Claim made blind | Reality | |
| --- | --- | :-: |
| Blocking retains essentially every true match | **99.90%** recall (961 of 962) | ✅ |
| The prior implies about **1,128** matches exist | **962** actual | ✅ |
| "Confidently different" is our most exposed claim | **0.5%** wrong (2 of 369) | ✅ |
| Picking the top tied candidate is near a coin flip | **66.3%** vs **53.4%** chance | ✅ |
| An independent AI judge put ~**31%** of accepts wrong | **43%** were — it was too generous | ❌ |

Eight predictions held, three failed, one was registered in advance as
unknowable. **[The full table, misses included →](docs/PREDICTIONS_VS_REALITY.md)**

The original pre-registered policy reached **59.46% F1** (56.82% precision,
62.37% recall, 1,056 auto-accepted pairs). Post-evaluation, label-informed
reciprocity and tie handling were added. With `u` sampling fixed at seed 0, the
current reproducible run reached **61.47% F1** (61.09% precision, 61.85% recall,
974 auto-accepted pairs), against a five-line heuristic's 54.24%. Its unattended
output is **not** deployable: 379 of the 974 accepted pairs were wrong, including
344 records with no known partner and 35 that chose the wrong partner. The
historical unseeded D46 run reached **61.46% F1** over 971 accepts. The evaluation
exposed a dominant no-partner error class; subsequent work identified policy
and reproducibility issues.

The seeded current run has a 95% bootstrap interval of **61.47 [58.95, 64.09]**;
the matched-coverage heuristic scores **54.24 [51.50, 56.80]**, and their
paired margin is **+7.23 [+4.36, +10.19]** percentage points
([D55](docs/DECISIONS.md#d55--fix-the-u-sampling-seed-and-report-the-reproducible-result)).
The older **61.46 [58.95, 64.07]** interval and **54.46** heuristic score
describe the historical unseeded run ([D48](docs/DECISIONS.md#d48--every-reported-figure-gets-an-interval-and-one-claim-does-not-survive-it)).

In a historical evaluation using unseeded scores under the benchmark's own
protocol — its candidate pairs, the test split alone, no one-to-one constraint —
the matcher reached **51.38
[46.61, 56.20]**, against published figures of 37.40 for Magellan, 53.80 for
DeepMatcher and 85.69 for Ditto, each of which trains on 60% of the labels
where this trains on none. That is **clearly above Magellan, clearly below
Ditto, and statistically indistinguishable from DeepMatcher**
([D44](docs/DECISIONS.md#d44--the-system-measured-under-the-benchmarks-own-protocol-and-a-threshold-that-does-not-transfer)).
That benchmark-protocol result has not been regenerated with seed 0.

## Status

| Stage | Status |
| --- | --- |
| Dataset selection & verification | ✅ Done |
| Data loading and guarded label access | ✅ Done |
| **Blocking** (candidate pair generation) | ✅ Done — 564,450 candidates from 56,376,996 possible pairs, 98.9988% reduction; 100% record reachability on both sides and 961/962 (99.90%) labeled true-pair recall |
| Blocking diagnostics (what was discarded, and why) | ✅ Done |
| Blocking ↔ matching interface contract | ✅ Done |
| **Matching** (Splink scoring) | ✅ Done — all 564,450 pairs scored without pair-label training; the seed-0 local rerun took about 185 seconds |
| **Selective prediction** / review-band design | ✅ Done — thresholds were pre-registered (6.0-bit accept, greater-than-1.0-bit margin, −3.5-bit floor); later reciprocity and tie handling were label-informed. The seeded current run accepted 974 records and queued 1,210 |
| **Review interface** | ✅ Built — a static [project-site demo](https://yasasu06.github.io/entity-resolution-project/) over 120 records and a local JSON queue with a terminal review tool; the site does not run the Python matcher |
| **Human review** of the queued records | ⚠️ Limited observation — one project-owner reviewer completed 60 distinct records from the historical 1,214-item D46 queue. Full-queue outcomes are projections for that historical queue; no operating review service, independent reviewers or production feedback loop is established ([D51](docs/DECISIONS.md#d51--the-human-arm-observed-high-recall-bought-at-a-precision-the-tier-cannot-afford)) |
| Embedding and model component-swap experiment | ✅ Run and **declined** — 1,416 alternative accepts and 66.86% F1, with 56.14% precision. Against the seeded current classical policy's 974 accepts, that is 45.3799% (≈45%) more accepts; against historical D46's 971, it was 45.8290% (≈46%). The historical D46 no-partner error class grew from 342 to 590 under the swap; the registered mechanism failed. An independent embedding blocker was not built ([D43](docs/DECISIONS.md#d43--the-component-swap-a-better-f1-a-failed-mechanism-and-no-second-system)) |
| **Original pre-registered evaluation** | ✅ One pass on 20 September 2026: 1,056 accepts, 56.82% precision, 62.37% recall, **59.46% F1** ([D39](docs/DECISIONS.md), [D40](docs/DECISIONS.md)). Earlier train/validation exploration is disclosed in D14 |
| Current reproducible policy | ✅ Mutual-best-match and tie handling were added after evaluation ([D41](docs/DECISIONS.md), [D46](docs/DECISIONS.md#d46--a-tie-is-not-a-preference-the-reciprocity-test-was-settled-by-record-id)). With `u` sample seed 0: **61.47% F1, 61.09% precision, 61.85% recall, 974 accepts, 1,210 review, 370 confidently different**. The historical unseeded D46 result was **61.46% F1 and 971 accepts** ([D55](docs/DECISIONS.md#d55--fix-the-u-sampling-seed-and-report-the-reproducible-result)) |

Every design decision — including several corrected mid-project on new
evidence — is recorded with its reasoning in
[`docs/DECISIONS.md`](docs/DECISIONS.md) (55 entries). That log,
not this README, is the authoritative account of what has actually been built
and why.

## What's here

| Path | Purpose |
| --- | --- |
| `data/raw/` | Benchmark datasets exactly as downloaded — never edited by hand |
| `data/processed/` | Generated pipeline outputs (candidate pairs, etc.) — not committed; regenerable from `data/raw/` |
| `notebooks/` | Jupyter notebooks for exploration |
| `src/` | Reusable Python code — data loading, text normalisation, blocking, feature and comparison definitions, the Splink matcher, decision and review routing, the terminal human-review study, optional AI experiments, baselines and uncertainty analysis |
| `tests/` | Automated tests (368 passing) covering the code in `src/`, run on every push by CI |
| `docs/` | Decision log, the pre-registered rule, the documented label-feedback boundary and proof file for its original text, dataset provenance |
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
python -m src.matcher                # train by EM and score every candidate (~185s in one local run)
python -m src.review_queue           # accept / review / different, and the queue
python -m src.baseline_fair          # the token-overlap baseline, same candidates
```

Local checks (some tests explicitly unlock and read train/validation labels;
pytest may write temporary files):

```bash
python -m src.data_loading           # confirm the source tables load and labels are guarded by default
python -m src.features               # confirm derived columns build
pytest                               # the test suite (368 tests)
```

These need an OpenAI API key in a gitignored `.env`, and cost money:

```bash
python -m src.embeddings             # embed records, build the top-30 shortlists
python -m src.ai_escalation          # the AI review arm (docs/PRE_REGISTRATION.md s6)
```

These read the answer key and sit after the original evaluation
[boundary](docs/PRE_UNSEAL.md):

```bash
python -m src.baseline_token_overlap --unlock-final-evaluation # historical train/valid baseline
python -m src.uncertainty            # bootstrap intervals on current local scores
```

## What this project demonstrates

The work is finished. These are the outcomes it was built to produce:

- **Blocking reduces 56,376,996 Cartesian pairs to 564,450 candidates**
  (98.9988% reduction, or 99.00% to two decimals). All 2,554 Walmart and
  22,074 Amazon records have at least one candidate. Separately, **961 of 962
  labeled true pairs survive blocking (99.90% recall)**.
- **Real iteration on evidence, not just a first pass.** A normalisation bug
  in the character-sequence blocking rule was found and fixed after measuring
  that 79% of its candidates were meaningless artifacts of collapsing
  whitespace ([D15](docs/DECISIONS.md#d15--fixing-how-text-is-split-for-n-gram-blocking));
  a "same brand" rule was found to only loosely match brands and was
  re-documented rather than silently left inaccurate
  ([D23](docs/DECISIONS.md#d23--correcting-how-r3-is-described)).
- **A documented label-feedback boundary.** The loader requires an explicit
  override to read labeled splits. Earlier train/validation analysis occurred;
  after D14, blocking and matching decisions for the original evaluation were
  developed without further label feedback. Tests can use the override, and
  later decision-policy changes used evaluation labels
  ([D14](docs/DECISIONS.md#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)).
- **Design choices backed by research, not intuition** — e.g. the decision on
  how to handle low-confidence pairs (human-only, AI-only, or AI-assisted
  review) was made only after checking what the human-AI collaboration
  literature actually shows, including a correction to an earlier claim of
  novelty ([D24](docs/DECISIONS.md#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai)).
- **A component swap with higher F1 was declined.** Replacing the matcher
  component with an embedding shortlist and model judgment scored **66.86% F1**
  and **56.14% precision** over the same candidate set. It accepted **1,416
  pairs**, 45.3799% (≈45%) more than the seeded current classical policy's
  **974**. Against historical D46's **971**, the increase was 45.8290% (≈46%).
  In that historical comparison, no-partner errors grew from **342 to 590**, so the registered
  mechanism failed its stopping condition. The swap also won some direct
  partner disagreements; the gain cannot all be attributed to accepting more
  ([D43](docs/DECISIONS.md#d43--the-component-swap-a-better-f1-a-failed-mechanism-and-no-second-system)).
- **Claims are withdrawn when the evidence does not carry them.** The current
  seeded headline has a 95% bootstrap interval. One historical comparison did not survive
  its own: the system was said to sit 2.42 points below DeepMatcher, and the
  interval contains DeepMatcher's figure, so the ranking was withdrawn
  ([D48](docs/DECISIONS.md#d48--every-reported-figure-gets-an-interval-and-one-claim-does-not-survive-it)).
- **Corrections run in both directions.** A denominator error in the baseline's
  recall was found and fixed; it had run against this project throughout,
  and correcting it roughly doubled the measured margin over the baseline
  ([D45](docs/DECISIONS.md#d45--correcting-d39-the-baselines-best-point-was-measured-on-the-wrong-denominator));
  55 decision entries record what changed and why, each superseded entry
  pointing forward to whatever replaced it.

## Label-feedback boundary

Before D14's stricter boundary, exploratory work used train/validation labels.
D14 quarantined those findings and committed to developing later blocking and
matching rules without label feedback. The loader rejects labeled-split reads
unless explicitly unlocked; some tests do unlock train/validation. The original
pre-registered policy was evaluated after this boundary. Mutual-best-match and
tie handling were then changed with knowledge of the results. See
[`docs/DECISIONS.md`](docs/DECISIONS.md) (D14, D39, D41 and D46).

## Decisions

Every significant decision on this project — and the reasoning behind it — is
recorded in [`docs/DECISIONS.md`](docs/DECISIONS.md), written to be readable
with no prior context. On a project like this the reasoning matters as much as
the code.

### Pre-registration

The original decision rule — its thresholds, logic and planned measurements —
was fixed in advance in
[`docs/PRE_REGISTRATION.md`](docs/PRE_REGISTRATION.md), committed before the
original final evaluation. Earlier train/validation analysis is disclosed in
D14. The pre-registration identifies which thresholds belonged to the original
**59.46%** evaluation; the later **61.46%** run used label-informed additions to
the decision rule and was unseeded. The same later policy now has a fixed-seed
result of **61.47% F1** ([D55](docs/DECISIONS.md#d55--fix-the-u-sampling-seed-and-report-the-reproducible-result)).

## License

[MIT](LICENSE)
