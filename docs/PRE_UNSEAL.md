# The label-free boundary

**Boundary commit: `9819d63b5257be5a0f67d29c93b8e8b48d9a0767`**
(`9819d63`, "Write the human-only arm and the comparable baseline", 20 September 2026)

Everything reachable from that commit was designed, written, measured and
documented **without any labelled data ever having been read**. No `train`,
`valid` or `test` split was opened at any point in its history.

This document exists so that the boundary is a specific, checkable claim rather
than a vague one.

## What the claim rests on

**Not on a tag or a timestamp.** The annotated tag `pre-unseal` marks this
commit for navigation. It is not evidence: `git tag -f` moves a tag freely,
commit dates are author-controlled, and a tagger date is self-reported. The same
is true of every date recorded in this repository.

The claim rests on three things a reader can check independently.

**1. The seal is enforced in code, not by assertion.** `src/data_loading.py`
refuses to open a labelled split without an explicit `unlock_final_evaluation`
override, and `src/baseline_token_overlap.py` refuses to run without a
command-line flag. Both guards have tests. A reader can inspect the mechanism
rather than trust a statement.

**2. The work makes falsifiable predictions.** `PRE_REGISTRATION.md` fixes exact
thresholds, an exact prompt, an exact model identifier and an exact list of
measurements, all before the answers were available. Several are specific enough
to be wrong: the display ceiling is predicted to fall below 1.00, the baseline is
predicted to accept 1,055 records, and the AI arm's stability floor was set at
60% before it was run. When the labels are read, these hold or they do not.

**3. The record is self-damaging.** [D36](DECISIONS.md) records that the system's
headline output fails: an independent judge rejects roughly 31% of
auto-accepted pairs, and a fabricated near-miss ties or beats the true partner in
49.0% of cases. [D37](DECISIONS.md) records that the one cleanly-working fix
reaches 1.5% of the problem. [D38](DECISIONS.md) declines a change that would
have improved the reported numbers, on the grounds that it would misrepresent a
structural problem as a calibration one.

Work is not retrofitted to look like this.

## Independent timestamping

`PRE_UNSEAL.md.ots` is an [OpenTimestamps](https://opentimestamps.org) proof for
this file, which contains the boundary commit hash. It anchors that content into
the Bitcoin blockchain and is verifiable with `ots verify docs/PRE_UNSEAL.md.ots`.

Unlike a git tag, it is controlled by neither this repository's author nor by
GitHub. It is the only artefact here that constitutes actual proof that this
content existed before a given time.

## The convention from this point

**Nothing at or before the boundary commit is ever edited after the labels are
read.** Corrections to pre-unseal documents are made by adding new entries that
reference them, never by revising them in place — the practice already followed
for [D34](DECISIONS.md)'s correction of an earlier reading, and for the
cross-reference added to section 6.3 rather than a rewrite of it.

Results obtained after unsealing go in **new documents**. A reader comparing a
post-unseal claim against a pre-unseal one should never have to wonder which was
written first.

## One disclosure about this repository's history

This repository's history was rewritten once, before the boundary commit, to
remove a local working-notes file that was never intended to be published. The
rewrite changed commit hashes throughout. It removed a file, added nothing, and
altered no code, document or result.
