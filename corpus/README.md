# Corpus — provenance

Every file here is a **real artefact**, not a hand-written fixture.

That distinction is the whole point. Synthetic samples are repetitive, and a
compressor scores brilliantly on repetition, so a benchmark built from invented
text measures nothing. These are the actual things a coding agent ends up holding
in context: a source file it read, an API response it fetched, a build log it
triggered, a traceback it caused.

| File | What it is | Where it came from | Licence |
|---|---|---|---|
| `trig_live.h` | 1,244-line C++ SFPU kernel — the `file_read` case, and deliberately the hardest one: dense identifiers, hex float literals, almost no filler | [tenstorrent/tt-metal](https://github.com/tenstorrent/tt-metal), `tt_metal/hw/ckernels/wormhole_b0/metal/llk_api/llk_sfpu/ckernel_sfpu_trigonometry.h` | Apache-2.0 |
| `paritok.md` | Project README — prose-heavy markdown, the easy end of the range | [Paritok-official/paritok-4b-v1](https://github.com/Paritok-official/paritok-4b-v1) | Apache-2.0 |
| `c4.json` | Live API response, 25 records of nested JSON — structure-heavy, low prose | `https://code4rena.com/api/v1/audits`, fetched 2026-08-01 | public endpoint |
| `pip_install.log` | Real dependency-resolution output from `pip install --dry-run --upgrade "paritok[proxy]"` | generated on the audit machine | — |
| `pytest_failure.txt` | A genuine Python traceback, produced by actually running a script that fails — not transcribed from memory | generated on the audit machine | — |

## Why these five

They span the axis that matters for a compressor: **information density**.

- `paritok.md` is mostly prose. A good compressor should cut it hard.
- `trig_live.h` is nearly all load-bearing tokens. Cutting it hard should be *impossible*
  without losing something an agent needs — so it is the sample that separates a
  compressor that understands code from one that just summarises.
- `c4.json` sits in between, and tests whether structure survives.
- `pytest_failure.txt` is small on purpose: it lands under Paritok's minimum-size
  gate and documents the passthrough path.

## Adding your own

Drop a file in this directory and register it in `paritok_audit/corpus.py` with the
`query` an agent would have been pursuing when it read that content. Paritok's
keep/drop decisions are query-conditioned, so measuring without the intent would
be measuring it unfairly.

Do **not** add private session logs. The audit reads whatever is here, and this
directory is published.
