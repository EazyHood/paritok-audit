# SPDX-License-Identifier: Apache-2.0
"""Command line: `paritok-audit [corpus_dir]`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import corpus, harness


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="paritok-audit",
        description="Measure what Paritok's compression costs you, not just what it saves.",
    )
    ap.add_argument(
        "corpus_dir",
        nargs="?",
        default="corpus",
        type=Path,
        help="directory of real agent-traffic artefacts (default: ./corpus)",
    )
    ap.add_argument("-o", "--out", type=Path, default=Path("REPORT.txt"))
    ap.add_argument(
        "--quiet", action="store_true", help="only print the final report"
    )
    ap.add_argument(
        "--via-proxy",
        nargs="?",
        const="http://127.0.0.1:8080",
        metavar="URL",
        help="replay the corpus through a running Paritok proxy and show its "
             "/stats dashboard instead of measuring fidelity directly "
             "(start one with: paritok proxy)",
    )
    ap.add_argument(
        "--only",
        action="append",
        metavar="NAME",
        help="audit just these samples by name; repeatable. Useful for a quick "
             "pass -- the full corpus takes minutes because the C++ header alone "
             "is 16k tokens",
    )
    ap.add_argument(
        "--levels",
        action="store_true",
        help="sweep SEG levels L0-L3 on each sample and print the savings/fidelity "
             "curve, instead of auditing once at the default level",
    )
    args = ap.parse_args(argv)

    if args.via_proxy:
        from . import proxy_demo

        snapshot = proxy_demo.replay(args.corpus_dir, args.via_proxy)
        if snapshot is None:
            return 1
        print(proxy_demo.render(snapshot))
        return 0

    samples = corpus.load(args.corpus_dir)
    if args.only:
        wanted = set(args.only)
        unknown = wanted - {s.name for s in samples}
        if unknown:
            print(f"unknown sample(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            print(f"available: {', '.join(s.name for s in samples)}", file=sys.stderr)
            return 1
        samples = [s for s in samples if s.name in wanted]
    if not samples:
        print(
            f"no corpus artefacts found in {args.corpus_dir}/ -- see corpus/README.md",
            file=sys.stderr,
        )
        return 1

    log = (lambda *a, **k: None) if args.quiet else print
    if not args.quiet:
        print(corpus.summarise(samples), end="\n\n")

    try:
        from paritok import CompressionPipeline, ParitokConfig, build_shadow_storage
    except ImportError:
        print("paritok is not installed: pip install 'paritok[proxy]'", file=sys.stderr)
        return 2

    cfg = ParitokConfig.load()
    try:
        storage = build_shadow_storage(cfg)
    except Exception:
        storage = None
    pipeline = CompressionPipeline(cfg, storage) if storage else CompressionPipeline(cfg)

    if args.levels:
        from . import levels

        chunks: list[str] = []
        for sample in samples:
            log(f"{sample.name}  ({sample.chars:,d} chars)")
            points = levels.sweep(sample, pipeline, log=log)
            chunks.append(levels.render(sample.name, points))
        text = "\n".join(chunks)
        print(text)
        args.out.write_text(text, encoding="utf-8")
        return 0

    result = harness.run(samples, pipeline, storage, log=log)
    text = harness.report(result)
    print("\n" + text)
    args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
