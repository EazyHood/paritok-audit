# SPDX-License-Identifier: Apache-2.0
"""
Run real agent traffic through Paritok and record both halves of the trade:
what it saved, and what it cost.

Three things are measured per sample:

  savings    tokens in vs tokens out -- the number everyone already reports
  fidelity   fraction of critical atoms still present verbatim
  recall     whether the shadow store really can hand back the exact original

The third matters most. Paritok's design claim is that compression is
*non-destructive*: dropped content is recoverable on demand. A fidelity score
of 60% is fine if recall works, and alarming if it doesn't -- so the two must be
read together, and neither alone is a verdict.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .atoms import Retention, measure
from .corpus import Sample


@dataclass
class Outcome:
    sample: Sample
    original_tokens: int
    compressed_tokens: int
    ratio: float
    seconds: float
    retention: Retention
    compressed: str
    recall_exact: bool | None = None      # None = not attempted
    note: str = ""

    @property
    def compressed_pct(self) -> float:
        if not self.original_tokens:
            return 1.0
        return self.compressed_tokens / self.original_tokens

    @property
    def passthrough(self) -> bool:
        """Paritok returned the input untouched."""
        return self.ratio == 0.0 and self.compressed == self.sample.text


@dataclass
class Run:
    outcomes: list[Outcome] = field(default_factory=list)

    def totals(self) -> tuple[int, int]:
        return (
            sum(o.original_tokens for o in self.outcomes),
            sum(o.compressed_tokens for o in self.outcomes),
        )


def _try_recall(storage, shadow_id: str | None, original: str) -> bool | None:
    """Ask the shadow store for the original back, if the API allows it.

    Returns None when no recall path is available rather than guessing, so a
    missing feature is never reported as a failed one.
    """
    if not shadow_id or storage is None:
        return None
    for method in ("get", "fetch", "load", "expand", "retrieve"):
        fn = getattr(storage, method, None)
        if not callable(fn):
            continue
        try:
            got = fn(shadow_id)
        except Exception:
            continue
        if isinstance(got, str):
            return got == original
        if isinstance(got, dict):
            for key in ("content", "original", "text"):
                if isinstance(got.get(key), str):
                    return got[key] == original
    return None


def run(samples: list[Sample], pipeline, storage=None, log=print) -> Run:
    result = Run()

    for i, s in enumerate(samples, 1):
        log(f"[{i}/{len(samples)}] {s.name}  ({s.chars:,d} chars) ...")
        t0 = time.time()
        try:
            res = pipeline.compress(s.text, query=s.query, kind=s.kind)
        except Exception as exc:                       # keep the run alive
            log(f"    FAILED: {type(exc).__name__}: {exc}")
            continue
        dt = time.time() - t0

        compressed = getattr(res, "compressed", "") or ""
        ret = measure(s.text, compressed)
        outcome = Outcome(
            sample=s,
            original_tokens=getattr(res, "original_tokens", 0) or 0,
            compressed_tokens=getattr(res, "compressed_tokens", 0) or 0,
            ratio=getattr(res, "ratio", 0.0) or 0.0,
            seconds=dt,
            retention=ret,
            compressed=compressed,
            recall_exact=_try_recall(storage, getattr(res, "shadow_id", None), s.text),
        )
        if outcome.passthrough:
            outcome.note = "passthrough: returned unchanged, no reason given"

        result.outcomes.append(outcome)
        log(
            f"    {outcome.original_tokens:>6,d} -> {outcome.compressed_tokens:>5,d} tok"
            f"   ratio {outcome.ratio:5.1%}"
            f"   fidelity {ret.rate:6.1%} ({len(ret.kept)}/{ret.total})"
            f"   {dt:5.1f}s"
            + (f"   [{outcome.note}]" if outcome.note else "")
        )

    return result


def report(result: Run) -> str:
    """Human-readable summary; this is what goes in the README and the writeup."""
    lines: list[str] = []
    orig, comp = result.totals()

    lines.append("=" * 78)
    lines.append("PARITOK AUDIT -- savings vs fidelity on real agent traffic")
    lines.append("=" * 78)
    lines.append("")
    lines.append(f"{'sample':24s} {'tokens in':>10s} {'out':>7s} {'saved':>7s} {'fidelity':>9s} {'recall':>8s}")
    lines.append("-" * 78)

    for o in result.outcomes:
        recall = {True: "exact", False: "MISMATCH", None: "n/a"}[o.recall_exact]
        lines.append(
            f"{o.sample.name:24s} {o.original_tokens:>10,d} {o.compressed_tokens:>7,d} "
            f"{o.ratio:>6.1%} {o.retention.rate:>9.1%} {recall:>8s}"
        )

    lines.append("-" * 78)
    saved = 1 - (comp / orig) if orig else 0.0
    lines.append(f"{'TOTAL':24s} {orig:>10,d} {comp:>7,d} {saved:>6.1%}")
    lines.append("")

    # per-category fidelity, aggregated -- this is where the interesting damage shows
    agg: dict[str, list[int]] = {}
    for o in result.outcomes:
        if o.passthrough:
            continue                                    # uncompressed proves nothing
        for cat, (kept, total) in o.retention.by_category().items():
            slot = agg.setdefault(cat, [0, 0])
            slot[0] += kept
            slot[1] += total

    if agg:
        lines.append("Fidelity by atom category (compressed samples only)")
        lines.append("-" * 78)
        for cat, (kept, total) in sorted(agg.items(), key=lambda kv: kv[1][0] / kv[1][1]):
            rate = kept / total
            bar = "#" * int(round(30 * rate))
            lines.append(f"  {cat:12s} {kept:>5,d}/{total:<6,d} {rate:6.1%}  {bar}")
        lines.append("")

    notes = [o for o in result.outcomes if o.note]
    if notes:
        lines.append("Notes")
        lines.append("-" * 78)
        for o in notes:
            lines.append(f"  {o.sample.name}: {o.note}")
        lines.append("")

    return "\n".join(lines)
