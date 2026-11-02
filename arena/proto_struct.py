#!/usr/bin/env python3
"""Prototype: a statement level parser for the block structure.

The parser implements the *suite* part of Python's grammar::

    file_input : (NEWLINE | stmt)* EOF
    stmt       : simple_stmt | compound_stmt
    compound_stmt
               : if_stmt | while_stmt | for_stmt | try_stmt | with_stmt
               | funcdef | classdef | decorated | match_stmt
    suite      : simple_stmt | NEWLINE INDENT stmt+ DEDENT

Expressions are not parsed -- the tokeniser already told us where the
statements start and end.  What the parser has to decide is where a suite
ends, and that is exactly the information the flattening destroyed.

The parser therefore works on *candidates*: for every construct it collects
the statements that could belong to it and lets the caller decide.
"""
from __future__ import annotations

import ast
import io
import sys
import tokenize
from dataclasses import dataclass, field
from typing import Sequence

sys.path.insert(0, "/home/user/formatter")
import reformat_python as R

#: Keywords that open a suite.
COMPOUND = {
    "if": "if",
    "while": "while",
    "for": "for",
    "try": "try",
    "with": "with",
    "def": "def",
    "class": "class",
    "async": "async",
    "match": "match",
}

#: Keywords that continue a suite.
CLAUSE = {"elif", "else", "except", "finally", "case"}


@dataclass
class Node:
    """A statement in the reconstructed tree."""

    #: Index of the logical line.
    line: int
    #: Indentation level.
    level: int = 0
    #: The suite this statement opens (for compound statements).
    body: list["Node"] = field(default_factory=list)
    #: The clauses of an ``if``/``try``/``for`` statement.
    clauses: list["Node"] = field(default_factory=list)


def main():
    src = open("/home/user/formatter/broken.py").read()
    lines = R._logical_lines(src)
    print("logical lines:", len(lines))
    # How many statements open a suite?
    openers = sum(1 for ll in lines if ll.is_code and ll.opens_block)
    print("block openers:", openers)
    clauses = sum(1 for ll in lines if ll.is_code and ll.head in CLAUSE)
    print("clauses:", clauses)


if __name__ == "__main__":
    main()
