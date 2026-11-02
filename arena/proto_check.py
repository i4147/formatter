"""Check the reformatted file.

The check runs the three tests that matter:

* the result has to be parsable Python,
* the token stream has to be the same as the one of the input -- the
  formatter may only change the indentation,
* the names that are read but never bound are reported, so that a
  reading that puts a constant into the wrong scope becomes visible.

Usage::

    python3 arena/proto_check.py broken.py /tmp/result.py
"""
from __future__ import annotations

import ast
import io
import sys
import tokenize

sys.path.insert(0, "/home/user/formatter")

import reformat_python as rp


def tokens(source: str) -> list[tuple[int, str]]:
    """The significant tokens of *source*."""
    result: list[tuple[int, str]] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (
            tokenize.NEWLINE,
            tokenize.NL,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENDMARKER,
            tokenize.COMMENT,
        ):
            continue
        result.append((token.type, token.string))
    return result


def check(source_path: str, result_path: str) -> int:
    source = open(source_path, encoding="utf-8").read()
    result = open(result_path, encoding="utf-8").read()

    failures = 0

    error = rp.check_syntax(result)
    if error is None:
        print("OK   the result is parsable Python")
    else:
        failures += 1
        print(f"FAIL the result does not parse: {error}")

    source_tokens = tokens(source)
    result_tokens = tokens(result)
    if source_tokens == result_tokens:
        print(f"OK   the token stream is unchanged ({len(source_tokens)} tokens)")
    else:
        failures += 1
        print("FAIL the token stream changed")
        for index, (left, right) in enumerate(zip(source_tokens, result_tokens)):
            if left != right:
                print(f"     first difference at token {index}: {left} != {right}")
                break

    problems = rp.undefined_names(result)
    print(f"INFO {len(problems)} names are read before they are bound")

    tree = ast.parse(rp._sanitize(result))
    definitions = sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    nodes = sum(1 for _ in ast.walk(tree))
    print(f"INFO {definitions} definitions, {nodes} syntax tree nodes")

    return failures


if __name__ == "__main__":
    source_path = sys.argv[1] if len(sys.argv) > 1 else "/home/user/formatter/broken.py"
    result_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/result.py"
    raise SystemExit(1 if check(source_path, result_path) else 0)
