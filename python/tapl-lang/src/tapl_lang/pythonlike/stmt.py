# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass, field
from typing import override

from tapl_lang.pythonlike import expr
from tapl_lang.syntax import ErrorTerm, LayerSeparator, Location, Term, TermWithLocation


def with_location(tree: ast.stmt, loc: Location) -> ast.stmt:
    if loc.start:
        tree.lineno = loc.start.line
        tree.col_offset = loc.start.column
    if loc.end:
        tree.end_lineno = loc.end.line
        tree.end_col_offset = loc.end.column
    return tree


@dataclass(frozen=True)
class Assign(TermWithLocation):
    targets: list[Term]
    value: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = self.value.get_errors()
        for t in self.targets:
            result.extend(t.get_errors())
        return result

    @override
    def layer_agnostic(self) -> bool:
        return all(t.layer_agnostic() for t in self.targets) and self.value.layer_agnostic()

    @override
    def separate(self) -> Term:
        ls = LayerSeparator()
        targets = [ls.separate(t) for t in self.targets]
        value = ls.separate(self.value)
        return ls.build(lambda layer: Assign(self.location, [layer(t) for t in targets], layer(value)))

    @override
    def codegen_stmt(self) -> ast.stmt:
        stmt = ast.Assign(targets=[t.codegen_expr() for t in self.targets], value=self.value.codegen_expr())
        return with_location(stmt, self.location)


@dataclass(frozen=True)
class Return(TermWithLocation):
    value: Term | None

    @override
    def get_errors(self) -> list[ErrorTerm]:
        if self.value:
            return self.value.get_errors()
        return []

    @override
    def layer_agnostic(self):
        if self.value:
            return self.value.layer_agnostic()
        return True

    @override
    def separate(self) -> Term:
        return self

    @override
    def codegen_stmt(self) -> ast.stmt:
        if self.value:
            return with_location(ast.Return(self.value.codegen_expr()), self.location)
        return with_location(ast.Return(), self.location)


@dataclass(frozen=True)
class Argument(TermWithLocation):
    name: str
    lock: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.lock.get_errors()

    @override
    def layer_agnostic(self) -> bool:
        return self.lock.layer_agnostic()

    @override
    def separate(self) -> Term:
        ls = LayerSeparator()
        lock = ls.separate(self.lock)
        return ls.build(lambda layer: Argument(self.location, self.name, layer(lock)))


@dataclass(frozen=True)
class FunctionDef(TermWithLocation):
    name: str
    args: list[Argument]
    body: list[Term] = field(default_factory=list)

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = []
        for s in self.body:
            result.extend(s.get_errors())
        return result

    @override
    def add_child(self, child: Term) -> None:
        self.body.append(child)

    @override
    def layer_agnostic(self) -> bool:
        return all(s.layer_agnostic() for s in self.body)

    @override
    def separate(self):
        ls = LayerSeparator()
        body = [ls.separate(s) for s in self.body]
        return ls.build(lambda layer: FunctionDef(self.location, self.name, self.args, [layer(s) for s in body]))

    @override
    def codegen_stmt(self) -> ast.stmt:
        args = [ast.arg(arg=arg.name) for arg in self.args]
        body = [s.codegen_stmt() for s in self.body]
        fn: ast.stmt = ast.FunctionDef(name=self.name, args=ast.arguments(args=args), body=body)
        fn = with_location(fn, self.location)
        absence_count = sum(1 for arg in self.args if isinstance(arg, expr.Absence))
        if absence_count == len(self.args):
            return fn
        temp_scope = ast.Try(body=[fn], finalbody=[with_location(ast.Pass(), self.location)])
        return with_location(temp_scope, self.location)
