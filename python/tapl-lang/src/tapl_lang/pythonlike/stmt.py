# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass, field
from typing import cast, override

from tapl_lang import syntax, tapl_error


@dataclass
class Sequence(syntax.Term):
    statements: list[syntax.Term]

    @override
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        for s in self.statements:
            s.gather_errors(error_bucket)

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Sequence(statements=[layer(s) for s in self.statements]))

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return [s for b in self.statements for s in b.codegen_stmt(setting)]


@dataclass
class Assign(syntax.Term):
    location: syntax.Location
    targets: list[syntax.Term]
    value: syntax.Term

    @override
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        for t in self.targets:
            t.gather_errors(error_bucket)
        self.value.gather_errors(error_bucket)

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
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        if self.value:
            self.value.gather_errors(error_bucket)

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
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        self.value.gather_errors(error_bucket)

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
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        pass

    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Absence())


@dataclass
class Parameter(syntax.Term):
    location: syntax.Location
    name: str
    type_: syntax.Term

    @override
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        self.type_.gather_errors(error_bucket)

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Parameter(location=self.location, name=self.name, type_=layer(self.type_)))


@dataclass
class FunctionDef(syntax.Term):
    location: syntax.Location
    name: str
    parameters: list[syntax.Term]
    body: list[syntax.Term]

    @override
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        for p in self.parameters:
            p.gather_errors(error_bucket)
        for s in self.body:
            s.gather_errors(error_bucket)

    @override
    def add_child(self, child: syntax.Term) -> None:
        self.body.append(child)

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: FunctionDef(
                location=self.location,
                name=self.name,
                parameters=[layer(p) for p in self.parameters],
                body=[layer(s) for s in self.body],
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
        body.extend(s for b in self.body for s in b.codegen_stmt(body_setting))
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
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        pass

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
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        pass

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
    body: list[syntax.Term]
    orelse: list[syntax.Term]

    @override
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        self.test.gather_errors(error_bucket)
        for s in self.body:
            s.gather_errors(error_bucket)
        for s in self.orelse:
            s.gather_errors(error_bucket)

    @override
    def add_child(self, child: syntax.Term) -> None:
        self.body.append(child)

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: If(
                location=self.location,
                test=layer(self.test),
                body=[layer(s) for s in self.body],
                orelse=[layer(s) for s in self.orelse],
            )
        )

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if_stmt = ast.If(
            test=self.test.codegen_expr(setting),
            body=[s for b in self.body for s in b.codegen_stmt(setting)],
            orelse=[s for b in self.orelse for s in b.codegen_stmt(setting)],
        )
        self.location.locate(if_stmt)
        return [if_stmt]

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        test_stmt = ast.Expr(self.test.codegen_expr(setting))
        self.location.locate(test_stmt)
        result: list[ast.stmt] = [test_stmt]
        for s in self.body:
            result.extend(s.codegen_stmt(setting))
        for s in self.orelse:
            result.extend(s.codegen_stmt(setting))
        return result

    @override
    def codegen_stmt(self, setting):
        if setting.code_evaluate:
            return self.codegen_evaluate(setting)
        if setting.code_typecheck:
            return self.codegen_typecheck(setting)
        raise tapl_error.UnhandledError


@dataclass
class Module(syntax.Term):
    statements: list[syntax.Term] = field(default_factory=list)

    @override
    def gather_errors(self, error_bucket: list[syntax.ErrorTerm]) -> None:
        for s in self.statements:
            s.gather_errors(error_bucket)

    @override
    def add_child(self, child: syntax.Term) -> None:
        return self.statements.append(child)

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Module([layer(s) for s in self.statements]))

    @override
    def codegen_ast(self, setting: syntax.AstSetting) -> ast.AST:
        body: list[ast.stmt] = []
        for b in self.statements:
            body.extend(b.codegen_stmt(setting))
        return ast.Module(body=body)
