"""Turning a record's text into the pieces used for blocking comparisons.

Blocking needs to decide cheaply whether two records are worth comparing
properly. To do that it breaks each record's text into small pieces and looks
for pieces the two records share. This module produces those pieces.

The interesting problem is **where one piece ends and the next begins.**

Two retailers describe the same product differently, and they punctuate
manufacturer part numbers differently in particular::

    Walmart : rrvtps28pkr1
    Amazon  : rr-vtps-28pk-r1

Splitting strictly on spaces and punctuation makes these look completely
unrelated, and the part number is the single most decisive piece of evidence a
product match has. Measured on the real data, 107 such identifiers in the
Walmart table are present inside the Amazon text but invisible to word-level
splitting.

The obvious fix -- delete every space and punctuation mark, then compare
overlapping character sequences -- fixes that but creates a much larger
problem. Gluing everything together also welds ordinary English words to each
other::

    "desktop computers"  ->  "desktopcomputers"

which invents sequences like ``ktopc`` and ``topco``. These look "rare" purely
because that particular collision of two common words is uncommon, and they
carry no information about what the product actually is. Measured on the real
data, **79.3% of all candidate pairs** produced this way were reachable *only*
through such welds.

So this module collapses a boundary **only when a digit sits on one side of
it**. Part numbers are alphanumeric, so their internal breaks are preserved;
boundaries between two ordinary words are not::

    "kvr400x64c3a 1g"    ->  kvr400x64c3a1g     (joined: '1' is a digit)
    "desktop computers"  ->  desktop | computers (kept apart: 'p' and 'c')

Character sequences are then taken **within** each resulting segment and never
across a boundary that was left in place, so the welds can never be formed.
"""

import re

# Splits on anything that is not a letter or a digit. Spaces, hyphens, slashes
# and dots are all treated the same way -- as a boundary whose fate is then
# decided by the digit rule below.
_WORD = re.compile(r"[a-z0-9]+")

# Length of the character sequences ("n-grams") used for comparison. Five is a
# compromise: shorter sequences appear in far too many records to distinguish
# anything, longer ones are more selective but less tolerant of small
# differences in spelling.
DEFAULT_NGRAM_SIZE = 5


def word_tokens(text: str) -> list[str]:
    """Split text into lowercase runs of letters and digits, in order.

    >>> word_tokens("RR-VTPS-28PK-R1")
    ['rr', 'vtps', '28pk', 'r1']
    """
    return _WORD.findall(str(text).lower())


def _boundary_is_collapsible(left: str, right: str) -> bool:
    """Should the gap between these two adjacent tokens be closed up?

    Yes only when a digit sits immediately on one side of the gap. That is the
    signature of a part number that has been split (``kvr400x64c3a`` + ``1g``,
    ``vtps`` + ``28pk``), and it is almost never the signature of two ordinary
    English words meeting (``desktop`` + ``computers``).

    Note this looks at the single character touching the gap, not the whole
    token -- ``28pk`` + ``r1`` is *not* joined, because 'k' and 'r' meet at the
    boundary. That is deliberate and costs us nothing in practice: the
    overlapping character sequences on either side still give the two records
    plenty of shared pieces to match on.

    The rule is not perfect in the other direction either. A plain word
    followed by a number also welds -- ``black 25 pack`` becomes
    ``black25pack`` -- because a leading digit triggers the join. That is a
    weaker version of the same problem this rule exists to solve, and it is
    accepted knowingly: the alternative (requiring digits on *both* sides)
    would discard genuine recoveries such as ``kvr400x64c3a`` + ``1g``. The
    residual is measured in docs/DECISIONS.md (D15).
    """
    return left[-1].isdigit() or right[0].isdigit()


def segments(text: str) -> list[str]:
    """Break text into the chunks that character sequences may be taken from.

    Adjacent tokens are welded into one chunk when the digit rule allows it,
    and left as separate chunks otherwise.

    >>> segments("edge 2gb 2x1gb pc25300 ecc")
    ['edge2gb2x1gb', 'pc25300ecc']
    >>> segments("desktop computers")
    ['desktop', 'computers']
    """
    tokens = word_tokens(text)
    if not tokens:
        return []

    out = [tokens[0]]
    for token in tokens[1:]:
        if _boundary_is_collapsible(out[-1], token):
            out[-1] += token          # weld onto the chunk being built
        else:
            out.append(token)         # start a new chunk
    return out


def char_ngrams(text: str, n: int = DEFAULT_NGRAM_SIZE) -> set[str]:
    """All distinct character sequences of length ``n``, taken within segments.

    Sequences are never taken across a boundary that :func:`segments` chose to
    keep, which is precisely what stops meaningless welds like ``ktopc`` from
    being created.

    A segment shorter than ``n`` yields nothing here. Such segments are short
    common words ('for', 'with', 'usb') that would be useless for blocking
    anyway, and they remain fully available to the word-token rules.
    """
    out: set[str] = set()
    for segment in segments(text):
        for i in range(len(segment) - n + 1):
            out.add(segment[i:i + n])
    return out


def legacy_collapsed(text: str) -> str:
    """The SUPERSEDED normalisation: delete every non-alphanumeric character.

    Kept only so the corrected approach can be measured against the flawed one
    it replaced. Not used by the blocking rules. See docs/DECISIONS.md (D15).
    """
    return re.sub(r"[^a-z0-9]", "", str(text).lower())
