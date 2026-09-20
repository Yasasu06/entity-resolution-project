# Entity Resolution

A system for **entity resolution**: deciding when two
records that came from different sources actually refer to the same real-world
company, when there is no shared ID to join on.

## The problem

Suppose one system lists `Acme Corp., 100 Main St, Springfield` and another
lists `ACME Corporation — 100 Main Street, Springfield IL`. A human sees one
company. A database sees two unrelated rows. There is no shared key, so the
records have to be matched on the messy, inconsistent content itself.

That is the problem this project explores: comparing records across sources and
deciding *same entity* or *different entity* — and, where the evidence genuinely
doesn't support a confident answer, saying so rather than guessing.

## Status: in progress

| Stage | Status |
| --- | --- |
| Dataset selection & verification | ✅ Done |
| Data loading, sealing of labelled data | ✅ Done |
| **Blocking** (candidate pair generation) | ✅ Done — 564,450 candidates from 56.4M possible pairs, 100% record reachability on both sides |
| Blocking diagnostics (what was discarded, and why) | ✅ Done |
| Blocking ↔ matching interface contract | ✅ Done |
| **Matching** (Splink probabilistic scoring) | ✅ Done — all 564,450 pairs scored, unsupervised, in ~157s |
| **Selective prediction** / review-band design | ✅ Done — rule pre-registered (6.0-bit threshold, 1.0-bit margin, −3.5-bit floor) and implemented; 1,072 records auto-accepted, 1,113 queued for review |
| **Human review** of the queued records | 🔜 Not started — 1,113 records queued and unreviewed; the interactive interface is deferred ([D24](docs/DECISIONS.md#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai)) |
| Second system (embedding-based), for comparison | 📋 Planned |
| Final evaluation against sealed labels | 🔒 Not started — labels stay sealed until everything above is finished |

Every design decision — including several corrected mid-project on new
evidence — is recorded with its reasoning in
[`docs/DECISIONS.md`](docs/DECISIONS.md) (31 entries and growing). That log,
not this README, is the authoritative account of what has actually been built
and why.

## What's here

| Path | Purpose |
| --- | --- |
| `data/raw/` | Benchmark datasets exactly as downloaded — never edited by hand |
| `data/processed/` | Generated pipeline outputs (candidate pairs, etc.) — not committed; regenerable from `data/raw/` |
| `notebooks/` | Jupyter notebooks for exploration |
| `src/` | Reusable Python code — data loading and label sealing, text normalisation, blocking rules and diagnostics, the blocking/matching interface contract, derived features, comparison definitions, the Splink matcher, the review queue, the AI escalation arm, and a simple token-overlap baseline |
| `tests/` | Automated tests (203 passing) covering the code in `src/` |
| `docs/` | Decision log, the pre-registered decision rule, dataset provenance, and generated diagnostics |

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
