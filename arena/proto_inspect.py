"""Inspect the failing region around a logical index."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

nested = set()
clause_of = {748: 738, 1138: 1134}

levels = indenter.run(nested, clause_of)
text = rp.render(lines, levels)
err = rp.check_syntax(text)
print("err:", err)

for idx in range(730, 760):
    ll = lines[idx]
    head = ll.head if ll.is_code else "#comment"
    print(f"{idx:5d} L{levels[idx]:2d} {head:12s} {ll.texts[0][:70]}")

print("-" * 60)
for idx in range(1125, 1150):
    ll = lines[idx]
    head = ll.head if ll.is_code else "#comment"
    print(f"{idx:5d} L{levels[idx]:2d} {head:12s} {ll.texts[0][:70]}")
