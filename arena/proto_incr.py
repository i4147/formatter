#!/usr/bin/env python3
"""Prototype 5: incremental solver using codeop as the oracle."""
from __future__ import annotations
import ast, codeop, io, sys, tokenize
from dataclasses import dataclass
from typing import Sequence

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R

TERMINATORS = frozenset({"return", "raise", "break", "continue", "pass"})
CLAUSES = frozenset({"else", "elif", "except", "finally", "case"})


def compile_check(text):
    """Return 'ok', 'incomplete' or the SyntaxError."""
    try:
        r = codeop.compile_command(text, "<check>", "exec")
        return "incomplete" if r is None else "ok"
    except SyntaxError as e:
        return e
    except (ValueError, OverflowError):
        return "ok"


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    print("logical lines:", len(lines))
    # Try: build prefix incrementally with a simple policy and see what
    # codeop reports.
    out = []
    for i, ll in enumerate(lines):
        for text in ll.texts:
            out.append(text.strip())
    text = "\n".join(out) + "\n"
    r = compile_check(text)
    print("flat:", r if isinstance(r, str) else (r.msg, r.lineno))


if __name__ == "__main__":
    main()
