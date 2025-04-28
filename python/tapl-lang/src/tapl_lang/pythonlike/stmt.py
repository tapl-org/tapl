# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from collections.abc import Generator
from dataclasses import dataclass
from typing import cast, override

from tapl_lang import syntax, tapl_error


@dataclass
class Assign(syntax.Term):
    location: syntax.Location
    targets: list[syntax.Term]
    value: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.targets
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Assign(
                location=self.location, targets=[layer(t) for t in self.targets], value=layer(self.value)
            )
        )

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.Assign(
            targets=[t.codegen_expr(setting) for t in self.targets], value=self.value.codegen_expr(setting)
        )
        self.location.locate(stmt)
        return [stmt]


@dataclass
class Return(syntax.Term):
    location: syntax.Location
    value: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Return(location=self.location, value=layer(self.value)))

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.Return(self.value.codegen_expr(setting)) if self.value else ast.Return()
        self.location.locate(stmt)
        return [stmt]


@dataclass
class Expr(syntax.Term):
    location: syntax.Location
    value: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Expr(location=self.location, value=layer(self.value)))

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.Expr(self.value.codegen_expr(setting))
        self.location.locate(stmt)
        return [stmt]


@dataclass
class Absence(syntax.Term):
    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Absence())


@dataclass
class Parameter(syntax.Term):
    location: syntax.Location
    name: str
    type_: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.type_

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Parameter(location=self.location, name=self.name, type_=layer(self.type_)))


@dataclass
class FunctionDef(syntax.Term):
    location: syntax.Location
    name: str
    parameters: list[syntax.Term]
    body: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.parameters
        yield self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: FunctionDef(
                location=self.location,
                name=self.name,
                parameters=[layer(p) for p in self.parameters],
                body=layer(self.body),
            )
        )

    def codegen_function(self, setting: syntax.AstSetting, decorator_list: list[ast.expr]) -> ast.FunctionDef:
        def locate(ast_expr: ast.expr) -> ast.expr:
            self.location.locate(ast_expr)
            return ast_expr

        params = [ast.arg(arg=cast(Parameter, p).name) for p in self.parameters]
        body: list[ast.stmt] = []
        if setting.scope_manual:
            body_setting = setting.clone(scope_level=setting.scope_level + 1)
            assign = ast.Assign(
                targets=[locate(ast.Name(id=body_setting.scope_name, ctx=ast.Store()))],
                value=ast.Call(
                    func=locate(
                        ast.Attribute(value=locate(ast.Name(id='predef', ctx=ast.Load())), attr='Scope', ctx=ast.Load())
                    ),
                    args=[locate(ast.Name(id=setting.scope_name, ctx=ast.Load()))],
                    keywords=[
                        ast.keyword(
                            arg=cast(Parameter, p).name,
                            value=locate(ast.Name(id=cast(Parameter, p).name, ctx=ast.Load())),
                        )
                        for p in self.parameters
                    ],
                ),
            )
            self.location.locate(assign)
            body.append(assign)
        else:
            body_setting = setting
        body.extend(self.body.codegen_stmt(body_setting))
        func = ast.FunctionDef(
            name=self.name, args=ast.arguments(args=params), body=body, decorator_list=decorator_list
        )
        self.location.locate(func)
        return func

    def gen_decorator(self, setting: syntax.AstSetting) -> ast.expr:
        predef = ast.Name('predef', ctx=ast.Load())
        func = ast.Attribute(value=predef, attr='function_type', ctx=ast.Load())
        decorator = ast.Call(func=func, args=[cast(Parameter, p).type_.codegen_expr(setting) for p in self.parameters])
        self.location.locate(func, decorator)
        return decorator

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if not all(isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise tapl_error.TaplError('All parameter type must be Absence when generating function in evaluate mode.')
        return [self.codegen_function(setting, decorator_list=[])]

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if not all(not isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise tapl_error.TaplError(
                'All parameter type must not be Absence when generating function in type-check mode.'
            )
        if setting.scope_native:
            return [self.codegen_function(setting, decorator_list=[self.gen_decorator(setting)])]
        if setting.scope_manual:

            def locate(ast_expr: ast.expr) -> ast.expr:
                self.location.locate(ast_expr)
                return ast_expr

            func = self.codegen_function(setting, decorator_list=[])
            assign = ast.Assign(
                targets=[
                    ast.Attribute(
                        value=locate(ast.Name(id=setting.scope_name, ctx=ast.Load())), attr=self.name, ctx=ast.Store()
                    )
                ],
                value=locate(
                    ast.Call(
                        func=ast.Attribute(
                            value=locate(ast.Name(id='predef', ctx=ast.Load())), attr='FunctionType', ctx=ast.Load()
                        ),
                        args=[
                            ast.List(
                                elts=[cast(Parameter, p).type_.codegen_expr(setting) for p in self.parameters],
                                ctx=ast.Load(),
                            ),
                            locate(
                                ast.Call(
                                    func=locate(ast.Name(id=self.name, ctx=ast.Load())),
                                    args=[cast(Parameter, p).type_.codegen_expr(setting) for p in self.parameters],
                                )
                            ),
                        ],
                    )
                ),
            )
            self.location.locate(assign)
            return [func, assign]
        raise tapl_error.UnhandledError

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if setting.code_evaluate:
            return self.codegen_evaluate(setting)
        if setting.code_typecheck:
            return self.codegen_typecheck(setting)
        raise tapl_error.UnhandledError


@dataclass
class Alias:
    name: str
    asname: str | None = None


@dataclass
class Import(syntax.Term):
    location: syntax.Location
    names: list[Alias]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda _: Import(location=self.location, names=[Alias(name=n.name, asname=n.asname) for n in self.names])
        )

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.Import(names=[ast.alias(n.name, n.asname) for n in self.names])
        self.location.locate(stmt)
        return [stmt]


@dataclass
class ImportFrom(syntax.Term):
    location: syntax.Location
    module: str | None
    names: list[Alias]
    level: int

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda _: ImportFrom(
                location=self.location,
                module=self.module,
                names=[Alias(name=n.name, asname=n.asname) for n in self.names],
                level=self.level,
            )
        )

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.ImportFrom(
            module=self.module, names=[ast.alias(n.name, n.asname) for n in self.names], level=self.level
        )
        self.location.locate(stmt)
        return [stmt]


@dataclass
class If(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term | None

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        if self.orelse is not None:
            yield self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: If(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse else None,
            )
        )

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if_stmt = ast.If(
            test=self.test.codegen_expr(setting),
            body=self.body.codegen_stmt(setting),
            orelse=self.orelse.codegen_stmt(setting) if self.orelse else [],
        )
        self.location.locate(if_stmt)
        return [if_stmt]

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        test_stmt = ast.Expr(self.test.codegen_expr(setting))
        self.location.locate(test_stmt)
        result: list[ast.stmt] = [test_stmt]
        result.extend(self.body.codegen_stmt(setting))
        if self.orelse:
            result.extend(self.orelse.codegen_stmt(setting))
        return result

    @override
    def codegen_stmt(self, setting):
        if setting.code_evaluate:
            return self.codegen_evaluate(setting)
        if setting.code_typecheck:
            return self.codegen_typecheck(setting)
        raise tapl_error.UnhandledError


@dataclass
class Else(syntax.DependentTerm):
    location: syntax.Location
    body: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.body

    @override
    def merge_into(self, block: syntax.Block) -> None:
        term = block.terms[-1]
        if isinstance(term, syntax.ErrorTerm):
            return
        if not isinstance(term, If):
            error = syntax.ErrorTerm('Else can only be merged into If.' + repr(term), location=self.location)
            block.terms.append(error)
        elif term.orelse is not None:
            error = syntax.ErrorTerm('An If statement can only have one Else clause.', location=self.location)
            block.terms.append(error)
        else:
            term.orelse = self.body


@dataclass
class Module(syntax.Term):
    body: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Module(layer(self.body)))

    @override
    def codegen_ast(self, setting: syntax.AstSetting) -> ast.AST:
        return ast.Module(body=self.body.codegen_stmt(setting))
