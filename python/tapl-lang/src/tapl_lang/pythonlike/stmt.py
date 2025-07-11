# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from collections.abc import Generator
from dataclasses import dataclass
from typing import cast, override

from tapl_lang.core import syntax, tapl_error


def ast_name(name: str, ctx: ast.expr_context | None = None) -> ast.expr:
    """Create an AST name with the given context."""
    if not name:
        raise ValueError('Name cannot be empty.')
    return ast.Name(id=name, ctx=ctx or ast.Load())


def ast_attribute(names: list[str], ctx: ast.expr_context | None = None) -> ast.expr:
    """Create an AST attribute from a list of names."""
    if not names:
        raise ValueError('Names list cannot be empty.')

    def get_ctx(i: int) -> ast.expr_context:
        return (ctx or ast.Load()) if i == len(names) - 1 else ast.Load()

    attr: ast.expr = ast.Name(id=names[0], ctx=get_ctx(0))
    for i, name in enumerate(names[1:], start=1):
        attr = ast.Attribute(value=attr, attr=name, ctx=get_ctx(i))
    return attr


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

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.Return(self.value.codegen_expr(setting)) if self.value else ast.Return()
        self.location.locate(stmt)
        return [stmt]

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        def locate(ast_expr: ast.expr) -> ast.expr:
            self.location.locate(ast_expr)
            return ast_expr

        stmt = ast.Expr(
            value=locate(
                ast.Call(
                    func=locate(
                        ast.Attribute(value=locate(ast.Name(id='predef', ctx=ast.Load())), attr='add_return_type')
                    ),
                    args=[locate(ast.Name(id=setting.scope_name, ctx=ast.Load())), self.value.codegen_expr(setting)],
                )
            )
        )
        self.location.locate(stmt)
        return [stmt]

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if setting.code_evaluate and setting.scope_native:
            return self.codegen_evaluate(setting)
        if setting.code_typecheck and setting.scope_manual:
            return self.codegen_typecheck(setting)
        raise tapl_error.UnhandledError


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

    def codegen_expr(self, setting):
        if setting.code_typecheck and setting.scope_manual:
            return self.type_.codegen_expr(setting)
        raise tapl_error.UnhandledError


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

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if not all(isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise tapl_error.TaplError('All parameter type must be Absence when generating function in evaluate mode.')

        params = [ast.arg(arg=cast(Parameter, p).name) for p in self.parameters]
        body: list[ast.stmt] = []
        body.extend(self.body.codegen_stmt(setting))
        func = ast.FunctionDef(name=self.name, args=ast.arguments(args=params), body=body, decorator_list=[])
        self.location.locate(func)
        return [func]

    def codegen_typecheck_main(self, setting: syntax.AstSetting) -> ast.stmt:
        params = [ast.arg(arg=cast(Parameter, p).name) for p in self.parameters]
        body: list[ast.stmt] = []
        body_setting = setting.clone(scope_level=setting.scope_level + 1)
        assign = ast.Assign(
            targets=[ast.Name(id=body_setting.scope_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast_attribute(['predef', 'Scope']),
                args=[ast_name(setting.scope_name)],
                keywords=[
                    ast.keyword(
                        arg=cast(Parameter, p).name,
                        value=ast_name(cast(Parameter, p).name),
                    )
                    for p in self.parameters
                ],
            ),
        )
        self.location.locate(assign)
        body.append(assign)

        body.extend(self.body.codegen_stmt(body_setting))
        body.append(
            ast.Return(
                value=ast.Call(
                    func=ast_attribute(['predef', 'get_return_type']),
                    args=[ast_name(body_setting.scope_name)],
                )
            )
        )
        func = ast.FunctionDef(name=self.name, args=ast.arguments(args=params), body=body, decorator_list=[])
        self.location.locate(func)
        return func

    def codegen_typecheck_type(self, setting: syntax.AstSetting) -> ast.stmt:
        if not all(not isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise tapl_error.TaplError(
                'All parameter type must not be Absence when generating function type in type-check mode.'
            )

        assign = ast.Assign(
            targets=[ast_attribute([setting.scope_name, self.name], ctx=ast.Store())],
            value=ast.Call(
                func=ast_attribute(['predef', 'FunctionType']),
                args=[
                    ast.List(
                        elts=[cast(Parameter, p).type_.codegen_expr(setting) for p in self.parameters],
                        ctx=ast.Load(),
                    ),
                    ast.Call(
                        func=ast_name(self.name),
                        args=[cast(Parameter, p).type_.codegen_expr(setting) for p in self.parameters],
                    ),
                ],
            ),
        )
        self.location.locate(assign)
        return assign

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return [self.codegen_typecheck_main(setting), self.codegen_typecheck_type(setting)]

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if setting.code_evaluate and setting.scope_native:
            return self.codegen_evaluate(setting)
        if setting.code_typecheck and setting.scope_manual:
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
        if setting.scope_native:
            raise tapl_error.TaplError('"If" statement type-checking does not support native scope.')

        def locate(ast_expr: ast.expr) -> ast.expr:
            self.location.locate(ast_expr)
            return ast_expr

        body_setting = setting.clone(scope_level=setting.scope_level + 1)
        body: list[ast.stmt] = []

        def add_new_scope_stmt() -> None:
            assign = ast.Assign(
                targets=[locate(ast.Name(id=body_setting.scope_name, ctx=ast.Store()))],
                value=ast.Call(
                    func=locate(
                        ast.Attribute(
                            value=locate(ast.Name(id=setting.forker_name, ctx=ast.Load())),
                            attr='new_scope',
                            ctx=ast.Load(),
                        )
                    ),
                ),
            )
            self.location.locate(assign)
            body.append(assign)

        add_new_scope_stmt()
        test_stmt = ast.Expr(self.test.codegen_expr(body_setting))
        self.location.locate(test_stmt)
        body.append(test_stmt)
        body.extend(self.body.codegen_stmt(body_setting))
        add_new_scope_stmt()
        if self.orelse:
            body.extend(self.orelse.codegen_stmt(body_setting))
        with_stmt = ast.With(
            items=[
                ast.withitem(
                    context_expr=locate(
                        ast.Call(
                            func=locate(ast.Attribute(locate(ast.Name('predef', ctx=ast.Load())), attr='ScopeForker')),
                            args=[locate(ast.Name(id=setting.scope_name))],
                        )
                    ),
                    optional_vars=locate(ast.Name(id=setting.forker_name, ctx=ast.Store())),
                )
            ],
            body=body,
            type_comment=None,
        )
        self.location.locate(with_stmt)
        return [with_stmt]

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
class Pass(syntax.Term):
    location: syntax.Location

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Pass(location=self.location))

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.Pass()
        self.location.locate(stmt)
        return [stmt]


@dataclass
class ClassDef(syntax.Term):
    location: syntax.Location
    name: str
    bases: list[syntax.Term]
    body: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.bases
        yield self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: ClassDef(
                location=self.location,
                name=self.name,
                bases=[layer(b) for b in self.bases],
                body=layer(self.body),
            )
        )

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.ClassDef(
            name=self.name,
            bases=[b.codegen_expr(setting) for b in self.bases],
            body=self.body.codegen_stmt(setting),
            decorator_list=[],
        )
        self.location.locate(stmt)
        return [stmt]

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if not isinstance(self.body, syntax.Block):
            raise tapl_error.TaplError('Class body must be a Block for type-checking.')
        class_name = self.name
        instance_name = f'{class_name}_'
        body = []
        methods: list[FunctionDef] = []
        init_method = None
        for item in self.body.children():
            if isinstance(item, FunctionDef):
                if item.name == '__init__':
                    init_method = item
                methods.append(item)
                body.append(item.codegen_typecheck_main(setting))
            else:
                body.extend(item.codegen_stmt(setting))
        class_stmt = ast.ClassDef(
            name=class_name,
            bases=[b.codegen_expr(setting) for b in self.bases],
            body=body,
            decorator_list=[],
        )
        self.location.locate(class_stmt)

        def declare_class(namespace: str) -> ast.stmt:
            assign = ast.Assign(
                targets=[ast_attribute([setting.scope_name, namespace], ctx=ast.Store())],
                value=ast.Call(
                    func=ast_attribute(['predef', 'Scope']),
                    keywords=[
                        ast.keyword('label__tapl', ast.Constant(value=namespace)),
                    ],
                ),
            )
            self.location.locate(assign)
            return assign

        def declare_method(namespace: str, method_name: str, args: list[ast.expr], result: ast.expr) -> ast.stmt:
            assign = ast.Assign(
                targets=[ast_attribute([setting.scope_name, namespace, method_name], ctx=ast.Store())],
                value=ast.Call(
                    func=ast_attribute(['predef', 'FunctionType']),
                    args=[
                        ast.List(elts=args, ctx=ast.Load()),
                        result,
                    ],
                ),
            )
            self.location.locate(assign)
            return assign

        method_types = []
        for method in methods:
            # The first parameter is the instance itself, so we can set it to the instance type.
            if not (
                len(method.parameters) >= 1
                and isinstance(method.parameters[0], Parameter)
                and isinstance(method.parameters[0].type_, Absence)
            ):
                raise tapl_error.TaplError(
                    f'First parameter of method {method.name} in class {class_name} must be self with no type annotation.'
                )
            tail_args = [p.codegen_expr(setting) for p in method.parameters[1:]]
            class_args = [ast_attribute([setting.scope_name, instance_name]), *tail_args]
            method_types.append(
                declare_method(
                    namespace=class_name,
                    method_name=method.name,
                    args=class_args,
                    result=ast.Call(
                        func=ast_attribute([class_name, method.name]),
                        args=class_args,
                    ),
                )
            )
            method_types.append(
                declare_method(
                    namespace=instance_name,
                    method_name=method.name,
                    args=tail_args,
                    result=ast_attribute([setting.scope_name, class_name, method.name, 'result']),
                )
            )
        constructor_args = []
        if init_method:
            constructor_args = [p.codegen_expr(setting) for p in init_method.parameters[1:]]
        constructor = declare_method(
            namespace=class_name,
            method_name='__call__',
            args=[ast_attribute([setting.scope_name, class_name]), *constructor_args],
            result=ast_attribute([setting.scope_name, instance_name]),
        )

        return [class_stmt, declare_class(class_name), declare_class(instance_name), *method_types, constructor]

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if setting.code_evaluate and setting.scope_native:
            return self.codegen_evaluate(setting)
        if setting.code_typecheck and setting.scope_manual:
            return self.codegen_typecheck(setting)
        raise tapl_error.UnhandledError


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
