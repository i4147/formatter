"""Show where the indentation explodes."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)
levels = indenter.run(set(), {})

prev = 0
for i, lv in enumerate(levels):
    if lv > prev + 1:
        print(f"jump at {i}: {prev} -> {lv}  head={lines[i].head!r} :: {lines[i].texts[0][:60]}")
    prev = lv
print("max", max(levels))
print("--- continued flags near the problem ---")
for i in (1617, 1621, 1619, 1612, 1614):
    print(i, lines[i].head, indenter._chain_is_continued(i))
