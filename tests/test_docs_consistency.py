"""The log and the places that describe it are checked against each other.

docs/ENGINEERING_STANDARDS.md carries a rule that a new decision entry and the
counts describing it move in the same commit. A written rule holds only while
someone remembers it, and four references had drifted before this file existed:
README.md said 49 entries and 307 tests, the standards document said 73 tests,
and the site's record row said 50 entries, 13 pre-registration sections and 318
tests.

No test here makes a network call.

Run with:  pytest
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "docs" / "DECISIONS.md"
README = ROOT / "README.md"
STANDARDS = ROOT / "docs" / "ENGINEERING_STANDARDS.md"
METHOD = ROOT / "site" / "src" / "components" / "Method.jsx"
PRE_REG = ROOT / "docs" / "PRE_REGISTRATION.md"


def entry_numbers() -> list:
    """Every decision entry number in the log, in order."""
    return sorted(int(n) for n in re.findall(r"^## D(\d+)", DECISIONS.read_text(), re.M))


# --- the log is internally sound ---------------------------------------------

def test_the_log_has_no_gaps_or_duplicates():
    numbers = entry_numbers()
    assert numbers == list(range(1, max(numbers) + 1))


# --- everything that states the count agrees with it -------------------------

def test_readme_states_the_entry_total():
    total = len(entry_numbers())
    assert f"({total} entries)" in README.read_text(), \
        f"README should say ({total} entries)"


def test_readme_prose_states_the_entry_total():
    total = len(entry_numbers())
    assert f"{total} decision entries" in README.read_text(), \
        f"README prose should say {total} decision entries"


def test_standards_states_the_highest_entry_number():
    highest = max(entry_numbers())
    text = STANDARDS.read_text()
    assert f"D1–D{highest}." in text, f"standards should say D1–D{highest}."


def test_the_site_record_row_states_the_entry_total():
    total = len(entry_numbers())
    assert f"{total} decision entries" in METHOD.read_text(), \
        f"site record row should say {total} decision entries"


def test_the_site_record_row_states_the_pre_registration_section_count():
    sections = len(re.findall(r"^## \d+\.", PRE_REG.read_text(), re.M))
    assert f"{sections} pre-registration sections" in METHOD.read_text(), \
        f"site record row should say {sections} pre-registration sections"


# --- the test total ----------------------------------------------------------
#
# The figure quoted in the documents is asserted against pytest's *collected*
# count, not its passing count. Those differ by environment: six tests in
# test_stream.py skip where data/processed/ is absent, so a run reports 358
# passing locally and 352 passing with 6 skipped in CI. Collection is the same
# number in both, which makes it the figure a test can hold to.

def collected_count() -> int:
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "--collect-only"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    found = re.search(r"(\d+) tests? collected", out)
    if not found:
        pytest.skip("could not read a collected count from pytest")
    return int(found.group(1))


def test_readme_states_the_test_total():
    total = collected_count()
    text = README.read_text()
    assert f"({total} passing)" in text and f"({total} tests)" in text, \
        f"README should say {total} in both the file table and the run instructions"


def test_standards_states_the_test_total():
    assert f"{collected_count()} tests currently pass." in STANDARDS.read_text()


def test_the_site_record_row_states_the_test_total():
    assert f"{collected_count()} tests" in METHOD.read_text()
