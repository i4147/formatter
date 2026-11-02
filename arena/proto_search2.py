#!/usr/bin/env python3
"""Prototype: proper backtracking search over the ambiguous decisions.

The search space is the set of decisions "does this block header open a
nested suite or start a new one next to the enclosing suite?".  A decision
is only ambiguous if the parser cannot tell the two apart, so the search
uses :func:`ast.parse` -- CPython's own parser -- as the oracle.

To keep the search small the decisions are made lazily: the algorithm first
runs with its default choices and only the decisions that are responsible
for a parse error are revisited.
"""
from __future__ import annotations

import ast
import sys
from typing import Sequence

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R


class Solver:
    def __init__(self, lines):
        self.lines = lines
        self.indenter = R.Indenter(lines)
        self.protected = R._find_protected(lines, self.indenter._keyword_of)
        self.indenter.protected = set(self.protected)
        self.nested: set[int] = set()
        self.levels = None
        self.error = None
        self.text = ""

    def run(self):
        self.levels = self.indenter.run(self.nested)
        self.text = R.render(self.lines, self.levels)
        self.error = R.check_syntax(self.text)
        return self.error

    def failing_index(self):
        for index, ll in enumerate(self.lines):
            if self.error.lineno in ll.physical:
                return index
        return len(self.lines) - 1

    def solve(self, max_flip=100000):
        for _ in range(max_flip):
            error = self.run()
            if error is None:
                return self.text
            if not self.flip():
                return None
        return None

    def flip(self):
        """Flip the decision that is responsible for the current error."""
        limit = self.failing_index()
        # The failing statement is often a clause keyword that could not be
        # attached; the construct it belongs to was closed too early.
        if self.lines[limit].is_code and self.lines[limit].head in R.CLAUSE_KEYWORDS:
            j = limit - 1
            while j >= 0 and not self.lines[j].is_code:
                j -= 1
            limit = j
        for decision in reversed(self.indenter.decisions):
            if decision.line > limit:
                continue
            if decision.line in self.nested:
                continue
            self.nested.add(decision.line)
            return True
        return False


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    solver = Solver(lines)
    result = solver.solve()
    if result is None:
        print("no solution; last error:", solver.error)
    else:
        open("/tmp/outD.py", "w").write(result)
        print("SOLVED, nested decisions:", len(solver.nested))


if __name__ == "__main__":
    main()
