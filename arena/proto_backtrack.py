#!/usr/bin/env python3
"""Prototype: proper backtracking search over the ambiguous decisions.

The reconstruction has a number of places where the flattened file does not
say whether a block header opens a nested suite or starts a new one next to
the enclosing suite.  The script guesses, validates the guess with
:func:`ast.parse` and backtracks when the guess is wrong.
"""
from __future__ import annotations

import ast
import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R


def solve(lines, max_iterations=400):
    """Search for an indentation that parses."""
    indenter = R.Indenter(lines)

    # The decisions are discovered while running, so the search works on
    # "prefixes" of the decision list: the first k decisions are fixed and
    # the rest are explored.
    best = None

    def attempt(fixed: dict[int, bool]):
        nonlocal best
        levels = indenter.run(fixed)
        text = R.render(lines, levels)
        error = R.check_syntax(text)
        return levels, text, error

    # Greedy pass to discover the decisions.
    levels, text, error = attempt({})
    decisions = list(indenter.decisions)
    print("decisions:", len(decisions))

    # Depth first search over the decisions: try to flip the last decision
    # first, because the error is usually caused by the most recent one.
    def dfs(index: int, fixed: dict[int, bool]):
        nonlocal best
        if index > len(decisions):
            return False
        levels, text, error = attempt(fixed)
        if error is None:
            best = text
            return True
        # find the decision to flip
        limit = _failing_index(lines, error)
        for d in reversed(decisions[: limit + 1]):
            if d.line in fixed:
                continue
            new_fixed = dict(fixed)
            new_fixed[d.line] = True
            if dfs(index + 1, new_fixed):
                return True
        return False

    if dfs(0, {}):
        return best
    return None


def _failing_index(lines, error):
    for index, ll in enumerate(lines):
        if error.lineno in ll.physical:
            return index
    return len(lines) - 1


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    result = solve(lines)
    if result is None:
        print("no solution found")
    else:
        open("/tmp/outC.py", "w").write(result)
        print("SOLVED")


if __name__ == "__main__":
    main()
