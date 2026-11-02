"""A scope aware undefined-name checker.

The parser alone cannot decide whether an ``else`` belongs to an ``if``
or to a loop that is nested inside the ``if``: both readings are valid
Python.  The *meaning* of the program decides it, though: a name that is
used has to be defined before it is used, in the scope that uses it.

The checker below walks the syntax tree with a proper scope stack and
reports every name that is read before it is bound in the scope that
reads it.  It is used as a second oracle: of the possible readings of a
construct, the one that leaves no name unbound is the right one.
"""
from __future__ import annotations

import ast
import builtins


class Scope:
    """One lexical scope."""

    def __init__(self, parent: "Scope | None" = None, kind: str = "module"):
        self.parent = parent
        self.kind = kind
        self.names: set[str] = set()
        #: Names that are declared ``global`` or ``nonlocal`` here.
        self.globals: set[str] = set()
        self.nonlocals: set[str] = set()

    def bind(self, name: str) -> None:
        self.names.add(name)

    def knows(self, name: str) -> bool:
        scope: Scope | None = self
        while scope is not None:
            if name in scope.names:
                return True
            scope = scope.parent
        return False

    def __contains__(self, name: str) -> bool:
        return self.knows(name)


class ScopeChecker:
    """Collect the names that are read before they are bound."""

    def __init__(self) -> None:
        self.undefined: list[tuple[str, int]] = []
        self.scope = Scope(None, "module")
        self.builtins = set(dir(builtins))
        #: The names the module binds at the top level.  They are visible
        #: everywhere, even before they are bound -- a module is executed
        #: from top to bottom, but a function body runs later.
        self.module_names: set[str] = set()

    # -- scope helpers ---------------------------------------------------
    def _bind(self, name: str) -> None:
        if name in self.scope.globals:
            self.module_names.add(name)
            return
        if name in self.scope.nonlocals:
            scope = self.scope.parent
            while scope is not None:
                if name in scope.nonlocals or scope.kind == "function":
                    scope.bind(name)
                    return
                scope = scope.parent
            self.scope.bind(name)
            return
        self.scope.bind(name)
        if self.scope.kind == "module":
            self.module_names.add(name)

    def _bind_target(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self._bind(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._bind_target(element)
        elif isinstance(target, ast.Starred):
            self._bind_target(target.value)

    # -- the walk --------------------------------------------------------
    def run(self, tree: ast.AST) -> list[tuple[str, int]]:
        body = tree.body if isinstance(tree, ast.Module) else []
        # The names a module binds are visible everywhere, even before
        # they are bound: a function body runs later than the module.
        for statement in body:
            self._collect_module_names(statement)
        # A name that a function declares ``global`` is a module level
        # name as well.
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                self.module_names.update(node.names)
        self._body(body, self.scope)
        return self.undefined

    def _collect_module_names(self, node: ast.stmt) -> None:
        """The names a top level statement binds."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            self.module_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                self._collect_target_names(target)
        elif isinstance(node, ast.AnnAssign):
            self._collect_target_names(node.target)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            self._collect_target_names(node.target)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    self._collect_target_names(item.optional_vars)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                self.module_names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                self.module_names.add(alias.asname or alias.name)

    def _collect_target_names(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self.module_names.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._collect_target_names(element)
        elif isinstance(target, ast.Starred):
            self._collect_target_names(target.value)

    def _body(self, body: list[ast.stmt], scope: Scope) -> None:
        """Walk a body, binding the names it defines before it uses them."""
        previous = self.scope
        self.scope = scope
        for statement in body:
            self._statement(statement)
        self.scope = previous

    def _statement(self, node: ast.stmt) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._bind(node.name)
            args = node.args
            for arg in (
                list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
            ):
                self._bind(arg.arg)
            if args.vararg:
                self._bind(args.vararg.arg)
            if args.kwarg:
                self._bind(args.kwarg.arg)
            inner = Scope(self.scope, "function")
            # The names of the enclosing scope are visible, and the names
            # of the function itself are local.
            for decorator in node.decorator_list:
                self._expr(decorator)
            for default in list(args.defaults) + [
                d for d in args.kw_defaults if d is not None
            ]:
                self._expr(default)
            self._body(node.body, inner)
            return
        if isinstance(node, ast.ClassDef):
            self._bind(node.name)
            inner = Scope(self.scope, "class")
            for decorator in node.decorator_list:
                self._expr(decorator)
            for base in node.bases:
                self._expr(base)
            for keyword in node.keywords:
                self._expr(keyword.value)
            self._body(node.body, inner)
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                self._bind(alias.asname or alias.name.split(".")[0])
            return
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                self._bind(alias.asname or alias.name)
            return
        if isinstance(node, ast.Assign):
            for target in node.targets:
                self._bind_target(target)
            self._expr(node.value)
            return
        if isinstance(node, ast.AnnAssign):
            self._bind_target(node.target)
            if node.value is not None:
                self._expr(node.value)
            return
        if isinstance(node, ast.AugAssign):
            self._expr(node.target)
            self._expr(node.value)
            return
        if isinstance(node, (ast.For, ast.AsyncFor)):
            self._expr(node.iter)
            self._bind_target(node.target)
            self._body(node.body, self.scope)
            self._body(node.orelse, self.scope)
            return
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                self._expr(item.context_expr)
                if item.optional_vars is not None:
                    self._bind_target(item.optional_vars)
            self._body(node.body, self.scope)
            return
        if isinstance(node, ast.Try):
            self._body(node.body, self.scope)
            for handler in node.handlers:
                if handler.type is not None:
                    self._expr(handler.type)
                if handler.name:
                    self._bind(handler.name)
                self._body(handler.body, self.scope)
            self._body(node.orelse, self.scope)
            self._body(node.finalbody, self.scope)
            return
        if isinstance(node, ast.If):
            self._expr(node.test)
            self._body(node.body, self.scope)
            self._body(node.orelse, self.scope)
            return
        if isinstance(node, ast.While):
            self._expr(node.test)
            self._body(node.body, self.scope)
            self._body(node.orelse, self.scope)
            return
        if isinstance(node, (ast.Expr, ast.Return, ast.Delete, ast.Assert)):
            for child in ast.iter_child_nodes(node):
                self._expr(child)
            return
        if isinstance(node, ast.Match):
            self._expr(node.subject)
            for case in node.cases:
                if case.guard is not None:
                    self._expr(case.guard)
                self._body(case.body, self.scope)
            return
        if isinstance(node, ast.Raise):
            if node.exc is not None:
                self._expr(node.exc)
            if node.cause is not None:
                self._expr(node.cause)
            return
        if isinstance(node, ast.Global):
            self.scope.globals.update(node.names)
            for name in node.names:
                self.module_names.add(name)
            return
        if isinstance(node, ast.Nonlocal):
            self.scope.nonlocals.update(node.names)
            return
        # Everything else: walk the children generically.
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                self._statement(child)
            elif isinstance(child, ast.expr):
                self._expr(child)

    def _expr(self, node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                if (
                    not self.scope.knows(node.id)
                    and node.id not in self.builtins
                    and node.id not in self.module_names
                ):
                    self.undefined.append((node.id, node.lineno))
            else:
                self._bind(node.id)
            return
        if isinstance(node, ast.Lambda):
            args = node.args
            inner = Scope(self.scope, "function")
            for arg in (
                list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
            ):
                inner.bind(arg.arg)
            if args.vararg:
                inner.bind(args.vararg.arg)
            if args.kwarg:
                inner.bind(args.kwarg.arg)
            for default in list(args.defaults) + [
                d for d in args.kw_defaults if d is not None
            ]:
                self._expr(default)
            previous = self.scope
            self.scope = inner
            self._expr(node.body)
            self.scope = previous
            return
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            # A comprehension has its own scope: the target of the first
            # generator is local to it.
            inner = Scope(self.scope, "comprehension")
            previous = self.scope
            self.scope = inner
            generators = node.generators
            for position, generator in enumerate(generators):
                self._expr(generator.iter)
                self._bind_target(generator.target)
                for condition in generator.ifs:
                    self._expr(condition)
            if isinstance(node, ast.DictComp):
                self._expr(node.key)
                self._expr(node.value)
            else:
                self._expr(node.elt)
            self.scope = previous
            return
        if isinstance(node, ast.NamedExpr):
            self._expr(node.value)
            # A walrus in a comprehension binds in the enclosing scope.
            if self.scope.kind == "comprehension":
                self.scope.parent.bind(node.target.id)  # type: ignore[union-attr]
            else:
                self._bind_target(node.target)
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._statement(node)
            return
        if isinstance(node, ast.ClassDef):
            self._statement(node)
            return
        for child in ast.iter_child_nodes(node):
            self._expr(child)


def undefined_names(tree: ast.AST) -> list[tuple[str, int]]:
    """The names that are read but never bound in *tree*."""
    return ScopeChecker().run(tree)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, "/home/user/formatter")
    from arena.proto_validate import sanitize

    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/outA.py"
    source = open(path, encoding="utf-8").read()
    tree = ast.parse(sanitize(source))
    problems = undefined_names(tree)
    print(f"{len(problems)} undefined names")
    for name, line in problems[:40]:
        print(f"  line {line}: {name}")
