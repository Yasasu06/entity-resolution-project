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
- Can the project's blocking and matching find the 962 known true matches when
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
data has shown what reviewers actually need to see.

---

## D5 — Review capacity is an assumption, clearly labelled

> ⚠️ **ASSUMPTION — invented for planning. This is not a real client
> requirement and no real figure exists yet.**

**Placeholder:** a human reviewer can process **200 pairs per day**, over a
**10-working-day** window — a total review budget of **2,000 pairs**.

**Why invent one at all.** Without a capacity limit, choosing a threshold is
arbitrary — you can always "send more to review". With one, it becomes a real
constrained problem: *given a budget of only 2,000 reviews, where is the band
drawn to catch the most true matches?* That is the question
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
(expectation-maximisation). An answer key *does* exist, and could be trained on —
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

### Where a language model may and may not be used

A language model is used **only** for escalation on the uncertain band. It is
**never** the matcher.

This needs stating explicitly because the project will later build a second,
embedding-based system, and it would be easy to assume "the AI system" means
"a language model scores the pairs". It does not, for a reason that is simply
arithmetic: blocking produces **564,450 candidate pairs**. Scoring those with a
language model would be roughly **1,100× the 500-call budget above** — the two
numbers are not in the same universe, and the budget was written for a band of
a few hundred pairs, not the whole candidate set.

So the division of labour is:

| Job | Volume | Tool |
| --- | ---: | --- |
| Matching every candidate pair | ~564,000 | **Embeddings** — computed locally, free after the model downloads, self-supervised |
| Escalating the uncertain band | ≤500 | **A language model**, within the budget above |

Embeddings also keep the second system compatible with the no-peek policy:
they are self-supervised and need no labelled data, whereas a supervised
transformer matcher could not legally be trained here at all
([D19](#d19--no-self-labelling-the-project-does-not-create-its-own-answer-key),
[D22](#d22--how-the-two-systems-will-be-compared)).

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

**Why this is the centrepiece.** The contribution is not the use of a matching
library, but the diagnosis of *why* the standard tool underperforms on this
specific corruption, and the extension built to address it. That is the work a
deployment engineer does at a client site, where the data never matches
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
>
> ⚠️ **R3 is also described inaccurately throughout this entry.** It does not
> require brand agreement in the ordinary sense — see
> [D23](#d23--correcting-how-r3-is-described) for what it actually matches on.

**Decision.** Blocking runs five rules. A pair becomes a candidate if *any* of
them accepts it.

| Rule | What it looks for | Setting |
| --- | --- | --- |
| **R1** | A shared word that is uncommon across both tables | document frequency ≤ 100 |
| **R2** | A shared word shaped like a part number (letters + digits, ≥5 chars) | any frequency |
| **R3** | A shared brand-vocabulary term **plus** other shared words (see [D23](#d23--correcting-how-r3-is-described)) | — |
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

### Why R1 and R5 were not loosened further to reach full coverage

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

R3 as first specified — one shared brand-vocabulary term plus *one* other
shared word — was measured
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
blocking design — insurance bought against an unrecoverable failure that cannot
currently be measured, at a cost in compute that can. It is justified on the
asymmetry, not on a demonstrated gain.

### A side benefit: one source of truth

The pooled frequency table has been removed rather than replaced. R1 now reads
the length of a word's Amazon posting list — the same list it then returns —
so the filter and the result come from one structure that cannot fall out of
step with itself. R5 was already written this way; R1 now matches it.

### Label-free

Every figure here is a count from the two source tables, per [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).

---

## D19 — No self-labelling: the project does not create its own answer key

**Decision.** Nobody on this project hand-judges pairs to create a feedback
signal. Not a batch of 30, not a batch of 3. This holds even though such
judgements would never touch the sealed `train`/`valid`/`test` files.

### The gap this closes

[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)
forbids *reading* the answer key. It says nothing about *writing* one.

That leaves an obvious loophole. Nothing would prevent pulling 40 raw candidate
pairs, deciding by eye which were genuine matches, and tuning thresholds
against those judgements. No sealed file would be opened. The letter of D14
would be satisfied — and its entire purpose defeated, because that would
manufacture exactly the ground truth it exists to deny.

D19 closes that loophole explicitly.

### Why, when real practitioners do exactly this

This is worth being clear about: **the rejected approach is standard industry
practice, and it works.** The two most widely used open-source entity
resolution tools both depend on it. `dedupe` learns its blocking predicates
from pairs a human labels interactively. Zingg reaches production quality from
roughly 30-40 human-labelled pairs via active learning. An engineer deploying
against a new client's data would very likely spend the second day labelling a
few dozen pairs by hand, and would be right to.

This is deliberately a harder constraint than the industry standard.

The reason is that the project's claim depends on it. This build exists to
demonstrate designing an entity resolution system *with genuinely zero access
to ground truth* — the position of an engineer facing a new client's data
before any labelling effort exists. A private, informal answer key would make
that claim false, and the claim is the point.

### What this rules out, concretely

- **Learned blocking schemes.** The `dedupe`/Zingg style of tuning blocking
  predicates against labelled examples is off the table for this build. The
  blocking rules are justified by the structure of the data and by pure counts
  (reduction ratio, reachability, block sizes) — never by how well they
  separate known matches.
- **Threshold tuning by eye.** Match/no-match thresholds cannot be chosen by
  sampling pairs and judging which look right.
- **Any model trained on judgements produced within the project**, by hand or by asking a
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

This is stricter than real practice, and something real is lost by it: no early
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
[D19](#d19--no-self-labelling-the-project-does-not-create-its-own-answer-key).

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

So the usual way of characterising a blocking step is unavailable for the
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
[D19](#d19--no-self-labelling-the-project-does-not-create-its-own-answer-key).

---

## D22 — How the two systems will be compared

**Decision.** This project builds **two** complete entity resolution systems on
the same raw data under the same no-peek policy — one classical and rule-based,
one built on embeddings — and compares them in a single evaluation at the end.
Four decisions govern how.

### 1. The contribution is framed in established terms

What this project has been calling the "uncertainty band" already has a name
and a literature. It is **selective prediction**, also called classification
with a reject option: the model answers only when confident enough and abstains
otherwise, producing an explicit **risk–coverage trade-off**. The idea was
formalised by Chow in 1970, and it has standard metrics — risk-coverage curves,
accuracy-rejection curves, and the area under them (AURC).

There is also a decade of work on the human-review half: CrowdER (VLDB 2012),
Corleone (SIGMOD 2014), Falcon and Waldo (both SIGMOD 2017) all address which
pairs to route to people and at what cost.

**So the framing is not novel, and this project will not claim it is.** An
earlier assessment in this conversation overstated the novelty; that was
wrong, and correcting it is an improvement rather than a loss. Adopting the
established vocabulary and metrics makes the work legible to anyone who knows
the field, which an invented term would not.

**What appears to remain open** is narrower and worth stating precisely: a
comparison of *risk-coverage behaviour between a classical matcher and an
embedding-based one, with review cost attached*. The crowdsourced ER work
predates transformers; the selective-prediction literature is mostly about
image classifiers; and a 2025 paper on confidence calibration for LLM-based
entity matching stops short of abstention, deferral, or routing cost. The
claim is therefore *applying an established method to an uncompared pair of
systems* — defensible, and checkable.

### 2. Embeddings do the matching; a language model only escalates

Recorded in full under [D7](#d7--ai-escalation-allowed-real-world-knowledge-judged-on-cost).
In short: matching all 564,450 candidate pairs with a language model would cost
roughly 1,100× the escalation budget, so the second system's matcher is
**embedding-based** — local, free after download, and self-supervised. A
language model stays reserved for the uncertain band, exactly as originally
planned.

There is a second reason beyond cost. The published results that make deep
learning look dominant on this dataset — EMTransformer at 83.95 F1 against
Magellan's 38.06 — come from **supervised** models trained on labelled pairs.
[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished) and
[D19](#d19--no-self-labelling-the-project-does-not-create-its-own-answer-key)
forbid that outright. So the comparison here is **unsupervised classical versus
self-supervised embedding**, and those published figures do not apply to it.
The gap should be expected to be smaller and far less predictable — and the
comparison is correspondingly less well studied, which makes it more
interesting rather than less.

### 3. A fixed contract between blocking and matching

Comparing two whole systems has a known weakness: they differ in *every*
component, so a difference in results cannot be attributed to any one of them.
The standard remedy is to hold everything constant but one part — which
requires the parts to be separable.

So the seam is fixed **now**, before either system is finished, in
`src/interfaces.py`:

```
table A ──┐
          ├──►  Blocker  ──►  candidate pairs  ──►  Matcher  ──►  scored pairs
table B ──┘                  (the contract)
```

- A blocker returns `unique_id_l`, `unique_id_r`, `rules`.
- A matcher consumes that and returns `unique_id_l`, `unique_id_r`,
  `match_probability`.
- Both shapes are checked at the boundary by `validate_candidates` and
  `validate_scores`, which reject unknown identifiers, swapped sides,
  duplicated pairs, invented pairs, unscored pairs, and probabilities outside
  [0, 1].

**The specific failure this prevents:** if a blocker computed embeddings and
its own matcher quietly reused them, the two would be welded together and could
never be swapped — and that would only become apparent at the very end, with
both systems already built. Passing nothing between stages but this table keeps
them genuinely independent.

Fixing the seam early also closes a gap found in the blocking design review:
candidates previously existed only in memory and were discarded when the
process exited. They are now written to `data/processed/`, which is **not**
committed, since it is regenerable from `data/raw/` — the same reasoning as
[D21](#d21--summarise-what-blocking-discards-rather-than-logging-it).

### 4. The final comparison will be pre-registered — later

Unsealing the labels once will produce **four** results: classical end-to-end,
embedding end-to-end, and two hybrids (classical blocking with the embedding
matcher, and the reverse) to show which component drives any difference.

Four evaluations against one test set is a multiple-comparisons problem. Choose
the framing after seeing the numbers and the test set has been fitted to — the
same contamination D14 exists to prevent, arriving by a different route.

**Commitment:** before the labels are unsealed, the exact comparisons, metrics,
and what counts as a meaningful difference will be written down and recorded
here.

**Deliberately not specified yet.** Pre-registering now, with neither system
built, would mean guessing at metrics for components that do not exist. This is
a firm commitment for the final-evaluation stage, not an open question — and it
is recorded here so it cannot be quietly skipped.

---

## D23 — Correcting how R3 is described

**Decision.** R3's documentation is corrected to describe what the rule
actually does. **The rule itself is unchanged** — this is an accuracy fix to
the description, not a change in behaviour.

### What was wrong

R3 was described everywhere as *"the same brand, plus other shared words"*.
That overstates it. "Brand" in R3 means *a term in the harvested brand
vocabulary*, and that vocabulary is looser than the word implies in two
measured ways.

**1. It contains ordinary words.** The vocabulary is every single-word value
appearing in either table's `brand` column, so it inherits whatever sits there:

| Term | Records containing it | Times used as a brand |
| --- | ---: | ---: |
| `case` | 2,055 | **1** |
| `digital` | 1,594 | 3 |
| `iphone` | 690 | 4 |
| `dual` | 547 | 9 |

47 such terms qualify. **2,140 Amazon records — 9.7% — have only one of these
as their harvested brand.**

**2. It picks up brands a record merely mentions.** Accessories name the device
they fit:

```
A_37  roocase multi-angle folio leather case ... for acer iconia tab a500
      harvests: roocase (its own brand), acer (the device), case (a word)

A_64  los angeles lakers iphone 3g duo case ... tribeca
      harvests: tribeca (its own brand), iphone (the device), case (a word)
```

**24.4% of Walmart and 34.2% of Amazon records harvest two or more terms.**

For that slice, R3 is closer to *"three or more shared words, one of which
happens to be in the brand list"* than to brand agreement.

### Why the rule is not being changed

The two-word requirement bounds the damage: a spurious brand term still needs
two genuine shared words alongside it. And over-generating is the cheap
direction of error under the asymmetry governing every blocking decision here
— a dropped pair is unrecoverable, an extra one costs the scoring step a little
work.

Re-tuning would also mean redoing threshold work already measured and approved
([D17](#d17--tightening-r3-and-closing-the-amazon-side-reachability-gap)), for
a rule whose behaviour is understood and bounded.

**So the behaviour is accepted and the claim is corrected.** Given that this
project's argument rests on its reasoning being honest, a rule described as
doing something stronger than it does is the more damaging of the two errors.

### A related limitation, now also stated

Multi-word brands are skipped entirely — **511 of 1,507 distinct brand values
(33.9%)** contain a space, affecting 313 Walmart and 2,231 Amazon records.
Matching those reliably inside free text needs phrase handling that would add
complexity for a small gain, and R1 and R5 still reach those records. It is a
coverage limitation, not a correctness one.

### How this was found, and a process note

Both issues surfaced in a deliberate end-to-end review of the finished
blocking design — reviewing the whole system at once, rather than one piece at
a time as it was built. Neither was visible while the rules were being built
individually.

Correcting the wording was recommended at that review and **not carried out at
the time**, which is why it needed a later pass. Two of the stale phrasings had
also survived an earlier edit that silently matched nothing and reported
success. Edits to documentation are now made with a replace that fails loudly
when it matches nothing, rather than one that can quietly do nothing.

---

## D24 — How abstained pairs are handled: build for humans, measure the AI

**Decision.** Three parts, deliberately separated because only one of them can
honestly be measured in this project.

| | Approach | What this project does |
| --- | --- | --- |
| 1 | Human-only review | **Modelled** under a declared accuracy assumption |
| 2 | AI-only review | **Measured** — the genuine headline result |
| 3 | AI-assisted human | **Built and designed for**, justified from the literature, **not measured** |

### Why the obvious choice is the one the research warns about

AI-assisting-a-human looks like the safe middle option. The evidence says
otherwise.

[Vaccaro, Almaatouq & Malone (*Nature Human Behaviour*, 2024)](https://www.nature.com/articles/s41562-024-02024-1)
— a preregistered meta-analysis of **106 studies and 370 effect sizes** — found
human–AI combinations performed **significantly worse than the best of humans
or AI alone**, with losses concentrated in **decision-making tasks**. Deciding
whether two records match is a decision task.

[Bansal et al. (CHI 2021)](https://dl.acm.org/doi/epdf/10.1145/3411764.3445717)
found AI explanations **increased acceptance of the AI's recommendation
regardless of whether it was correct**. Explanations raised agreement, not
accuracy.

The evidence is not one-sided. [Human-LLM Collaborative Annotation (CHI 2024)](https://dl.acm.org/doi/full/10.1145/3613904.3641960)
found human *verification of* LLM labels beat both LLM-only and human-only —
but "AI proposes, human verifies" is a different shape from "AI advises, human
decides", and Vaccaro's moderator reconciles them: **gains when the human is
stronger alone, losses when the AI is.**

### 1. The interface shows evidence, never a recommendation

The review interface presents: the two records, which blocking rules proposed
the pair, where the matcher's evidence was in tension, and the specific point
of disagreement. It does **not** display a suggested answer, a predicted label,
or an AI-written argument for one side.

This follows Bansal directly — a recommendation plus reasoning is the exact
intervention shown to raise acceptance irrespective of correctness. It is also
compatible with [Buçinca et al. (CSCW 2021)](https://www.eecs.harvard.edu/~kgajos/papers/2021/bucinca21trust.pdf),
whose **cognitive forcing functions** — requiring analytic engagement before
any AI opinion is revealed — significantly reduced over-reliance. Worth
recording their honest caveat: *people rated the designs that helped most as
the least pleasant to use.* Reducing over-reliance costs something in comfort.

### 2. Only the AI-only arm produces a real number

AI-only review is fully measurable: the language model decides each abstained
pair, and the decisions are scored against the answer key at final evaluation.
This is the headline result, and it answers [D7](#d7--ai-escalation-allowed-real-world-knowledge-judged-on-cost)'s
question directly — *how much of the review queue can the AI clear at
equal-or-better precision?*

### 3. Human-only is modelled, with the assumption made visible

> ⚠️ **ASSUMPTION — a model, not an observation.** No human will review these
> pairs. Human accuracy is a supplied input, not something measured.

Rather than invent a single accuracy figure, the model is run across a
**range** — 80%, 90%, 95% and 100% correct — and the review economics reported
as a sensitivity analysis. A single invented number would hide how much the
conclusion depends on it; a range makes that dependence visible and is more
honest than pretending to know.

Grounding, such as it is: crowdsourced ER work (CrowdER, Corleone) treats
worker accuracy as variable enough to require redundancy and voting, so high
figures should not be assumed. And the abstained band is **by construction the
hardest subset of pairs** — the ones a calibrated matcher could not separate —
so published accuracy figures, human or machine, measured on full
distributions do not transfer to it.

### The constraint that forced this split

**[D19](#d19--no-self-labelling-the-project-does-not-create-its-own-answer-key)
makes option 3 unmeasurable here.** The only people available to review pairs
are the project's own participants, and hand-judging pairs is exactly what D19
forbids. So the "human" in options 1 and 3 is necessarily simulated.

And a simulated reviewer **has no psychology**. Every finding above — over-
reliance, automation bias, anchoring, cognitive forcing — concerns how a real
person's judgement shifts when a machine offers an opinion. A simulation cannot
be anchored and cannot over-rely. Any figure produced for option 3 would
therefore encode *an assumption about how much assistance helps*, which is
assuming the conclusion — the same error D14 and D19 exist to prevent.

So option 3 is built and defended from the literature; it is not assigned a
measured result.

### What will and will not be claimed

**Will:** AI-only review on the abstained band *was measured*. · Human-only
review *was modelled* across a stated range of accuracies. · The interface
*was designed* to withhold recommendations, on published evidence about
over-reliance.

**Will not:** "AI assistance improved reviewer accuracy by X%." That claim
requires reviewers this project does not have.

### The open variable

Vaccaro's moderator — **whether the human or the AI is stronger, alone, on the
hard band specifically** — decides which approach is actually right in
deployment. It cannot be known until the band exists and the labels are
unsealed.

Measuring the AI-only arm supplies one half of that comparison as a real
number. A strong result weakens the case for keeping a human in the loop at
all; a weak one strengthens it. Either way the moderator gets **measured rather
than guessed**, which is the most this project can honestly do.

### Sequencing

None of this can be built until the matcher exists, since the abstained band is
defined by matcher scores. This entry records the design so it is settled
before the work starts, not decided under pressure once scores are in hand.

---

## D25 — The prior probability that two random records match

**Decision.** Splink's `probability_two_random_records_match` is set to
**λ = 2.0e-05**, derived label-free, and sensitivity-tested at final evaluation.

> ⚠️ **ASSUMPTION — a declared estimate, not a measured quantity.** This number
> cannot be computed without the answer key. It is derived from a documented
> method plus one honest judgement call, recorded here in full so it can be
> argued with. Flagged the same way as the review capacity in
> [D5](#d5--review-capacity-is-an-assumption-clearly-labelled).

### What this parameter is, and why it needs care

Splink's matching model needs a starting point: **before looking at any
evidence, how likely is it that two records picked at random are the same
product?** Everything the comparisons contribute is an adjustment to that prior.

The obvious way to set it is to divide the known number of matches by the size
of the comparison space. **That is reading the answer key**, and would breach
[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished) at
the single most consequential parameter in the model. So it is estimated
instead.

### The method

Splink documents a label-free route: count the pairs caught by **high-precision
deterministic rules** — rules strict enough that a pair satisfying one is very
probably a match — then divide by an *assumed* recall for those rules.

Two rules were used, both computed from the source tables alone:

| Deterministic rule | Pairs found |
| --- | ---: |
| D1: shares a very rare identifier token (DF ≤ 2, length ≥ 6) | 380 |
| D2: identical title (same bag of words) | 2 |
| **Union** | **382** |

### The judgement call: what recall do those rules have?

This is the part that cannot be measured, so it was settled **on its own
merits, before looking at what λ it implied** — the ordering matters, and is
stated here so the reasoning can be checked rather than trusted.

The rule requires *both* records to carry the same very rare identifier. Three
measured facts say it cannot be catching most matches:

- Only **54.7%** of Walmart and **61.0%** of Amazon records contain any
  identifier-shaped token at all.
- `modelno` is absent from roughly half of all records.
- The two retailers punctuate part numbers differently — `rrvtps28pkr1` versus
  `rr-vtps-28pk-r1` — which is the entire reason
  [D15](#d15--fixing-how-text-is-split-for-n-gram-blocking) exists.

**Estimated recall: 30–40%.** Taking 35% gives 1,091 implied matches and
λ = 1.94e-05, rounded to **2.0e-05**.

| Assumed recall | Implied matches | λ |
| ---: | ---: | ---: |
| 30% | 1,273 | 2.26e-05 |
| **35%** | **1,091** | **1.94e-05** |
| 50% | 764 | 1.36e-05 |
| 70% | 546 | 9.68e-06 |

### A structural ceiling, for sanity

Walmart has only **2,554** records, so there can be at most 2,554 one-to-one
matches however generous the assumption. That caps λ at **4.53e-05**. The
chosen value implies 1,128 matches — about **44%** of Walmart's catalogue
having an Amazon counterpart, which is plausible for two large retailers with
overlapping electronics ranges, and comfortably inside the ceiling.

### Honest note on prior exposure

**The method is label-free. The person applying it is not.**

The published match count for this benchmark appears in this project's own
earlier documentation, so it is known to whoever set this parameter. A
clean-room derivation cannot honestly be claimed. Had the recall assumption
been quietly adjusted until λ landed somewhere comfortable, that would be
precisely the leakage D14 exists to prevent — and it would be undetectable
from the outside.

What was actually done: the recall figure was fixed from the token-coverage
reasoning above, and whatever λ fell out was reported. That is a stated
discipline, not a guarantee, and it belongs in the same category as the prior
contamination D14 already records rather than being presented as airtight.

### The mitigation that actually settles it

Arguing about the value matters less than showing it does not matter. λ is a
weak prior that expectation-maximisation largely overrides, so its influence on
final results should be small.

**Commitment:** at final evaluation, results are recomputed across
**λ ∈ [1e-05, 4e-05]** and the sensitivity reported. That range is deliberately
wide — it spans 564 to 2,255 implied matches, or 22% to 88% of Walmart's
catalogue.

If conclusions hold across it, the assumption demonstrably is not driving
anything, which is a far stronger claim than any argument for a particular
value. If conclusions *do* move, that is a finding worth reporting in its own
right — and better discovered by testing than left buried in a parameter.

---

## D26 — Blocking rules for expectation-maximisation training

**Decision.** Three EM training sessions, run in order **T1 → T3 → T2**,
blocking on a different derived column each time.

| | Blocks on | Pairs generated | Cannot estimate | Estimates |
| --- | --- | ---: | --- | --- |
| **T1** | `rare_identifier_tokens` | **930** | rare identifiers | title, brand, rare tokens, common identifiers, price |
| **T3** | `rare_tokens` (DF ≤ 20) | **22,918** | rare tokens | title, both identifier columns, brand, price |
| **T2** | `brand_terms` | **868,299** | brand terms | title, both identifier columns, rare tokens, price |

Counts verified with Splink's `count_comparisons_from_blocking_rule` before
any session is run, as its documentation recommends.

### Why training rules are a separate question from prediction rules

Prediction blocking must reproduce the exact candidate set, because a pair it
never generates can never be matched. That requirement is what forced the
pair-key construction recorded in [D22](#d22--how-the-two-systems-will-be-compared).

Training has no such requirement. From Splink's documentation:

> *"Unlike blocking rules for prediction, it does not matter if Training Rules
> exclude some true matches — it just needs to generate examples of matches and
> non-matches."*

Training needs a **sample**, not a reproduction. So these rules are ordinary
`block_on(..., arrays_to_explode=[...])` expressions with no special
machinery.

### The constraint that determines how many sessions are needed

Verified in Splink's source rather than assumed — `em_training_session.py`
extracts the columns named in a training rule and drops any comparison that
uses them:

```python
# Remove comparison columns which are either 'used up' by the blocking rules
if set(br_cols).intersection(cc_cols):
    comparisons_to_deactivate.append(cc)
```

Blocking on a column fixes it at agreement, leaving no variation to learn
from. **Every comparison therefore needs at least one session that does not
block on it.** The three sessions above satisfy this: each derived column is
estimated in the other two, and `title`, `price` and
`common_identifier_tokens` are never blocked, so they are estimated in all
three — which is what the primary signal warrants.

### Why these three, at these thresholds

Splink notes EM works best on a block containing *"anywhere between around
0.1% and 99.9% true matches"*, and works badly under extreme imbalance. The
three rules were chosen to enrich differently:

- **T1** selects on near-decisive evidence — two records sharing a rare
  part-number-shaped token. The most concentrated sample available, and the
  smallest. It runs first so the broader sessions begin from better estimates.
- **T3** at DF ≤ 20 rather than the stricter DF ≤ 5, which yields only ~3,500
  pairs and is probably too concentrated as well as too small.
- **T2** is the volume session: broad, weakly enriched, and by far the largest.
  If it proves slow, Splink's `max_pairs` caps it without altering the rule.

Total across all three is roughly 892,000 pairs. Per Splink's documentation,
training cost is the **sum** across sessions rather than a cumulative union.

### Training samples the full space, not the candidate set

> ⚠️ **ASSUMPTION — standard practice, but stated rather than assumed.**

These rules generate pairs from the complete input tables, not from the
564,450 candidates that blocking produced. That is how Splink training
normally works, and it should be sound: EM estimates the *m* probabilities —
*P(agreement | match)* — and u probabilities come separately from
`estimate_u_using_random_sampling` over the full space. Both are conditional on
match status, which is a property of the population rather than an artefact of
how candidates were selected.

Training could instead be confined to the candidate set by combining the
pair-key condition with each rule. That is **not** done here: it adds real
complexity for a concern that is theoretical. Recorded so the choice is
visible.

### The match concentration is inferred, not measured

> ⚠️ **A limit on what can be claimed.**

Splink's 0.1%–99.9% guidance concerns the proportion of *true matches* inside
each training block. That proportion is exactly what the answer key would
reveal, and [D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)
seals it away.

So the reasoning that T1 is heavily concentrated and T2 only weakly so is
**structural inference from token rarity, not measurement**. It is plausible —
a shared rare part number really should imply a match far more often than a
shared brand does — but it is unverified, and will stay unverified until the
final evaluation.

The practical consequence is worth stating plainly: **if EM converges poorly,
a badly-proportioned training block is a likely cause, and diagnosing that
without labels will be difficult.** Recorded before building rather than
discovered afterwards.

### Supporting work

The four derived comparison columns are implemented in `src/features.py`:
`rare_identifier_tokens`, `common_identifier_tokens`, `brand_terms` and
`rare_tokens`. Coverage across the source tables:

| Column | Walmart non-empty | Amazon non-empty |
| --- | ---: | ---: |
| `rare_identifier_tokens` | 78.3% | 72.7% |
| `common_identifier_tokens` | 8.1% | 7.5% |
| `brand_terms` | 89.0% | 91.2% |
| `rare_tokens` | 98.9% | 98.6% |

Two details recorded there rather than left implicit. Rarity is judged by
document frequency **pooled across both tables**, unlike blocking rule R1 which
counts on the Amazon side only ([D18](#d18--r1-counts-word-frequency-on-the-amazon-side-only));
the difference is deliberate, since R1's threshold governs candidate *cost*
while this one governs how *informative* agreement is. And the identifier shape
test accepts pure-numeric tokens as well as mixed ones, which blocking's R2
does not — **R2 is unchanged**, since altering it would invalidate every
measured blocking figure.

---

## D27 — Comparing titles by proportion of shared words

**Decision.** The title comparison is custom SQL computing **word-level
Jaccard** — shared words as a proportion of all distinct words across the pair
— sorted into five levels plus a null level. Implemented in
`src/comparisons.py`, with `title_tokens` added to `src/features.py`.

### Splink's built-in Jaccard would have been actively harmful

`JaccardAtThresholds` generates `jaccard("title_l", "title_r")`, and DuckDB's
`jaccard()` compares **character sets, not words**: `jaccard('cat', 'act')`
returns 1.0.

On titles of this length that barely discriminates. Measured across the
candidate set:

| Percentile | Character Jaccard | Word Jaccard |
| --- | ---: | ---: |
| p05 | 0.484 | 0.000 |
| median | 0.636 | 0.065 |
| p95 | 0.788 | 0.226 |
| **usable range** | **0.304** | **0.857** |

The entire population sits inside a band of 0.30, because any two long
lowercase English strings draw on most of the same alphabet. A concrete pair:

```
"sumdex slr camera sling pack 39.99"  vs  "slr camera sling pack sumdex poc-484bk"  -> 0.667
"sumdex slr camera sling pack 39.99"  vs  "kingston datatraveler 8 gb usb flash..."  -> 0.500
```

The same product reordered, and an unrelated product, are **0.167 apart**.

### Jaro-Winkler is the wrong family for this data

| | chars (median / p90 / max) | words (median / p90) |
| --- | --- | --- |
| Walmart | 73 / 108 / 205 | 12 / 19 |
| Amazon | 84 / 128 / **857** | 14 / 23 |

Jaro-Winkler is built for short strings and weights a shared **prefix**
heavily, which suits `Jon`/`John` and not a 14-word product listing. The two
retailers reorder words freely, so a prefix bonus rewards an accident of word
order rather than agreement.

### ArrayIntersectAtSizes has a length bias

Splink's array comparison grades on the raw count of shared elements, which
scales with how much text a record happens to contain:

| Walmart title length | Median shared words | Median word-Jaccard |
| --- | ---: | ---: |
| Short (≤ 10 words) | 1 | 0.059 |
| Long (≥ 25 words) | **3** | 0.070 |

Three times the raw overlap for essentially the same normalised similarity.
Unnormalised counts would systematically favour verbose listings, and Amazon
titles reach 857 characters. Dividing by the union size removes that bias,
which is the reason for custom SQL rather than a built-in.

### The levels

Placed against the measured distribution rather than at round numbers. The
counts below are the pairs falling **within** each band, which are mutually
exclusive:

| Level | Condition | Pairs | Share |
| --- | --- | ---: | ---: |
| Exact | token sets identical | **5** | 0.001% |
| High | Jaccard ≥ 0.60 | 390 | 0.069% |
| Medium | Jaccard ≥ 0.35 | 5,126 | 0.908% |
| Low | Jaccard ≥ 0.20 | 37,717 | 6.682% |
| None | below 0.20 | 521,212 | 92.340% |

- **0.60** sits just above p99.9 (0.556).
- **0.35** is almost exactly p99 (0.350) — a boundary the data suggests rather
  than one imposed on it.
- **0.20** is close to p95 (0.226).
- **Exact match keeps its own level** despite covering only 5 pairs: agreement
  that rare should carry far more weight than merely close agreement, and
  merging it into the band above would discard that.

Five levels rather than two because a comparison that can only say "agree or
disagree" forces "close but not identical" into one of them. Splink learns each
level's weight; these cuts only decide where the boundaries fall.

### Implementation notes worth recording

The expression uses the inclusion-exclusion identity
`|A union B| = |A| + |B| - |A intersect B|`, because **DuckDB has no
`list_union`** and because this avoids building the union list at all. The
token lists are distinct and sorted upstream, so the identity is exact.

It casts to `DOUBLE`, not `FLOAT`. Single precision introduced errors around
3e-8 — small, but enough to move a pair sitting exactly on a threshold into the
wrong level. Verified against the same calculation in Python: double precision
agrees **exactly across all 564,450 pairs**, single precision did not.

`title_tokens` is the one derived column holding a single field rather than
evidence gathered from the whole record, because this comparison is
deliberately title-against-title. The other four columns carry cross-field
evidence. It uses the same tokeniser as everything else, so `1TB` and `1 tb`
reduce identically on both sides.

### Thresholds are placed on shape, not on separation

> ⚠️ **A limit on what these numbers mean.**

Every threshold above comes from where candidate pairs *fall* — percentiles of
an observed distribution. None comes from how well a threshold **separates
matches from non-matches**, because that requires the answer key sealed by
[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished).

So these are defensible starting points, not optimised ones. A cut at p99 is a
natural break in the data; whether it is the *right* break for distinguishing
products is unverified and stays unverified until the final evaluation.

### A known fragility

The exact-match level rests on **5 pairs**. Expectation-maximisation may be
unable to estimate a stable m-probability from a level that fires so rarely.
If it proves unstable, the agreed fallback is to fold exact match into the
≥ 0.60 level, losing the distinction but gaining a level with enough support to
estimate. Recorded in advance rather than discovered during training.

---

## D28 — Absence of evidence is not evidence of disagreement

**Decision.** The derived comparison columns emit `None` rather than an empty
list when a record carries no evidence of that kind, so Splink's null level
fires and contributes zero weight.

### The defect

Splink's array comparison opens with a null level:

```sql
"brand_terms_l" IS NULL OR "brand_terms_r" IS NULL
```

`src/features.py` originally emitted `[]` for a record with no brand terms. **An
empty list is not NULL** — `[] IS NULL` is false — so it fell past that level to
the final one and collected the weight for **disagreement**.

Those are opposite meanings. A record carrying no brand term has nothing to say
about brand; that is not evidence against a match.

### Scale, measured across all 564,450 candidate pairs

| Comparison | Pairs scored as disagreement through absence |
| --- | ---: |
| `common_identifier_tokens` | **550,934 — 97.61%** |
| `rare_identifier_tokens` | 264,117 — 46.79% |
| `brand_terms` | 92,001 — 16.30% |
| `rare_tokens` | 15,416 — 2.73% |

`common_identifier_tokens` would have contributed evidence *against* a match on
97.61% of pairs, on the strength of a field most records simply do not have.

### Why this contradicts the project's own reasoning

It inverts [D8](#d8--the-field-scrambling-problem-and-the-plan-for-it). The
benchmark's corruption is precisely what emptied these fields — values were
moved into `title` and their own column blanked. Scoring absence as
disagreement penalises a record **for having been corrupted**, which is the
opposite of what the cross-field design exists to do.

It also contradicts the conflicting-evidence design recorded in
[D22](#d22--how-the-two-systems-will-be-compared), which states that missing
values contribute zero weight rather than counting as disagreement. The
principle was right; the implementation did not honour it.

### The fix preserves genuine conflict

Only true absence becomes null. Two records that both carry brand terms which
happen not to overlap still produce two non-empty lists and an empty
intersection, and still reach the disagreement level — correctly.

| Situation | Arrays | Before | After |
| --- | --- | --- | --- |
| One side has no brand at all | `["sony"]` vs `[]` | disagreement ✗ | **null, zero weight** ✓ |
| Both have brands, different ones | `["sony"]` vs `["canon"]` | disagreement ✓ | disagreement ✓ |
| Both have the same brand | `["sony"]` vs `["sony"]` | agreement ✓ | agreement ✓ |

Verified end to end through DuckDB: `None` becomes SQL NULL, the null level
fires for absence, and does not fire for conflict or agreement. Two tests pin
the distinction so the two cases cannot silently collapse into one again.

### Result

Comparisons contributing weight, across all 564,450 candidate pairs:

| Contributing | Pairs | Share |
| --- | ---: | ---: |
| 1 of 5 | 4,731 | 0.84% |
| 2 of 5 | 57,883 | 10.25% |
| 3 of 5 | 237,168 | 42.02% |
| 4 of 5 | 255,559 | 45.28% |
| 5 of 5 | 9,109 | 1.61% |

**No pair has all five comparisons null.** `title_tokens` is populated on 100%
of records on both sides, so the title comparison always fires at some level and
every pair carries real evidence. The thinnest case is 4,731 pairs — 0.84% —
resting on the title comparison alone.

### How this was found

A direct safety check: *across the candidate set, are there pairs where every
comparison is blank, leaving nothing to score?* The answer to that question was
reassuring — zero such pairs. The defect was found while measuring it, and
would not have surfaced from reading the code, since `[]` and `None` look
equally innocuous until they meet SQL's null semantics.

It would also have been invisible in the output. The model would have trained
and predicted without error, simply weighting most of the candidate set
slightly against matching for reasons that were an artefact of representation.

### A sparsity note carried forward

Even corrected, `common_identifier_tokens` is null on 97.61% of pairs, so it
fires on roughly 2.4%. Expectation-maximisation may be unable to estimate a
stable weight from that. If it proves unestimable, the fallback is to merge it
into the rare identifier comparison — the same concern already recorded for the
5-pair exact-title level in [D27](#d27--comparing-titles-by-proportion-of-shared-words).

---

## D29 — A fourth training round, and a lesson about which statistic governs

**Decision.** A fourth expectation-maximisation session blocks on
`common_identifier_tokens`. Training order is now, by concentration:
rare identifiers, common identifiers, rare tokens, brand terms.

### The defect it fixes

The first full matcher run left one parameter unestimated:

```
Level All other comparisons on comparison rare_tokens not observed in dataset,
unable to train m value
```

That level — **no rare-token overlap** — applies to **526,116 pairs, 93.2% of
the candidate set**, at prediction time. Expectation-maximisation had never
seen a single example of it.

The cause was that the three training blocks in
[D26](#d26--blocking-rules-for-expectation-maximisation-training) were not
independent. Each selects on agreement over something that is *itself* a rare
token: rare identifiers are rare tokens, and brand terms with document
frequency ≤ 20 are rare tokens. Every block therefore guaranteed rare-token
overlap, and the dominant prediction case never appeared in training.

D26 had recorded the risk that training blocks might not represent the
prediction population. It did not anticipate that the three blocks would be
correlated with one another.

### Why `common_identifier_tokens` was expected to fail, and did not

The proposal looked unpromising on inspection. `common_identifier_tokens` means
document frequency above 5; `rare_tokens` means 20 or below. Tokens between 6
and 20 therefore sit in **both** columns, so blocking on the first ought to
imply agreement on the second.

Measured at token level, that held:

| | Count | Share |
| --- | ---: | ---: |
| Distinct common identifier tokens | 145 | |
| ...also inside `rare_tokens` | **119** | **82.1%** |
| ...genuinely outside (DF > 20) | 26 | 17.9% |

Measured at **pair** level, the conclusion reversed:

| Within the block | Pairs | Share |
| --- | ---: | ---: |
| `rare_tokens` null | 43 | 0.66% |
| `rare_tokens` some overlap | 786 | 11.98% |
| **`rare_tokens` zero overlap** | **5,732** | **87.36%** |

The reason is that pair generation scales as the **product** of the two posting
lists, so a handful of high-frequency tokens dominate:

| Token | Pooled DF | In `rare_tokens`? | Pairs generated |
| --- | ---: | --- | ---: |
| `1080p` | 156 | No | 3,275 |
| `500gb` | 66 | No | 728 |
| `00001` | 56 | No | 384 |
| `cat5e` | 70 | No | 325 |

**90.2% of the block's pairs come from the 26 tokens outside `rare_tokens`.**
The 119 overlapping tokens are numerous but individually rare, and contribute
almost nothing.

**The lesson worth keeping:** counting token *types* answered a different
question from counting the *pairs* those types generate, and only the second
governs what a training block contains. The same distinction caused hand
estimates of the D26 block sizes to run about 3.5% high, by counting a pair
once per shared key where Splink counts distinct pairs. A statistic that
sounds like the right one is not necessarily the one that governs.

### Result

The block contains 6,561 pairs — between T1 at 930 and T3 at 22,918 — and the
session converges in 20 iterations in 3.6 seconds.

**Every parameter in the model is now estimated. No level is imputed.**

The previously imputed level:

| | Before T4 | After T4 |
| --- | ---: | ---: |
| m probability | 0.8304 *(imputed)* | **0.7612** *(estimated)* |
| Weight | −0.27 bits | **−0.39 bits** |

Normalisation of the `rare_tokens` m probabilities improved substantially, from
a sum of **1.4152** to **1.0695** against an ideal of 1.0.

### Honest note on how much this changed

Very little, in the scores themselves. Pairs above 0.99 moved from 4,518 to
4,419, and the overall shape is unchanged — 93.4% still below 0.01.

The imputed value had been close enough that its practical effect was small.
The point of the fix is not that the numbers moved but that they are now
derived rather than guessed: an imputed parameter applied to 93% of the
candidate set is not something to leave in place because it happens to look
about right.

### A residual imprecision, recorded rather than hidden

The m probabilities within a comparison should sum to 1. After four sessions:

| Comparison | Sum |
| --- | ---: |
| `rare_identifier_tokens` | 1.0000 |
| `common_identifier_tokens` | 1.0000 |
| `brand_terms` | 0.9949 |
| `title` | **0.9372** |
| `rare_tokens` | **1.0695** |

Separate EM sessions estimate different levels against different populations,
and Splink does not renormalise across them. Two comparisons are off by 6-7%.
This is a property of multi-session training rather than a defect introduced
here, and it is far better than the 42% overshoot before T4 — but the model is
not perfectly calibrated, and that should be known when reading its
probabilities.

---

## D30 — Comparing prices by relative difference

**Decision.** Price is compared by `|a - b| / max(a, b)` — the gap as a share of
the larger price — in five levels plus a null level. Prices at or below zero are
parsed to NULL and treated as missing.

### Why relative rather than absolute

Five pounds is most of the price of a cable and a rounding error on a
television. An absolute threshold would be far too strict at one end of the
catalogue and meaningless at the other. Dividing by the larger of the two values
keeps the result between 0 and 1 and makes it symmetric, so argument order
cannot change the answer.

### Why zero and negative prices are missing, not zero

A price of zero in this data reads as an absent value rather than a free
product, and a relative difference measured against zero is undefined in any
case. Treating those as missing follows the principle established in
[D28](#d28--absence-of-evidence-is-not-evidence-of-disagreement): absence is not
evidence of disagreement. This affects 2,499 candidate pairs.

### The levels, placed against the measured distribution

Across the 119,109 candidate pairs carrying a usable price on both sides, the
relative difference has p5 = 0.023 and p10 = 0.109, with a **median of 0.624** —
the typical usable pair differs by 62%, which is what a candidate set of mostly
non-matches should look like.

| Level | Pairs in band | Cumulative |
| --- | ---: | ---: |
| Exact match | 1,177 | 1,177 |
| Within 2% | 4,553 | 5,730 |
| Within 10% | 5,387 | 11,117 |
| Within 20% | 7,571 | 18,688 |
| More than 20% apart | 100,421 | 119,109 |
| **Null** | **445,341** | |

**78.9% of candidate pairs reach the null level** and contribute nothing, which
is the intended behaviour: only 21.1% carry a usable price on both sides.

### What the model learned

| Level | m | u | Weight |
| --- | ---: | ---: | ---: |
| Exact match | 0.0262 | 0.000662 | **+5.31 bits** |
| Within 2% | 0.0536 | 0.00938 | +2.52 bits |
| Within 10% | 0.0875 | 0.0349 | **+1.33 bits** |
| Within 20% | 0.1233 | 0.0495 | **+1.32 bits** |
| More than 20% apart | 0.7034 | 0.906 | −0.36 bits |

Price is **weak evidence, as expected**. An exact price match is worth +5.31
bits against +12.39 for an exact title match and +11.52 for a shared rare
identifier. The structural prediction — that two retailers pricing
independently would make price a poor signal — is confirmed by the data rather
than assumed.

Including it was still the right call. Letting the model learn how little price
agreement is worth is more defensible than asserting in advance that it is
worthless, and an exact price match on an expensive item does carry real
information.

### Two of the five levels collapsed

**"Within 10%" and "Within 20%" learned essentially the same weight — +1.33 and
+1.32 bits.** The 10% boundary is not carrying information: a pair 15% apart is
being treated exactly like one 5% apart.

Those two levels could be merged into a single "within 20%" band without losing
anything the model is using.

> **Note added 19 September 2026.** This collapse has a practical consequence
> recorded later in [D32](#d32--tied-candidates-are-shown-as-an-unordered-set-not-a-ranked-list):
> the 0.0106-bit difference between these two levels is one of the recurring
> gaps that would otherwise rank review candidates against each other on a
> distinction the model did not make. That is **not** done here, because the levels were
approved as specified and the collapse is a finding to report rather than a
licence to change the design unilaterally. Recorded as an open simplification.

This is worth noting as a general point: level boundaries placed on the shape of
a distribution are not guaranteed to correspond to boundaries the *model* finds
meaningful. Here, one of four did not.

### Effect on the scores

Minimal. Pairs above 0.99 moved from 4,419 to 4,454 and the overall shape is
unchanged, with 93.3% still below 0.01. A weak comparison covering 21% of pairs
should not move much, and it did not.

---

## D31 — Tied partners: when the model cannot choose between candidates

**Decision.** A **tie** is defined as a within-record match-weight gap of **one
bit or less** between a record's best candidate and its runner-up. Tied
candidates are **not** resolved by taking the highest score. The record and its
whole candidate set go to human review as a **single item**, and the reviewer
may answer *none of these*. The underlying cause — a missing comparison — is
recorded as a known limitation rather than patched, and tied groups become the
first defined target for AI escalation.

Scoped to the confident region only; see [Scope](#scope-and-what-is-deliberately-left-open)
at the end.

> **Note added 19 September 2026.** The counts in this entry — 4,454 pairs,
> 1,412 records, 257 exactly tied — were measured at p ≥ 0.99, the working
> threshold at the time of writing. The accept threshold was afterwards fixed at
> **6.0 bits (p ≥ 0.9846)** in [`PRE_REGISTRATION.md`](PRE_REGISTRATION.md),
> under which **346** records are tied. The figures below are left as they were
> measured rather than restated, so that the evidence the decision actually
> rested on stays visible. The policy is unchanged; only the region it applies
> to has moved.

### The problem

Scoring all 564,450 candidate pairs leaves 4,454 pairs above 0.99, but those
involve only **1,412 distinct Walmart records**. The average confident Walmart
record claims 3.1 Amazon partners and the worst claims 20. Something has to be
decided about records whose candidates the model ranks equally, because a naive
reading of the output would report all of them as matches.

### Measuring ties in bits, not in probability

An early reading compared probabilities and concluded that 61.8% of confident
records had a tied runner-up. **That figure was wrong, and the error is worth
recording.** Above 0.99 the probability scale compresses: every one of the 4,454
confident pairs sits inside a window 0.0087 wide, so pairs the model separates
clearly still look identical when compared as probabilities.

The model's own currency is match weight in bits. Measured there:

| Gap, best vs runner-up | Records | Share |
| --- | ---: | ---: |
| Exactly 0 — identical evidence | 257 | 18.2% |
| 0 to 1 bit | 87 | 6.1% |
| 1 to 2 bits | 214 | 15.2% |
| 2 to 8 bits | 158 | 11.2% |
| More than 8 bits — decisive | 696 | 49.3% |

The real figure is roughly 18%, not 62%. Half of all confident records are
separated by more than 8 bits, meaning the runner-up is over 256 times less
likely.

**This measurement is exactly immune to the prior.** The value of
`probability_two_random_records_match` enters every pair's match weight as the
same additive constant, so it cancels completely in a within-record difference.
Of all the analysis carried out on these scores, this is the part least affected
by the calibration concerns recorded in [D25](#d25--the-prior-probability-that-two-random-records-match).
The `m` normalisation drift does still affect gaps, since it changes individual
comparison weights.

### Why one bit, and why the number is robust

The gap distribution is not smooth. It has a sparse region immediately below
one bit:

| Gap band | Records |
| --- | ---: |
| (0.00, 0.25] | 23 |
| (0.25, 0.50] | 41 |
| (0.50, 0.75] | **10** |
| (0.75, 1.00] | **13** |
| (1.00, 1.25] | 72 |
| (1.25, 1.50] | 36 |
| (1.50, 2.00] | 106 |

Only 23 records fall across the whole (0.5, 1.0] interval. A threshold placed
anywhere in that valley selects between 321 and 344 records, so the exact
placement barely changes the outcome — the boundary is not slicing through a
dense cluster. That robustness is the argument for the number; it is empirical
rather than assumed.

The interpretation is also defensible on its own terms: a one-bit gap means the
runner-up is half as likely as the winner. No reviewer would call that
distinguishable.

At one bit, **344 records are tied, covering 1,624 of the 4,454 confident
pairs.**

### The cause is a missing comparison, not a scoring defect

In every case examined, the attribute that would settle the question is present
in the text and no comparison captures it.

**A_501** — Walmart *"edge tech **512mb** proshot 100x compact flash memory
card"* ties across **eleven** Amazon Edge ProShot cards, of 4GB, 8GB, 16GB and
32GB. None of the eleven is a 512MB card. Very likely *zero* are correct.

**A_2402** — Walmart *"crown ecostep mat **36 x 60 midnight blue**, et0035mb"*
ties between `et0310mb` (36×120, right colour, wrong size) and `et0035ch`
(36×60, right size, wrong colour). Neither is correct.

**A_2401** — Walmart *"amzer luxe argyle high-gloss skin case … **smoke gray**"*
ties between the hot pink variant and the smoke grey variant. Here the correct
answer *is* present; the model cannot see that one token decides it.

**A_1285** — Walmart *"paperpro compact stapler 15 sheet, modelno 1510"* ties
across eight staplers of differing model numbers and sheet capacities.

The mechanism: `title` is compared by proportion of shared words
([D27](#d27--comparing-titles-by-proportion-of-shared-words)), so `512mb` is one
token among fifteen and weighs no more than `memory`. The identifier
comparisons fire on any shared rare token, and `proshot` is shared by all
eleven.

A supporting measurement, **observational rather than causal**: where a usable
price exists on both sides the tie rate is **6.6%**; where it is absent, it is
**21.8%**. Price is the one attribute that separates a 512MB card from a 32GB
one. The median gap is almost unchanged (7.45 against 7.90 bits), so price does
not generally increase separation — it specifically breaks exact ties. Price
availability may also stand in for record quality more broadly.

### What was decided, and what was rejected

Four policies were costed against the 4,454 confident pairs.

| Option | Predicted | Reviewed | Outcome |
| --- | ---: | ---: | --- |
| A — every tied partner is a match | 4,454 | 0 | Rejected |
| B — keep the highest-scoring partner | 1,412 | 0 | **Rejected** |
| C — abstain on tied *pairs* | 2,830 | 1,624 pairs | Rejected |
| D — abstain on tied *groups* | 2,830 | 1,624 pairs as **344 items** | **Adopted** |

**Option A is rejected** because A_501 alone would contribute eleven predicted
matches of which at most one, and probably none, is correct.

**Option B is rejected, and specifically so.** In the 257 records where the gap
is exactly zero the top score is *equal*, so selecting the highest-scoring
partner is decided by row order — a coin flip. Option B is the worst of the four
precisely because its errors arrive carrying high confidence, which is the one
failure mode selective prediction exists to prevent.

**C and D touch identical pairs** and differ only in presentation. That
difference is the entire point.

### The review unit is the record, not the pair

*Is A_501 ↔ B_11152 a match?* cannot be answered in isolation. A reviewer can
only answer it by seeing all eleven candidates together and noticing that not
one of them is a 512MB card. The unit of review is therefore **one Walmart
record together with its confident candidate set**, which converts 1,624
pair-decisions into **344 record-decisions** — better value from a fixed review
budget, and the correct unit of work regardless of budget.

**The review process must accept *none of these* as a valid answer.** A_501 and
A_2402 both appear to have no correct partner present. An interface that forced
a choice among the candidates would manufacture errors rather than record the
truth, and would corrupt the very judgements the review exists to collect. This
extends the queue design in [D24](#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai).

### The obvious fix is deliberately not applied

The direct remedy is a comparison weighting capacity, colour, size and variant
tokens. **It is not built.** It would be constructed from four hand-picked
examples with no labelled data available to validate it, which is how a model
becomes fitted to its author's intuitions rather than to the problem. Recorded
as a known limitation.

This also stays within the no-peek rule: choosing a comparison because it
resolves cases that *look* wrong is a weak form of the same self-labelling that
[D14](#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished) rules out.

### Tied groups are the first defined AI escalation target

Separating *512MB* from *32GB*, or *smoke grey* from *hot pink*, requires
semantics rather than string overlap — the capability the AI system has and the
classical system provably lacks. The 344 tied groups are a well-defined
escalation target, and they sharpen the comparison the project is built to make:
not a diffuse accuracy difference, but *on the cases where the classical system
is demonstrably blind, how much does AI escalation recover?*

This is the escalation criterion anticipated in
[D22](#d22--how-the-two-systems-will-be-compared), now with a concrete
population attached.

### Scope, and what is deliberately left open

**This analysis covers only the region above 0.99**, because that is the region
characterised so far. Ties occur throughout the score range. The policy is
**not** applied more widely until the main confident/unsure boundary is settled;
applying it first and choosing the boundary afterwards would mean measuring
twice. The 344 records and 1,624 pairs above are therefore figures for the
p ≥ 0.99 region, not final counts.

Nothing is implemented by this entry. It records the definition, the policy and
the reasoning; the code follows once the boundary is fixed.

---

## D32 — Tied candidates are shown as an unordered set, not a ranked list

**Decision.** In the review queue, candidates whose scores are tied are
presented as an **unordered set with no rank numerals**, rendered in a
**deterministic shuffle seeded by the Walmart record id**. The tied scores are
displayed and the group is labelled as tied, so the presentation explains
itself. Candidates that are **not** tied keep their ranking, because there the
order reflects evidence.

The threshold defining a display tie is **deliberately tighter than the one-bit
rule in [D31](#d31--tied-partners-when-the-model-cannot-choose-between-candidates)**
and is recorded below as still open.

### Why a ranked list would be misleading

Among candidates holding the same score, the order is decided by row position
in the Amazon table. It is an artefact of how the data was loaded and carries no
information about which candidate is the better match. Numbering such a list
1, 2, 3 asserts a fact that does not exist.

Measured across the 1,113 records routed to review, **59 records (5.3%) have
more than five candidates sharing their exact top score**, and one has 36. For
those records any ranked presentation is fiction over its whole visible length.

### The harm is systematic, not random

Position bias in ranked lists is well established: the first item is selected
disproportionately often. Where the order is arbitrary, a ranked display does
not merely fail to help — it **converts an arbitrary artefact into a systematic
bias**, correlated with Amazon table position, in exactly the judgements being
collected to evaluate the system.

This is the distinction that decides the question. Random error across 1,113
reviews largely averages out. Bias correlated with an external ordering does
not: it accumulates in one direction and contaminates the evaluation set. The
concern is the same one behind the cognitive-forcing-function literature cited
in [D24](#d24--how-abstained-pairs-are-handled-build-for-humans-measure-the-ai),
and it is the reason the reviewer's independence is worth protecting at some
cost to speed.

It is also the same failure D31 guards against one layer up. D31 refuses to let
the system pick the argmax of a tie, on the grounds that the choice is decided
by row order. A ranked display would reintroduce that identical coin flip inside
the interface, with a human pulling the lever.

### Why D31's one-bit threshold does not transfer

D31's margin answers *"is the model confident enough to accept without review?"*
Display answers a different question: *"can the reviewer use this difference?"*
Reusing one number for both would be a silent error.

Of the 1,191 candidates that sit within one bit of their record's best without
being exactly tied:

| Gap below best | Candidates | The runner-up is |
| --- | ---: | --- |
| 0.00–0.10 bits | 411 | 93–100% as likely |
| **0.10–0.25 bits** | **21** | 84–93% as likely |
| 0.25–0.50 bits | 464 | 71–84% as likely |
| 0.50–1.00 bits | 295 | 50–71% as likely |

Treating all of these as tied would flatten real evidence. A candidate half as
likely as the leader is a meaningfully weaker candidate and the reviewer can act
on that. **390 of the 1,113 reviewed records differ between the two
definitions.**

The distribution also shows a **sparse region between 0.10 and 0.25 bits** — 21
candidates, between clusters of 411 and 464 — which is the same structural
argument used to place every other threshold on this project. A display-tie
epsilon in that valley would separate the effectively identical from the
genuinely distinguishable without cutting through a dense cluster.

### The epsilon, and what the small gaps turned out to be

**The display-tie epsilon is 0.05 bits.** Two candidates whose scores differ by
0.05 bits or less are treated as tied for presentation.

The number follows from what the small gaps actually are. Below 0.30 bits there
are only 24 distinct gap values across the reviewed records, and **397 of the
411 candidates under 0.10 bits sit on just two of them**:

| Gap | Candidates | Traced to |
| ---: | ---: | --- |
| **0.0389 bits** | 374 | `rare_identifier_tokens`: absent versus present-and-non-overlapping |
| 0.0106 bits | 23 | `price`: "Within 10%" against "Within 20%" |

Both were traced to specific levels in the saved model rather than inferred.

The 0.0106 quantum is the collapsed price pair already recorded in
[D30](#d30--comparing-prices-by-relative-difference) at +1.3264 and +1.3158
bits — a boundary D30 found was carrying no information.

The 0.0389 quantum is **not** a second collapsed pair, and the distinction
matters. `rare_identifier_tokens` assigns **−0.0389 bits** to "All other
comparisons", from m = 0.97334 against u = 0.99997 — nearly identical, because
almost every pair, matching or not, lacks rare-identifier overlap. A null level
contributes nothing. So the gap separates a candidate whose column is **absent**
from one where it is **present and fails to overlap**: having the evidence and
missing on it is fractionally worse than not having it. Verified on 400 sampled
candidates, consistent in all 400.

That is defensible Fellegi-Sunter behaviour and follows directly from
[D28](#d28--absence-of-evidence-is-not-evidence-of-disagreement). The point here
is only that the resulting weight is **indistinguishable from zero**, so
ordering two candidates on it presents a distinction the model did not really
make.

An epsilon of 0.05 bits sits immediately above the dominant 0.0389 quantum, in a
sparse region holding roughly 14 candidates across six values, and below the
scattered differences from 0.10 bits upward — 21 candidates across 11 values,
with no dominant quantum, which read as genuine if small evidence differences
and keep their order.

The choice is insensitive: **any epsilon from 0.05 to 0.25 bits changes only 19
records** (117 against 136 differing from strict equality), the same robustness
property used to place every other threshold on this project.

**Strict score equality was considered and rejected.** It needs no number
defended, but it would leave 374 candidates ranked on a distinction where the
runner-up is 97.3% as likely — the largest single group of false-precision cases,
and precisely what this entry exists to prevent.

### A list cannot be displayed without a spatial order

Removing the numerals stops the interface *claiming* a ranking. It does not
remove position bias, because whatever appears first is still seen first. The
labelling is necessary and not sufficient, and the load-bearing decision is what
order the tied group is actually rendered in.

**A deterministic shuffle seeded by the record id** is adopted. Seeding keeps
the queue reproducible — the same artefact regenerates identically, which
matters for an evaluation input — while decorrelating the order from the Amazon
table, so any residual position bias becomes noise rather than a systematic
lean in one direction.

**Alphabetical ordering was considered and rejected.** It is easier to work
through, but it reintroduces a systematic order that may correlate with brand —
and brand is frequently the only signal these tied candidates share, which is
why they are tied in the first place. Trading an arbitrary bias for a bias
aligned with the confounder would be worse than doing nothing.

### The cost, accepted deliberately

An unordered set has no natural entry point and reviewers may work more slowly
through one. That cost is accepted. These records are routed to a human
precisely because the machine's ordering of them is worthless, and a slower
correct judgement is worth more than a fast anchored one.

### Scope

This entry settles presentation and the display-tie epsilon. It does **not** set
the display cap — how many candidates a reviewer sees per record — which remains
open.

---

## Working conventions

- **Raw data is never edited in place.** Files in `data/raw/` stay exactly as
  downloaded. Any cleaning produces new files elsewhere.
- **Data provenance is verified, not assumed.** Every dataset records where it
  came from, and was checked against the benchmark's published row and match
  counts before use.
- **Nothing is silently substituted.** If data cannot be obtained or verified,
  that is reported plainly rather than filled with a placeholder or a
  stand-in source.
