"""Measure the memory/time of a single indentation run and a full parse."""
import resource
import sys
import time

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
t0 = time.time()
lines = rp._logical_lines(source)
indenter = rp.Indenter(lines)
print(f"logical lines: {len(lines)}  rss={rss():.1f}MB  t={time.time()-t0:.2f}s")

t0 = time.time()
levels = indenter.run(set(), {})
print(f"run: rss={rss():.1f}MB  t={time.time()-t0:.2f}s")

t0 = time.time()
text = rp.render(lines, levels)
print(f"render: len={len(text)} rss={rss():.1f}MB  t={time.time()-t0:.2f}s")

t0 = time.time()
err = rp.check_syntax(text)
print(f"parse: rss={rss():.1f}MB  t={time.time()-t0:.2f}s err={err}")
print("decisions:", len(indenter.decisions))
