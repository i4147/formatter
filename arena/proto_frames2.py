"""Trace the frame stack around logical lines 735-760."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)

orig = rp.Indenter._handle_clause


def patched(self, lines, i, frames, clause_of):
    if 735 <= i <= 760:
        print(f"--- clause at {i}: {lines[i].head!r}")
        for k, f in enumerate(frames):
            print(f"    frame[{k}] kw={f.keyword!r} chain={f.chain!r} "
                  f"closed={f.chain_closed} level={f.level} "
                  f"header_level={f.header_level} opened_at={f.opened_at}")
    idx = orig(self, lines, i, frames, clause_of)
    if 735 <= i <= 760:
        print(f"    -> level {self.levels[i]}")
    return idx


rp.Indenter._handle_clause = patched

orig_run = rp.Indenter.run


def patched_run(self, nested=None, clause_of=None):
    # instrument the header handling
    return orig_run(self, nested, clause_of)


indenter = rp.Indenter(lines)
indenter.run(set(), {})
for i in range(735, 760):
    ll = lines[i]
    head = ll.head if ll.is_code else "#"
    print(f"{i:5d} L{indenter.levels[i]:2d} {head:10s} {ll.texts[0][:60]}")
