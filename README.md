# Entity Resolution — Portfolio Project

A learning/portfolio project exploring **entity resolution**: deciding when two
records that came from different sources actually refer to the same real-world
company, when there is no shared ID to join on.

## The problem

Suppose one system lists `Acme Corp., 100 Main St, Springfield` and another
lists `ACME Corporation — 100 Main Street, Springfield IL`. A human sees one
company. A database sees two unrelated rows. There is no shared key, so the
records have to be matched on the messy, inconsistent content itself.

That is the problem this project explores: comparing records across sources and
deciding *same entity* or *different entity*.

## Status

**Early setup / data exploration.** At this stage the repository contains the
project scaffolding and the raw benchmark datasets. No cleaning, matching, or
modelling has been done yet, and there are no results to report.

## What's here

| Path | Purpose |
| --- | --- |
| `data/raw/` | Benchmark datasets exactly as downloaded — never edited by hand |
| `notebooks/` | Jupyter notebooks for exploration |
| `src/` | Reusable Python code, as it gets factored out of the notebooks |
| `docs/` | Notes, findings, and write-ups |

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
pytest                                  # the test suite
```

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

## License

[MIT](LICENSE)
