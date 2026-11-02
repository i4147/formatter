"""Debug the chain-continuation scanner."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

for idx in (738, 740, 742, 750):
    print(idx, lines[idx].head, "continued =", indenter._chain_is_continued(idx))

# Manual trace of the scanner for 738
stack = []
for j in range(738, 770):
    ll = lines[j]
    if not ll.is_code:
        continue
    head = ll.head
    print(f"  j={j} head={head!r} opens={ll.opens_block} inline={ll.inline_suite} stack={stack}")
