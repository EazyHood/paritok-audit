# SPDX-License-Identifier: Apache-2.0
"""
Corpus of real coding-agent traffic.

Synthetic fixtures are the easy mistake here: hand-written samples are repetitive,
so any compressor scores brilliantly on them and the measurement means nothing.
Everything below is a real artefact -- an actual source file, an actual API
response, an actual dependency-resolution log -- of the kind a coding agent
genuinely stuffs into its context.

Each sample carries the `query` an agent would plausibly have been pursuing when
it read that content, because Paritok's keep/drop decisions are query-conditioned.
Judging a compressor without giving it the intent would be judging it unfairly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Sample:
    name: str
    kind: str        # paritok's content-type hint
    query: str       # what the agent was trying to do
    text: str

    @property
    def chars(self) -> int:
        return len(self.text)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# Content-type hint by extension, for files the shipped corpus doesn't name.
# Paritok's keep/drop behaviour is conditioned on `kind`, so guessing badly is
# worse than guessing coarsely -- these are the two kinds it actually trains on.
_KIND_BY_SUFFIX = {
    ".py": "file_read", ".js": "file_read", ".ts": "file_read",
    ".tsx": "file_read", ".jsx": "file_read", ".rs": "file_read",
    ".go": "file_read", ".c": "file_read", ".h": "file_read",
    ".cpp": "file_read", ".hpp": "file_read", ".java": "file_read",
    ".rb": "file_read", ".php": "file_read", ".cs": "file_read",
    ".md": "file_read", ".rst": "file_read",
}
_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".pyc"}


def _discovered(corpus_dir: Path, already: set[str]) -> list[Sample]:
    """Pick up any other file in the directory, so bringing your own costs nothing.

    The shipped artefacts are curated -- each has the query an agent would have
    been pursuing, which matters because Paritok's decisions are query-conditioned.
    A dropped-in file has no such context, so it gets a generic query and a kind
    inferred from its extension. That is weaker, and the report says so, but it
    beats the alternative of having to edit Python to measure your own traffic.

    Put `<name>.query` next to a file to supply the real intent.
    """
    out: list[Sample] = []
    for path in sorted(corpus_dir.iterdir()):
        if not path.is_file() or path.name in already:
            continue
        if path.suffix in _SKIP_SUFFIXES or path.suffix == ".query":
            continue
        if path.name.startswith(("_", ".")) or path.name == "README.md":
            continue

        text = _read(path)
        if not text or not text.strip():
            continue

        sidecar = path.with_suffix(path.suffix + ".query")
        query = (_read(sidecar) or "").strip() or (
            f"Work with the contents of {path.name}"
        )
        kind = _KIND_BY_SUFFIX.get(path.suffix, "tool_output")
        out.append(Sample(path.stem, kind, query, text))

    return out


def load(corpus_dir: Path, discover: bool = True) -> list[Sample]:
    """Load the curated artefacts, then anything else the directory contains.

    Missing files are skipped rather than faked, so a run never silently
    substitutes invented data for the real thing.
    """
    samples: list[Sample] = []

    specs = [
        (
            "source_c++_header",
            "file_read",
            "Find why sin() loses accuracy for large arguments in this SFPU kernel",
            "trig_live.h",
        ),
        (
            "api_response_json",
            "tool_output",
            "List the audit competitions that are still open and their prize pools",
            "c4.json",
        ),
        (
            "readme_markdown",
            "file_read",
            "How do I self-host this model and point my agent at it?",
            "paritok.md",
        ),
        (
            "dependency_log",
            "tool_output",
            "Did the install succeed, and which package pulled in torch?",
            "pip_install.log",
        ),
        (
            "test_failure",
            "tool_output",
            "Fix the failing test test_commit_retries",
            "pytest_failure.txt",
        ),
        (
            "error_log",
            "tool_output",
            "Triage these 12 failures and tell me which are the same root cause",
            "error_log.txt",
        ),
    ]

    curated: set[str] = set()
    for name, kind, query, filename in specs:
        curated.add(filename)
        text = _read(corpus_dir / filename)
        if text:
            samples.append(Sample(name, kind, query, text))

    if discover and corpus_dir.is_dir():
        samples.extend(_discovered(corpus_dir, curated))

    return samples


def summarise(samples: list[Sample]) -> str:
    lines = [f"{len(samples)} samples:"]
    for s in samples:
        lines.append(f"  {s.name:22s} {s.kind:12s} {s.chars:>8,d} chars")
    return "\n".join(lines)
