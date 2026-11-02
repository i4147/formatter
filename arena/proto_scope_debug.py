"""Run the formatter with the scope-pass debugger switched on."""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/user/formatter")

import reformat_python as rp

rp._DEBUG = []

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()

try:
    result = rp.reformat(source)
    print("OK, length", len(result))
except Exception as exc:  # noqa: BLE001
    print("EXCEPTION:", type(exc).__name__, exc)

print("breakage points:", len(rp._DEBUG))
for item in rp._DEBUG[:5]:
    print("  ", item)
