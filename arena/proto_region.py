"""Check the region parse for the rectangle elif."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

print("clause candidates for 748:",
      rp._clause_candidates(lines, indenter, 748)[:10])

clause_of = {748: 738}
levels = indenter.run(set(), clause_of)
print("region 738..748 parses:", rp._region_parses(lines, levels, 738, 748))

region = rp._region(lines, levels, 738, 748)
print("---- region 738..748 ----")
print(region)
try:
    compile(region, "<r>", "exec")
    print("OK")
except SyntaxError as e:
    print("SyntaxError:", e)
    print("---- region 738..756 ----")
    print(rp._region(lines, levels, 738, 756))
