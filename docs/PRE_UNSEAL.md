# The label-feedback boundary

> **Correction added after the original boundary.** Earlier exploratory work
> used `train` and `valid` labels before the stricter D14 policy was adopted.
> The original version of this document wrongly claimed that no labeled data
> had ever been read. The defensible claim is that later blocking and matching
> design decisions for the original pre-registered evaluation were made without
> further label feedback. [D14](DECISIONS.md#d14--strict-no-peek-no-labelled-data-until-the-system-is-finished)
> documents the earlier exposure. D41 and D46 then changed the decision policy
> after the original evaluation with knowledge of its labels. The original
> document text is available at `26f5d30`, its first commit; the `.ots` proof
> belongs to the original bytes, not this corrected file.

**Boundary commit: `9819d63b5257be5a0f67d29c93b8e8b48d9a0767`**
(`9819d63`, "Write the human-only arm and the comparable baseline", 20 September 2026)

This commit marks the end of the later design period governed by D14. The
blocking, matching and original decision rules developed in that period were
not selected using label feedback. Earlier train/validation exploration had
already occurred and is disclosed in D14 and [ASSESSMENT.md](ASSESSMENT.md).

This document identifies the pre-evaluation policy and the limits of its
label-feedback claim.

## What the claim rests on

**Not on a tag or a timestamp.** The annotated tag `pre-unseal` marks this
commit for navigation. It is not evidence: `git tag -f` moves a tag freely,
commit dates are author-controlled, and a tagger date is self-reported. The same
is true of every date recorded in this repository.

The narrower claim is supported by three kinds of evidence a reader can inspect.

**1. Label reads require an explicit unlock.** `src/data_loading.py` refuses
to open a labeled split without `unlock_final_evaluation`, and
`src/baseline_token_overlap.py` requires a command-line flag. Tests exercise
these guards, and some tests explicitly unlock and read train/validation labels.
The guards make access deliberate; they do not prove that no prior access
occurred.

**2. The work makes falsifiable predictions.** `PRE_REGISTRATION.md` fixes exact
thresholds, an exact prompt, an exact model identifier and an exact list of
measurements before the original final evaluation. Several are specific enough
to be wrong: the display ceiling is predicted to fall below 1.00, the baseline is
predicted to accept 1,055 records, and the AI arm's stability floor was set at
60% before it was run. The original evaluation tested these predictions.

**3. The record is self-damaging.** [D36](DECISIONS.md) records that the system's
headline output fails: an independent judge rejects roughly 31% of
auto-accepted pairs, and a fabricated near-miss ties or beats the true partner in
49.0% of cases. [D37](DECISIONS.md) records that the one cleanly-working fix
reaches 1.5% of the problem. [D38](DECISIONS.md) declines a change that would
have improved the reported numbers, on the grounds that it would misrepresent a
structural problem as a calibration one.

These entries can be compared against the original evaluation in D39.

## Independent timestamping

`PRE_UNSEAL.md.ots` is an [OpenTimestamps](https://opentimestamps.org) proof for
the **original version** of this file, first committed as `26f5d30` after the
boundary commit. Because this
document now contains a correction, running `ots verify` against the current
file will not verify its contents. Retrieve the original bytes from
`26f5d30:docs/PRE_UNSEAL.md` to verify that historical version with the proof.

The proof file records a proposed independent timestamp anchor. Its external
anchor was not independently verified in this correction pass, and it does not
prove that earlier labels were unread.

## The convention from this point

The pre-evaluation policy is accessible at the boundary commit; the original
version of this document is accessible at `26f5d30`. This corrected document
explicitly records where its original claim went too
far. Historical decision-log entries remain as written, with later corrections
identified as later work.

Original and post-evaluation results are identified separately: D39 is the
original pre-registered policy; D41 and D46 are later label-informed changes.

## One disclosure about this repository's history

This repository's history was rewritten once, before the boundary commit, to
remove a local working-notes file that was never intended to be published. The
rewrite changed commit hashes throughout. It removed a file, added nothing, and
altered no code, document or result.
