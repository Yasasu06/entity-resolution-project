# Decision log

A running record of every significant decision on this project and the
reasoning behind it. Newest entries are added at the bottom as work proceeds.

It is written to be readable by someone with **no prior context** — including
someone who has never seen the code. Jargon is explained where it appears.

---

## Background, in one minute

**The problem.** Two companies' databases both list the same product. One says
`sumdex slr camera sling pack`, the other says `slr camera sling pack sumdex
poc-484bk`. A person sees one product; a computer sees two unrelated rows.
There is no shared ID to join them on. Deciding which records refer to the same
real-world thing is called **entity resolution** (or record linkage).

**What makes it hard.** You cannot check every pair against every other pair —
here that would be 56 million comparisons. And even when you find a candidate,
"same or not?" is often genuinely ambiguous, not just computationally awkward.

**What this project is really about.** Most matching systems force every pair
into a yes/no answer. This one deliberately keeps a third option: **"unsure"**.
Pairs in that band get routed to a human, with a sparing AI-assisted step to
keep that human queue affordable. The interesting engineering is in deciding
*what belongs in that band* and *what it costs*.

---

## D1 — Walmart-Amazon (dirty version) is the primary dataset

**Decision.** Build and evaluate the system on the Walmart-Amazon₂ "dirty"
benchmark. Keep DBLP-ACM₂ as a secondary comparison case only.

**Why.** Both were inspected before choosing. On measurement, Walmart-Amazon is
substantially harder, and difficulty is the point — a system whose selling
point is handling uncertainty needs genuinely uncertain cases to handle.
Specifically: matching and non-matching pairs overlap heavily in text
similarity (about 82% of true matches look *less* similar than a top-decile
non-match), only 9.4% of labelled pairs are matches, one table is 8× the size
of the other, and the single most decisive field is missing from 64% of rows.

DBLP-ACM is comparatively easy — academic paper titles are near-identical
across sources — so it serves better as a contrast than as the main target.

Full evidence: [`ASSESSMENT.md`](ASSESSMENT.md).

---

## D2 — The Company dataset is deliberately deferred

**Decision.** Stop pursuing the third benchmark dataset. Not an open task.

**Why.** Two independent blockers. Its canonical host is unreachable from the
development environment (refused at the network level, so no URL on that host
works, and every published mirror is dead or blocked). And its main file is
reported at ~185 MB, which exceeds GitHub's hard 100 MB per-file limit — so it
could not live in this repository without extra tooling regardless.

It is also a *textual* matching problem (long free-text descriptions), which is
a different problem from the structured-but-corrupted attribute matching this
project is built around. Deferring it narrows scope rather than losing
something essential.

No substitute or synthetic data was used in its place.

Full reasoning and the conditions that would reopen it: [`DATASETS.md`](DATASETS.md).

---

## D3 — Evaluate the full pipeline first, not just the pre-filtered pairs

**Decision.** Build and evaluate blocking + matching across the realistic
**~56.4 million** possible pairs (2,554 × 22,074). Treat scoring against the
benchmark's own curated 10,242-pair file as a **separate, later** exercise.

**Why this matters more than it sounds.** The benchmark ships a file of 10,242
labelled pairs, and it is tempting to treat that as "the dataset". It is not —
it is already the *output* of the original researchers' own filtering step. In
that file, 9.4% of pairs are real matches. In the full space, real matches are
about **0.0017%** of all pairs.

That gap is not a detail. A decision threshold that looks precise at 9.4%
prevalence can be swamped by false positives at 0.0017%. Reporting only the
curated-file number is the most common way a project like this quietly
overstates itself.

**What this stage is actually asking:**
- Can our own blocking and matching find the 962 known true matches when
  searching the full, realistic space rather than a pre-filtered one?
- How many false positives does that produce at realistic rarity?
- Does the approach run practically at that scale at all?

**Reporting rule.** Numbers from the two evaluations are **never combined or
presented as one figure**. Every reported number states which evaluation it
came from.

*Terminology: "blocking" means cheaply narrowing 56 million candidate pairs
down to a manageable shortlist worth comparing properly — the equivalent of
only comparing books on the same shelf rather than the whole library.*

---

## D4 — Human review: measure and export now, build the interface later

**Decision.** Deliver (a) a simulation with metrics, and (b) a review queue
artifact — the uncertain pairs exported with the evidence that made them
uncertain, in a format a person could actually work through.

**Deferred, explicitly not dropped:** (c) a real interactive review interface.
This is a **planned future phase**, to be built for the live demo once the core
pipeline, matching logic, and review simulation are working well.

**Why this order.** (a) and (b) are what actually prove the concept — they
produce the number that matters ("routing the top N% most-uncertain pairs to a
human lifts precision from X to Y, at a cost of Z reviews"). A user interface
demonstrates front-end skill, which is not what this project is arguing. Built
first, it would also lock in decisions about the review workflow before the
data has told us what reviewers actually need to see.

---

## D5 — Review capacity is an assumption, clearly labelled

> ⚠️ **ASSUMPTION — invented for planning. This is not a real client
> requirement and no real figure exists yet.**

**Placeholder:** a human reviewer can process **200 pairs per day**, over a
**10-working-day** window — a total review budget of **2,000 pairs**.

**Why invent one at all.** Without a capacity limit, choosing a threshold is
arbitrary — you can always "send more to review". With one, it becomes a real
constrained problem: *given that we can only afford 2,000 reviews, where do we
draw the uncertainty band to catch the most true matches?* That is the question
an actual deployment faces, and it makes the resulting design defensible.

Replace with a real number if one ever becomes available.

---

## D6 — Splink runs unsupervised; labels are for evaluation only

**Decision.** The matching model learns **without** using the labels. Labels are
used only to evaluate results and to choose thresholds, and only on the
`train` and `valid` splits. The `test` split is **sealed** until one final
evaluation at the very end of the project.

**Why unsupervised.** Splink learns how much each kind of agreement between two
records is worth using a statistical method that needs no answer key
(expectation-maximisation). We *do* have an answer key, and could train on it —
but real client engagements almost never come with 10,000 labelled examples. A
system that works without them is both a more honest simulation and a stronger
claim: *"this works with no labelled data, and here is the labelled data
proving it worked."*

**Why seal the test split.** Every time you check a result against a set of
answers and then adjust something, you leak a little of those answers into your
design. Do it often enough and your final number measures how well you tuned
to that specific data, not how well the system works. Keeping one split
genuinely untouched preserves one honest number at the end.

**How it is enforced.** Not by memory — by code. The data loader refuses to
load the test split unless explicitly overridden, and a test asserts that the
refusal works.

---

## D7 — AI escalation: allowed real-world knowledge, judged on cost

**Decision.** For pairs in the uncertain band, an AI step may be consulted.

**Scope.** It is explicitly allowed to use general world knowledge beyond the
literal text of the two records — for example, recognising that `ph3100u-1e3s`
is a Toshiba part number even when the word "Toshiba" appears nowhere in that
record. This is deliberate: that kind of judgement is precisely what a string
comparison engine cannot do, and is the entire reason for the step to exist.

**Success is defined as:** *reduces the human review queue by X% at
equal-or-better precision, measured only on the uncertain band.*

Deliberately **not** framed as "beats human accuracy". This positions the step
honestly as a **cost-reduction layer**, not an oracle — a claim that can be
demonstrated rather than asserted.

> ⚠️ **ASSUMPTION — invented for planning, not a real requirement.**
> Budget placeholder: at most **500 AI calls per full evaluation run**,
> escalating at most **5%** of candidate pairs, with a rough cost ceiling of
> **~$5 per run**. "Sparing" should mean a number, so here is one to design
> against until a real one exists.

---

## D8 — The field-scrambling problem, and the plan for it

**The situation.** The "dirty" benchmark is not naturally messy. Its authors
took clean data and deliberately corrupted it: for each record they moved
attribute values into the `title` field and blanked the original column. So
about half of every non-title column is empty, and titles trail stray prices,
model numbers and categories that belong elsewhere.

**Why this collides with the standard tool.** Splink compares like with like —
`brand` against `brand`, `price` against `price`. When a field is empty on
either side it simply drops that comparison. On this data that means throwing
away evidence *that is still present in the record*, just sitting in the wrong
column.

**Decision — a three-part plan, in order:**

1. **(a) Naive field-to-field matching first.** Accept the null handling as-is.
   This is a baseline to beat, not the final system.
2. **(c) Custom cross-field comparisons — the main contribution.** Comparisons
   that ignore which column a value happens to sit in. For example: *does table
   A's `brand` value appear anywhere in table B's `title` text?* Or: *do both
   records share a rare alphanumeric token — a model number like
   `ph3100u-1e3s` — regardless of which field holds it?* Each such comparison
   will be documented with the reasoning behind it.
3. **(b) Field repair — deferred, not dropped.** Attempting to un-scramble
   values back into their proper columns before matching. A plausible future
   direction, deliberately not attempted now: it is error-prone, and errors
   would contaminate everything downstream.

**Why this is the centrepiece.** The story is not "I used a matching library".
It is *"I diagnosed exactly why the standard tool underperforms on this
specific messy data, and extended it to fix that."* That is the work a Forward
Deployed Engineer actually does at a client site, where the data never matches
the tool's assumptions.

---

## D9 — Establish a deliberately dumb baseline before building anything clever

> ⚠️ **SUPERSEDED by [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).**
> The *idea* stands — a crude baseline is still built and still has to be
> beaten. What changed is *when* it may be scored. The result below was
> computed correctly under the rule in force at the time, which permitted
> checking against `train` and `valid`. Under the stricter rule that replaced
> it, **no labelled data may be consulted until the whole system is finished**,
> so the number below is **no longer a live result**. It is retained here as
> history. The baseline will be rebuilt and re-scored at the end, as part of
> one single honest evaluation alongside the real system.
>
> This is a rule change, not an error.

**Decision.** Before touching Splink, build the crudest matcher that could work
and score it honestly.

**What it does.** Mash every attribute of a record into one bag of words, count
what proportion of words two records share, and call it a match above some
threshold. No learning, no probabilities, no awareness of which field a word
came from.

**Result (SUPERSEDED — historical record only, see D14):** F1 = 0.381 on the
validation split *(precision 0.408, recall 0.358; threshold 0.450 chosen on
train)*.

> **Scope of that number:** the benchmark's curated pairs — the decision step
> only. **Not** the full 56.4M-pair pipeline evaluation (see D3). The two are
> not comparable.

**Why bother.** It is easy to build something complicated, watch it produce
plausible output, and never check whether five lines of naive code would have
done as well. This is now the floor: the real system has to beat 0.381 to have
justified its own existence. That the floor is low also independently confirms
D1 — this dataset really is hard.

**Note on splits.** The original plan said to score this on the test split,
which contradicts D6's sealing rule. The sealing rule won: the threshold was
chosen on `train` and reported on `valid`, and `test` has not been read.

---

## D10 — Tooling: Splink 4.0.17 on DuckDB 1.5.5, versions pinned

**Decision.** Use Splink as the matching engine, running on DuckDB, with exact
versions pinned in `requirements.txt`.

**Why Splink.** It implements a well-established statistical approach to record
linkage (the Fellegi-Sunter model), is actively maintained, and — importantly
for this project — produces a **calibrated probability** for each pair rather
than a bare yes/no. An explicit "unsure" band needs meaningful probabilities to
define its edges, so this is a prerequisite, not a preference.

**Why DuckDB.** Splink expresses its work as SQL and needs a database to run it.
DuckDB runs inside the Python process with no server to install or configure.
A useful side effect: the matching logic is readable SQL, which suits a project
with a stated goal of learning SQL.

**Why pin versions.** Without exact pins, a future `pip install` could pick up
newer libraries and silently change results — making old numbers impossible to
reproduce.

**One compatibility check worth recording.** Splink 4.0.17 declares no upper
limit on its pandas version, but pandas 3.x is a major release with breaking
changes. Rather than assume compatibility, a full Splink linker was actually
run end-to-end on this combination before pinning it. It works.

---

## D11 — One canonical data loader, to prevent an invisible bug

**Decision.** All data loading goes through `src/data_loading.py`. Nothing reads
the CSVs directly.

**The bug it prevents.** Both source tables number their records starting from
zero. Table A has a record `0`; so does table B. Fed into a matching engine
unchanged, those two different products share an identifier — and the failure
mode is not a crash or an error message. It is plausible-looking output that is
quietly wrong, which is far more dangerous.

The loader gives every record a prefixed identifier (`A_0`, `B_0`) in exactly
one place, so it cannot be forgotten in some notebook six weeks from now.

**It also** reads all values as text so that model numbers and prices are not
silently reinterpreted as numbers, refuses to load the sealed test split, and
fails loudly if the two tables ever stop sharing a schema. Twelve tests cover
these properties.

---

## D12 — Strip notebook outputs before committing

**Decision.** Use `nbstripout` to remove Jupyter notebook outputs automatically
at commit time.

**Why.** A notebook file stores its results — tables, charts, images — inside
the file itself. Committing that means every rerun produces an enormous,
unreadable change, and merge conflicts land in machine-generated content that
cannot sensibly be resolved by hand. Stripping outputs keeps the repository
history about the *code*.

**Setup note.** This is a local git setting, not something a clone inherits.
After cloning, run `nbstripout --install` once.

---

## D13 — Docker deferred until the pipeline works

**Decision.** No containerisation yet.

**Why.** Docker's value is reproducing an environment reliably. Doing that while
the design is still moving means maintaining a container spec that changes
daily, for no current benefit. Revisit once the pipeline is stable.

---

## D14 — Strict no-peek: no labelled data until the system is finished

**Decision.** No labelled answers — `train`, `valid` **or** `test` — are
consulted for any purpose until the entire system, including the full
56.4M-pair blocking and matching pipeline, is completely built. Then one single
evaluation is run, once.

**This supersedes D6**, which allowed using `train` and `valid` along the way
and sealed only `test`. It also supersedes the live status of the D9 baseline
result.

**It explicitly includes checks that feel like basic due diligence.** The
clearest example: *"how many of the 962 known true matches survive my blocking
step?"* That feels like sanity-checking rather than cheating. It is not. If a
blocking rule is kept or discarded based on how many known answers it
preserves, the answer key has shaped the design — and the final number stops
measuring how well the system works and starts measuring how well it was fitted
to that specific data.

**Why go this far.** The aim is to build the way a researcher or a Forward
Deployed Engineer genuinely has to work on a real deployment: arriving at a
client with no ground truth at all, having to justify every design choice from
the structure of the data itself. Not merely *"don't touch the test file"* but
*"don't know how well any part of this is working"* until it is finished. A
system designed under that constraint is one whose reasoning has to stand on
its own.

**The accepted trade-off.** This is real and was accepted deliberately, with
open eyes:

- No early sanity checks. If blocking silently discards a large share of true
  matches, that will not surface until the very end.
- No incremental feedback. Design choices in blocking, comparison logic and
  thresholds are all made without knowing whether they help.
- Rework risk. A flaw discovered at final evaluation may invalidate work built
  on top of it, and correcting it then re-running honestly is expensive.

This is the price of the guarantee, and it is being paid on purpose. It is
recorded here as a conscious trade-off, not an oversight.

**How it is enforced — in code, not by memory:**

- `src/data_loading.py` refuses to load *any* labelled split without an
  explicit `unlock_final_evaluation=True`.
- `src/baseline_token_overlap.py` refuses to run without
  `--unlock-final-evaluation`, and explains why.
- `src/inspect_datasets.py` no longer summarises label counts by default —
  reporting how many matches a split contains is answer-key information too,
  even though it looks like plain description.
- A test asserts that all three splits are sealed by default.

### Known prior contamination, recorded honestly

This rule cannot retroactively unsee what was already seen. Before it existed,
some analysis **did** use `train.csv` labels, and that knowledge informed the
project. Stated precisely, so the final write-up does not overclaim:

**Label-derived (must not inform design):**
- The word-overlap separation figures in [`ASSESSMENT.md`](ASSESSMENT.md) —
  mean similarity of true matches (0.422) vs non-matches (0.298), the
  separation gap, and the percentile-crossover statistics.
- The observation that ~39% of field comparisons *in true matches* have the
  attribute present on one side and missing on the other.
- The specific example record pairs shown in that document, which were selected
  because they are labelled matches.
- The superseded D9 baseline result.

**Not label-derived (safe to use freely):** row counts, column names,
missing-value rates per column, table sizes, token frequency distributions, the
documented corruption mechanism, and the published benchmark totals.

**Consequence.** The blocking design that follows is built only from the second
list. The first list is quarantined — flagged in `ASSESSMENT.md` and not used
as design input. The honest claim this project can make is therefore *"blocking
and matching were designed without label feedback, on a codebase where some
earlier exploratory analysis had used training labels"* — which is narrower
than *"designed in total ignorance"*, and is the claim that will be made.

---

## D15 — Fixing how text is split for n-gram blocking

**Decision.** When preparing a record's text for character-sequence blocking,
close up the gap between two adjacent words **only when a digit sits
immediately on one side of it**. Take character sequences *within* the
resulting chunks and never across a gap that was left in place.

### The problem this fixes

Blocking rule R5 compares records by overlapping 5-character sequences rather
than whole words. The reason is concrete: the two retailers punctuate
manufacturer part numbers differently.

| Walmart writes | Amazon writes |
| --- | --- |
| `rrvtps28pkr1` | `rr-vtps-28pk-r1` |
| `kvr400x64c3a1g` | `kvr400x64c3a 1g` |
| `n570gtxm2d12d5o` | `n570gtx-m2d12d5 oc` |

Word-level splitting sees these as unrelated, discarding the most decisive
evidence a product match has. Measured on the real data, **107** part numbers
in the Walmart table sit inside the Amazon text but are invisible to word-level
comparison.

The first implementation solved that by deleting *every* space and punctuation
mark before cutting the text into sequences. That worked for part numbers — and
created a much bigger problem, because it also welded ordinary words together:

```
"desktop computers"  ->  "desktopcomputers"
```

inventing sequences like `ktopc`, `topco` and `opcom`. These appear rare only
because that particular collision of two common words is uncommon; they say
nothing about what the product is. Measured on a 400-record sample, **79.3% of
all candidate pairs R5 produced were reachable only through such welds** — the
rule was mostly generating noise.

### Why this particular rule

Part numbers are alphanumeric, so the breaks inside them almost always have a
digit on one side. Boundaries between two ordinary English words almost never
do. That single signal separates the two cases without needing a dictionary,
a model, or any labelled data.

```
"kvr400x64c3a 1g"    ->  kvr400x64c3a1g        (joined - '1' is a digit)
"desktop computers"  ->  desktop | computers   (kept apart - 'p' and 'c')
```

### Measured effect

| | Before | After |
| --- | ---: | ---: |
| Part-number recoveries preserved | 107 | **101 (94.4%)** |
| Candidates reachable only via welds (400-record sample) | 71,682 (79.3%) | **13,807 (47.7%)** |
| R5 candidates at DF≤20 (whole dataset) | 255,051 | **87,152** |

The rule keeps almost all of the evidence it was built to keep, while removing
roughly two-thirds of the candidate pairs and more than four-fifths of the junk
ones.

### What it costs — stated honestly

**Six of the 107 recoveries are lost.** They share a shape: a short,
letter-only prefix split from the rest by a hyphen, where no digit touches the
gap and the remaining chunks are too short to yield a 5-character sequence.

```
vgpbkb1  vs  sony vaio bluetooth keyboard ... vgp-bkb1
acl100   vs  sony ac-l100 portable handycam ac adaptor ...
pwe550   vs  sharp electronics pw-e550 electronic dictionary
```

**A weaker version of the original problem remains.** A plain word followed by
a number still welds — `black 25 pack` becomes `black25pack` — because a
leading digit triggers the join. Requiring a digit on *both* sides would remove
this but would also discard genuine recoveries like `kvr400x64c3a` + `1g`. The
residual is accepted knowingly, is pinned by a test so it cannot drift
unnoticed, and accounts for the 47.7% figure above.

### Consequences

**All earlier threshold numbers are withdrawn.** Every sweep run before this
fix measured the flawed rule, including the `R1≤50 / R5≤20` recommendation.
Those figures are void and must not be reused or cited. A fresh sweep was run
against the corrected rule.

**This reopens the R4 question.** R4 was previously recommended for deferral on
the grounds that R5 alone reached 100% of Walmart records with zero orphans.
That result was an artefact of the noise: once the junk welds are removed, R5
at DF≤5 reaches 98.2% and leaves 46 records with no candidates at all. R5 alone
no longer provides a coverage guarantee, so the case for a fallback rule is
stronger than when deferral was proposed. Decision still open.

**Validation stays label-free.** Every figure here comes from the two source
tables. No labelled data was read, consistent with [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).

Implementation: `src/text_normalisation.py`, with 11 tests in
`tests/test_text_normalisation.py` covering both the recoveries and the
accepted residual.

---

## D16 — Final blocking design: five rules, and the thresholds behind them

> ⚠️ **Three settings here were later changed.**
> [D17](#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap) made
> R3 require **two** other shared words rather than one, and made R4 run in
> **both directions** rather than only from the Walmart side.
> [D18](#d18--r1-counts-word-frequency-on-the-amazon-side-only) changed R1 to
> count word frequency on the **Amazon side only** rather than pooled across
> both tables. The threshold *values* and the reasoning for choosing them
> stand unchanged.

**Decision.** Blocking runs five rules. A pair becomes a candidate if *any* of
them accepts it.

| Rule | What it looks for | Setting |
| --- | --- | --- |
| **R1** | A shared word that is uncommon across both tables | document frequency ≤ 100 |
| **R2** | A shared word shaped like a part number (letters + digits, ≥5 chars) | any frequency |
| **R3** | The same brand **plus** at least one other shared word | — |
| **R5** | A shared character sequence that is rare on the Amazon side | Amazon-side frequency ≤ 50 |
| **R4** | Nearest neighbours by text similarity, for records nothing else reached | 100 neighbours |

Implementation: `src/blocking.py`. Run `python -m src.blocking` for the report.

### Why these thresholds

Chosen from a measured sweep, not judgement. The governing metric is
**Amazon-reach**: how many of the 22,074 Amazon records are reachable from any
Walmart record at all. An unreachable record cannot be matched no matter how
good the scoring is. Walmart-side coverage saturates early and stops
discriminating between options, so it could not be used to choose.

Sweeping R1 and R5 together (R2 fixed, R3 and R4 excluded):

| R1 | R5 | Candidates | Orphans | Amazon-reach |
| ---: | ---: | ---: | ---: | ---: |
| ≤50 | ≤20 | 158,439 | 6 | 93.6% |
| ≤50 | ≤50 | 230,013 | 5 | 96.0% |
| ≤100 | ≤20 | 301,493 | 2 | 97.5% |
| **≤100** | **≤50** | **359,165** | **1** | **98.3%** |
| ≤100 | ≤100 | 488,560 | 1 | 98.6% |

The returns bend sharply at the chosen point: the step before it buys +2.3
percentage points of reach, the step after it buys +0.3. Loosening further
spends compute for almost nothing.

### Why we did not loosen R1 or R5 further to reach full coverage

At the chosen setting one Walmart record still had no candidates. Two ways to
fix that: loosen the thresholds until it is swept up, or give it a dedicated
fallback.

Loosening is the wrong instrument. It is indiscriminate — pushing R5 to ≤200
to reach zero orphans costs 922,896 candidates, quadrupling the workload across
*every* record to rescue one. It also degrades the rules it touches, since each
loosening admits weaker evidence everywhere. A targeted fallback fixes the
actual problem at its actual size.

### R4 reinstated — a reversal, and why

R4 was previously recommended for deferral, on the grounds that R5 alone
reached 100% of Walmart records with zero orphans, leaving nothing for a
fallback to do.

**That finding was an artefact.** It was measured before the [D15](#d15--fixing-how-text-is-split-for-n-gram-blocking)
normalisation fix, when roughly 79% of R5's candidates came from meaningless
character sequences welded across word boundaries. Those spurious candidates
were manufacturing the appearance of full coverage. With the noise removed, R5
at DF≤5 reaches 98.2% and leaves 46 records with nothing.

So the justification for deferring R4 did not survive the fix, and R4 is kept
as a guarantee that no record is ever left with zero candidates. The reversal
is recorded rather than quietly corrected, because the reasoning matters: the
original recommendation was sound given what was measured at the time, and the
measurement was wrong.

### R3 measured for the first time — and it is expensive

Every sweep before this point covered only R1, R2 and R5. R3 had been designed
but never implemented or measured, so the 359,165 figure above does not include
it. Measured now:

| Rule set | Candidates | Orphans | Amazon-reach | max/record |
| --- | ---: | ---: | ---: | ---: |
| R1 + R2 + R5 | 359,165 | 1 | 98.3% | 561 |
| **+ R3 (as specified)** | **730,885** | **0** | **99.7%** | **2,773** |
| + R3 requiring ≥2 other words | 496,729 | 0 | 99.4% | 1,556 |
| + R3 requiring ≥3 other words | 410,649 | 1 | 99.0% | 953 |

R3 as specified **doubles the candidate count** — 371,720 pairs are unique to
it — to buy 1.4 percentage points of reach, and pushes the worst-case record
from 561 candidates to 2,773. By the same value test used to choose the R1/R5
thresholds, that is poor. Requiring two other shared words instead of one keeps
zero orphans and 99.4% reach for a third fewer pairs.

R3 is implemented as specified and approved. The tightening is **not** applied
unilaterally; it is recorded here as an open option.

### R4 is currently inert — and that is fine

With R3 included there are **zero** orphans, so R4 rescues nothing and
contributes no pairs. It is retained deliberately: it costs nothing when it
fires on nothing, and it is the guarantee that keeps a threshold change from
silently reintroducing unreachable records. A safety net that never catches
anyone is working.

### Brand harvesting — the cross-field idea, applied early

R3 cannot rely on the `brand` column, which the corruption blanked on about
half the records. Instead every record's text is searched for any brand name
either retailer uses. This recovers a brand for **88.2%** of Walmart and
**90.6%** of Amazon records whose column is empty — the [D8](#d8--the-field-scrambling-problem-and-the-plan-for-it)
cross-field principle showing up in blocking as well as in scoring.

### Final result at the approved settings

```
730,885 candidate pairs, from 56,376,996 possible  (98.70% reduction)
Walmart records with at least one candidate : 2,554/2,554 (100%)   orphans: 0
Amazon records reachable                    : 22,001/22,074 (99.7%)
Candidates per Walmart record               : median 183, p99 1,578, max 2,773
```

### Two notes on consistency

R1 counts a word's frequency across **both** tables pooled, while R5 counts a
sequence's frequency on the **Amazon side only**. The asymmetry is not
principled — it is how each rule was first written. Whether R1 should switch to
an Amazon-side count is an open question raised separately, and it would only
ever admit more candidates, never fewer.

Every figure here is a count derived from the two source tables. None of it
consults the labelled data, per [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).
These numbers describe how *reachable* records are, never how *correct* the
pairs are — that cannot be known until the final evaluation.

---

## D17 — Tightening R3, and closing the Amazon-side reachability gap

**Two decisions, taken together.**

1. **R3 now requires two other shared words**, not one, beyond the brand match.
2. **R4 now runs in both directions.** A new symmetric pass rescues any Amazon
   record that no Walmart record reached, using the same 100-neighbour
   allowance as the original Walmart-side rule.

### 1. Why R3 was tightened

R3 as first specified — same brand plus *one* other shared word — was measured
for the first time in D16 and turned out to dominate the candidate set:

| R3 setting | Candidates | Walmart orphans | Amazon-reach | worst record |
| --- | ---: | ---: | ---: | ---: |
| ≥1 other word | 730,885 | 0 | 99.7% | 2,773 |
| **≥2 other words** | **496,729** | **0** | **99.4%** | **1,556** |
| ≥3 other words | 410,649 | 1 | 99.0% | 953 |

One extra shared word is a weak filter, because the word can be anything —
"black", "usb", "cable". Requiring two removes a third of all candidate pairs,
keeps every Walmart record reachable, and halves the worst-case record's
workload, for 0.3 percentage points of Amazon-reach.

Going to three starts costing real coverage and reintroduces an orphan, so two
is the point where the rule stops dominating without starting to hurt.

### 2. Why the Amazon side needed its own safety net

Every rule — R1, R2, R3, R5, and the original R4 — is phrased *"for each
Walmart record, find matching Amazon records."* That phrasing has a blind spot
it cannot see out of: an Amazon record that no Walmart record happens to reach
is never considered by anything.

This matters exactly as much as a stranded Walmart record. A true match is a
pair, and it is lost if *either* side is unreachable. R4 was designed only for
the Walmart side and had never been intended to address this.

### The correction that changed the decision

The gap was first argued to be mostly harmless, on this reasoning: Amazon holds
22,074 records against Walmart's 2,554, so most Amazon records cannot have a
partner — there are not enough Walmart records to go round. A specific example
supported it: `B_1037`, an HP LaserJet toner whose part number `c4096a` appears
nowhere in the Walmart table, not even as a substring. Walmart evidently does
not stock it, so excluding it costs nothing.

**That reasoning was tested and did not hold.** Of the 133 unreachable Amazon
records at the tightened setting, **none shared zero words with Walmart** —
every one had vocabulary overlap. They were not `B_1037`-style isolates. They
were unreachable because their overlap was not *discriminative*: common words
that fail R1's frequency cutoff, no rare character sequences, and not enough
agreement to clear R3.

And they are ordinary products, not oddities:

```
B_314   audio-technica ath-ckl200bk in-ear headphones
B_894   kingston datatraveler 8 gb high-speed usb flash drive dtig3
B_700   m-rock mesa verde compact camera bag
B_1241  d-link printer accessories
```

Mainstream goods from major brands, of the kind Walmart plausibly stocks.
`B_894` even carries `kingston` in its brand column — it failed R3 only because
no Kingston record in Walmart shared two further words with it.

So the assumption that these were mostly unmatchable leftovers was not
supported by the data, and the case for closing the gap was stronger than first
presented. The original reasoning is recorded here rather than quietly replaced,
because the correction is the point: a plausible structural argument was
checked against the records themselves and did not survive.

### Why the full neighbour count, not a reduced one

A smaller allowance for the Amazon side was considered, on the argument that
100 neighbours for a record with no partner is mostly waste.

That argument rested on the same "mostly unmatched" premise the measurement
undercut. If these records plausibly have real partners, then trimming the
allowance trims the chance of catching them — saving a rounding error in
compute at the cost of the very thing the rule exists to protect. The two
directions therefore use the same count, and the nearest-neighbour search is
written **once** and called twice, so they cannot drift apart.

### Cost

| | Pairs |
| --- | ---: |
| Before the symmetric pass | 496,729 |
| Added by it | **11,883** |
| **Total** | **508,612** |

A 2.4% increase. Against an asymmetry that has governed every blocking decision
in this project — a dropped pair is unrecoverable, an extra pair merely costs
the scoring step a little work — that is a small premium for removing a whole
category of guaranteed loss.

### Final result

```
508,612 candidate pairs from 56,376,996 possible   (99.0978% reduction)
Walmart records with at least one candidate : 2,554/2,554 (100%)    orphans: 0
Amazon records reachable                    : 22,072/22,074 (99.99%)
Candidates per Walmart record               : median 161, p99 978, max 1,560
```

Per rule, after the changes:

| Rule | Pairs | Unique to it |
| --- | ---: | ---: |
| R1 | 236,025 | 149,944 |
| R2 | 6,695 | 2,479 |
| R3 | 179,940 | 137,564 |
| R5 | 186,541 | 113,669 |
| R4 (Walmart side) | 0 | 0 |
| R4 (Amazon side) | 11,883 | 11,883 |

### Two records remain unreachable — and cannot be rescued this way

The symmetric pass closed 131 of the 133. Two resist it:

```
B_2852    "mydesk pink lap desk"
          -> only two 5-character sequences exist ('mydes', 'ydesk'),
             because almost every word is shorter than five characters.
             Neither appears anywhere in the Walmart table.

B_14604   mivizu ipad endulge skin
          -> 21 sequences, none of which appear in any Walmart record.
```

Nearest-neighbour rescue ranks by shared character sequences. These two share
none with anything in Walmart, so there is nothing to rank and the rule returns
empty. This is a limit of the method, not a bug.

They could be reached by a further fallback — word overlap including common
words, or shorter sequences for records made entirely of short words — at a
cost of at most 200 pairs.

> ✅ **This was subsequently built. See [D20](#d20--a-last-resort-tier-for-records-with-no-five-character-overlap).**
> Both records are now reachable, and the design has no unreachable records in
> either direction.

### Label-free, as always

Every figure above is a count taken from the two source tables. No labelled
data was read, per [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).
These numbers say how *reachable* records are, never how *correct* the pairs
are.

---

## D18 — R1 counts word frequency on the Amazon side only

**Decision.** R1 ignores a word once it appears in more than 100 **Amazon**
records. Previously it counted the word across both tables pooled.

### The problem with counting both tables

R1's job is to skip words too common to mean anything. The natural question is
"common where?" — and the original implementation answered "across both tables
added together", which is the wrong measure of cost.

Blocking runs as *"for each Walmart record, find Amazon records."* The work a
word creates is therefore **exactly the number of Amazon records holding it**.
How many Walmart records also contain it is irrelevant to cost — it inflates
the pooled count without creating a single extra comparison.

Because Amazon is 8.6× the size of Walmart, the pooled figure is usually
dominated by the Amazon side anyway, so the distortion is mild. But it is
systematic and one-directional, and it discards exactly the words that are
*distinctive to Walmart's catalogue*:

| Word | Walmart records | Amazon records | Pooled | Verdict under pooled counting |
| --- | ---: | ---: | ---: | --- |
| `stationery` | 327 | **7** | 334 | rejected — though it costs 7 |
| `draper` | 153 | **16** | 169 | rejected — though it costs 16 |
| `diagonal` | 137 | 93 | 230 | rejected |
| `manual` | 68 | 90 | 158 | rejected |

`draper` is a projector-screen brand. Walmart stocks a lot of them and Amazon
only 16. Under pooled counting that word was thrown away as "too common",
when using it would have cost sixteen comparisons.

### The switch cannot remove anything

This is arithmetic, not an empirical finding. Pooled frequency is the Walmart
count *plus* the Amazon count, so it is always greater than or equal to the
Amazon count alone. Every word admitted under the old rule is therefore still
admitted under the new one. The change can only ever add candidates.

Measured at the live threshold of 100: **42 words newly admitted, 0 lost.**

*(An earlier measurement of this question reported 72 words. That was taken
when the threshold was 50. The figure moves with the cutoff, and 42 is the
number that applies to the rule as it actually runs.)*

### Effect on the candidate set

| | Before | After |
| --- | ---: | ---: |
| R1 pairs | 236,025 | **305,101** |
| Total candidate pairs | 508,612 | **564,273** |
| Reduction | 99.0978% | 98.9991% |
| Walmart records reached by R1 | 2,485 | 2,505 |
| Median candidates per record | 161 | 187 |
| Worst-case record | 1,560 | 1,615 |

A 10.9% increase overall — smaller than R1's own growth, because some of the
new pairs were already being found by other rules, and because the Amazon-side
safety net had less left to rescue (11,883 pairs → 10,599).

### What it does not buy — stated plainly

**Reachability is unchanged.** Still zero Walmart records without candidates,
and still exactly 2 Amazon records unreachable — the same two the
nearest-neighbour rescue cannot help ([D17](#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap)).

So this change does not close any gap. What it adds is **evidence depth**:
55,661 pairs that no rule previously produced, and additional routes to pairs
that were previously found by only one rule. Whether any of those pairs is a
real match cannot be known until the final evaluation.

That makes this the same kind of purchase as every other loosening in the
blocking design — insurance bought against an unrecoverable failure we cannot
currently measure, at a cost in compute we can. It is justified on the
asymmetry, not on a demonstrated gain.

### A side benefit: one source of truth

The pooled frequency table has been removed rather than replaced. R1 now reads
the length of a word's Amazon posting list — the same list it then returns —
so the filter and the result come from one structure that cannot fall out of
step with itself. R5 was already written this way; R1 now matches it.

### Label-free

Every figure here is a count from the two source tables, per [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).

---

## D19 — No self-labelling: we will not create our own answer key either

**Decision.** Nobody on this project hand-judges pairs to create a feedback
signal. Not a batch of 30, not a batch of 3. This holds even though such
judgements would never touch the sealed `train`/`valid`/`test` files.

### The gap this closes

[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)
forbids *reading* the answer key. It says nothing about *writing* one.

That leaves an obvious loophole. Nothing stopped us pulling 40 raw candidate
pairs, deciding by eye which were genuine matches, and tuning thresholds
against our own judgements. No sealed file would be opened. The letter of D14
would be satisfied — and its entire purpose defeated, because we would have
manufactured exactly the ground truth it exists to deny us.

D19 closes that loophole explicitly.

### Why, when real practitioners do exactly this

This is worth being clear about: **the rejected approach is standard industry
practice, and it works.** The two most widely used open-source entity
resolution tools both depend on it. `dedupe` learns its blocking predicates
from pairs a human labels interactively. Zingg reaches production quality from
roughly 30-40 human-labelled pairs via active learning. A Forward Deployed
Engineer arriving at a client site on Monday would very likely spend Tuesday
labelling a few dozen pairs by hand, and would be right to.

We are deliberately choosing a harder constraint than the industry standard.

The reason is that the project's claim depends on it. This build exists to
demonstrate designing an entity resolution system *with genuinely zero access
to ground truth* — the position of an engineer facing a new client's data
before any labelling effort exists. A private, informal answer key would make
that claim false, and the claim is the point.

### What this rules out, concretely

- **Learned blocking schemes.** The `dedupe`/Zingg style of tuning blocking
  predicates against labelled examples is off the table for this build. Our
  blocking rules are justified by the structure of the data and by pure counts
  (reduction ratio, reachability, block sizes) — never by how well they
  separate known matches.
- **Threshold tuning by eye.** Match/no-match thresholds cannot be chosen by
  sampling pairs and judging which look right.
- **Any model trained on judgements we produced**, by hand or by asking a
  language model to stand in for a human judge.
- **Iterating on a design because a sample "looked wrong."**

### Where the line actually falls

The distinction that matters is **what is being judged**, not who is judging.

**Allowed — reasoning about the data's structure.** Noticing that
`rr-vtps-28pk-r1` is a part number split by hyphens; that collapsing all
whitespace welds `desktop computers` into meaningless character sequences;
that the `brand` column is empty on half the records. These are observations
about how the data is shaped. Every design decision in this project so far
rests on this kind of reasoning, plus counts — and none of it required knowing
whether any particular pair is a match. The [D15](#d15--fixing-how-text-is-split-for-n-gram-blocking)
normalisation fix is the clearest example: driven entirely by the structure of
the text, with no view on whether any pair matched.

**Forbidden — reasoning about whether a specific pair is the same product**,
where that judgement then feeds back into a design choice.

Illustrative candidate pairs have been shown in reports throughout this
project (the Edge memory modules, the Toshiba drives). Those were used to
explain what the rules do. They were **not** used to select thresholds — every
threshold here was chosen from counts alone. Under D19 that separation becomes
a rule rather than a habit.

> **Flagged for confirmation:** the boundary above is an interpretation, not
> something that was specified. If the intended line is stricter — no looking
> at candidate pairs at all, even to illustrate behaviour — say so and it will
> be applied.

### Deferred, not rejected

The self-labelling approach is explicitly worth testing, as a **separate
follow-up exercise once this strict build is complete**. Running both and
comparing them would be a genuinely interesting result: how much does a few
dozen hand-labelled pairs actually buy, against a system designed without any?

That comparison only works if this build stays clean. Doing it later is what
makes it possible; doing it now is what would make it meaningless.

### The cost, stated plainly

This is stricter than real practice and we lose something real by it: no early
feedback, no way to catch a bad design choice before the final evaluation, and
a system that may well perform worse than one tuned against 40 labelled pairs.
That is the price of the claim, and it is being paid deliberately — consistent
with the trade-off already accepted in [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).

---

## D20 — A last-resort tier for records with no five-character overlap

**Decision.** When an Amazon record shares no five-character sequence with
anything in Walmart, retry it with **shorter** sequences — four characters
first, then three — and stop at the first length that finds something.

This closes the gap [D17](#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap)
left open. **No record in either table is now unreachable.**

### The problem

Two Amazon records survived even the symmetric safety net, for two different
reasons:

```
B_2852    "mydesk pink lap desk"
          Almost every word is shorter than the five-character window, so the
          record produces only two sequences in total ('mydes', 'ydesk').
          Neither occurs anywhere in Walmart.

B_14604   "mivizu ipad red endulge skin skins decals ... cipdwrprd"
          Produces 21 sequences, but not one of them occurs in Walmart.
```

Nearest-neighbour rescue ranks candidates by *shared* sequences. With none
shared there is nothing to rank, so the rule returned empty. The failure was
structural, not a bug.

### Why shorter sequences, and why not simply use three

Shortening the window makes sequences easier to share — that is the entire
trick, and equally the entire risk, because shorter sequences are far less
selective. Measured on the two records:

| Length | `B_2852` | `B_14604` |
| --- | --- | --- |
| 5 | 0 shared — unreachable | 0 shared — unreachable |
| **4** | **2 shared: `pink`(31), `desk`(71)** | **4 shared: `cipd`(1), `endu`(5), `skin`(9), `ipad`(64)** |
| 3 | 5 shared, reaching 397 Walmart records | 26 shared, reaching 615 records |

Three characters works but is markedly worse: it reaches hundreds of records on
fragments like `esk`, `des` and `ink`, which carry no meaning. Four characters
surfaces whole words — `pink`, `desk`, `skin`, `ipad` — and one genuinely rare
sequence, `cipd`, which occurs in exactly one Walmart record.

So the rule tries the **most selective length that works** and stops there,
rather than dropping straight to the weakest option. Both records were rescued
at four characters; the three-character tier has never fired on this data. It
remains as a further step should a record ever need it.

### Cost

| | Pairs |
| --- | ---: |
| Before | 564,273 |
| Added by this tier | **177** |
| **Total** | **564,450** |

177 pairs — 0.03% — against the ≤200 estimated beforehand.

### Result

```
564,450 candidate pairs from 56,376,996 possible   (98.9988% reduction)
Walmart records with at least one candidate : 2,554/2,554 (100%)
Amazon records reachable                    : 22,074/22,074 (100%)
Candidates per Walmart record               : median 187, p99 991, max 1,615
```

### What this does and does not establish

It establishes **reachability**: every record in both tables now appears in at
least one candidate pair, so no record is excluded by construction.

It does **not** establish that the rescues are useful. The evidence behind them
is weak, and measurably so — similarity scores for the rescued pairs run
between 0.019 and 0.049, against a median record whose candidates come from
rare words, part numbers or brand agreement. `B_2852` in particular contains
four words in total, two of which (`pink`, `desk`) are all the rule has to work
with. A record that thin may simply not be matchable by any method.

Whether the correct partner is among these candidates — or whether either
record has a partner at all — cannot be known until the final evaluation, per
[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).
What the tier guarantees is that the possibility is no longer foreclosed.

### Why it is worth 177 pairs regardless

The same asymmetry that governs every blocking decision here. A pair never
generated is unrecoverable no matter how good the scoring is; a weak pair that
gets generated merely costs the scoring step a little work to reject. At 0.03%
of the candidate set, removing the last category of certain loss is cheap
insurance — and it means the blocking stage can be described without an
asterisk.

### Label-free

Every figure above is a count or a text-similarity score computed from the two
source tables. No labelled data was read, and no judgement about whether any
particular pair is a genuine match informed the design, per
[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished) and
[D19](#d19--no-self-labelling-we-will-not-create-our-own-answer-key-either).

---

## D21 — Summarise what blocking discards, rather than logging it

**Decision.** Blocking now emits a summary of what it excluded, written to
[`blocking_diagnostics.json`](blocking_diagnostics.json) by
`src/blocking_diagnostics.py`. The discarded pairs themselves are **not**
stored.

### Why record anything

Blocking throws away **55,812,546 of 56,376,996 pairs — 99.00% of the space**.
A step that discards that much should not do so silently. If a real match is
lost here nothing downstream can recover it, so the exclusion deserves at least
enough of a trace to reason about.

### Why a summary rather than a log

Storing 55.8 million pairs would cost gigabytes to preserve something entirely
regenerable: rerun `src.blocking` against the untouched raw data and the
identical set comes back. What a rerun does *not* give you at a glance is a
characterisation of those pairs — which is the part actually worth keeping.

### Is this standard practice?

**Partly, and the distinction is worth being exact about.** The blocking
literature has three established evaluation metrics: **reduction ratio**,
**pair completeness**, and **pairs quality**
([survey](https://arxiv.org/pdf/1905.06167)).

- **Reduction ratio is standard and label-free.** It is reported here.
- **Pair completeness and pairs quality are equally standard but both require
  the answer key.** Under [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)
  neither can be computed until the final evaluation.

So the usual way of characterising a blocking step is unavailable to us for the
entire build. There is no named standard technique for describing the discarded
set without labels. **Everything beyond the reduction ratio here is a design
choice for this project, not an established method** — reasoned from the fact
that the recall-side metrics are off the table and something has to stand in
their place.

### What it reports, and what each thing is for

**1. Headline counts and reduction ratio.** The standard metric.

**2. How the discarding falls across records.** Pairs discarded per Walmart
record: minimum 20,459, median 21,887, maximum 22,066 — meaning the thinnest
record retained just 8 candidates out of 22,074. **68 records keep fewer than
50 candidates.** Those are the records most exposed if blocking has erred, and
they are worth naming rather than leaving inside an average.

**3. Near-miss counts — the most useful number here.** How many extra pairs
each rule would admit if its threshold moved one notch:

| Loosening | Extra pairs |
| --- | ---: |
| R1, Amazon-DF 100 → 150 | 333,833 |
| R3, shared words 2 → 1 | 232,899 |
| R5, Amazon-DF 50 → 75 | 62,350 |
| **Any of the three** | **613,067** |

This says the design sits on a steep slope, not a plateau: a modest loosening
on all three fronts would **more than double** the candidate set, which
currently stands at 564,450. That is a useful thing to know and impossible to
infer from the reduction ratio alone. It quantifies how consequential the
threshold choices are, without saying anything about whether they are correct.

**4. A sampled taxonomy of why pairs were discarded.** From 100,000 uniformly
sampled discarded pairs, each placed in the strongest category it qualifies
for:

| The best evidence this pair had | Share |
| --- | ---: |
| Nothing at all — no shared word, no shared sequence | **67.31%** |
| Shared words, but all too common for R1 | 27.64% |
| Shared sequences, but all too common for R5 | 4.64% |
| Brand agreed, but too few other shared words | **0.40%** |

And how much overlap discarded pairs had at all:

| Shared words | Share of discarded pairs |
| --- | ---: |
| 0 | 71.95% |
| 1 | 22.47% |
| 2 | 4.45% |
| 3 | 0.86% |
| 4 | 0.17% |
| 5 or more | 0.10% |

**Two-thirds of everything discarded had literally nothing in common** with its
counterpart, and 72% shared not one word. That is the reassuring shape: the
bulk of the discarding is obviously safe, and the genuinely marginal calls are
a thin band. The 0.40% brand-agreed bucket is the closest thing to a borderline
population — around 223,000 pairs scaled to the full space — and it is exactly
the group R3's two-word requirement was tightened to exclude
([D17](#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap)).

### A self-check built into the taxonomy

One bucket exists purely to catch a bug: `UNEXPECTED_shared_part_number`. R2
accepts a shared part-number-shaped word at *any* frequency, so a discarded
pair sharing one would mean a rule is not doing what it claims. The bucket is
empty, and a test asserts it stays that way.

### What this does not establish

Nothing here says whether any discarded pair was a genuine match. It describes
the **shape** of what was excluded, not its correctness. Pair completeness —
the metric that would answer that — needs the answer key and waits for the
final evaluation.

The figures are reproducible: the sample uses a fixed seed, so the numbers do
not drift between runs.

### Label-free

Every figure is a count or a set operation over the two source tables, per
[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished) and
[D19](#d19--no-self-labelling-we-will-not-create-our-own-answer-key-either).

---

## Working conventions

- **Commit authorship.** All commits are authored solely by the repository
  owner, with no AI or assistant attribution trailers.
- **Raw data is never edited in place.** Files in `data/raw/` stay exactly as
  downloaded. Any cleaning produces new files elsewhere.
- **Data provenance is verified, not assumed.** Every dataset records where it
  came from, and was checked against the benchmark's published row and match
  counts before use.
- **Nothing is silently substituted.** If data cannot be obtained or verified,
  that is reported plainly rather than filled with a placeholder or a
  stand-in source.
