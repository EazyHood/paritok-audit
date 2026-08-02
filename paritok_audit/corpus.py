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


def load(corpus_dir: Path) -> list[Sample]:
    """Load whatever real artefacts are present in `corpus_dir`.

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
    ]

    for name, kind, query, filename in specs:
        text = _read(corpus_dir / filename)
        if text:
            samples.append(Sample(name, kind, query, text))

    return samples


def summarise(samples: list[Sample]) -> str:
    lines = [f"{len(samples)} samples:"]
    for s in samples:
        lines.append(f"  {s.name:22s} {s.kind:12s} {s.chars:>8,d} chars")
    return "\n".join(lines)
