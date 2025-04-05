# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass, field
from typing import cast, override

from tapl_lang.syntax import (
    MODE_EVALUATE,
    MODE_TYPECHECK,
    ErrorTerm,
    Layers,
    LayerSeparator,
    Term,
    TermWithLocation,
    flatten_statements,
)
from tapl_lang.tapl_error import TaplError


@dataclass
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
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Assign(self.location, [layer(t) for t in self.targets], layer(self.value)))

    @override
    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        stmt = ast.Assign(targets=[t.codegen_expr() for t in self.targets], value=self.value.codegen_expr())
        self.locate(stmt)
        return stmt


@dataclass
class Return(TermWithLocation):
    value: Term | None

    @override
    def get_errors(self) -> list[ErrorTerm]:
        if self.value:
            return self.value.get_errors()
        return []

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        if self.value:
            value = self.value  # hack: python type check could not narrow the self.value from Term|None to Term
            return ls.build(lambda layer: Return(self.location, layer(value)))
        return ls.replicate(self)

    @override
    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        stmt = ast.Return(self.value.codegen_expr()) if self.value else ast.Return()
        self.locate(stmt)
        return stmt


@dataclass
class Expr(TermWithLocation):
    value: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.value.get_errors()

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Expr(self.location, layer(self.value)))

    @override
    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        stmt = ast.Expr(self.value.codegen_expr())
        self.locate(stmt)
        return stmt


@dataclass
class Absence(Term):
    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []


@dataclass
class Parameter(TermWithLocation):
    name: str
    type_: Term

    @override
    def get_errors(self):
        return self.type_.get_errors()

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Parameter(self.location, self.name, layer(self.type_)))


@dataclass
class FunctionDef(TermWithLocation):
    name: str
    parameters: list[Term]
    body: list[Term]
    mode: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = self.mode.get_errors()
        for p in self.parameters:
            result.extend(p.get_errors())
        for s in self.body:
            result.extend(s.get_errors())
        return result

    @override
    def add_child(self, child: Term) -> None:
        self.body.append(child)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: FunctionDef(
                self.location,
                self.name,
                [layer(p) for p in self.parameters],
                [layer(s) for s in self.body],
                layer(self.mode),
            )
        )

    def codegen_function(self, decorator_list: list[ast.expr]) -> ast.FunctionDef:
        params = [ast.arg(arg=cast(Parameter, p).name) for p in self.parameters]
        body = flatten_statements(b.codegen_stmt() for b in self.body)
        func = ast.FunctionDef(
            name=self.name, args=ast.arguments(args=params), body=body, decorator_list=decorator_list
        )
        self.locate(func)
        return func

    def gen_decorator(self) -> ast.expr:
        func = ast.Name('function_type', ctx=ast.Load())
        decorator = ast.Call(func=func, args=[cast(Parameter, p).type_.codegen_expr() for p in self.parameters])
        self.locate(func, decorator)
        return decorator

    @override
    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        if not self.body:
            raise TaplError('Function body is empty.')
        if self.mode is MODE_EVALUATE:
            if not all(isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
                raise TaplError('All parameter type must be Absence when generating function in evaluate mode.')
            return self.codegen_function(decorator_list=[])
        if self.mode is MODE_TYPECHECK:
            if not all(not isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
                raise TaplError('All parameter type must not be Absence when generating function in type-check mode.')
            return self.codegen_function(decorator_list=[self.gen_decorator()])
        raise TaplError(f'Run mode not found. {self.mode} term={self.__class__.__name__}')


@dataclass
class Alias:
    name: str
    asname: str | None = None


@dataclass
class Import(TermWithLocation):
    names: list[Alias]

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.replicate(self)

    @override
    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        stmt = ast.Import(names=[ast.alias(n.name, n.asname) for n in self.names])
        self.locate(stmt)
        return stmt


@dataclass
class ImportFrom(TermWithLocation):
    module: str | None
    names: list[Alias]
    level: int

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.replicate(self)

    @override
    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        stmt = ast.ImportFrom(
            module=self.module, names=[ast.alias(n.name, n.asname) for n in self.names], level=self.level
        )
        self.locate(stmt)
        return stmt


@dataclass
class If(TermWithLocation):
    test: Term
    body: list[Term]
    orelse: list[Term]

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = []
        result.extend(self.test.get_errors())
        for s in self.body:
            result.extend(s.get_errors())
        for s in self.orelse:
            result.extend(s.get_errors())
        return result

    @override
    def add_child(self, child: Term) -> None:
        self.body.append(child)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: If(
                self.location,
                test=layer(self.test),
                body=[layer(s) for s in self.body],
                orelse=[layer(s) for s in self.orelse],
            )
        )

    @override
    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        if_stmt = ast.If(
            test=self.test.codegen_expr(),
            body=flatten_statements(s.codegen_stmt() for s in self.body),
            orelse=flatten_statements(s.codegen_stmt() for s in self.orelse),
        )
        self.locate(if_stmt)
        return if_stmt


@dataclass
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
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Module([layer(s) for s in self.statements]))

    @override
    def codegen_ast(self) -> ast.AST:
        body = flatten_statements(s.codegen_stmt() for s in self.statements)
        return ast.Module(body=body)
