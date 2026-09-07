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

See [`docs/DATASETS.md`](docs/DATASETS.md) for exactly which datasets are
included, where each one was downloaded from, and their verified row counts.

Raw data CSVs are intentionally committed to this repository so the project is
reproducible from a single clone.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## License

[MIT](LICENSE)
