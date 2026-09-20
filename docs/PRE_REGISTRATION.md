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

---

## 6. The two review arms

**Added 19 September 2026, still before any labelled data has been read.** The
sections above were written first and are unchanged. This section fixes the two
arms described in [D24](DECISIONS.md#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai)
before either is run.

### 6.1 Population

Both arms run over **the same records**, or their results cannot be compared.

The full population is the **1,113 records routed to review** by the rule in
section 1. The **346 tied records** are run first as a validation slice — to
check stability and calibrate cost — and the arm is then extended to all 1,113.
Any result reported for one arm is reported over the same population as the
other, and the slice is never presented as the headline.

### 6.2 The AI arm

**Model:** `claude-opus-5`, temperature 0. The exact model identifier, the
prompt, and every raw response are stored with the results.

**Evidence shown.** The AI receives exactly what a human reviewer would see: the
same queue artefact, the same candidates under the display rule of
[D33](DECISIONS.md#d33--how-many-candidates-a-reviewer-sees-and-how-truncation-is-disclosed),
the same seeded shuffle and the same truncation labels.

**Evidence withheld: the match scores.** The purpose of escalation is to resolve
cases the classical system cannot — *512MB against 32GB*, *smoke grey against
hot pink*. Supplying the classical system's scores would anchor the AI to the
tie and destroy the independence the comparison depends on. The AI sees record
text only.

**The prompt, fixed here verbatim:**

```
You are matching product listings between two retailers. Decide whether the
Walmart listing below refers to the same real-world product as any one of the
Amazon listings.

WALMART LISTING
<title, brand, modelno, price, category>

CANDIDATE AMAZON LISTINGS
<for each: id, title, brand, modelno, price, category>

Exactly one candidate may refer to the same product, or none may. Attributes
such as storage capacity, physical dimensions, colour, model number and product
variant distinguish otherwise similar products: two listings differing on any of
these are different products even when their descriptions are otherwise nearly
identical.

Respond with JSON only:
{"decision": "match" | "none_of_these" | "cannot_tell",
 "amazon_id": "<id, or null>",
 "reasoning": "<one or two sentences>"}

Choose "cannot_tell" only where the listings lack the information needed to
decide, not where the decision is merely difficult.
```

**Decision schema.** The three outcomes match the reviewer options in
[D31](DECISIONS.md#d31--tied-partners-when-the-model-cannot-choose-between-candidates)
exactly, so the arms are scored identically. The `reasoning` field is stored for
audit and is **not** scored.

**Cost.** Input and output tokens are recorded per record and priced, because
[D7](DECISIONS.md#d7--ai-escalation-allowed-real-world-knowledge-judged-on-cost)
judges escalation on cost reduction rather than accuracy alone.


#### Amendment, 19 September 2026 — the model was changed

**The commitment above is left standing and unedited.** This project pre-registered
`claude-opus-5`, and that is what section 6.2 says. It was changed before the arm
ran, and this block records the change rather than hiding it in a revision.

| | |
| --- | --- |
| Originally committed | `claude-opus-5` |
| Now used | **`gpt-5.4-mini-2026-03-17`** |
| Reason | Account access, and cost: the cheapest viable option was preferred |
| Date | 19 September 2026 |

**When this happened matters.** No call had been made, no result existed, and no
labelled data had been read. The change could not have been influenced by an
outcome, because there was no outcome. Had the arm already run, replacing the
model would have voided the pre-registration rather than amended it.

**A dated snapshot, not a floating alias.** `gpt-5.4-mini` without the date can be
repointed to a different model without notice, which would leave this document
naming something that no longer exists. The dated identifier cannot.

**What was verified before fixing on it**, because published information about
whether this model belongs to the reasoning family was contradictory:

| Check | Result |
| --- | --- |
| Accepts `temperature=0` on the call path used | Yes |
| **Honours** it — three runs of a variance-prone prompt | Yes, identical output each time |
| Reports reasoning tokens | No — `reasoning_tokens: 0` |

The second check is the one that mattered. A model that accepted the parameter and
ignored it would satisfy the letter of section 6.2 while breaking what it is for:
the stability gate in 6.3 assumes that variation between runs comes from candidate
ordering. If the model sampled freely at temperature 0, a flip would no longer mean
what the gate says it means.

**What this changes about the claim.** The arm now measures what *an OpenAI model*
can do with this queue. It is not a result about Claude, and the write-up must not
imply one. The question D7 and D24 pose — how much of the review queue an AI can
clear, and at what cost — is unchanged, because neither is specific to a vendor.

### 6.3 The stability gate, and what disqualifies the arm

A language model is exposed to position bias in the same way a human reviewer
is. Each record is therefore judged **three times under three different shuffle
seeds**, and the agreement between those runs is measured.

This is a genuine validity check that requires **no labels** and is therefore
run **before** unsealing.

Two criteria, both fixed now:

1. **Against chance.** Unanimous agreement must be clearly above the agreement
   expected from choosing uniformly at random among the same displayed
   candidates, computed per record from its own candidate count.
2. **An absolute floor: unanimous agreement across the three runs on at least
   60% of records.**

> The 60% figure is a **judgement, not a measurement.** Below it, two in five
> decisions depend on the order candidates happened to be displayed in, and
> reporting such decisions as a measured headline result would misrepresent
> them. No evidence fixes the number precisely; it is recorded in advance so it
> cannot be chosen after seeing which side of it the result falls.

If the arm fails either criterion, that is **reported as the finding**, and its
accuracy is not presented as a headline result.


#### The same-ordering control

Determinism at temperature 0 was confirmed on a short prompt. Real prompts are
roughly 644 tokens with long candidate lists, and identical output is not
guaranteed to hold as strongly at that length: large-batch inference can vary
slightly even at temperature 0.

Each record is therefore judged a **fourth** time, using **the same ordering as the
first run**. Any disagreement between those two is sampling noise, because nothing
about the input changed.

This costs one extra call per record and needs no labels. It separates the two
things the gate would otherwise confuse:

* run 1 against run 4 — **sampling noise**, the input was identical
* runs 1 to 3 against each other — **position bias**, the ordering differed

The control rate is **reported alongside the gate result**. A high control rate
does not by itself disqualify the arm, but it caps how much of the measured
instability can honestly be attributed to presentation, and the gate result must
be read against it.

> **Cross-reference added 19 September 2026, after the arm was run on the
> validation slice.** Nothing above is altered. The same-ordering control found
> that a flip indicates *either* position bias *or* sampling noise, and that
> noise is roughly three times the larger contributor — so this section
> describes its own measurement more narrowly than the measurement turned out to
> be. The correction, with the decomposition, is recorded in
> [D34](DECISIONS.md#d34--the-ai-arm-passes-its-stability-gate-and-what-the-control-revealed).
> It is recorded there rather than here because a pre-registration edited after
> results exist is no longer one.

### 6.4 The human-only arm

> ⚠️ **ASSUMPTION — a model, not an observation.** No human reviews these
> records. Accuracy is a supplied input, per D24.

Run at accuracies of **0.80, 0.90, 0.95 and 1.00**, seeded for reproducibility.

**The error model, fixed here.** With probability *a* the simulated reviewer
returns the correct outcome. With probability *1 − a* it chooses **uniformly at
random among the displayed candidates and the "none of these" option**.

Uniform choice is deliberate. Weighting the error by match score would smuggle
the classical system's opinion into the arm that is supposed to be independent
of it, and would flatter the comparison in a way that could not be detected from
the result.

**This arm cannot run before unsealing**, because simulating a reviewer who is
correct 90% of the time requires knowing what correct is. It is written and
fixed now, and executed once, at final evaluation.

### 6.5 The display ceiling

A reviewer can only choose among the candidates D33 displays. Where the true
match was truncated away, a reviewer of **any** accuracy — including 1.00 —
answers wrongly: they would correctly report "none of these" given what they
saw, and be scored incorrect.

The human-only arm therefore has a ceiling **below 1.00 that is set by this
project's display rule, not by human fallibility.**

That ceiling is **reported as a metric in its own right**, not folded into the
accuracy figures. It is also the honest measurement of what D33's choice of ten
extra candidates cost, which was recorded there as a judgement the label-free
data could not settle.

### 6.6 What is measured, for both arms

For each arm, over the agreed population:

1. Precision, recall and F1 of its decisions against the answer key.
2. How often "none of these" was the correct answer, and how often each arm gave
   it — the outcome D31 argued the interface must allow.
3. For the AI arm: cost per record, and cost per correct decision.
4. For the AI arm: the pre-unsealing stability result, reported whether or not
   it passed.
5. For the human arm: results at all four accuracies, with the display ceiling
   stated alongside.
6. The share of the review queue the AI could clear at precision equal to or
   better than the modelled human — the question D7 asked.

---

## 7. The baseline comparison

**Added 19 September 2026, before any labelled data has been read.**

[D9](DECISIONS.md#d9--establish-a-deliberately-dumb-baseline-before-building-anything-clever)'s baseline result was voided by
[D14](DECISIONS.md#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).
Section 3.4.13 commits to re-running the baseline before any comparison against
it is reported. This section fixes what that comparison actually is, because as
things stood it was not well defined.

### 7.1 Two problems with the baseline as it was written

**It was supervised and the real system was not.** `choose_threshold` picks the
threshold maximising F1 on `train` labels. The matcher never saw a label: its
prior was derived structurally, its thresholds were placed on the shape of the
score distribution, and the whole rule was pre-registered blind. A baseline
granted a supervised tuning step that the real system was denied does not
measure what a reader would assume it measures.

**They did not evaluate the same thing.** The baseline scored the benchmark's
own curated pairs - the decision step alone, on a set where roughly 9.4% of
pairs are matches. The real system runs the full pipeline over 564,450
candidates drawn from 56,376,996 possible pairs. The baseline module says so
itself: *those two numbers are not comparable*. A third asymmetry: the system
emits at most one match per record, the baseline predicted per pair with no such
constraint.

### 7.2 The decision rule

Fixed here:

* **Similarity**: Jaccard over all attribute values combined, as already
  implemented - the baseline stays deliberately unsophisticated.
* **Candidate set**: the same 564,450 candidate pairs the real system scores.
* **One match per Walmart record**, taking its highest-scoring candidate. This
  matches the system's one-to-one constraint so the two produce the same shape
  of output.
* **Accept at Jaccard ≥ 0.34.**

The baseline gains the structural treatment the system had - a label-free
threshold and the one-to-one constraint - and none of the sophistication. That
isolates what the probabilistic model buys.

### 7.3 Why 0.34: equal coverage

The threshold is set so that the baseline auto-accepts **the same number of
records the system does**, and the two are compared on precision at matched
coverage. Neither can then buy precision by abstaining more, and nothing about
the choice requires a label.

The system auto-accepts **1,072** records. On this data:

| Threshold | Records accepted |
| ---: | ---: |
| 0.33 | 1,161 |
| **0.34** | **1,055** |
| 0.35 | 1,021 |

A search at 0.0005 resolution finds no value closer than 1,055, so 0.34 is the
round number at the nearest achievable point.

### 7.4 Why the flat-spot method was not reused

The thresholds in section 1 were placed on **measured flat spots** - regions
where moving the threshold changes the outcome least. The same method was tried
here first, and **it does not transfer.** It is recorded rather than omitted, so
that the two pre-registrations read consistently to anyone comparing them.

It worked for the matcher because that distribution is genuinely lumpy: a single
match-weight value held 17.9% of all pairs and the top five held roughly 57%, so
a threshold physically could not land between them. The baseline's is not:

| | Matcher (bits) | Baseline (Jaccard) |
| --- | ---: | ---: |
| Largest single value | 17.9% of pairs | 4.15% of records |
| Top five values | ~57% | 15.5% |

With 250 distinct values over 2,554 records the scale is near-continuous, so
churn stops measuring structure and starts measuring **density**. Normalised by
how many records remain, it rises steadily with the threshold - 0.133 at 0.20,
0.283 at 0.40, 0.412 at 0.66 - which is the signature of a distribution with no
flat spots at all.

Taken at face value the method would have selected **0.66, accepting 68 of 2,554
records**: a crippled baseline, and a result flattering to the real system
produced by an argument that does not apply to it. The "flattest" placement was
simply the emptiest one.

### 7.5 What is reported

1. **Headline**: precision of the baseline's accepted set at matched coverage,
   against the system's, over the same candidates.
2. **Supporting**: the **full precision-recall curve** across all thresholds.
   This is what makes the headline uncherry-pickable - if the baseline beats the
   system at some other threshold, the curve says so and that is reported.
3. **Secondary**: the original curated-pairs run, kept for continuity with the
   benchmark literature, labelled **supervised and not comparable** to either
   number above.
