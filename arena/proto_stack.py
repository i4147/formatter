#!/usr/bin/env python3
"""Prototype: heuristic stack machine for indentation recovery."""
from __future__ import annotations
import ast, io, sys, tokenize
from dataclasses import dataclass, field
from typing import Sequence

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R


@dataclass
class Frame:
    kind: str
    level: int
    terminated: bool = False
    empty: bool = True   # no statement emitted yet


def classify(ll):
    """Return (kind, is_terminator) for a logical line."""
    head = ll.head
    if not ll.is_code:
        return ("blank", False)
    if head in ("else", "elif", "except", "finally", "case"):
        return ("clause", False)
    if head in ("return", "raise", "break", "continue", "pass"):
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


def compute(lines, dedent_preference=True):
    """Return list of levels."""
    n = len(lines)
    levels = [0] * n
    frames: list[Frame] = []

    # precompute classification
    cls = [classify(ll) for ll in lines]

    i = 0
    while i < n:
        kind, term = cls[i]
        ll = lines[i]
        if kind == "blank":
            levels[i] = frames[-1].level if frames else 0
            i += 1
            continue

        if kind == "clause":
            # attach to innermost matching frame
            target = match_frame(frames, ll.head)
            if target is None:
                levels[i] = frames[-1].level if frames else 0
                i += 1
                continue
            idx = frames.index(target)
            clause_level = frames[idx].level - 1
            del frames[idx + 1:]
            levels[i] = clause_level
            frames[idx] = Frame(kind=ll.head, level=clause_level + 1, empty=True)
            i += 1
            continue

        # plain / opener statement
        # pop frames that cannot contain this statement
        while frames and not can_contain(frames, cls, i, dedent_preference):
            frames.pop()

        level = frames[-1].level if frames else 0
        levels[i] = level
        if frames:
            frames[-1].empty = False
        i += 1

        if kind not in ("plain", "blank", "clause"):
            frames.append(Frame(kind=kind, level=level + 1, empty=True))
        elif term:
            if frames:
                frames[-1].terminated = True
    return levels


def match_frame(frames, head):
    for f in reversed(frames):
        if head in ("except", "finally"):
            if f.kind == "try":
                return f
        elif head in ("else", "elif"):
            if f.kind in ("if", "elif"):
                return f
        elif head == "case":
            if f.kind == "match":
                return f
    return None


def can_contain(frames, cls, i, dedent_pref):
    """Can the innermost frame contain statement i?"""
    f = frames[-1]
    kind, term = cls[i]
    if f.terminated:
        return False
    if f.kind in ("def", "class") and kind in ("def", "class"):
        # method vs sibling
        if f.kind == "class" and kind == "def" and f.empty:
            return True
        return False
    if dedent_pref and f.kind in ("if", "for", "while") and kind in (
        "if", "for", "while", "def", "class", "try", "with", "match"
    ):
        return False
    return True


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    levels = compute(lines)
    out = R.render(lines, levels)
    open("/tmp/out2.py", "w").write(out)
    try:
        ast.parse(out)
        print("PARSES OK")
    except SyntaxError as e:
        print("SyntaxError line", e.lineno, e.msg)


if __name__ == "__main__":
    main()
