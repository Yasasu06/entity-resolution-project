# Initial data assessment

Written before any cleaning or matching was done, from a direct reading of the
raw files. The purpose was to choose a primary dataset on evidence rather than
on published accuracy scores.

Reproduce the underlying figures with `python src/inspect_datasets.py`.

## Conclusion

**Walmart-Amazon₂ is substantially the harder dataset, and is the project's
primary target.** DBLP-ACM₂ looks messy on the surface but the mess is
superficial; Walmart-Amazon₂ is hard in ways that survive cleaning.

## Both datasets share the same artificial corruption

The "dirty" variants are not naturally messy. The benchmark authors took the
clean structured version and, for each attribute, randomly moved values into
`title` and blanked the original column. So in both datasets roughly 50% of
every non-`title` column is empty, and `title` often ends with a stray year,
price, or author list belonging elsewhere.

Because this corruption is identical in kind across both datasets, it is *not*
what separates them in difficulty.

## What actually separates them

Word-overlap (Jaccard) similarity between the two records in each labeled pair,
computed over all attributes concatenated, on the training split:

| Measure | DBLP-ACM₂ | Walmart-Amazon₂ |
| --- | ---: | ---: |
| Mean similarity, true matches | 0.719 | 0.422 |
| Mean similarity, non-matches | 0.144 | 0.298 |
| **Separation gap** | **0.575** | **0.124** |
| Non-matches scoring above the median true match | 0.31% | **10.70%** |
| True matches scoring below the 99th-pct non-match | 10.1% | **81.8%** |

The last row is the headline: in Walmart-Amazon₂, about 82% of genuinely
matching pairs look *less* similar than a top-decile non-match. Signal and
noise sit almost on top of each other. In DBLP-ACM₂ they barely overlap.

## Why, from the actual records

**Academic titles are near-verbatim across sources.** A real DBLP-ACM₂ match
differs mainly in author ordering (`barbara liskov , atul adya , robert gruber`
vs `atul adya , robert gruber , barbara liskov`) or venue naming (`sigmod
record` vs `acm sigmod record`). The title itself is essentially identical — a
large, reliable anchor.

**Product listings are rewritten by each retailer.** A real Walmart-Amazon₂
match: `sumdex slr camera sling pack 39.99` vs `slr camera sling pack sumdex
poc-484bk`. Different word order; one side carries a model number, the other a
price; and the prices *disagree* ($39.99 vs $44.59). Another: `toshiba
ph3100u-1e3s 1tb usb 3.0 desktop hard drive` vs `toshiba 1 tb usb 3.0 external
hard drive ... black silver` — note `1tb` vs `1 tb`, which tokenise
differently, and "desktop" vs "external".

**Non-matches are actively deceptive in the product data.** Two unrelated
Toshiba drives share brand, capacity, category, and most title words. Two
unrelated papers share almost nothing. That is the 0.298 vs 0.144 baseline.

**Attributes actively mislead.** Matching pairs land in different categories
(`mp3 accessories` vs `cases bags`; `printers` vs `printer ink toner`) and at
different prices. In DBLP-ACM₂, when `year` is present on both sides it agrees.

**Missingness bites hardest where it matters.** `modelno` — the one field that
would settle a product match outright — is absent from 64% of `tableB`. Across
true matches, ~39% of field comparisons have the attribute present on one side
and missing on the other, so the decisive field is often unusable exactly when
it is needed.

## Structural difficulty

| | DBLP-ACM₂ | Walmart-Amazon₂ |
| --- | ---: | ---: |
| tableA rows | 2,616 | 2,554 |
| tableB rows | 2,294 | 22,074 |
| Labeled pairs | 12,363 | 10,242 |
| Matches | 2,220 (18.0%) | 962 (9.4%) |

Walmart-Amazon₂'s right-hand table is ~8× its left, giving a much larger and
more lopsided candidate space, and its positives are half as frequent — so
precision is punished harder.

## Note on the labeled pairs

The shipped `train`/`valid`/`test` pairs are **not** a random sample of all
possible pairs. They are the output of the benchmark authors' own blocking
step. The full cross product for Walmart-Amazon₂ would be 2,554 × 22,074 ≈ 56.4
million pairs, in which the true-match rate is roughly 0.0017% rather than 9.4%.
Any end-to-end evaluation has to account for this; scoring only on the shipped
pairs measures the *classifier*, not the *pipeline*.
