"""Inspect a logical-line region with a given set of overrides."""
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
if err:
    lineno = err.lineno
    # map physical -> logical
    for index, ll in enumerate(lines):
        if lineno in ll.physical:
            print("failing logical index:", index, ll.head, ll.texts[0][:70])
            lo, hi = index - 15, index + 15
            break
    else:
        lo, hi = 2260, 2300
else:
    lo, hi = 2260, 2300

for idx in range(max(0, lo), min(len(lines), hi)):
    ll = lines[idx]
    head = ll.head if ll.is_code else "#comment"
    print(f"{idx:5d} L{levels[idx]:2d} {head:12s} {ll.texts[0][:70]}")
