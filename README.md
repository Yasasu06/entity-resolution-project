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

The headline result is mixed and the record says so: the system reaches 59.46% F1
against a five-line heuristic's 57.66%, and its unattended output is **not**
deployable. What the project demonstrates is that every material weakness was
found, measured and published *before* the answer key was opened.

## Status

| Stage | Status |
| --- | --- |
| Dataset selection & verification | ✅ Done |
| Data loading, sealing of labelled data | ✅ Done |
| **Blocking** (candidate pair generation) | ✅ Done — 564,450 candidates from 56.4M possible pairs, 100% record reachability on both sides |
| Blocking diagnostics (what was discarded, and why) | ✅ Done |
| Blocking ↔ matching interface contract | ✅ Done |
| **Matching** (Splink probabilistic scoring) | ✅ Done — all 564,450 pairs scored, unsupervised, in ~157s |
| **Selective prediction** / review-band design | ✅ Done — rule pre-registered (6.0-bit threshold, 1.0-bit margin, −3.5-bit floor) and implemented; 994 records auto-accepted, 1,191 queued for review |
| **Review interface** | ✅ Built — working demo over 120 real records on the [project site](https://yasasu06.github.io/entity-resolution-project/); the full 1,191-record queue is generated but unreviewed |
| **Human review** of the queued records | 🔜 Not started — no human has worked the queue; the human-only arm is modelled, not observed ([D24](docs/DECISIONS.md#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai)) |
| Second system (embedding-based), for comparison | 📋 Next — D37 and D41 established what it has to beat: the classical approach reaches 1.5% of the identity problem, and the rest needs semantics |
| **Final evaluation** against sealed labels | ✅ Done — one pass, 20 September 2026; system F1 59.46% against the baseline's 57.66%; see [D39](docs/DECISIONS.md) and [D40](docs/DECISIONS.md) |
| Post-evaluation improvement | ✅ Mutual-best-match check added — F1 **60.94%**, precision 59.96% ([D41](docs/DECISIONS.md)). Label-informed, unlike everything above the [boundary](docs/PRE_UNSEAL.md) |

Every design decision — including several corrected mid-project on new
evidence — is recorded with its reasoning in
[`docs/DECISIONS.md`](docs/DECISIONS.md) (41 entries). That log,
not this README, is the authoritative account of what has actually been built
and why.

## What's here

| Path | Purpose |
| --- | --- |
| `data/raw/` | Benchmark datasets exactly as downloaded — never edited by hand |
| `data/processed/` | Generated pipeline outputs (candidate pairs, etc.) — not committed; regenerable from `data/raw/` |
| `notebooks/` | Jupyter notebooks for exploration |
| `src/` | Reusable Python code — data loading and label sealing, text normalisation, blocking rules and diagnostics, the blocking/matching interface contract, derived features, comparison definitions, the Splink matcher, the review queue, the quantity veto, the AI escalation arm, the modelled human reviewer, and both token-overlap baselines |
| `tests/` | Automated tests (254 passing) covering the code in `src/` |
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

```bash
python src/inspect_datasets.py          # structural summary of the raw data
python -m src.baseline_token_overlap    # sealed baseline (final evaluation only)
python -m src.blocking                  # generate candidate pairs (writes data/processed/)
python -m src.blocking_diagnostics      # summarise what blocking discarded
pytest                                  # the test suite (73 tests)
```

## Highlights so far

Notable engineering outcomes:

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
