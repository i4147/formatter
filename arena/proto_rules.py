#!/usr/bin/env python3
"""Prototype 9: the "empty body" rule.

A block header that appears while the innermost open suite is still empty
*starts* that suite; a block header that appears after the suite already
received a statement *closes* it.
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

        is_header = kind not in ("plain", "blank", "clause")
        is_def = kind in ("def", "class")

        # --- decide how many frames to pop -----------------------------
        pop = 0
        if frames:
            top = frames[-1]
            if is_def:
                # definitions never nest inside a definition, except for
                # methods: a 'def' directly inside a class body.
                if top.kind == "class" and kind == "def" and not top.filled:
                    pass  # method -> stays
                elif top.kind in ("def", "class"):
                    pop = 1
                    # also pop enclosing def/class frames
                    while len(frames) - pop > 0 and frames[len(frames) - pop - 1].kind in ("def", "class"):
                        pop += 1
            elif is_header:
                if not top.filled:
                    pass  # the header starts the body of 'top'
                elif top.terminated:
                    pop = 1
                else:
                    # the suite already has a statement -> the header closes it
                    pop = 1
                    while len(frames) - pop > 0 and frames[len(frames) - pop - 1].kind in ("if", "for", "while") and frames[len(frames) - pop - 1].filled:
                        # keep popping while the outer suite is also filled?
                        break
            else:
                if top.terminated:
                    pop = 1

        if pop:
            del frames[len(frames) - pop:]
        lvl = frames[-1].level if frames else 0
        out.extend(render_stmt(ll.texts, lvl))
        levels[i] = lvl
        if frames:
            frames[-1].filled = True
        if is_header:
            frames.append(Frame(kind=kind, level=lvl + 1))
        elif term:
            if frames:
                frames[-1].terminated = True
        i += 1

    text = "\n".join(out) + "\n"
    open("/tmp/out9.py", "w").write(text)
    try:
        ast.parse(text)
        print("PARSES OK")
    except SyntaxError as e:
        print("SyntaxError line", e.lineno, e.msg)


if __name__ == "__main__":
    main()
