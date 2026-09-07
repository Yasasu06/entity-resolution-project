# Company dataset — NOT PRESENT

This folder is intentionally empty of data.

The **Company** textual benchmark (DeepMatcher / Magellan collection) could not
be downloaded from any verifiable source reachable from the environment this
project was set up in. No substitute dataset was used and no synthetic data was
generated in its place.

Full details of every source that was tried, and the exact command to fetch it
from a machine with unrestricted internet access, are in
[`docs/DATASETS.md`](../../../docs/DATASETS.md).

Short version — from an unrestricted network:

```bash
curl -O http://pages.cs.wisc.edu/~anhai/data1/deepmatcher_data/Textual/Company/company_exp_data.zip
unzip company_exp_data.zip -d data/raw/company/
```
