#!/usr/bin/env python3
"""Prototype 2: greedy stack machine + ast.parse-driven repair loop."""
from __future__ import annotations
import ast, io, sys, tokenize
from dataclasses import dataclass
from typing import Sequence

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R


@dataclass
class Frame:
    kind: str
    level: int
    terminated: bool = False
    empty: bool = True


def classify(ll):
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


def compute(lines, overrides=None):
    """Compute levels; `overrides` maps statement index -> forced level."""
    overrides = overrides or {}
    n = len(lines)
    levels = [0] * n
    frames: list[Frame] = []
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

        if i in overrides:
            levels[i] = overrides[i]
            i += 1
            if kind not in ("plain", "blank", "clause"):
                frames.append(Frame(kind=kind, level=levels[i] + 1, empty=True))
            continue

        while frames and not can_contain(frames, cls, i):
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


def can_contain(frames, cls, i):
    f = frames[-1]
    kind, term = cls[i]
    if f.terminated:
        return False
    if f.kind in ("def", "class") and kind in ("def", "class"):
        if f.kind == "class" and kind == "def" and f.empty:
            return True
        return False
    if f.kind in ("if", "for", "while") and kind in ("if", "for", "while"):
        return False
    return True


def render(lines, levels):
    return R.render(lines, levels)


def check(text):
    try:
        ast.parse(text)
        return None
    except SyntaxError as e:
        return e


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    overrides = {}
    for attempt in range(30):
        levels = compute(lines, overrides)
        text = render(lines, levels)
        err = check(text)
        if err is None:
            print("PARSES OK after", attempt, "repairs")
            open("/tmp/out3.py", "w").write(text)
            return
        print("attempt", attempt, "error:", err.msg, "line", err.lineno, "text:", err.text)
        # map physical line -> logical line index
        lineno = err.lineno
        # find logical line containing that physical line
        idx = None
        for i, ll in enumerate(lines):
            if lineno in ll.physical:
                idx = i
                break
        print("   logical idx", idx, lines[idx].texts[0][:60] if idx is not None else None)
        break


if __name__ == "__main__":
    main()
