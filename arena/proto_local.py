#!/usr/bin/env python3
"""Prototype 7: local indent-stack validation (no per-statement compile)."""
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

    out: list[str] = []
    frames: list[Frame] = []
    levels = [0] * n

    i = 0
    while i < n:
        kind, term = cls[i]
        ll = lines[i]

        if kind == "blank":
            lvl = frames[-1].level if frames else 0
            out.extend(render_stmt(ll.texts, lvl))
            levels[i] = lvl
            i += 1
            continue

        if kind == "clause":
            idx = None
            for j in range(len(frames) - 1, -1, -1):
                if clause_matches(frames[j], ll.head):
                    idx = j
                    break
            if idx is None:
                lvl = frames[-1].level if frames else 0
                out.extend(render_stmt(ll.texts, lvl))
                levels[i] = lvl
                i += 1
                continue
            clause_level = frames[idx].level - 1
            del frames[idx + 1:]
            out.extend(render_stmt(ll.texts, clause_level))
            levels[i] = clause_level
            frames[idx] = Frame(kind=ll.head, level=clause_level + 1)
            i += 1
            continue

        # ---- normal statement: choose the level -------------------------
        # The candidate levels are the levels of the open frames.  We walk
        # the stack from the innermost outwards and pick the first frame
        # that may contain this statement.
        chosen_depth = None
        chosen_lvl = None
        for depth in range(len(frames), -1, -1):
            f = frames[depth - 1] if depth else None
            lvl = f.level if f else 0
            if f is not None:
                if f.terminated:
                    continue
                if f.kind in ("def", "class") and kind in ("def", "class"):
                    if not (f.kind == "class" and kind == "def" and not f.filled):
                        continue
                if f.kind in ("if", "for", "while") and kind in ("if", "for", "while"):
                    continue
            chosen_depth = depth
            chosen_lvl = lvl
            break

        if chosen_depth is None:
            chosen_depth = len(frames)
            chosen_lvl = frames[-1].level if frames else 0

        lvl = chosen_lvl
        out.extend(render_stmt(ll.texts, lvl))
        levels[i] = lvl
        newframes = frames[:chosen_depth]
        if newframes:
            newframes[-1].filled = True
        frames = newframes
        if kind != "plain":
            frames.append(Frame(kind=kind, level=lvl + 1))
        elif term:
            if frames:
                frames[-1].terminated = True
        i += 1

    text = "\n".join(out) + "\n"
    open("/tmp/out7.py", "w").write(text)
    try:
        ast.parse(text)
        print("PARSES OK")
    except SyntaxError as e:
        print("SyntaxError line", e.lineno, e.msg)


if __name__ == "__main__":
    main()
