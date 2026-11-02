#!/usr/bin/env python3
"""Version tolerant syntax validation.

The file we have to re-indent uses Python 3.12 syntax (``type X = ...``
type aliases).  The interpreter available in this sandbox is 3.11, so a
plain :func:`ast.parse` would report a spurious error.  The helpers below
retry the check with the offending construct rewritten into a form the older
parser understands.
"""
from __future__ import annotations

import ast
import re
from typing import Sequence

#: ``type Point = tuple[float, float]``  ->  ``Point: TypeAlias = ...``
_TYPE_ALIAS_RE = re.compile(r"^(\s*)type\s+([A-Za-z_]\w*)\s*=\s*(.+)$")


def sanitize(source: str) -> str:
    """Rewrite 3.12-only syntax into a form that older parsers accept."""
    out = []
    for line in source.splitlines():
        m = _TYPE_ALIAS_RE.match(line)
        if m:
            out.append(f"{m.group(1)}{m.group(2)}: object = {m.group(3)}")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def check_syntax(source: str) -> SyntaxError | None:
    """Return ``None`` when *source* parses, else the syntax error."""
    for candidate in (source, sanitize(source)):
        try:
            ast.parse(candidate)
            return None
        except SyntaxError as exc:
            last = exc
    return last


def main():
    src = open("/home/user/formatter/broken.py").read()
    print("sanitized parse:", check_syntax(src))


if __name__ == "__main__":
    main()
