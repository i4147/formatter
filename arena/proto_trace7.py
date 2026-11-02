"""Trace the search: print the failure sequence with the move applied."""
import sys
import time

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

orig_run = rp.Indenter.run
records = []


def traced_run(self, nested=None, clause_of=None):
    levels = orig_run(self, nested, clause_of)
    records.append((sorted(nested or ()), dict(clause_of or {}), max(levels)))
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
for r in records[-8:]:
    print("  nested=%s clauses=%s max=%s" % (r[0], r[1], r[2]))
