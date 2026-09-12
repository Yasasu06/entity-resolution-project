"""Tests for the blocking text normalisation.

These pin down the behaviour the fix exists to produce: real manufacturer part
numbers stay findable across the two retailers' different punctuation, while
ordinary words are not welded into meaningless character sequences.

Run with:  pytest
"""

from src.text_normalisation import (
    char_ngrams,
    legacy_collapsed,
    segments,
    word_tokens,
)


def test_word_tokens_splits_on_all_punctuation():
    assert word_tokens("RR-VTPS-28PK-R1") == ["rr", "vtps", "28pk", "r1"]
    assert word_tokens("edge 2gb/2x1gb") == ["edge", "2gb", "2x1gb"]


# --- the behaviour the fix was made for -------------------------------------

def test_split_part_number_is_welded_back_together():
    """The case that motivated the whole rule: a digit starts the next token."""
    assert segments("kvr400x64c3a 1g") == ["kvr400x64c3a1g"]


def test_ordinary_words_are_never_welded():
    """The noise the fix removes: 'desktop computers' stays two chunks."""
    assert segments("desktop computers") == ["desktop", "computers"]


def test_ngrams_never_cross_a_kept_boundary():
    """A sequence must lie inside one segment, never straddle two.

    These are the exact junk sequences the old normalisation produced from
    'desktop computers', and which drove 79.3% of its candidate pairs.
    """
    grams = char_ngrams("desktop computers")
    assert "deskt" in grams        # inside the first word
    assert "puter" in grams        # inside the second
    for junk in ("ktopc", "topco", "opcom", "pcomp"):
        assert junk not in grams, f"{junk!r} spans the boundary and must not exist"


def test_two_retailers_spellings_still_share_sequences():
    """Walmart's run-together form vs Amazon's hyphenated form."""
    walmart = char_ngrams("rrvtps28pkr1")
    amazon = char_ngrams("rr-vtps-28pk-r1")
    shared = walmart & amazon
    assert shared, "the two spellings must still have something in common"
    assert "vtps2" in shared


def test_digit_on_either_side_triggers_the_weld():
    assert segments("io2305 1109msl") == ["io23051109msl"]   # digit on the right
    assert segments("28pk r1") == ["28pk", "r1"]             # 'k' and 'r' - no weld


def test_known_residual_word_number_welding():
    """Documented, accepted imperfection - see docs/DECISIONS.md (D15).

    A plain word followed by a number still welds. Pinned here so the
    behaviour is deliberate and visible rather than a surprise later.
    """
    assert segments("black 25 pack") == ["black25pack"]


# --- general properties ------------------------------------------------------

def test_segments_of_empty_or_punctuation_only_text():
    assert segments("") == []
    assert segments("---") == []
    assert char_ngrams("") == set()


def test_short_segments_yield_no_ngrams():
    """Segments shorter than the window produce nothing, by definition."""
    assert char_ngrams("usb") == set()
    assert char_ngrams("abcde") == {"abcde"}


def test_ngrams_are_the_right_length():
    for gram in char_ngrams("kingston valueram 400mhz"):
        assert len(gram) == 5


def test_legacy_collapsed_is_kept_only_for_comparison():
    """The superseded normalisation, retained so the fix can be measured."""
    assert legacy_collapsed("desktop computers") == "desktopcomputers"
    assert legacy_collapsed("rr-vtps-28pk-r1") == "rrvtps28pkr1"
