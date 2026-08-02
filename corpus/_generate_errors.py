# SPDX-License-Identifier: Apache-2.0
"""
Produce `error_log.txt`: real Python tracebacks, actually raised.

The audit's first run had no `error` row at all, because none of the five
artefacts contained exception types — so it said nothing about Paritok's claim
that it protects error strings. Writing tracebacks by hand would have closed the
gap dishonestly: invented ones are uniform, and uniformity compresses.

These are raised for real and captured from the interpreter, so the frames, line
numbers and messages are whatever CPython actually produced.

Regenerate with:  python corpus/_generate_errors.py
"""

from __future__ import annotations

import json
import pathlib
import traceback


def _boom_index():
    rows = [{"id": i} for i in range(3)]
    return rows[7]["id"]


def _boom_key():
    cfg = {"database": {"host": "db-01.internal"}}
    return cfg["database"]["dsn"]


def _boom_type():
    timeout = "30"
    return timeout / 2


def _boom_attr():
    class Session:
        def commit(self): ...
    return Session().flush_pending()


def _boom_value():
    return int("2.0.31")


def _boom_json():
    return json.loads('{"orders": [{"id": 500,}]}')


def _boom_zero():
    hits, total = 214, 0
    return hits / total


def _boom_file():
    return pathlib.Path("app/db/session.yaml").read_text()


def _boom_unpack():
    host, port = "db-01.internal:5432:extra".split(":")
    return host, port


def _boom_recursion():
    def walk(node, depth=0):
        return walk(node, depth + 1)
    return walk({"root": True})


def _boom_import():
    import sqlalchemy_asyncpg_shim  # noqa: F401


def _boom_chained():
    try:
        _boom_key()
    except KeyError as exc:
        raise RuntimeError("failed to build session for orders-api") from exc


CASES = [
    _boom_index, _boom_key, _boom_type, _boom_attr, _boom_value, _boom_json,
    _boom_zero, _boom_file, _boom_unpack, _boom_recursion, _boom_import,
    _boom_chained,
]


def main() -> None:
    out: list[str] = []
    for i, case in enumerate(CASES, 1):
        out.append(f"[{i:02d}/{len(CASES)}] running {case.__name__} "
                   f"-- pytest tests/test_session.py::{case.__name__[1:]}")
        try:
            case()
        except BaseException:
            out.append(traceback.format_exc(limit=8).rstrip())
        else:
            out.append("  (unexpectedly passed)")
        out.append("")

    text = "\n".join(out)
    target = pathlib.Path(__file__).with_name("error_log.txt")
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target.name}: {len(text):,d} chars, "
          f"{text.count(chr(10)) + 1} lines, {len(CASES)} real tracebacks")


if __name__ == "__main__":
    main()
