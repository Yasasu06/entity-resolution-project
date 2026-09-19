# Pre-registration: the decision rule and how it will be evaluated

**Written 19 September 2026, before any labelled data has been read.**

This document fixes the decision rule, its thresholds and the measurements that
will be taken, in advance of unsealing `train`, `valid` or `test`. Its purpose
is to make the final result a *result* rather than a *claim*: once labels are
visible it becomes impossible to prove, even in good faith, that a threshold was
not nudged to flatter the outcome. Writing the rule down first costs nothing and
settles the question.

Nothing in this document may be revised after the labels are unsealed. If the
rule turns out to be wrong, that finding is reported against this text, not
substituted for it.

---

## 1. The rule

Every Walmart record is assigned exactly one outcome, determined by its
**best-scoring candidate** and by the **margin** between that candidate and the
record's runner-up. Scores are expressed as **match weight in bits**,
`log2(p / (1 - p))`, which is the model's natural scale.

| Symbol | Meaning | Value | As probability |
| --- | --- | ---: | ---: |
| **S** | accept threshold on the best candidate | **6.0 bits** | 0.9846 |
| **M** | margin required over the runner-up | **1.0 bit** | — |
| **L** | boundary below which no candidate is credible | **−3.5 bits** | 0.0812 |

```
if best >= S and margin > M   -> ACCEPT the single best pair
if best >= S and margin <= M   -> REVIEW (tied at the top)
if L <= best < S               -> REVIEW (unsure)
if best < L                    -> CONFIDENTLY DIFFERENT
```

A record therefore contributes **at most one** predicted match. This
one-to-one constraint is part of the rule, not an implementation detail.

### Why these numbers

Both thresholds are placed at **measured flat spots** in the score
distribution, chosen so that the exact placement matters as little as possible.
Sensitivity is quantified as *churn*: the number of records that change side if
the threshold moves by half a bit in either direction.

| Threshold | Churn (±0.5 bits) | Nearest unstable point |
| --- | ---: | --- |
| S = 6.0 bits | 15 records | 7.0 bits, churn 139 |
| L = −3.5 bits | 1 record | −3.0 bits, churn 143 |

The score is coarse — 879 distinct values across 564,450 pairs, with single
values carrying up to 101,012 pairs — so a threshold lands on the nearest step
rather than where it is placed. Choosing flat placements is what makes the rule
reproducible rather than an artefact of a decimal point.

**S deliberately does not sit at p = 0.99.** That is 6.63 bits, at the edge of
the stable shelf and immediately before the cliff. The round-numbered
probability is the less defensible choice.

`M = 1.0 bit` is carried over from
[D31](DECISIONS.md#d31--tied-partners-when-the-model-cannot-choose-between-candidates),
where it was placed in a sparse region of the margin distribution.

### Predicted split, from the scores alone

| Outcome | Records | Share |
| --- | ---: | ---: |
| Auto-accept | 1,072 | 42.0% |
| Review — tied at top | 346 | 13.5% |
| Review — unsure band | 767 | 30.0% |
| Confidently different | 369 | 14.4% |
| **Total** | **2,554** | |

Review load is **1,113 record-level decisions**, 56% of the 2,000-decision
budget.

---

## 2. What the two-dimensional rule was and was not shown to do

This section states the evidence precisely, because a shorter and more
flattering summary is available and would be misleading.

Three rules were compared at matched accepted-pair counts, using Amazon-side
collisions — two Walmart records claiming the same Amazon record — as a
label-free coherence measure. Only the Amazon side is informative here: the
margin test constrains the Walmart side *by construction*, so a Walmart-side
measure would be circular.

| Accepted pairs | Plain score rule | Best-only (one-to-one) | Best + margin |
| ---: | ---: | ---: | ---: |
| 700 | 2.60% | 1.54% | 1.13% |
| 800 | 4.66% | 1.83% | 1.75% |
| 900 | 7.00% | 2.23% | **3.19%** |
| 1,000 | 6.77% | 4.27% | 3.71% |
| 1,100 | 7.40% | 4.89% | 4.63% |

**Most of the measured improvement comes from the one-to-one constraint, not
from the margin test.** At 1,000 accepted pairs the one-to-one constraint closes
2.50 percentage points; the margin test adds a further 0.56. At 900 the margin
test is 0.96 points *worse* — a nine-pair difference, which is noise at this
scale, but it is not a gain.

**The margin test is therefore not adopted because it tested better on this
measure.** It is adopted on separate grounds: selecting the highest-scoring
partner among tied candidates is, in the 257 records where the gap is exactly
zero, decided by row order — a coin flip producing errors that carry high
confidence. That failure mode is **invisible to the collision measure**, because
an arbitrary pick from a tied group is no more likely to collide on the Amazon
side than a correct one. The guarantee against it was already committed to in
D31.

The simpler framing — *"the two-dimensional rule tested better"* — is true only
in a narrower sense than it sounds, and is not the claim made here.

A caveat on the measure itself: Amazon-side excess treats a legitimate
one-to-many match as an error. Where such matches genuinely exist, the absolute
percentages above are pessimistic for all three rules. The comparison between
rules is unaffected, since all three are scored identically.

---

## 3. Measurements to be taken at final evaluation

These are fixed now. All are computed after unsealing, none before.

### 3.1 Headline performance

1. **Precision, recall and F1 of the auto-accept set** (1,072 pairs) against the
   answer key.
2. **Precision, recall and F1 of the full system**, auto-accept plus the
   outcomes of the 1,113 reviewed records.
3. **Coverage**: the share of records decided without review, and the share of
   true matches captured within it.
4. **The true risk-coverage curve**, replacing the model-implied curve
   currently available. Reported with AURC.

### 3.2 The claims this project has made, tested directly

5. **Do the "confidently different" records have matches?** 369 records are
   assigned this outcome. Each one that has a true match is a false negative the
   system asserted confidently. This is the single most exposed claim in the
   rule.
6. **Is the true match present in a tied group at all?** For each of the 346
   tied records, whether the answer key's partner appears among the tied
   candidates. Worked examples in D31 suggest some groups contain no correct
   partner.
7. **Would the coin flip have been right?** For the tied records, how often
   selecting the highest-scoring partner would have chosen correctly. This
   directly tests the reasoning that rejected Option B. **If it would have been
   right far more often than chance, D31's rejection of Option B was wrong, and
   that will be reported as such.**
8. **Does the margin test earn its place after all?** Precision of the accepted
   set with and without the margin test, now measurable directly.

### 3.3 The calibration concerns on record

9. **The prior.** The posteriors sum to 12,941 expected matches against a
   λ-implied 1,128 — an 11.5× inflation. The true match count settles which, if
   either, is right. **No absolute probability from this model is treated as
   trustworthy until this is resolved**, and no threshold in section 1 was
   chosen using one.
10. **The `m` normalisation drift** (`rare_tokens` 1.0725, `title` 0.9541) and
    its effect on the accepted set.
11. **Blocking recall**, deferred since D14: the share of true matches surviving
    into the 564,450 candidate pairs. This bounds everything above.

### 3.4 Open questions with no prediction recorded

12. **A third of Walmart records have no plausible candidate.** 859 records
    (33.6%) have nothing scoring above p = 0.5 and 369 (14.4%) nothing above
    p = 0.081. Two explanations exist — no counterpart is present in the Amazon
    table, or blocking and scoring failed these records — and they cannot be
    distinguished without labels. **No prediction is recorded here.** The
    measurement is registered so the answer cannot later be presented as
    though it had been expected.
13. **The baseline.** The D9 result was voided by D14 and the baseline must be
    re-run before any comparison against it is reported.

---

## 4. What would count as the rule failing

Recorded so that the standard is set before the result is known.

- Precision on the auto-accept set materially below the model-implied 0.106%
  risk would confirm the calibration concerns in section 3.3 — expected, and not
  by itself a failure of the *rule*, which was chosen on structure rather than
  on calibration.
- A substantial share of the 369 "confidently different" records having true
  matches **is** a failure of the rule, and of the decision to use that label.
- The tied-group measurements (6 and 7) going against D31 would mean the tie
  policy was wrong. It would be reported, not quietly dropped.

---

## 5. What is not claimed

The label **confidently different** reflects genuine confidence derived from the
analysis in this document, and is used deliberately in preference to a softer
phrase. That confidence is nonetheless **structural, not empirical**: it rests
on the model's ordering of pairs and on the shape of the score distribution, and
**it has never been checked against a real label.** Until the measurements in
section 3 are taken, every number in this document describes what the system
believes, not what is true.
