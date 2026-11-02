"""Trace the frames around the elif at 748 during run()."""
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)

orig = rp.Indenter._handle_clause


def patched(self, lines, i, frames, clause_of):
    print(f"--- clause at {i}: {lines[i].head!r}")
    for k, f in enumerate(frames):
        print(f"    frame[{k}] keyword={f.keyword!r} level={f.level} "
              f"header_level={f.header_level} opened_at={f.opened_at} "
              f"from_clause={f.from_clause}")
    idx = orig(self, lines, i, frames, clause_of)
    print(f"    -> level {self.levels[i]}")
    return idx


rp.Indenter._handle_clause = patched
indenter = rp.Indenter(lines)
indenter.run(set(), {})
print("level at 748:", indenter.levels[748])
