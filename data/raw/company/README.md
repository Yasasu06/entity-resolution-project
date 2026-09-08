# Company dataset — deliberately deferred

This folder is intentionally empty of data. **That is a decision, not an
unfinished task.**

The Company textual benchmark was pursued, could not be obtained from any
verifiable source reachable from this environment, and was then consciously set
aside for two independent reasons:

1. The canonical host (`pages.cs.wisc.edu`) is refused by this environment's
   network egress policy at the connection stage, so no path on it is
   reachable. Every published mirror is dead or blocked.
2. Its `tableA.csv` is reported at ~185 MB (figure supplied by the project
   owner; not independently verified, as the file was never retrievable), which
   exceeds GitHub's 100 MB per-file limit — so it could not be committed here
   without Git LFS regardless.

No substitute dataset was used and no synthetic data was generated in its place.

Company is a *textual* matching problem (long free-text descriptions), which is
a different problem from the structured-but-corrupted attribute matching this
project focuses on — so deferring it narrows scope rather than losing anything
essential.

Full reasoning, the complete list of sources tried, and the conditions that
would reopen this decision are in [`docs/DATASETS.md`](../../../docs/DATASETS.md).
