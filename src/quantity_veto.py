"""A post-hoc veto on pairs whose stated quantities conflict.

D36 found the matcher cannot separate a real partner from a near-miss differing
in one identity-bearing attribute: a 512MB card and a 32GB card present almost
the same evidence, because every comparison measures token *overlap* and the
mutated token simply joins the set rather than displacing anything.

This module refuses auto-acceptance where both records state a quantity of the
same family and share no value. A 32GB card is not a 512MB card, and that
inference needs no world knowledge - which is exactly why it can be made here
rather than left to the AI arm.

**It is a veto, not a comparison** (docs/PRE_REGISTRATION.md section 9.1).
Adding a comparison would require retraining, changing every score and
invalidating the pre-registered thresholds and everything measured on them. A
signal this precise and this rare is also badly served as one weighted term
among six, where expectation-maximisation can dilute it. As a veto it cannot be
outvoted and can be switched off on its own.

**Its reach is small and that is reported, not hidden.** It fires on about 1.5%
of accepted pairs - not the 9.6% the planted probes suggest, because that recipe
manufactured quantity conflicts far above their natural rate.

**It does not address conflicting model numbers**, which were most of the
problem. That exclusion is deliberate and evidence-based; see section 9.5.

Quantities are read from **every attribute**, not only the title: a capacity or
a dimension frequently appears in a model number or a category. That choice was
made on design grounds before the held-out test in section 9.3 was run.
"""

import re

import pandas as pd

# Each family maps a unit to a multiplier into that family's base unit, so that
# 1tb and 1024gb compare equal rather than merely differing as strings.
FAMILIES: dict[str, tuple[re.Pattern, dict[str, float]]] = {
    "storage": (
        re.compile(r"\b(\d+(?:\.\d+)?)\s?(kb|mb|gb|tb)\b"),
        {"kb": 1.0, "mb": 1024.0, "gb": 1024.0**2, "tb": 1024.0**3},
    ),
    "length": (
        re.compile(r"\b(\d+(?:\.\d+)?)\s?(inch|inches|in|\")(?![a-z])"),
        {"inch": 1.0, "inches": 1.0, "in": 1.0, '"': 1.0},
    ),
    "power": (
        re.compile(r"\b(\d+(?:\.\d+)?)\s?(w|watt|watts)\b"),
        {"w": 1.0, "watt": 1.0, "watts": 1.0},
    ),
}


def quantities(text: str) -> dict[str, set[float]]:
    """Every quantity stated in the text, normalised within its family."""
    lowered = str(text).lower()
    found: dict[str, set[float]] = {}
    for family, (pattern, units) in FAMILIES.items():
        values = {float(m.group(1)) * units[m.group(2)]
                  for m in pattern.finditer(lowered)}
        if values:
            found[family] = values
    return found


def record_quantities(row: pd.Series, columns: list[str]) -> dict[str, set[float]]:
    """Quantities stated anywhere in a record, not only in its title."""
    text = " ".join(str(row[c]) for c in columns if pd.notna(row[c]))
    return quantities(text)


def conflicts(left: dict[str, set[float]], right: dict[str, set[float]]) -> bool:
    """True when both sides state a quantity of one family and share no value.

    Silence is never a conflict: a record that states no capacity disagrees with
    nothing. This follows the principle set in D28 - absence of evidence is not
    evidence of disagreement.
    """
    for family in set(left) & set(right):
        if not (left[family] & right[family]):
            return True
    return False


def conflicting_pairs(
    pairs: pd.DataFrame,
    table_a: pd.DataFrame,
    table_b: pd.DataFrame,
    left_id: str,
    right_id: str,
) -> pd.Series:
    """Boolean per pair: does this pair state conflicting quantities?"""
    from src.data_loading import attribute_columns

    columns = attribute_columns(table_a)
    qa = {i: record_quantities(r, columns) for i, r in
          table_a.set_index("unique_id").iterrows()}
    qb = {i: record_quantities(r, columns) for i, r in
          table_b.set_index("unique_id").iterrows()}
    return pd.Series(
        [conflicts(qa.get(l, {}), qb.get(r, {}))
         for l, r in zip(pairs[left_id], pairs[right_id])],
        index=pairs.index,
    )
