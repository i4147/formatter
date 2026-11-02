"""Map physical line numbers around the error to logical lines."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
raw = source.splitlines()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

levels = indenter.run(set(), {748: 738, 1138: 1134})
text = rp.render(lines, levels)
err = rp.check_syntax(text)
print("err:", err)

print("--- physical 2960-2985 of broken.py ---")
for n in range(2960, 2986):
    print(f"{n:5d}: {raw[n-1][:80]}")

print("--- logical lines containing physical 2960-2985 ---")
for index, ll in enumerate(lines):
    if any(2960 <= p <= 2985 for p in ll.physical):
        print(f"{index:5d} phys={ll.physical} head={ll.head!r} :: {ll.texts[0][:70]!r}")
