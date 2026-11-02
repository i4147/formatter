"""Trace the search states: print nested/clause_of at every check."""
import sys
import time

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

original = rp.reformat
state = {"n": 0}


def patched_check(source):
    error = rp.check_syntax.__wrapped__(source) if hasattr(rp.check_syntax, "__wrapped__") else None
    return error


# Patch Indenter.run to record the state.
orig_run = rp.Indenter.run
records = []


def traced_run(self, nested=None, clause_of=None):
    levels = orig_run(self, nested, clause_of)
    records.append((len(nested or ()), len(clause_of or {}), max(levels)))
    return levels


rp.Indenter.run = traced_run

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
t0 = time.time()
try:
    rp.reformat(source)
    print("SUCCESS")
except rp.ReformatError as exc:
    print("FAILED:", exc)
print("runs:", len(records), "t=%.1fs" % (time.time() - t0))
print("last 30 (nested, clauses, maxlevel):")
for r in records[-30:]:
    print("  ", r)
