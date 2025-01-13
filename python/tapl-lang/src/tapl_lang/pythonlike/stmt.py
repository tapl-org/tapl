# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass, field
from typing import override

from tapl_lang.ast_util import ast_typelib_call
from tapl_lang.pythonlike import expr
from tapl_lang.syntax import ErrorTerm, LayerSeparator, Term, TermWithLocation


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
        self.locate(stmt)
        return stmt


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
        stmt = ast.Return(self.value.codegen_expr()) if self.value else ast.Return()
        self.locate(stmt)
        return stmt


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
        self.locate(fn)
        absence_count = sum(1 for arg in self.args if isinstance(arg, expr.Absence))
        if absence_count == len(self.args):
            return fn
        pass_stmt = ast.Pass()
        fn_name = ast.Name(id=self.name, ctx=ast.Load())
        fn_type = ast_typelib_call(function_name='FunctionType', args=[fn_name], loc=self.location)
        temp_scope = ast.Try(body=[fn], finalbody=[pass_stmt])
        self.locate(pass_stmt, fn_name, fn_type, temp_scope)
        return temp_scope
