"""A recursive-descent parser for flattened Python source.

The parser works on the logical lines produced by
``reformat_python._logical_lines``.  It rebuilds the block structure by
trying to parse a block and backtracking *locally* when the choice turns
out to be wrong.

Grammar (simplified)::

    block   := statement*
    stmt    := simple | compound
    compound:= header ':' (inline | block)
    header  := 'if' ... | 'for' ... | 'def' ... | ...

The parser returns, for every logical line, the indentation level of the
block it belongs to.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

CLAUSES = rp.CLAUSE_KEYWORDS
DEFS = rp.DEFINITION_KEYWORDS


class Parser:
    def __init__(self, lines):
        self.lines = lines
        self.n = len(lines)
        self.levels = [0] * self.n

    # -- helpers ---------------------------------------------------------
    def code(self, i):
        while i < self.n and not self.lines[i].is_code:
            i += 1
        return i

    def is_clause(self, i):
        ll = self.lines[i]
        return ll.is_code and ll.head in CLAUSES and rp.Indenter._is_clause(ll)

    def head_kw(self, i):
        return rp.Indenter._keyword_of(self.lines[i])

    def opens(self, i):
        ll = self.lines[i]
        return ll.opens_block and not ll.inline_suite

    # -- the parser ------------------------------------------------------
    def parse_block(self, i, level):
        """Parse a block of statements starting at *i* at *level*.

        Returns the index of the first line that is *not* part of the
        block, or ``None`` when the block runs to the end of the file.
        """
        while True:
            i = self.code(i)
            if i >= self.n:
                return i
            ll = self.lines[i]
            if self.is_clause(i):
                # A clause keyword cannot start a block; it belongs to an
                # enclosing construct.  The caller decides.
                return i
            if ll.opens_block and not ll.inline_suite:
                self.levels[i] = level
                nxt = self.code(i + 1)
                if nxt >= self.n:
                    return self.n
                end = self.parse_block(nxt, level + 1)
                if end is None:
                    return None
                i = self.code(end)
                continue
            # A simple statement.
            self.levels[i] = level
            if ll.head in rp.TERMINATORS:
                # A terminating statement ends the suite it is in, but the
                # block itself may continue with more statements.
                pass
            i += 1


def main():
    source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
    lines = rp._logical_lines(source)
    p = Parser(lines)
    end = p.parse_block(0, 0)
    print("parsed to", end, "of", p.n)
    print("max level", max(p.levels))
    text, mapping = rp.render_with_map(lines, p.levels)
    err = rp.check_syntax(text)
    print("err:", err)
    if err:
        ln = err.lineno or 0
        idx = mapping[ln - 1] if 1 <= ln <= len(mapping) else -1
        print("failing index", idx)
        for i in range(max(0, idx - 10), min(p.n, idx + 6)):
            print(f"{i:5d} L{p.levels[i]:2d} {lines[i].head!r:12s} {lines[i].texts[0][:60]}")


if __name__ == "__main__":
    main()
