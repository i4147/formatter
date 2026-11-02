"""Inspect the frames at the else clause of logical 1629."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)

orig = rp.Indenter._handle_clause


def patched(self, lines, i, frames, clause_of):
    if 1615 <= i <= 1635:
        print(f"--- clause at {i}: {lines[i].head!r}")
        for k, f in enumerate(frames):
            print(f"    frame[{k}] kw={f.keyword!r} chain={f.chain!r} "
                  f"closed={f.chain_closed} level={f.level} "
                  f"header_level={f.header_level} opened_at={f.opened_at}")
    idx = orig(self, lines, i, frames, clause_of)
    if 1615 <= i <= 1635:
        print(f"    -> level {self.levels[i]}")
    return idx


rp.Indenter._handle_clause = patched
indenter = rp.Indenter(lines)
indenter.run(set(), {})
print()
for i in range(1614, 1634):
    ll = lines[i]
    head = ll.head if ll.is_code else "#"
    print(f"{i:5d} L{indenter.levels[i]:2d} {head:10s} {ll.texts[0][:60]}")
