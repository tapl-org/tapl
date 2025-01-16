# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass, field
from typing import override

from tapl_lang.syntax import (
    MODE_EVALUATE,
    MODE_SAFE,
    MODE_TYPECHECK,
    ErrorTerm,
    LayerSeparator,
    Term,
    TermWithLocation,
)
from tapl_lang.tapl_error import TaplError


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
        if self.value:
            ls = LayerSeparator()
            value = ls.separate(self.value)
            return ls.build(lambda layer: Return(self.location, layer(value)))
        return self

    @override
    def codegen_stmt(self) -> ast.stmt:
        stmt = ast.Return(self.value.codegen_expr()) if self.value else ast.Return()
        self.locate(stmt)
        return stmt


@dataclass(frozen=True)
class Absence(Term):
    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []

    @override
    def layer_agnostic(self):
        return True

    def separate(self):
        return self


@dataclass(frozen=True)
class FunctionDef(TermWithLocation):
    name: str
    parameter_names: list[str]
    locks: list[Term]
    body: list[Term] = field(default_factory=list)
    mode: Term = MODE_SAFE

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = self.mode.get_errors()
        for p in self.locks:
            result.extend(p.get_errors())
        for s in self.body:
            result.extend(s.get_errors())
        return result

    @override
    def add_child(self, child: Term) -> None:
        self.body.append(child)

    @override
    def separate(self):
        ls = LayerSeparator()
        locks = [ls.separate(p) for p in self.locks]
        body = [ls.separate(s) for s in self.body]
        mode = ls.separate(self.mode)
        return ls.build(
            lambda layer: FunctionDef(
                self.location,
                self.name,
                self.parameter_names,
                [layer(p) for p in locks],
                [layer(s) for s in body],
                layer(mode),
            )
        )

    def codegen_function(self) -> ast.FunctionDef:
        params = [ast.arg(arg=param_name) for param_name in self.parameter_names]
        body = [s.codegen_stmt() for s in self.body]
        func = ast.FunctionDef(name=self.name, args=ast.arguments(args=params), body=body)
        self.locate(func)
        return func

    def codegen_function_type(self) -> ast.stmt:
        fn_name = ast.Name(id=self.name, ctx=ast.Load())
        fn_type = ast.Name(id='FunctionType', ctx=ast.Load())
        fn_type_call = ast.Call(func=fn_type, args=[fn_name])
        target = ast.Name(id=self.name, ctx=ast.Store())
        assign = ast.Assign(targets=[target], value=fn_type_call)
        pass_stmt = ast.Pass()
        temp_scope = ast.Try(body=[self.codegen_function(), assign], finalbody=[pass_stmt])
        self.locate(fn_name, fn_type, fn_type_call, target, assign, pass_stmt, temp_scope)
        return temp_scope

    @override
    def codegen_stmt(self) -> ast.stmt:
        if not self.body:
            raise TaplError('Function body is empty.')
        if self.mode is MODE_EVALUATE:
            if not all(isinstance(lock, Absence) for lock in self.locks):
                raise TaplError('All parameter locks must be Absence when generating function in evaluate mode.')
            return self.codegen_function()
        if self.mode is MODE_TYPECHECK:
            if not all(not isinstance(lock, Absence) for lock in self.locks):
                raise TaplError('All parameter locks must not be Absence when generating function in type-check mode.')
            return self.codegen_function_type()
        raise TaplError(f'Run mode not found. {self.mode} term={self.__class__.__name__}')


@dataclass(frozen=True)
class Module(Term):
    statements: list[Term] = field(default_factory=list)

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = []
        for s in self.statements:
            result.extend(s.get_errors())
        return result

    @override
    def add_child(self, child: Term) -> None:
        return self.statements.append(child)

    @override
    def separate(self) -> Term:
        ls = LayerSeparator()
        statements = [ls.separate(s) for s in self.statements]
        return ls.build(lambda layer: Module([layer(s) for s in statements]))

    @override
    def codegen_ast(self) -> ast.AST:
        return ast.Module(body=[s.codegen_stmt() for s in self.statements])
