# SPDX-License-Identifier: Apache-2.0
"""
The savings/fidelity curve across SEG levels.

Paritok exposes four compression levels, L0 through L3, and ships L1 as the
default. What it does not tell you is what the other three cost -- the model card
reports one operating point, not a curve.

That is the question anyone deciding to turn compression on actually has: not
"how good is L1" but "which level should I run, and what do I give up moving one
notch". Savings alone can't answer it, because savings always improve as you
compress harder. You need both axes.

This measures both, on the same input, one level at a time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .atoms import measure
from .corpus import Sample

LEVELS = ("L0", "L1", "L2", "L3")
DEFAULT_LEVEL = "L1"


@dataclass
class Point:
    level: str
    original_tokens: int
    compressed_tokens: int
    ratio: float
    fidelity: float
    seconds: float
    kept: int
    total: int

    @property
    def is_default(self) -> bool:
        return self.level == DEFAULT_LEVEL


def sweep(sample: Sample, pipeline, log=print) -> list[Point]:
    points: list[Point] = []
    for level in LEVELS:
        t0 = time.time()
        try:
            res = pipeline.compress(
                sample.text, query=sample.query, kind=sample.kind, level=level
            )
        except Exception as exc:
            log(f"    {level}: FAILED {type(exc).__name__}: {str(exc)[:70]}")
            continue
        dt = time.time() - t0

        compressed = getattr(res, "compressed", "") or ""
        ret = measure(sample.text, compressed)
        point = Point(
            level=level,
            original_tokens=getattr(res, "original_tokens", 0) or 0,
            compressed_tokens=getattr(res, "compressed_tokens", 0) or 0,
            ratio=getattr(res, "ratio", 0.0) or 0.0,
            fidelity=ret.rate,
            seconds=dt,
            kept=len(ret.kept),
            total=ret.total,
        )
        points.append(point)
        log(
            f"    {level}{' (default)' if point.is_default else '':<10} "
            f"{point.original_tokens:>6,d} -> {point.compressed_tokens:>5,d} tok  "
            f"saved {point.ratio:5.1%}   fidelity {point.fidelity:6.1%}   {dt:5.1f}s"
        )
    return points


def render(sample_name: str, points: list[Point]) -> str:
    if not points:
        return f"{sample_name}: no levels completed\n"

    lines = [
        "",
        f"Savings vs fidelity by SEG level -- {sample_name}",
        "-" * 72,
        f"{'level':>7}  {'tokens out':>10}  {'saved':>7}  {'fidelity':>9}  {'atoms kept':>11}",
        "-" * 72,
    ]
    for p in points:
        mark = "  <- default" if p.is_default else ""
        lines.append(
            f"{p.level:>7}  {p.compressed_tokens:>10,d}  {p.ratio:>6.1%}  "
            f"{p.fidelity:>8.1%}  {p.kept:>5,d}/{p.total:<5,d}{mark}"
        )
    lines.append("-" * 72)

    # The comparison that decides the setting: what one notch actually buys.
    for a, b in zip(points, points[1:]):
        d_saved = b.ratio - a.ratio
        d_fid = b.fidelity - a.fidelity
        lines.append(
            f"  {a.level} -> {b.level}:  {d_saved:+.1%} tokens saved  "
            f"for {d_fid:+.1%} fidelity"
        )
    lines.append("")
    return "\n".join(lines)
