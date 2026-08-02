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
the source, so retention is *decidable*: given a compressed output, the score is
a search, not an opinion.

The compressor itself is not deterministic, so the numbers do move between runs —
measured, the C++ sample scored 47.8% and 42.8% on two consecutive runs. Treat
single-run figures as a few points wide. What does not move is the *method*: rerun
it and you get a number you can argue with, not a vibe.

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
git clone https://github.com/EazyHood/paritok-audit
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

**Bring your own traffic.** Drop any file into the corpus directory and it is picked
up on the next run — content type inferred from the extension, no code to edit:

```bash
cp ~/work/failing-build.log corpus/
echo "Find which dependency pulled in torch" > corpus/failing-build.log.query
paritok-audit
```

The sidecar `.query` matters more than it looks: Paritok's keep/drop decisions are
conditioned on what the agent was trying to do, so measuring without the intent
measures it unfairly.

Output goes to `REPORT.txt`, with the compressed text and a TSV of every lost
atom written to `out/` so losses can be inspected by hand rather than taken on
trust.

### Through the proxy

The audit calls `CompressionPipeline` directly, which is right for measurement —
it isolates compression from network and upstream behaviour. But operators read
the proxy's `/stats` dashboard, and those counters only move for traffic that
goes through the proxy. To fill it with the same corpus:

```bash
paritok proxy                  # terminal 1
paritok-audit --via-proxy      # terminal 2
```

```
  requests                             4
  input tokens, original          27,431
  input tokens, forwarded          5,614
  tokens saved                    21,817
  compression ratio               20.5%
  estimated cost saved             $0.05
```

No upstream API key is needed: the proxy records its statistics *before* it
forwards, so compression is measured and counted even when the forward itself is
rejected for want of credentials.

That detail also produced the sharpest evidence in this repo. Four samples came
back `401` — forward rejected, compression fine. One came back **`500`**: it
never reached the forward at all. That is the bug below, and it means a live
agent session gets a 500, not just a library caller getting an exception.

## Corpus

Five **real** artefacts, not hand-written fixtures — a 1,244-line C++ kernel, a
live JSON API response, a project README, a dependency-resolution log, and a
genuine Python traceback. Provenance and licences: [`corpus/README.md`](corpus/README.md).

Synthetic fixtures are the easy mistake: hand-written samples are repetitive, and
repetition compresses beautifully, so a benchmark built from invented text
measures nothing.

## Results

Run on the corpus below, Paritok `1.2.8`, `paritok-4b-v1` q4 via Ollama, `num_ctx=8192`.

| sample | tokens in | out | saved | fidelity | recall |
|---|---:|---:|---:|---:|:--:|
| `source_c++_header` | 16,360 | 4,906 | 70.0% | 42.8% | exact |
| `readme_markdown` | 7,873 | 863 | 89.0% | 15.3% | exact |
| `dependency_log` | 3,045 | 75 | 97.5% | 4.5% | exact |
| `error_log` | 2,073 | 414 | 80.0% | 54.9% | exact |
| `test_failure` | 153 | 153 | 0.0% | — | passthrough |
| **total** | **29,504** | **6,411** | **78.3%** | | |

**The savings claim holds.** 78.3% against a stated ~74% on typical workloads, on
traffic Paritok has never seen.

**Recall holds, and it is the finding that matters.** The shadow store returned
the byte-exact original for every compressed sample. Fidelity of 15% would be
alarming for a lossy compressor; for a *non-destructive* one it is the design
working as advertised. Read the two columns together or you will draw the wrong
conclusion from either.

### Fidelity by atom category

What survives, when something has to go:

| category | kept | rate | |
|---|---|---:|---|
| `error` | 10/11 | **90.9%** | `███████████████████████████` |
| `identifier` | 72/166 | 43.4% | `█████████████` |
| `hash` | 19/59 | 32.2% | `██████████` |
| `path` | 9/38 | 23.7% | `███████` |
| `url` | 5/24 | 20.8% | `██████` |
| `number` | 18/137 | 13.1% | `████` |
| `command` | 2/16 | 12.5% | `████` |

**The error-string claim checks out.** Paritok's README says the model protects
error strings; on a log of 12 real tracebacks it kept 10 of 11 exception types at
80% compression. The one it dropped was a `RuntimeError` wrapper whose underlying
`KeyError` survived — so the root cause came through. That is the single clearest
"working as designed" result in this repo, and it is worth stating as loudly as
the failures.

**Numeric literals and commands are the weak end**, at 13.1% and 12.5%. For a
coding agent, numbers are line numbers, versions, sizes and error codes —
`line 214`, `2.0.31`, `0x1f4` — and commands are how it reproduces a failure at
all. Both are among the cheapest tokens to keep and the most expensive to lose,
which makes them the most promising place to spend the next few points of budget.

Two caveats that bound all of the above:

- **Fidelity is not solve quality.** Surviving facts are necessary for an agent to
  act correctly, not sufficient. This measures a precondition, not an outcome.
- **Low fidelity is not a defect when recall is exact.** It is the trade being
  made. The point of the tool is to make that trade visible per category, not to
  score it.

### A bug this found

`api_response_json` — a 25,279-char single-line API response — did not compress.
It raised `httpx.HTTPStatusError: 400 Bad Request`.

The cause is line length, not size. The same JSON re-indented is *larger*
(33 KB) and compresses fine; a 46 KB C++ header with 1,244 newlines is fine too.
`_token_split_block` only ever cuts *between* lines, so a single line above
`CHUNK_SIZE` passes through whole and overflows the model context — bypassing the
boundary-less guard that exists specifically to prevent it.

Fixed and sent upstream: [Paritok-official/paritok-4b-v1#15](https://github.com/Paritok-official/paritok-4b-v1/pull/15).
After the fix the same input compresses 7,773 → 609 tokens (92.2%).

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
