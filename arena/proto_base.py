"""Show the base (no search) result and its first error."""
import sys
import time

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)

t0 = time.time()
levels = indenter.run(set(), {})
text, mapping = rp.render_with_map(lines, levels)
err = rp.check_syntax(text)
print("t=%.2fs err=%s" % (time.time() - t0, err))
print("max level:", max(levels))
print("decisions:", len(indenter.decisions))
if err:
    ln = err.lineno or 0
    idx = mapping[ln - 1] if 1 <= ln <= len(mapping) else -1
    print("failing logical index:", idx)
    if idx >= 0:
        for i in range(max(0, idx - 12), min(len(lines), idx + 8)):
            ll = lines[i]
            head = ll.head if ll.is_code else "#"
            print(f"{i:5d} L{levels[i]:2d} {head:10s} {ll.texts[0][:60]}")
