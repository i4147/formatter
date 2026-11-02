"""Trace the scope pass: record every layout that fails to parse."""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/user/formatter")

import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()

failures: list = []
original = rp.check_syntax


def traced(text):
    error = original(text)
    if error is not None:
        # Keep the error and a few lines around it -- keeping the whole
        # text would use far too much memory.
        lines = text.splitlines()
        start = max(0, (error.lineno or 1) - 3)
        failures.append((error, lines[start : start + 6]))
    return error


rp.check_syntax = traced

try:
    result = rp.reformat(source)
    print("OK, length", len(result))
except Exception as exc:  # noqa: BLE001
    print("EXCEPTION:", type(exc).__name__, exc)

print("layouts that did not parse:", len(failures))
for error, context in failures[:3]:
    print("  ", error)
    for line in context:
        print(f"    {line!r}")
