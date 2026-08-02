# SPDX-License-Identifier: Apache-2.0
"""Entry point: audit Paritok on the real-traffic corpus."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from paritok import CompressionPipeline, ParitokConfig, build_shadow_storage
from paritok_audit import corpus, harness

ROOT = Path(__file__).parent


def main() -> int:
    samples = corpus.load(ROOT / "corpus")
    if not samples:
        print("no corpus found -- see corpus/README.md", file=sys.stderr)
        return 1
    print(corpus.summarise(samples))
    print()

    cfg = ParitokConfig.load()
    try:
        storage = build_shadow_storage(cfg)
    except Exception:
        storage = None

    pipeline = CompressionPipeline(cfg, storage) if storage else CompressionPipeline(cfg)

    result = harness.run(samples, pipeline, storage)
    print()
    text = harness.report(result)
    print(text)
    (ROOT / "REPORT.txt").write_text(text, encoding="utf-8")

    # keep the compressed outputs so losses can be inspected by hand
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    for o in result.outcomes:
        (out / f"{o.sample.name}.compressed.txt").write_text(o.compressed, encoding="utf-8")
        if o.retention.lost:
            lost = "\n".join(f"{a.category}\t{a.text}" for a in o.retention.lost)
            (out / f"{o.sample.name}.lost.tsv").write_text(lost, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
