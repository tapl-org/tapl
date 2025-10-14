# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from collections.abc import Generator
from dataclasses import dataclass
from typing import cast, override

from tapl_lang.core import syntax, tapl_error
from tapl_lang.lib import python_backend, typed_terms, untyped_terms


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
    def unfold(self) -> syntax.Term:
        return untyped_terms.Assign(
            location=self.location,
            targets=self.targets,
            value=self.value,
        )

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


@dataclass
class Return(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Return(location=self.location, value=layer(self.value), mode=layer(self.mode)))

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is typed_terms.MODE_EVALUATE:
            return untyped_terms.Return(location=self.location, value=self.value)
        if self.mode is typed_terms.MODE_TYPECHECK:
            call = untyped_terms.Call(
                location=self.location,
                func=typed_terms.Path(
                    location=self.location, names=['api__tapl', 'add_return_type'], ctx='load', mode=self.mode
                ),
                args=[
                    untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                    self.value,
                ],
                keywords=[],
            )
            return untyped_terms.Expr(location=self.location, value=call)
        raise tapl_error.UnhandledError

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


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
    def unfold(self):
        return untyped_terms.Expr(location=self.location, value=self.value)

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


# TODO: Remove Absence, and implement it differently according to ground rules.
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
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.type_
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Parameter(
                location=self.location, name=self.name, type_=layer(self.type_), mode=layer(self.mode)
            )
        )

    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.type_.codegen_expr(setting)
        raise tapl_error.UnhandledError


@dataclass
class FunctionDef(syntax.Term):
    location: syntax.Location
    name: str
    parameters: list[syntax.Term]
    body: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.parameters
        yield self.body
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: FunctionDef(
                location=self.location,
                name=self.name,
                parameters=[layer(p) for p in self.parameters],
                body=layer(self.body),
                mode=layer(self.mode),
            )
        )

    def unfold_evaluate(self) -> syntax.Term:
        if not all(isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise tapl_error.TaplError('All parameter type must be Absence when generating function in evaluate mode.')

        return untyped_terms.FunctionDef(
            location=self.location,
            name=self.name,
            posonlyargs=[],
            args=[cast(Parameter, p).name for p in self.parameters],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
            body=self.body,
            decorator_list=[],
        )

    def unfold_typecheck_main(self) -> syntax.Term:
        def setting_changer(setting: syntax.AstSetting) -> syntax.AstSetting:
            return setting.clone(scope_level=setting.scope_level + 1)

        param_names = [cast(Parameter, p).name for p in self.parameters]

        keywords: list[tuple[str, syntax.Term]] = []
        keywords.append(
            (
                'parent__tapl',
                untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
            )
        )
        keywords.extend((name, untyped_terms.Name(location=self.location, id=name, ctx='load')) for name in param_names)
        new_scope = Assign(
            location=self.location,
            targets=[
                syntax.AstSettingChanger(
                    changer=setting_changer,
                    inner=untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                )
            ],
            value=typed_terms.Call(
                location=self.location,
                func=typed_terms.Path(
                    location=self.location, names=['api__tapl', 'create_scope'], ctx='load', mode=self.mode
                ),
                args=[],
                keywords=keywords,
            ),
        )

        nested_body = syntax.AstSettingChanger(changer=setting_changer, inner=self.body)

        return_type = syntax.AstSettingChanger(
            changer=setting_changer,
            inner=untyped_terms.Return(
                location=self.location,
                value=untyped_terms.Call(
                    location=self.location,
                    func=typed_terms.Path(
                        location=self.location, names=['api__tapl', 'get_return_type'], ctx='load', mode=self.mode
                    ),
                    args=[
                        untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load')
                    ],
                    keywords=[],
                ),
            ),
        )

        return untyped_terms.FunctionDef(
            location=self.location,
            name=self.name,
            posonlyargs=[],
            args=param_names,
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
            body=syntax.TermList(terms=[new_scope, nested_body, return_type]),
            decorator_list=[],
        )

    def unfold_typecheck_type(self) -> syntax.Term:
        if not all(not isinstance(cast(Parameter, p).type_, Absence) for p in self.parameters):
            raise tapl_error.TaplError(
                'All parameter type must not be Absence when generating function type in type-check mode.'
            )

        return Assign(
            location=self.location,
            targets=[typed_terms.Name(location=self.location, id=self.name, ctx='store', mode=self.mode)],
            value=typed_terms.Call(
                location=self.location,
                func=typed_terms.Path(
                    location=self.location, names=['api__tapl', 'create_function'], ctx='load', mode=self.mode
                ),
                args=[
                    untyped_terms.List(
                        location=self.location,
                        elts=[cast(Parameter, p).type_ for p in self.parameters],
                        ctx='load',
                    ),
                    typed_terms.Call(
                        location=self.location,
                        func=untyped_terms.Name(location=self.location, id=self.name, ctx='load'),
                        args=[cast(Parameter, p).type_ for p in self.parameters],
                        keywords=[],
                    ),
                ],
                keywords=[],
            ),
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.unfold_evaluate()
        if self.mode is typed_terms.MODE_TYPECHECK:
            return syntax.TermList(terms=[self.unfold_typecheck_main(), self.unfold_typecheck_type()])
        raise tapl_error.UnhandledError

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)

    def codegen_typecheck_main(self, setting: syntax.AstSetting) -> ast.stmt:
        params = [ast.arg(arg=cast(Parameter, p).name) for p in self.parameters]
        body: list[ast.stmt] = []
        body_setting = setting.clone(scope_level=setting.scope_level + 1)
        assign = ast.Assign(
            targets=[ast.Name(id=body_setting.scope_name, ctx=ast.Store())],
            value=ast.Call(
                func=ast_attribute([setting.scope_name, 'api__tapl', 'create_scope']),
                args=[],
                keywords=[ast.keyword(arg='parent__tapl', value=ast_name(setting.scope_name))]
                + [
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
                    func=ast_attribute([body_setting.scope_name, 'api__tapl', 'get_return_type']),
                    args=[ast_name(body_setting.scope_name)],
                )
            )
        )
        func = ast.FunctionDef(name=self.name, args=ast.arguments(args=params), body=body, decorator_list=[])
        self.location.locate(func)
        return func


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
    def unfold(self) -> syntax.Term:
        return untyped_terms.Import(
            location=self.location, names=[untyped_terms.Alias(name=n.name, asname=n.asname) for n in self.names]
        )

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


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
    def unfold(self) -> syntax.Term:
        return untyped_terms.ImportFrom(
            location=self.location,
            module=self.module,
            names=[untyped_terms.Alias(name=n.name, asname=n.asname) for n in self.names],
            level=self.level,
        )

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


# XXX: Implement unfold for this term, then move the todo to the next term #refactor


@dataclass
class If(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term | None  # FIXME: Make non none
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        if self.orelse is not None:
            yield self.orelse
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: If(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return untyped_terms.If(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        def nested_scope(inner_term: syntax.Term) -> syntax.Term:
            return syntax.AstSettingChanger(
                changer=lambda setting: setting.clone(scope_level=setting.scope_level + 1), inner=inner_term
            )

        def new_scope() -> syntax.Term:
            return Assign(
                location=self.location,
                targets=[
                    nested_scope(
                        untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='store')
                    )
                ],
                value=untyped_terms.Call(
                    location=self.location,
                    func=typed_terms.Path(
                        location=self.location, names=['api__tapl', 'fork_scope'], ctx='load', mode=self.mode
                    ),
                    args=[
                        untyped_terms.Name(location=self.location, id=lambda setting: setting.forker_name, ctx='load')
                    ],
                    keywords=[],
                ),
            )

        body: list[syntax.Term] = []

        body.append(new_scope())
        body.append(nested_scope(Expr(location=self.location, value=self.test)))
        body.append(nested_scope(self.body))
        body.append(new_scope())
        if self.orelse is not None:
            body.append(nested_scope(self.orelse))

        return untyped_terms.With(
            location=self.location,
            items=[
                untyped_terms.WithItem(
                    context_expr=typed_terms.Call(
                        location=self.location,
                        func=typed_terms.Path(
                            location=self.location, names=['api__tapl', 'scope_forker'], ctx='load', mode=self.mode
                        ),
                        args=[
                            untyped_terms.Name(
                                location=self.location, id=lambda setting: setting.scope_name, ctx='load'
                            )
                        ],
                        keywords=[],
                    ),
                    optional_vars=untyped_terms.Name(
                        location=self.location, id=lambda setting: setting.forker_name, ctx='store'
                    ),
                )
            ],
            body=syntax.TermList(terms=body),
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


@dataclass
class Else(syntax.SiblingTerm):
    location: syntax.Location
    body: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.body

    @override
    def integrate_into(self, previous_siblings: list[syntax.Term]) -> None:
        term = previous_siblings[-1]
        if isinstance(term, syntax.ErrorTerm):
            return
        if not isinstance(term, If):
            error = syntax.ErrorTerm('Else can only be integrated into If.' + repr(term), location=self.location)
            previous_siblings.append(error)
        elif term.orelse is not None:
            error = syntax.ErrorTerm('An If statement can only have one Else clause.', location=self.location)
            previous_siblings.append(error)
        else:
            term.orelse = self.body


@dataclass
class While(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term | None
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        if self.orelse is not None:
            yield self.orelse
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: While(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        while_stmt = ast.While(
            test=self.test.codegen_expr(setting),
            body=self.body.codegen_stmt(setting),
            orelse=self.orelse.codegen_stmt(setting) if self.orelse is not None else [],
        )
        self.location.locate(while_stmt)
        return [while_stmt]

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        def locate(ast_expr: ast.expr) -> ast.expr:
            self.location.locate(ast_expr)
            return ast_expr

        body_setting = setting.clone(scope_level=setting.scope_level + 1)
        body: list[ast.stmt] = []

        def add_new_scope_stmt() -> None:
            assign = ast.Assign(
                targets=[locate(ast.Name(id=body_setting.scope_name, ctx=ast.Store()))],
                value=ast.Call(
                    func=ast_attribute([setting.scope_name, 'api__tapl', 'fork_scope']),
                    args=[ast.Name(id=setting.forker_name, ctx=ast.Load())],
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
        if self.orelse is not None:
            body.extend(self.orelse.codegen_stmt(body_setting))
        with_stmt = ast.With(
            items=[
                ast.withitem(
                    context_expr=locate(
                        ast.Call(
                            func=ast_attribute([setting.scope_name, 'api__tapl', 'scope_forker']),
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
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.codegen_evaluate(setting)
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.codegen_typecheck(setting)
        raise tapl_error.UnhandledError


@dataclass
class For(syntax.Term):
    location: syntax.Location
    target: syntax.Term
    iter: syntax.Term
    body: syntax.Term
    orelse: syntax.Term | None
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.target
        yield self.iter
        yield self.body
        if self.orelse is not None:
            yield self.orelse
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: For(
                location=self.location,
                target=layer(self.target),
                iter=layer(self.iter),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        for_stmt = ast.For(
            target=self.target.codegen_expr(setting),
            iter=self.iter.codegen_expr(setting),
            body=self.body.codegen_stmt(setting),
            orelse=self.orelse.codegen_stmt(setting) if self.orelse is not None else [],
            type_comment=None,
        )
        self.location.locate(for_stmt)
        return [for_stmt]

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        def locate(ast_expr: ast.expr) -> ast.expr:
            self.location.locate(ast_expr)
            return ast_expr

        body_setting = setting.clone(scope_level=setting.scope_level + 1)
        body: list[ast.stmt] = []

        def add_new_scope_stmt() -> None:
            assign = ast.Assign(
                targets=[locate(ast.Name(id=body_setting.scope_name, ctx=ast.Store()))],
                value=ast.Call(
                    func=ast_attribute([setting.scope_name, 'api__tapl', 'fork_scope']),
                    args=[ast.Name(id=setting.forker_name, ctx=ast.Load())],
                ),
            )
            self.location.locate(assign)
            body.append(assign)

        def extract_iter_item(value: ast.expr) -> ast.expr:
            iterator = ast.Call(func=ast.Attribute(value=value, attr='__iter__'), args=[])
            return ast.Call(func=ast.Attribute(value=iterator, attr='__next__'), args=[])

        add_new_scope_stmt()
        header_stmt = ast.Assign(
            targets=[self.target.codegen_expr(body_setting)],
            value=extract_iter_item(self.iter.codegen_expr(body_setting)),
        )
        self.location.locate(header_stmt)
        body.append(header_stmt)
        body.extend(self.body.codegen_stmt(body_setting))
        add_new_scope_stmt()
        if self.orelse is not None:
            body.extend(self.orelse.codegen_stmt(body_setting))
        with_stmt = ast.With(
            items=[
                ast.withitem(
                    context_expr=locate(
                        ast.Call(
                            func=ast_attribute([setting.scope_name, 'api__tapl', 'scope_forker']),
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
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.codegen_evaluate(setting)
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.codegen_typecheck(setting)
        raise tapl_error.UnhandledError


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
    mode: syntax.Term

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
                mode=layer(self.mode),
            )
        )

    def _class_name(self) -> str:
        return f'{self.name}_'

    def codegen_evaluate(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        stmt = ast.ClassDef(
            name=self._class_name(),
            bases=[b.codegen_expr(setting) for b in self.bases],
            body=self.body.codegen_stmt(setting),
            decorator_list=[],
        )
        self.location.locate(stmt)
        return [stmt]

    def codegen_typecheck(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        instance_name = self.name
        class_name = self._class_name()
        body = []
        methods: list[FunctionDef] = []
        constructor_args = []
        for item in self.body.children():
            if isinstance(item, FunctionDef):
                if item.name == '__init__':
                    constructor_args = [p.codegen_expr(setting) for p in item.parameters[1:]]
                else:
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

        method_types: list[ast.expr] = []
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
            method_types.append(
                ast.Tuple(
                    elts=[ast.Constant(value=method.name), ast.List(elts=tail_args, ctx=ast.Load())], ctx=ast.Load()
                )
            )

        create_class = ast.Assign(
            targets=[
                ast.Tuple(
                    elts=[
                        ast_attribute([setting.scope_name, instance_name], ctx=ast.Store()),
                        ast_attribute([setting.scope_name, class_name], ctx=ast.Store()),
                    ],
                    ctx=ast.Store(),
                )
            ],
            value=ast.Call(
                func=ast_attribute([setting.scope_name, 'api__tapl', 'create_class']),
                args=[],
                keywords=[
                    ast.keyword(arg='cls', value=ast_name(class_name)),
                    ast.keyword(arg='init_args', value=ast.List(elts=constructor_args, ctx=ast.Load())),
                    ast.keyword(arg='methods', value=ast.List(elts=method_types, ctx=ast.Load())),
                ],
            ),
        )
        self.location.locate(create_class)

        return [class_stmt, create_class]

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.codegen_evaluate(setting)
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.codegen_typecheck(setting)
        raise tapl_error.UnhandledError
