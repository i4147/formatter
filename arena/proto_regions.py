"""Group the undefined names of a rendered file by the region they are in."""
from __future__ import annotations

import ast
import sys

sys.path.insert(0, "/home/user/formatter")

from arena.proto_scope import undefined_names
from arena.proto_validate import sanitize


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/outA.py"
    source = open(path, encoding="utf-8").read()
    tree = ast.parse(sanitize(source))
    problems = undefined_names(tree)
    lines = source.splitlines()

    # Group the problems by the innermost enclosing function.
    functions: list[tuple[str, int, int]] = []  # (name, first line, last line)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            functions.append((node.name, node.lineno, end))

    groups: dict[str, list[tuple[str, int]]] = {}
    for name, line in problems:
        owner = "<module>"
        best = None
        for fname, start, end in functions:
            if start <= line <= end:
                if best is None or start > best[1]:
                    best = (fname, start)
        if best is not None:
            owner = best[0]
        groups.setdefault(owner, []).append((name, line))

    total = sum(len(v) for v in groups.values())
    print(f"{total} undefined names in {len(groups)} groups")
    for owner, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"\n=== {owner}: {len(items)} undefined")
        seen: set[str] = set()
        for name, line in items:
            if name in seen:
                continue
            seen.add(name)
            text = lines[line - 1].strip() if line <= len(lines) else ""
            print(f"    {name:24s} line {line:5d}  {text[:60]}")


if __name__ == "__main__":
    main()
