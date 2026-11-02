#!/usr/bin/env python3
"""Prototype: repair the clause levels with a local parse.

For every clause keyword the candidate constructs are tried: the region
that starts at the construct's header and ends at the clause is rendered on
its own and handed to CPython's parser.  Only the candidate that produces
valid Python survives.
"""
from __future__ import annotations

import ast
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R


def region(lines, levels, start, end):
    """Render the logical lines *start*..*end* as a standalone program."""
    out = []
    base = levels[start]
    for ll, level in zip(lines[start : end + 1], levels[start : end + 1]):
        if not ll.is_code:
            for text in ll.texts:
                out.append("" if text.strip() == "" else "    " * (level - base) + text.strip())
            continue
        first = True
        for text in ll.texts:
            s = text.strip()
            if not s:
                out.append("")
                continue
            out.append("    " * ((level - base) if first else level - base + 1) + s)
            first = False
    return "\n".join(out) + "\n"


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    ind = R.Indenter(lines)
    levels = ind.run(set())
    text = R.render(lines, levels)
    err = R.check_syntax(text)
    print("error:", err.msg if err else None, err.lineno if err else "")

    # Try to repair the first failing clause.
    for index, ll in enumerate(lines):
        if not (ll.is_code and ll.head in R.CLAUSE_KEYWORDS):
            continue
        cands = R._clause_candidates(lines, ind, index)
        for c in cands[:5]:
            trial = list(levels)
            trial[index] = levels[c]
            body = region(lines, trial, c, index)
            try:
                ast.parse(body)
                print("clause", index, "-> construct", c, "PARSES")
            except SyntaxError as e:
                print("clause", index, "-> construct", c, "fails:", e.msg)


if __name__ == "__main__":
    main()
