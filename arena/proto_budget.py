"""Measure how long the phases of the formatter take."""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "/home/user/formatter")

import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()

counter = {"analyse": 0, "syntax": 0}
original_check = rp.check_syntax


def counted(text):
    counter["syntax"] += 1
    return original_check(text)


rp.check_syntax = counted

start = time.time()
try:
    result = rp.reformat(source)
    print("OK, length", len(result))
except Exception as exc:  # noqa: BLE001
    print("EXCEPTION:", type(exc).__name__, exc)

print(f"time {time.time() - start:.1f}s")
print("syntax checks:", counter["syntax"])
