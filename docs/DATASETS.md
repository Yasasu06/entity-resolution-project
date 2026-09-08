# Datasets

All datasets here come from the **Magellan / DeepMatcher entity-matching
benchmark collection**, produced by the AnHai Doan research group at the
University of Wisconsin–Madison and published alongside *Deep Learning for
Entity Matching: A Design Space Exploration* (SIGMOD 2018).

Official index: <https://github.com/anhaidgroup/deepmatcher/blob/master/Datasets.md>

## Summary

| Dataset | Role in this project | Folder | Pairs | Matches |
| --- | --- | --- | ---: | ---: |
| **Walmart-Amazon₂ (dirty)** | **Primary dataset** — the system is built and evaluated on this | `data/raw/dirty_walmart_amazon/` | 10,242 | 962 |
| DBLP-ACM₂ (dirty) | Secondary reference point, used for comparison only | `data/raw/dirty_dblp_acm/` | 12,363 | 2,220 |
| Company (textual) | **Deliberately deferred** — see [decision](#company-textual--deliberately-deferred) | `data/raw/company/` | — | — |

### Why Walmart-Amazon is the primary dataset

It is the harder and more interesting of the two, which makes it the better
showcase for a system whose whole point is handling genuinely uncertain cases.
Measured on the actual data (see [`ASSESSMENT.md`](ASSESSMENT.md)): matching
pairs and non-matching pairs overlap heavily in raw text similarity, only 9.4%
of labeled pairs are matches, its right-hand table is 8× larger than its left,
and its most decisive attribute (`modelno`) is missing from 64% of rows.
DBLP-ACM₂ is comparatively easy — academic titles are near-verbatim across
sources — so it is kept as a contrast case rather than the main target.

## Where each file actually came from

The canonical host for these datasets is `pages.cs.wisc.edu`. That host is
**blocked by the network egress policy** of the environment this project was
set up in, so the two datasets below were retrieved from a research mirror on
GitHub that redistributes the benchmark in its original file layout.

### DBLP-ACM₂ and Walmart-Amazon₂ (dirty versions)

- **Retrieved from:** `https://raw.githubusercontent.com/brunnurs/entity-matching-transformer/master/data/{dirty_dblp_acm,dirty_walmart_amazon}/deep_matcher/`
- **Mirror repository:** <https://github.com/brunnurs/entity-matching-transformer>
  (code for Brunner & Stockinger, *Entity Matching with Transformer
  Architectures*, EDBT 2020)
- **Canonical origin (blocked here):**
  - `http://pages.cs.wisc.edu/~anhai/data1/deepmatcher_data/Dirty/DBLP-ACM/dirty_dblp_acm_exp_data.zip`
  - `http://pages.cs.wisc.edu/~anhai/data1/deepmatcher_data/Dirty/Walmart-Amazon/dirty_walmart_amazon_exp_data.zip`

**Mirror fidelity was verified, not assumed.** The official DeepMatcher
`Datasets.md` publishes the expected size of each benchmark. The downloaded
files reproduce those figures exactly:

| Dataset | Official pairs / matches | Downloaded pairs / matches | Match |
| --- | --- | --- | --- |
| DBLP-ACM₂ | 12,363 / 2,220 | 12,363 / 2,220 | ✅ exact |
| Walmart-Amazon₂ | 10,242 / 962 | 10,242 / 962 | ✅ exact |

Attribute counts also agree (4 matchable attributes for DBLP-ACM₂, 5 for
Walmart-Amazon₂, excluding `id`).

### Company (textual) — deliberately deferred

**Status: evaluated, and consciously set aside. This is a decision, not an
open problem or an oversight.**

The Company dataset was pursued thoroughly, could not be obtained from any
verifiable source, and was then dropped on purpose after weighing the cost of
pursuing it further against the value it would add. Nothing was substituted for
it, and no synthetic stand-in was generated.

**Two independent reasons, either of which is sufficient:**

1. **The canonical host is unreachable.** `pages.cs.wisc.edu` is refused at the
   HTTPS `CONNECT` stage by this environment's network egress policy. Because
   the refusal happens before any URL path is transmitted, *no* path on that
   host is reachable — not the zip, not the per-file CSVs, not the directory
   listing. Every published mirror was also checked and is dead or blocked
   (table below).
2. **It would not survive in this repository anyway.** Company's `tableA.csv`
   is reported to be roughly 185 MB (figure supplied by the project owner from
   the live directory listing; not independently verified here, since the file
   was never retrievable), well past GitHub's hard 100 MB per-file limit. Committing
   it would require Git LFS or an out-of-band download step, which adds real
   setup friction to a project whose stated aim is to be reproducible from a
   single `git clone`.

**Why deferring costs us little.** Company is a *textual* benchmark — long
free-text company descriptions — which is a meaningfully different matching
problem from the structured-but-corrupted attribute matching this project is
built around. Adding it would widen the project's scope rather than deepen it.
The two datasets in hand already provide both a hard case and an easy contrast
case.

**What would reopen this decision:** unrestricted network access to
`pages.cs.wisc.edu` (or an equivalent verified mirror) *and* a decision to take
on Git LFS. If both change, the fetch command is at the end of this section.
Until then, this is settled and needs no further investigation.

Routes attempted and their outcomes:

| Source | Result |
| --- | --- |
| `pages.cs.wisc.edu/.../Textual/Company/company_exp_data.zip` (official) | Blocked — proxy returned 403 (egress policy denial) |
| `pages.cs.wisc.edu/.../Textual/Company/exp_data/{tableA,tableB,train,valid,test}.csv` (official, per-file) | Blocked — all five files returned `CONNECT tunnel failed, response 403` |
| `ditto-em.s3.us-east-2.amazonaws.com/Company.zip` (mirror named in Ditto's own README) | HTTP 403 AccessDenied from S3 — bucket no longer public |
| `megagonlabs/ditto` repo, `data/er_magellan/Textual/Company/` | Contains only a README pointing at the dead S3 link above |
| `brunnurs/entity-matching-transformer` repo | No `company` folder (has abt_buy, amazon_google, dirty_* only) |
| `icip-cas/EntityMatcher` repo | No `company` folder |
| Google Drive, Zenodo, Figshare, HuggingFace, Uni-Mannheim, Uni-Leipzig | All blocked by the same egress policy |

The block occurs at the HTTPS `CONNECT` stage, before any URL path is
transmitted, so the proxy only ever sees the hostname `pages.cs.wisc.edu:443`.
No path on that host is reachable from this environment — the files themselves
are live and publicly served, and download normally from an unrestricted
network.

**To obtain it**, from a machine with unrestricted internet access:

```bash
curl -O http://pages.cs.wisc.edu/~anhai/data1/deepmatcher_data/Textual/Company/company_exp_data.zip
unzip company_exp_data.zip -d data/raw/company/
```

For reference, the published description: Company matches company homepages
against Wikipedia pages describing companies — 112,632 labeled pairs, 28,200
matches, and a single long free-text attribute per record.

## File layout

Each downloaded dataset uses the standard DeepMatcher `exp_data` layout:

```
data/raw/<dataset>/
├── tableA.csv   # left source table  (id + attributes)
├── tableB.csv   # right source table (id + attributes, same schema)
├── train.csv    # labeled pairs: ltable_id, rtable_id, label
├── valid.csv    # same schema
└── test.csv     # same schema
```

`label` is `1` when the two referenced rows are the same real-world entity and
`0` otherwise. The train/valid/test split ships with the benchmark so results
are comparable across published papers.

## What "dirty" means here

The dirty variants are **not** naturally messy data. The benchmark authors took
the clean structured version and deliberately corrupted it: for each attribute,
values were randomly moved into the `title` attribute and left blank in their
own column. This simulates poor schema alignment — the information is still
present in the record, just in the wrong field.

That artificial corruption is visible in the data: roughly 50% of values are
missing from every non-title column, and `title` frequently ends with a stray
year, price, or author list that belongs elsewhere.

## Reproducing the summary

```bash
python src/inspect_datasets.py
```

This prints file sizes, columns, row counts, missing-value rates, label balance,
and the first rows of every file. It reads only — it never modifies the raw data.
