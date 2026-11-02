"""How many decisions are near the failing index?"""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)
levels = indenter.run(set(), {})

for window in (10, 20, 40, 80):
    near = [d for d in indenter.decisions if 1629 - window <= d <= 1629]
    print(f"window {window}: {len(near)} decisions -> {near}")

print()
print("decisions near 1629 (40):")
for d in indenter.decisions:
    if 1589 <= d <= 1629:
        print(f"  {d} head={lines[d].head!r} :: {lines[d].texts[0][:55]}")
