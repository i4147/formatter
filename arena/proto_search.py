#!/usr/bin/env python3
"""Prototype 3: backtracking search for indentation recovery.

The search walks the logical lines and decides, for every statement, at which
block depth it lives.  Ambiguities are resolved by trying the most likely
alternative first and backtracking when the result does not parse.
"""
from __future__ import annotations
import ast, io, sys, tokenize
from dataclasses import dataclass
from typing import Sequence

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R

TERMINATORS = frozenset({"return", "raise", "break", "continue", "pass"})
CLAUSES = frozenset({"else", "elif", "except", "finally", "case"})


@dataclass
class Frame:
    kind: str
    level: int          # indentation level of the suite body
    terminated: bool = False
    filled: bool = False


def classify(ll):
    """(kind, is_terminator) for a logical line."""
    head = ll.head
    if not ll.is_code:
        return ("blank", False)
    if head in CLAUSES:
        return ("clause", False)
    if head in TERMINATORS:
        return ("plain", True)
    if ll.opens_block:
        kw = head
        if kw == "async":
            for t in ll.tokens[1:]:
                if t.type == tokenize.NAME and t.string in ("def", "for", "with"):
                    kw = t.string
                    break
        return (kw, False)
    return ("plain", False)


def clause_matches(frame: Frame, head: str) -> bool:
    if head in ("except", "finally"):
        return frame.kind == "try"
    if head in ("else", "elif"):
        return frame.kind in ("if", "elif")
    if head == "case":
        return frame.kind == "match"
    return False


def search(lines, verbose=False):
    """Return (levels, ok)."""
    n = len(lines)
    cls = [classify(ll) for ll in lines]
    levels = [0] * n
    used = set()

    def candidates(frames, i):
        """Yield the possible target levels for statement i."""
        kind, term = cls[i]
        head = lines[i].head

        if kind == "clause":
            # find innermost matching frame
            for idx in range(len(frames) - 1, -1, -1):
                if clause_matches(frames[idx], head):
                    yield ("clause", idx, frames[idx].level - 1)
                    return
            yield ("plain", None, frames[-1].level if frames else 0)
            return

        # Normal statement: the candidate levels are the frames that may
        # contain it.  We try the innermost first (deepest nesting) but with
        # the "sibling preference" for definition-like headers.
        opts = []
        for depth in range(len(frames), -1, -1):
            f = frames[depth - 1] if depth else None
            lvl = f.level if f else 0
            if f is not None and f.terminated:
                continue
            opts.append((depth, lvl))
        # Order: try the deepest allowed, but for definition-like headers
        # prefer to pop def/class frames first.
        return opts

    def recurse(i, frames):
        if i in used and False:
            return None
        if i >= n:
            # all frames must be non-empty
            if any(f.kind and not f.filled for f in frames):
                return None
            return list(frames)
        kind, term = cls[i]
        if kind == "blank":
            levels[i] = frames[-1].level if frames else 0
            return recurse(i + 1, frames)

        if kind == "clause":
            for mode, idx, lvl in candidates(frames, i):
                if mode == "clause":
                    newframes = frames[: idx + 1]
                    newframes[idx] = Frame(kind=lines[i].head, level=lvl + 1)
                    levels[i] = lvl
                    r = recurse(i + 1, newframes)
                    if r is not None:
                        return r
                    continue
                else:
                    levels[i] = lvl
                    r = recurse(i + 1, frames)
                    if r is not None:
                        return r
                    continue
            return None

        # normal statement
        opts = candidates(frames, i)
        # order the options
        ordered = sorted(
            opts,
            key=lambda o: (
                # prefer popping def/class frames (sibling definitions)
                0 if (o[0] == 0 or (frames[o[0] - 1].kind in ("def", "class"))) else 1,
                -o[0],
            ),
        )
        for depth, lvl in ordered:
            newframes = list(frames[:depth])
            levels[i] = lvl
            if newframes:
                newframes[-1].filled = True
            if kind not in ("plain",):
                newframes.append(Frame(kind=kind, level=lvl + 1))
            elif term:
                if newframes:
                    newframes[-1].terminated = True
            r = recurse(i + 1, newframes)
            if r is not None:
                return r
        return None

    sys.setrecursionlimit(100000)
    res = recurse(0, [])
    if res is None:
        return None, False
    return levels, True


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    levels, ok = search(lines)
    print("search ok:", ok)
    if ok:
        text = R.render(lines, levels)
        open("/tmp/out4.py", "w").write(text)
        try:
            ast.parse(text)
            print("PARSES OK")
        except SyntaxError as e:
            print("SyntaxError", e.lineno, e.msg)


if __name__ == "__main__":
    main()
