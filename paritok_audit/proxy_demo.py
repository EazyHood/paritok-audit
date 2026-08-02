# SPDX-License-Identifier: Apache-2.0
"""
Drive the corpus through a running Paritok proxy so its /stats dashboard fills up.

The audit normally calls `CompressionPipeline` directly, which is the right thing
for measurement -- it isolates compression from network and upstream behaviour.
But the proxy keeps its own counters, and `/stats` is what an operator actually
looks at to decide whether Paritok is earning its keep. Those counters only move
when traffic goes through the proxy.

So this replays the same corpus as real agent requests. Each sample is wrapped as
a `tool_result` block, which is the shape Paritok is trained to compress.

No upstream API key is needed. The proxy records its statistics *before* it
forwards (`proxy_stats.record(...)` then `Forward`), so the compression is
measured and counted even when the forward itself fails for want of credentials.
The failure is expected and reported as such rather than hidden.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from .corpus import Sample, load

DEFAULT_PROXY = "http://127.0.0.1:8080"


def _post(url: str, payload: dict, timeout: float) -> tuple[int, str]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "content-type": "application/json",
            "x-api-key": "not-needed-stats-are-recorded-before-forward",
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(200).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(200).decode("utf-8", "replace")
    except Exception as e:  # connection refused, timeout, ...
        return 0, f"{type(e).__name__}: {e}"


def as_agent_request(sample: Sample) -> dict:
    """Wrap a corpus sample the way a coding agent would actually send it."""
    return {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": sample.query},
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": f"toolu_{sample.name}",
                        "name": "read_file",
                        "input": {"path": sample.name},
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": f"toolu_{sample.name}",
                        "content": sample.text,
                    }
                ],
            },
            {"role": "user", "content": sample.query},
        ],
    }


def stats(proxy: str = DEFAULT_PROXY, timeout: float = 10.0) -> dict | None:
    try:
        with urllib.request.urlopen(f"{proxy}/stats", timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def replay(
    corpus_dir: Path,
    proxy: str = DEFAULT_PROXY,
    timeout: float = 600.0,
    log=print,
) -> dict | None:
    samples = load(corpus_dir)
    if not samples:
        log(f"no corpus artefacts in {corpus_dir}/")
        return None

    if stats(proxy) is None:
        log(f"no proxy answering at {proxy} -- start it with:  paritok proxy")
        return None

    log(f"replaying {len(samples)} samples through {proxy}\n")
    for i, s in enumerate(samples, 1):
        code, body = _post(f"{proxy}/v1/messages", as_agent_request(s), timeout)
        # 4xx/5xx here means the *forward* failed (no upstream key), which is
        # expected and harmless: compression already happened and was counted.
        verdict = "compressed & counted" if code else f"unreachable ({body[:60]})"
        log(f"  [{i}/{len(samples)}] {s.name:22s} {s.chars:>8,d} chars  "
            f"upstream {code or '--'}  {verdict}")

    return stats(proxy)


def render(snapshot: dict) -> str:
    """Format the /stats payload the way the dashboard reads.

    Field names come straight from the proxy's own snapshot, so this stays a
    faithful view of the dashboard rather than a re-derivation of it.
    """
    orig = snapshot.get("input_tokens_original", 0)
    comp = snapshot.get("input_tokens_compressed", 0)

    lines = [
        "",
        "Paritok proxy /stats  (the dashboard operators actually read)",
        "-" * 58,
        f"  requests                {snapshot.get('total_requests', 0):>14,d}",
        f"  input tokens, original  {orig:>14,d}",
        f"  input tokens, forwarded {comp:>14,d}",
        f"  tokens saved            {snapshot.get('tokens_saved', 0):>14,d}",
        f"  compression ratio       {snapshot.get('compression_ratio', 0.0):>13.1%}",
    ]
    if snapshot.get("tools_filtered"):
        lines.append(f"  tool schemas stubbed    {snapshot['tools_filtered']:>14,d}")
    cost = snapshot.get("estimated_cost_saved_usd")
    if cost:
        lines.append(f"  estimated cost saved    {str(cost):>14s}")
    lines.append("-" * 58)
    return "\n".join(lines)
