#!/usr/bin/env python3
"""Prototype 6: incremental indentation solver driven by the codeop oracle.

The solver walks the logical lines of the flattened file and decides, for
each of them, at which indentation level it lives.  Every decision is
validated against CPython's own compiler: the text produced so far is fed to
:func:`codeop.compile_command`, which behaves exactly like the interpreter's
interactive mode and therefore knows about Python's indentation rules.

The compiler tells us three things:

``ok``
    The prefix is complete and valid.
``incomplete``
    The prefix is valid so far, but a block is still waiting for its body.
``SyntaxError``
    The prefix is invalid; the message says why.

Because the compiler is the ground truth for *Python syntax*, the solver only
has to guess the *intent* (which statements belong to which block); every
guess that the compiler rejects is corrected by trying the next candidate.
"""
from __future__ import annotations

import codeop
import io
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
    level: int          # indentation level of the suite body
    terminated: bool = False
    filled: bool = False


def classify(ll):
    """Return ``(kind, is_terminator)`` for a logical line."""
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
    """Render the physical lines of one logical statement at *level*."""
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

    def check():
        text = "\n".join(out) + "\n"
        try:
            r = codeop.compile_command(text, "<check>", "exec")
            return "incomplete" if r is None else "ok"
        except SyntaxError as e:
            return e

    i = 0
    while i < n:
        kind, term = cls[i]
        ll = lines[i]

        if kind == "blank":
            out.extend(render_stmt(ll.texts, frames[-1].level if frames else 0))
            levels[i] = frames[-1].level if frames else 0
            i += 1
            continue

        if kind == "clause":
            # find innermost matching frame
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

        # normal statement: choose the level
        candidates = []
        # candidate levels: the level of each open frame (innermost first)
        seen = set()
        for depth in range(len(frames), -1, -1):
            f = frames[depth - 1] if depth else None
            lvl = f.level if f else 0
            if lvl in seen:
                continue
            seen.add(lvl)
            candidates.append((depth, lvl))
        # also: one deeper than the innermost frame (for a body that follows
        # a block header)
        if frames:
            lvl = frames[-1].level + 1
            if lvl not in seen:
                candidates.append((len(frames), lvl))

        chosen = None
        for depth, lvl in candidates:
            trial = out + render_stmt(ll.texts, lvl)
            text = "\n".join(trial) + "\n"
            try:
                codeop.compile_command(text, "<check>", "exec")
                chosen = (depth, lvl)
                break
            except SyntaxError as e:
                # If the compiler complains about *this* line, try another
                # level.  Errors about earlier lines are fatal for this
                # candidate as well.
                continue

        if chosen is None:
            # fall back to the innermost frame level
            depth, lvl = candidates[0] if candidates else (0, 0)
            chosen = (depth, lvl)

        depth, lvl = chosen
        out.extend(render_stmt(ll.texts, lvl))
        levels[i] = lvl
        newframes = frames[:depth]
        if newframes:
            newframes[-1].filled = True
        frames = newframes
        if kind not in ("plain",):
            frames.append(Frame(kind=kind, level=lvl + 1))
        elif term:
            if frames:
                frames[-1].terminated = True
        i += 1

    text = "\n".join(out) + "\n"
    open("/tmp/out6.py", "w").write(text)
    try:
        import ast
        ast.parse(text)
        print("PARSES OK")
    except SyntaxError as e:
        print("SyntaxError", e.lineno, e.msg)


if __name__ == "__main__":
    main()
