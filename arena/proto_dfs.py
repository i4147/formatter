#!/usr/bin/env python3
"""Prototype 8: DFS with constraint pruning.

The search explores the possible block nesting of the flattened file.  It is
pruned by hard syntactic constraints that Python itself enforces:

* ``break`` / ``continue`` must live inside a ``for`` / ``while`` loop.
* ``return`` / ``yield`` must live inside a function.
* a block header must be followed by an indented body.
* an ``else`` / ``elif`` / ``except`` / ``finally`` / ``case`` clause must
  attach to a matching construct that is still open.
"""
from __future__ import annotations

import ast
import sys
import tokenize
from dataclasses import dataclass
from typing import Sequence

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R

TERMINATORS = frozenset({"return", "raise", "break", "continue", "pass"})
CLAUSES = frozenset({"else", "elif", "except", "finally", "case"})
LOOPS = frozenset({"for", "while"})
FUNCS = frozenset({"def", "async"})


@dataclass
class Frame:
    kind: str
    level: int
    terminated: bool = False
    filled: bool = False


def classify(ll):
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


def render_stmt(texts, level):
    out = []
    first = True
    for t in texts:
        s = t.strip()
        if not s:
            out.append("")
            continue
        out.append("    " * (level if first else level + 1) + s)
        first = False
    return out


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    n = len(lines)
    cls = [classify(ll) for ll in lines]
    levels = [0] * n
    out: list[str] = []
    frames: list[Frame] = []

    sys.setrecursionlimit(100000)

    def candidate_frames(depth, kind):
        """Is it legal for a statement of *kind* to live at frame *depth*?"""
        if depth == 0:
            # module level: no return/break/continue/yield allowed
            if kind in ("return", "raise", "break", "continue"):
                return False
            return True
        f = frames[depth - 1]
        if f.terminated:
            return False
        if kind == "break" or kind == "continue":
            # needs an enclosing loop
            if not any(frames[j].kind in LOOPS for j in range(depth)):
                return False
        if kind == "return":
            # needs an enclosing function
            if not any(frames[j].kind in ("def",) for j in range(depth)):
                return False
        return True

    def recurse(i):
        if i >= n:
            if any(not f.filled for f in frames):
                return False
            return True
        kind, term = cls[i]
        ll = lines[i]

        if kind == "blank":
            lvl = frames[-1].level if frames else 0
            out.extend(render_stmt(ll.texts, lvl))
            levels[i] = lvl
            return recurse(i + 1)

        if kind == "clause":
            idx = None
            for j in range(len(frames) - 1, -1, -1):
                if clause_matches(frames[j], ll.head):
                    idx = j
                    break
            if idx is None:
                return False
            clause_level = frames[idx].level - 1
            saved = list(frames)
            del frames[idx + 1:]
            frames[idx] = Frame(kind=ll.head, level=clause_level + 1)
            out.extend(render_stmt(ll.texts, clause_level))
            levels[i] = clause_level
            if recurse(i + 1):
                return True
            frames[:] = saved
            del out[len(out) - len(render_stmt(ll.texts, clause_level)):]
            return False

        # normal statement: try candidate depths from innermost to outermost
        for depth in range(len(frames), -1, -1):
            if not candidate_frames(depth, kind):
                continue
            f = frames[depth - 1] if depth else None
            lvl = f.level if f else 0
            # heuristic preference: definition-like headers pop def/class
            if f is not None and f.kind in ("def", "class") and kind in ("def", "class"):
                if not (f.kind == "class" and kind == "def" and not f.filled):
                    continue
            saved = list(frames)
            savedout = len(out)
            newframes = frames[:depth]
            if newframes:
                newframes[-1].filled = True
            frames[:] = newframes
            out.extend(render_stmt(ll.texts, lvl))
            levels[i] = lvl
            if kind != "plain":
                frames.append(Frame(kind=kind, level=lvl + 1))
            elif term:
                if frames:
                    frames[-1].terminated = True
            if recurse(i + 1):
                return True
            # backtrack
            frames[:] = saved
            del out[savedout:]
        return False

    ok = recurse(0)
    print("search:", "OK" if ok else "FAILED")
    if ok:
        text = "\n".join(out) + "\n"
        open("/tmp/out8.py", "w").write(text)
        try:
            ast.parse(text)
            print("PARSES OK")
        except SyntaxError as e:
            print("SyntaxError", e.lineno, e.msg)


if __name__ == "__main__":
    main()
