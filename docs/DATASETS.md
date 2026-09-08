# Datasets

All datasets here come from the **Magellan / DeepMatcher entity-matching
benchmark collection**, produced by the AnHai Doan research group at the
University of Wisconsin–Madison and published alongside *Deep Learning for
Entity Matching: A Design Space Exploration* (SIGMOD 2018).

Official index: <https://github.com/anhaidgroup/deepmatcher/blob/master/Datasets.md>

## Summary

| Dataset | Folder | Status | Pairs | Matches |
| --- | --- | --- | ---: | ---: |
| DBLP-ACM₂ (dirty) | `data/raw/dirty_dblp_acm/` | ✅ downloaded | 12,363 | 2,220 |
| Walmart-Amazon₂ (dirty) | `data/raw/dirty_walmart_amazon/` | ✅ downloaded | 10,242 | 962 |
| Company (textual) | `data/raw/company/` | ❌ **not obtained** | — | — |

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

### Company (textual) — NOT OBTAINED

The Company dataset could **not** be downloaded from any verifiable source
reachable from this environment. Nothing was substituted for it, and no
synthetic stand-in was generated.

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
