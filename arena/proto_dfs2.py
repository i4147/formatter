#!/usr/bin/env python3
"""Prototype: depth first search over the ambiguous decisions.

The reconstruction is a function of the decisions "does this block header
open a nested suite?".  The search explores them in order; whenever the
result does not parse, the decision that is responsible for the error is
tried the other way round.
"""
from __future__ import annotations

import ast
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R


def solve(lines, verbose=False):
    indenter = R.Indenter(lines)
    protected = R._find_protected(lines, indenter._keyword_of)
    indenter.protected = set(protected)

    # ``choice[line]`` is True when the header opens a nested suite.
    choice: dict[int, bool] = {}

    def attempt():
        levels = indenter.run(choice)
        text = R.render(lines, levels)
        return levels, text, R.check_syntax(text)

    # The decisions are discovered while running; keep the list so that the
    # search can walk through it.
    def failing_line(error):
        for index, ll in enumerate(lines):
            if error.lineno in ll.physical:
                return index
        return len(lines) - 1

    tried = set()

    def search():
        levels, text, error = attempt()
        if error is None:
            return text
        limit = failing_line(error)
        if lines[limit].is_code and lines[limit].head in R.CLAUSE_KEYWORDS:
            j = limit - 1
            while j >= 0 and not lines[j].is_code:
                j -= 1
            limit = j
        # Try to flip the decisions before the error, newest first.
        for decision in reversed(indenter.decisions):
            if decision.line > limit:
                continue
            key = (decision.line, choice.get(decision.line, False))
            if key in tried:
                continue
            tried.add(key)
            choice[decision.line] = not choice.get(decision.line, False)
            result = search()
            if result is not None:
                return result
            choice[decision.line] = not choice[decision.line]
        return None

    return search()


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    result = solve(lines)
    if result is None:
        print("no solution found")
    else:
        open("/tmp/outE.py", "w").write(result)
        print("SOLVED")


if __name__ == "__main__":
    main()
