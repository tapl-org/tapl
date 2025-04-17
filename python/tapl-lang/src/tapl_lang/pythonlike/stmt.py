# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass, field
from typing import cast, override

from tapl_lang.syntax import (
    ErrorTerm,
    Layers,
    LayerSeparator,
    Location,
    Term,
    TypedStatement,
)
from tapl_lang.tapl_error import TaplError


@dataclass
class Sequence(Term):
    statements: list[Term]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        for s in self.statements:
            s.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Sequence(statements=[layer(s) for s in self.statements]))

    @override
    def codegen_stmt(self) -> list[ast.stmt]:
        return [s for b in self.statements for s in b.codegen_stmt()]


@dataclass
class Assign(Term):
    location: Location
    targets: list[Term]
    value: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        for t in self.targets:
            t.gather_errors(error_bucket)
        self.value.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: Assign(
                location=self.location, targets=[layer(t) for t in self.targets], value=layer(self.value)
            )
        )

    @override
    def codegen_stmt(self) -> list[ast.stmt]:
        stmt = ast.Assign(targets=[t.codegen_expr() for t in self.targets], value=self.value.codegen_expr())
        self.location.locate(stmt)
        return [stmt]


@dataclass
class Return(Term):
    location: Location
    value: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        if self.value:
            self.value.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Return(location=self.location, value=layer(self.value)))

    @override
    def codegen_stmt(self) -> list[ast.stmt]:
        stmt = ast.Return(self.value.codegen_expr()) if self.value else ast.Return()
        self.location.locate(stmt)
        return [stmt]


@dataclass
class Expr(Term):
    location: Location
    value: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.value.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Expr(location=self.location, value=layer(self.value)))

    @override
    def codegen_stmt(self) -> list[ast.stmt]:
        stmt = ast.Expr(self.value.codegen_expr())
        self.location.locate(stmt)
        return [stmt]


@dataclass
class Absence(Term):
    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda _: Absence())


@dataclass
class Parameter(Term):
    location: Location
    name: str
    type_: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.type_.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Parameter(location=self.location, name=self.name, type_=layer(self.type_)))


@dataclass
class FunctionDef(TypedStatement):
    location: Location
    name: str
    parameters: list[Term]
    body: list[Term]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        for p in self.parameters:
            p.gather_errors(error_bucket)
        for s in self.body:
            s.gather_errors(error_bucket)

    @override
    def add_child(self, child: Term) -> None:
        self.body.append(child)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: FunctionDef(
                mode=layer(self.mode),
                location=self.location,
                name=self.name,
                parameters=[layer(p) for p in self.parameters],
                body=[layer(s) for s in self.body],
            )
        )

    def codegen_function(self, decorator_list: list[ast.expr]) -> ast.FunctionDef:
        params = [ast.arg(arg=cast(Parameter, p).name) for p in self.parameters]
        body = [s for b in self.body for s in b.codegen_stmt()]
        func = ast.FunctionDef(
            name=self.name, args=ast.arguments(args=params), body=body, decorator_list=decorator_list
        )
        self.location.locate(func)
        return func

    def gen_decorator(self) -> ast.expr:
        predef = ast.Name('predef', ctx=ast.Load())
        func = ast.Attribute(value=predef, attr='function_type', ctx=ast.Load())
        decorator = ast.Call(func=func, args=[cast(Parameter, p).type_.codegen_expr() for p in self.parameters])
        self.location.locate(func, decorator)
        return decorator

    @override
    def codegen_evaluate(self) -> list[ast.stmt]:
        if not all(isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise TaplError('All parameter type must be Absence when generating function in evaluate mode.')
        return [self.codegen_function(decorator_list=[])]

    @override
    def codegen_typecheck(self) -> list[ast.stmt]:
        if not all(not isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise TaplError('All parameter type must not be Absence when generating function in type-check mode.')
        return [self.codegen_function(decorator_list=[self.gen_decorator()])]


@dataclass
class Alias:
    name: str
    asname: str | None = None


@dataclass
class Import(Term):
    location: Location
    names: list[Alias]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda _: Import(location=self.location, names=[Alias(name=n.name, asname=n.asname) for n in self.names])
        )

    @override
    def codegen_stmt(self) -> list[ast.stmt]:
        stmt = ast.Import(names=[ast.alias(n.name, n.asname) for n in self.names])
        self.location.locate(stmt)
        return [stmt]


@dataclass
class ImportFrom(Term):
    location: Location
    module: str | None
    names: list[Alias]
    level: int

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda _: ImportFrom(
                location=self.location,
                module=self.module,
                names=[Alias(name=n.name, asname=n.asname) for n in self.names],
                level=self.level,
            )
        )

    @override
    def codegen_stmt(self) -> list[ast.stmt]:
        stmt = ast.ImportFrom(
            module=self.module, names=[ast.alias(n.name, n.asname) for n in self.names], level=self.level
        )
        self.location.locate(stmt)
        return [stmt]


@dataclass
class If(TypedStatement):
    location: Location
    test: Term
    body: list[Term]
    orelse: list[Term]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.test.gather_errors(error_bucket)
        for s in self.body:
            s.gather_errors(error_bucket)
        for s in self.orelse:
            s.gather_errors(error_bucket)

    @override
    def add_child(self, child: Term) -> None:
        self.body.append(child)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: If(
                mode=layer(self.mode),
                location=self.location,
                test=layer(self.test),
                body=[layer(s) for s in self.body],
                orelse=[layer(s) for s in self.orelse],
            )
        )

    @override
    def codegen_evaluate(self) -> list[ast.stmt]:
        if_stmt = ast.If(
            test=self.test.codegen_expr(),
            body=[s for b in self.body for s in b.codegen_stmt()],
            orelse=[s for b in self.orelse for s in b.codegen_stmt()],
        )
        self.location.locate(if_stmt)
        return [if_stmt]

    @override
    def codegen_typecheck(self) -> list[ast.stmt]:
        test_stmt = ast.Expr(self.test.codegen_expr())
        self.location.locate(test_stmt)
        result: list[ast.stmt] = [test_stmt]
        for s in self.body:
            result.extend(s.codegen_stmt())
        for s in self.orelse:
            result.extend(s.codegen_stmt())
        return result


@dataclass
class Module(Term):
    statements: list[Term] = field(default_factory=list)

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        for s in self.statements:
            s.gather_errors(error_bucket)

    @override
    def add_child(self, child: Term) -> None:
        return self.statements.append(child)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Module([layer(s) for s in self.statements]))

    @override
    def codegen_ast(self) -> ast.AST:
        body: list[ast.stmt] = []
        for b in self.statements:
            body.extend(b.codegen_stmt())
        return ast.Module(body=body)
