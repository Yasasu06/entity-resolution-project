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
