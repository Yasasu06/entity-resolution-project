# Predictions versus reality

Every substantive claim this project made **before any labelled data was read**,
set against what the answer key actually said.

The claims were committed to git and independently timestamped before the labels
were opened — see [`PRE_UNSEAL.md`](PRE_UNSEAL.md) for the boundary commit and
the proof. The measurements are in [D39](DECISIONS.md) and [D40](DECISIONS.md).

**The misses are included.** A table showing only successful predictions would
be worth nothing: anyone who found a single omitted failure would be right to
discount the whole thing. Three predictions were wrong, and they are here with
the rest.

---

## Summary

| # | Claim made blind | Reality | |
| --- | --- | --- | :-: |
| 1 | Blocking retains essentially every true match | **99.90%** recall (961 of 962) | ✅ |
| 2 | λ ⇒ about **1,128** matches exist | **962** actual | ✅ |
| 3 | "Confidently different" is the claim most likely to fail | **0.5%** wrong (2 of 369) | ✅ |
| 4 | Picking the top tied candidate is near a coin flip | **66.3%** vs **53.4%** chance | ✅ |
| 5 | Tied groups often contain no correct partner at all | correct partner present only **25.7%** of the time | ✅ |
| 6 | The display cap costs some true matches | **11 of 1,129** (ceiling 99.03%) | ✅ |
| 7 | The auto-accepted set is unreliable | **43%** of accepts wrong | ✅ |
| 8 | The model's aggregate confidence is badly inflated | posteriors sum to **12,941** against **962** actual | ✅ |
| 9 | "A threshold will not fix it" (D38) | precision **56.8% → 75.0%** when raised | ❌ |
| 10 | The AI judge estimated **~31%** of accepts were wrong | **43%** were (51.3% on the judged subset) | ❌ |
| 11 | A `test`-only figure would be reported (§10.1) | **not computable** — the splits partition pairs, not records | ❌ |
| 12 | *No prediction recorded* — do low-scoring records have matches? (§3.4.12) | **4.7%** of the 859 do | — |

**Eight held. Three failed. One was registered in advance as unknowable.**

---

## The eight that held

**1 — Blocking.** The blocking stage was built to guarantee that every record on
both sides remained reachable, and was validated without labels on reduction
ratio and reachability alone. It retained **961 of 962** true matches, and
**100%** of those in `test`. The most heavily scrutinised component was right.

**2 — The prior.** [D25](DECISIONS.md) derived λ = 2.0×10⁻⁵ structurally, with no
labels, implying roughly **1,128** matches across the cross product. The true
count is **962** — within 17%. This had been the project's longest-running open
worry.

**3 — The most exposed claim.** Section 4 of the pre-registration named one
outcome that would constitute outright failure: a substantial share of the 369
"confidently different" records turning out to have matches. **Two did. 0.5%.**

**4 and 5 — The tie policy.** [D31](DECISIONS.md) refused to let the system pick
the highest-scoring candidate among ties, on the grounds that the choice was
effectively arbitrary, and insisted "none of these" be answerable. Section 3.2.7
committed in advance to reporting that D31 was **wrong** if argmax beat chance.
It did not: **66.3%** against **53.4%** by chance. And the correct partner is
present in a tied group only **25.7%** of the time, so the "none of these"
requirement was load-bearing rather than decorative.

**6 — The display ceiling.** [D33](DECISIONS.md) capped how many candidates a
reviewer sees, recording that the cost was a judgement the label-free data could
not settle. It cost **11 records of 1,129**.

**7 — The central failure, found blind.** [D36](DECISIONS.md) concluded from two
independent label-free methods that the auto-accepted set was unreliable at the
level of product identity. **It was: 456 of the 1,056 accepts at that point were
wrong.** The finding, the diagnosis and the evidence were published weeks before
the answer key was opened. The system now accepts 994, of which 398 are wrong.

**8 — Overconfidence.** The tension between λ's implied 1,128 and the posteriors'
13,000 was recorded as unresolved from D25 onward. It resolves against the model:
**12,941 implied, 962 actual.** The scores are not calibrated probabilities and
were never treated as such.

---

## The three that failed

**9 — D38's reasoning was overstated.** [D38](DECISIONS.md) declined to raise the
accept threshold, arguing *"a threshold will not fix it."* Precision rises from
**56.82% to 75.00%** when the threshold is raised to the rejected setting.

The decision still holds on F1 — 59.46% against 53.15% — but the reasoning was
wrong, and [D40](DECISIONS.md) records why. The planted probes measured only
*near-miss* confusion, which really is threshold-invariant. Most wrong accepts
fail for a different reason: **the record has no partner at all.** The probe was
built by mutating partners of already-accepted pairs, so every probe had one by
construction, and it was structurally blind to the dominant failure.

**10 — The AI judge was too generous, twice.** D36 used an independent language
model to estimate that **~31%** of accepts were wrong. The true figure is
**43%**, and **51.3%** on the records it actually judged. Of the 429 accepts the
judge positively *endorsed*, only **73.4%** were correct.

The judge was still useful — its disagreement correlated with real errors and it
identified the failure — but as a calibrated estimate of error rate it was
optimistic, not alarmist.

**11 — A pre-registered commitment that could not be honoured.** Section 10.1
committed to reporting a `test`-only figure for comparability. It cannot be
computed honestly: **746 of the 900 records appearing in `test` also appear in
`train`**. The benchmark splits *pairs*; this system decides *records*. Only the
combined figure is reported. This is a flaw in a document written before the
labels, discovered by trying to honour it.

---

## The one registered as unknowable

**12 —** Section 3.4.12 recorded that 859 records had no candidate scoring above
p = 0.5, that this could mean either "no counterpart exists" or "the pipeline
failed them", and that **no prediction was being made** — registered so that
neither answer could afterwards be presented as expected. **4.7% of them have a
true match.** The pipeline was largely right, and the records mostly have no
partner.

---

## What this is and is not evidence of

**It is not evidence that the system works.** It does not: 59.96% precision on
unattended output is not deployable, and [D39](DECISIONS.md) says so. (That figure
was 56.82% when D39 was written; [D41](DECISIONS.md)'s mutual-best-match rule
raised it, and F1 with it, from 59.46% to 60.94%.)

**It is evidence that the reasoning was sound more often than not, and that the
failures were found before the answers were available.** The project's largest
weakness was documented, diagnosed and published while the labels were still
sealed — and the pre-unseal analysis turned out to be *conservative* about that
weakness rather than defensive of it.

The three misses matter as much as the eight hits. Two of them are cases where
this project was **too pessimistic or too narrow**, not too flattering — and the
third is a pre-registration that could not be executed as written.
