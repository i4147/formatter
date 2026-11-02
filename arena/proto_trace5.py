"""Trace the current search strategy by monkey-patching reformat_python.

The trace prints the sequence of failures the search runs into, so that
the point where it gets stuck is visible.
"""
import sys
import time

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

original_check = rp.check_syntax
seen = []


def traced_check(source):
    error = original_check(source)
    seen.append(error)
    return error


rp.check_syntax = traced_check

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
t0 = time.time()
try:
    result = rp.reformat(source)
    print("SUCCESS")
except rp.ReformatError as exc:
    print("FAILED:", exc)

print("checks:", len(seen), "t=%.1fs" % (time.time() - t0))
for err in seen[-6:]:
    print("  ", err)
