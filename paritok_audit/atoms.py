# SPDX-License-Identifier: Apache-2.0
"""
Critical atoms: the substrings a coding agent cannot afford to lose.

Compression benchmarks report how *much* was removed. That is half a metric.
The half that decides whether you can turn compression on is: *what* was removed.

An agent reading `File "app/db.py", line 214, in commit` needs `app/db.py`, `214`
and `commit` to survive verbatim. Prose around them is padding. This module pulls
those load-bearing substrings out of a context blob so retention can be measured
exactly -- no LLM judge, no scoring model, no subjective rubric.

Every atom is a literal substring of the source. Retention is therefore decidable
by exact search, and the result is reproducible byte-for-byte.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable


# --- categories -------------------------------------------------------------
# Ordered by how expensive it is for an agent to lose one. A dropped file path
# sends it editing the wrong file; a dropped prose adjective costs nothing.

PATH = "path"
IDENTIFIER = "identifier"
ERROR = "error"
NUMBER = "number"
COMMAND = "command"
URL = "url"
HASH = "hash"

CATEGORIES = (PATH, IDENTIFIER, ERROR, NUMBER, COMMAND, URL, HASH)


@dataclass(frozen=True)
class Atom:
    """A literal substring that must survive compression."""

    text: str
    category: str

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"{self.category}:{self.text}"


# --- patterns ---------------------------------------------------------------
# Deliberately conservative. A false positive inflates the denominator and makes
# the tool look harsher than reality; we would rather under-claim than over-claim.

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # posix and windows paths with a real extension, or dotted module paths
    (PATH, re.compile(r"(?:[A-Za-z]:)?[\w.\-/\\]*[\w\-]+\.(?:py|js|ts|tsx|jsx|rs|go|c|h|cpp|hpp|java|rb|php|sh|yaml|yml|toml|json|md|sql|txt|cfg|ini)\b")),
    # urls
    (URL, re.compile(r"https?://[^\s\"'`<>)\]]+")),
    # git sha / long hex blobs
    (HASH, re.compile(r"\b[0-9a-f]{7,40}\b")),
    # python/js exception and error type names
    (ERROR, re.compile(r"\b(?:[A-Z][A-Za-z0-9]*(?:Error|Exception|Warning|Fault|Panic))\b")),
    # errno-style and http-style codes
    (ERROR, re.compile(r"\b(?:E[A-Z]{3,}|HTTP\s?[45]\d{2}|exit(?:\s+code)?\s+\d+)\b")),
    # shell invocations at line start
    (COMMAND, re.compile(r"(?m)^\s*(?:\$|>|#)\s*([a-z][\w\-]*(?:\s+[^\n|;&]{0,60})?)")),
    # dotted or qualified identifiers, and snake/camel names with an underscore
    (IDENTIFIER, re.compile(r"\b(?:[A-Za-z_][\w]*\.)+[A-Za-z_][\w]*\b")),
    (IDENTIFIER, re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")),
    (IDENTIFIER, re.compile(r"\b[a-z]+(?:[A-Z][a-z0-9]+)+\b")),
    # numeric literals worth keeping: line numbers, sizes, versions, hex
    (NUMBER, re.compile(r"\b0x[0-9a-fA-F]+\b")),
    (NUMBER, re.compile(r"\b\d+(?:\.\d+){1,3}\b")),          # versions
    (NUMBER, re.compile(r"(?:line|:)\s*(\d{1,6})\b")),
)

# Words that match the identifier patterns but carry no information for an agent.
# Keeping them would let a compressor score well by preserving filler.
_STOP = frozenset(
    """
    e.g i.e etc vs os.path self.assert this.state true false null none
    """.split()
)

_MIN_LEN = 3


def _clean(raw: str, category: str) -> str | None:
    text = raw.strip().strip("\"'`,;:()[]{}")
    if len(text) < _MIN_LEN:
        return None
    if text.lower() in _STOP:
        return None
    # a bare small integer is noise; line numbers arrive via the `line N` pattern
    if category == NUMBER and text.isdigit() and len(text) < 2:
        return None
    return text


def extract(text: str) -> list[Atom]:
    """Pull every critical atom out of `text`, de-duplicated, order preserved.

    The same substring can match several patterns (`app/db.py` is both a path and
    a dotted identifier). First match wins, using the category order above, so a
    path is never double-counted as an identifier.
    """
    if not text:
        return []

    seen: set[str] = set()
    out: list[Atom] = []
    # Paths and URLs are matched first and swallow their own tails: once
    # `app/db/session.py` is an atom, counting `session.py` again would inflate
    # the denominator and flatter any compressor that keeps the full path.
    containers: list[str] = []

    for category, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            raw = m.group(m.lastindex or 0)
            cleaned = _clean(raw, category)
            if cleaned is None or cleaned in seen:
                continue
            if category not in (PATH, URL) and any(cleaned in c for c in containers):
                continue
            seen.add(cleaned)
            if category in (PATH, URL):
                containers.append(cleaned)
            out.append(Atom(cleaned, category))

    return out


# --- retention --------------------------------------------------------------


@dataclass
class Retention:
    """How many critical atoms survived, overall and per category."""

    kept: list[Atom] = field(default_factory=list)
    lost: list[Atom] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.kept) + len(self.lost)

    @property
    def rate(self) -> float:
        return len(self.kept) / self.total if self.total else 1.0

    def by_category(self) -> dict[str, tuple[int, int]]:
        """category -> (kept, total)"""
        kept = Counter(a.category for a in self.kept)
        lost = Counter(a.category for a in self.lost)
        return {
            c: (kept[c], kept[c] + lost[c])
            for c in CATEGORIES
            if kept[c] + lost[c] > 0
        }

    def worst_losses(self, n: int = 10) -> list[Atom]:
        """Lost atoms, most damaging category first."""
        order = {c: i for i, c in enumerate(CATEGORIES)}
        return sorted(self.lost, key=lambda a: order.get(a.category, 99))[:n]


def measure(original: str, compressed: str, atoms: Iterable[Atom] | None = None) -> Retention:
    """Check which of `original`'s critical atoms still appear in `compressed`.

    Exact substring search, case-sensitive: an agent that reads `getUserId` cannot
    use `getuserid`. Being strict here is the whole point -- a lenient match would
    let a compressor pass by preserving the gist while breaking the call.
    """
    atoms = list(atoms) if atoms is not None else extract(original)
    result = Retention()
    for atom in atoms:
        (result.kept if atom.text in compressed else result.lost).append(atom)
    return result
