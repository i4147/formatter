"""Inspect the try at logical 3109 and its surroundings."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

print("clauses after 3109:", rp._clauses_after(lines, indenter, 3109))
print()
for i in range(3100, 3135):
    ll = lines[i]
    head = ll.head if ll.is_code else "#"
    print(f"{i:5d} {head:10s} {ll.texts[0][:70]}")
