#!/usr/bin/env python3
"""Prototype 4: greedy + parse-error-driven repair loop."""
from __future__ import annotations
import ast, io, sys, tokenize
from dataclasses import dataclass
from typing import Sequence

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R
from proto_repair import compute, render, check, classify


def physical_to_logical(lines):
    m = {}
    for i, ll in enumerate(lines):
        for p in ll.physical:
            m[p] = i
    return m


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    p2l = physical_to_logical(lines)
    overrides = {}
    last_err = None
    for attempt in range(500):
        levels = compute(lines, overrides)
        text = render(lines, levels)
        err = check(text)
        if err is None:
            print("PARSES OK after", attempt, "repairs")
            open("/tmp/out5.py", "w").write(text)
            return
        lineno = err.lineno
        idx = p2l.get(lineno)
        if idx is None:
            print("cannot map line", lineno, err.msg)
            return
        msg = err.msg
        if "expected an indented block" in msg:
            # the block header is at err.lineno-? ; find header logical index
            hdr = None
            for j in range(idx, -1, -1):
                if lines[j].is_code and lines[j].opens_block:
                    hdr = j
                    break
            if hdr is None:
                print("no header found", lineno)
                return
            new = levels[hdr] + 1
            if overrides.get(hdr) == new:
                print("stuck: header already at", new)
                return
            overrides[hdr] = new
            print(f"[{attempt}] {msg} @ {lineno} -> indent header {hdr} to {new}")
        elif "unexpected indent" in msg:
            new = levels[idx] - 1
            if new < 0:
                new = 0
            if overrides.get(idx) == new:
                print("stuck unexpected indent")
                return
            overrides[idx] = new
            print(f"[{attempt}] {msg} @ {lineno} -> dedent {idx} to {new}")
        else:
            print(f"[{attempt}] UNHANDLED: {msg} @ {lineno}: {err.text!r}")
            return


if __name__ == "__main__":
    main()
