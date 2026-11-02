"""A recursive-descent parser for flattened Python source (prototype 2).

Unlike the first prototype the parser knows about clause keywords: an
``else``/``elif``/``except``/``finally`` closes the block that was
parsed before it and attaches to an enclosing construct.

The parser keeps, for every block it parses, the chain of constructs that
are open, so that a clause can be attached to the right one.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/user/formatter")
import reformat_python as rp

CLAUSES = rp.CLAUSE_KEYWORDS


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
    def parse_block(self, i, level, chain=None):
        """Parse a block of statements starting at *i* at *level*.

        *chain* is the list of open constructs of the enclosing blocks.
        It is used to attach a clause keyword to the construct it
        continues.

        Returns ``(end, chain)``.
        """
        if chain is None:
            chain = []
        while True:
            i = self.code(i)
            if i >= self.n:
                return i, chain
            ll = self.lines[i]
            if self.is_clause(i):
                # The clause closes this block.  The caller attaches it.
                return i, chain
            if self.opens(i):
                self.levels[i] = level
                nxt = self.code(i + 1)
                if nxt >= self.n:
                    return self.n, chain
                end, _ = self.parse_block(nxt, level + 1, chain + [self.head_kw(i)])
                if end is None:
                    return None, chain
                i = self.code(end)
                continue
            self.levels[i] = level
            i += 1


def main():
    source = open("/home/user/formatter/broken.py", encoding="utf-8").read()
    lines = rp._logical_lines(source)
    p = Parser(lines)
    end, _ = p.parse_block(0, 0)
    print("parsed to", end, "of", p.n)
    text, mapping = rp.render_with_map(lines, p.levels)
    err = rp.check_syntax(text)
    print("err:", err)


if __name__ == "__main__":
    main()
