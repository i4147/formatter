"""Check every clause candidate for the elif at 748."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

for cand in rp._clause_candidates(lines, indenter, 748):
    clause_of = {748: cand}
    levels = indenter.run(set(), clause_of)
    ok = rp._region_parses(lines, levels, cand, 748)
    print(f"candidate {cand:5d} head={lines[cand].head!r:10s} parses={ok}")
