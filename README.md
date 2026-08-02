<h1 align="center">paritok-audit</h1>

<p align="center"><b>Measure what context compression costs you — not just what it saves.</b></p>

<p align="center">
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue" alt="Apache 2.0"/>
  <img src="https://img.shields.io/badge/python-3.11+-blue" alt="Python 3.11+"/>
  <a href="https://github.com/Paritok-official/paritok-4b-v1"><img src="https://img.shields.io/badge/built%20on-Paritok-purple" alt="Paritok"/></a>
</p>

---

## The gap

Every context compressor reports the same number: **how much it removed**.

That number cannot answer the only question a developer actually has before
turning compression on — *what did it remove, and do I need it?*

A compressor that turns

```
File "app/db/session.py", line 214, in commit
sqlalchemy.exc.IntegrityError: duplicate key (order_id)=(0x1f4)
```

into *"a database commit failed due to a unique constraint violation"* scores a
beautiful compression ratio and has just deleted every fact the agent needed:
the file, the line, the exception type, the key. The ratio says success. The
agent then edits the wrong file.

`paritok-audit` measures the other half.

## The method: critical atoms

For each piece of context, the tool extracts the **literal substrings an agent
cannot afford to lose** — file paths, identifiers, exception types, numeric
literals, shell commands, URLs, hashes — then checks, by exact substring search,
how many survived compression.

No LLM judge. No scoring model. No rubric. Every atom is a literal substring of
the source, so retention is *decidable*, and two runs produce byte-identical
numbers.

Atoms are grouped by how expensive they are to lose:

| Category | Example | Cost of losing it |
|---|---|---|
| `path` | `app/db/session.py` | agent edits the wrong file |
| `identifier` | `self._flush_pending` | agent calls a function that doesn't exist |
| `error` | `IntegrityError`, `HTTP 409` | agent misdiagnoses the failure |
| `number` | `214`, `0x1f4`, `2.0.31` | agent patches the wrong line or version |
| `command` | `pytest tests/test_db.py -k commit` | agent can't reproduce |
| `url` | `https://api.internal/v2/orders` | agent loses the endpoint |
| `hash` | `abc1234def5678` | agent loses the revision |

Reported alongside is **recall**: Paritok's design claim is that compression is
*non-destructive* — dropped content stays recoverable from the shadow store. A
fidelity score of 60% is perfectly fine if recall works, and alarming if it
doesn't. The two must be read together; neither alone is a verdict.

## Install

```bash
git clone https://github.com/<your-handle>/paritok-audit
cd paritok-audit
pip install -e .
```

You need Paritok running locally — see
[Paritok-official/paritok-4b-v1](https://github.com/Paritok-official/paritok-4b-v1):

```bash
pip install "paritok[proxy]"
ollama pull paritok/paritok-4b-v1
ollama cp paritok/paritok-4b-v1 paritok-4b-v1
```

## Run

```bash
paritok-audit                 # audits ./corpus
paritok-audit path/to/corpus  # or your own artefacts
```

Output goes to `REPORT.txt`, with the compressed text and a TSV of every lost
atom written to `out/` so losses can be inspected by hand rather than taken on
trust.

## Corpus

Five **real** artefacts, not hand-written fixtures — a 1,244-line C++ kernel, a
live JSON API response, a project README, a dependency-resolution log, and a
genuine Python traceback. Provenance and licences: [`corpus/README.md`](corpus/README.md).

Synthetic fixtures are the easy mistake: hand-written samples are repetitive, and
repetition compresses beautifully, so a benchmark built from invented text
measures nothing.

## Results

<!-- RESULTS -->

## What this is not

- **Not a quality benchmark.** It does not claim to measure whether an agent
  still solves the task. It measures whether the facts survived, which is a
  necessary condition, not a sufficient one.
- **Not a verdict on Paritok.** High compression with low fidelity is the
  expected shape for a compressor; the point is to make that trade *visible* and
  per-category, so you can decide it deliberately.
- **Not tuned to flatter.** Atom extraction is deliberately conservative and
  matching is case-sensitive, because a lenient match would let a compressor pass
  by preserving the gist while breaking the call.

## Credits

Built for the [Build with Paritok](https://build-with-paritok.devpost.com/)
hackathon, on top of
[Paritok-official/paritok-4b-v1](https://github.com/Paritok-official/paritok-4b-v1)
— the open-source compression model for coding agents.

Apache-2.0.
