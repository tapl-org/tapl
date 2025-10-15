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
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
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
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
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
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
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

    def codegen_expr(self, setting: syntax.BackendSetting) -> ast.expr:
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
        def nested_scope(nested_term: syntax.Term) -> syntax.Term:
            return syntax.BackendSettingTerm(
                backend_setting_changer=syntax.BackendSettingChanger(
                    lambda setting: setting.clone(scope_level=setting.scope_level + 1)
                ),
                term=nested_term,
            )

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
                nested_scope(
                    untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
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

        return_type = untyped_terms.Return(
            location=self.location,
            value=untyped_terms.Call(
                location=self.location,
                func=typed_terms.Path(
                    location=self.location, names=['api__tapl', 'get_return_type'], ctx='load', mode=self.mode
                ),
                args=[untyped_terms.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load')],
                keywords=[],
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
            body=syntax.TermList(terms=[new_scope, nested_scope(self.body), nested_scope(return_type)]),
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
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)

    def codegen_typecheck_main(self, setting: syntax.BackendSetting) -> ast.stmt:
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
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
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
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


@dataclass
class BranchTyping(syntax.Term):
    location: syntax.Location
    branches: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.branches

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: BranchTyping(location=self.location, branches=[layer(b) for b in self.branches]))

    @override
    def unfold(self) -> syntax.Term:
        def nested_scope(inner_term: syntax.Term) -> syntax.Term:
            return syntax.BackendSettingTerm(
                backend_setting_changer=syntax.BackendSettingChanger(
                    lambda setting: setting.clone(scope_level=setting.scope_level + 1)
                ),
                term=inner_term,
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
                        location=self.location,
                        names=['api__tapl', 'fork_scope'],
                        ctx='load',
                        mode=typed_terms.MODE_TYPECHECK,
                    ),
                    args=[
                        untyped_terms.Name(location=self.location, id=lambda setting: setting.forker_name, ctx='load')
                    ],
                    keywords=[],
                ),
            )

        body: list[syntax.Term] = []
        for b in self.branches:
            body.append(new_scope())
            body.append(nested_scope(b))

        return untyped_terms.With(
            location=self.location,
            items=[
                untyped_terms.WithItem(
                    context_expr=typed_terms.Call(
                        location=self.location,
                        func=typed_terms.Path(
                            location=self.location,
                            names=['api__tapl', 'scope_forker'],
                            ctx='load',
                            mode=typed_terms.MODE_TYPECHECK,
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
        true_side = syntax.TermList(terms=[Expr(location=self.location, value=self.test), self.body])
        false_side = self.orelse if self.orelse is not None else syntax.TermList(terms=[])
        return BranchTyping(location=self.location, branches=[true_side, false_side])

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError

    @override
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
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
            lambda layer: While(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return untyped_terms.While(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        return If(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse,
            mode=self.mode,
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError

    @override
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


@dataclass
class For(syntax.Term):
    location: syntax.Location
    target: syntax.Term
    iter: syntax.Term
    body: syntax.Term
    orelse: syntax.Term | None  # FIXME: Make non none
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

    def codegen_evaluate(self) -> syntax.Term:
        return untyped_terms.For(
            location=self.location,
            target=self.target,
            iter=self.iter,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        iterator_type = untyped_terms.Call(
            location=self.location,
            func=untyped_terms.Attribute(location=self.location, value=self.iter, attr='__iter__', ctx='load'),
            args=[],
            keywords=[],
        )
        item_type = untyped_terms.Call(
            location=self.location,
            func=untyped_terms.Attribute(location=self.location, value=iterator_type, attr='__next__', ctx='load'),
            args=[],
            keywords=[],
        )
        assign_target = Assign(
            location=self.location,
            targets=[self.target],
            value=item_type,
        )
        for_branch = syntax.TermList(terms=[assign_target, self.body])
        else_branch = self.orelse if self.orelse is not None else syntax.TermList(terms=[])
        return BranchTyping(
            location=self.location,
            branches=[for_branch, else_branch],
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError

    @override
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


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
    def unfold(self) -> syntax.Term:
        return untyped_terms.Pass(location=self.location)

    @override
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)


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

    def codegen_evaluate(self) -> syntax.Term:
        return untyped_terms.ClassDef(
            location=self.location,
            name=self._class_name(),
            bases=self.bases,
            keywords=[],
            body=[self.body],
            decorator_list=[],
        )

    def codegen_typecheck(self) -> syntax.Term:
        instance_name = self.name
        class_name = self._class_name()
        body = []
        methods: list[FunctionDef] = []
        constructor_args = []
        for item in self.body.children():
            if isinstance(item, FunctionDef):
                if item.name == '__init__':
                    constructor_args = item.parameters[1:]
                else:
                    methods.append(item)
                body.append(item.unfold_typecheck_main())
            else:
                body.append(item)
        class_stmt = untyped_terms.ClassDef(
            location=self.location,
            name=class_name,
            bases=self.bases,
            keywords=[],
            body=body,
            decorator_list=[],
        )

        method_types: list[syntax.Term] = []
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
            tail_args = method.parameters[1:]
            method_types.append(
                untyped_terms.Tuple(
                    location=self.location,
                    elts=[
                        untyped_terms.Constant(location=self.location, value=method.name),
                        untyped_terms.List(location=self.location, elts=tail_args, ctx='load'),
                    ],
                    ctx='load',
                )
            )

        create_class = untyped_terms.Assign(
            location=self.location,
            targets=[
                untyped_terms.Tuple(
                    location=self.location,
                    elts=[
                        typed_terms.Name(location=self.location, id=instance_name, ctx='store', mode=self.mode),
                        typed_terms.Name(location=self.location, id=class_name, ctx='store', mode=self.mode),
                    ],
                    ctx='store',
                )
            ],
            value=untyped_terms.Call(
                location=self.location,
                func=typed_terms.Path(
                    location=self.location, names=['api__tapl', 'create_class'], ctx='load', mode=self.mode
                ),
                args=[],
                keywords=[
                    ('cls', untyped_terms.Name(location=self.location, id=class_name, ctx='load')),
                    ('init_args', untyped_terms.List(location=self.location, elts=constructor_args, ctx='load')),
                    ('methods', untyped_terms.List(location=self.location, elts=method_types, ctx='load')),
                ],
            ),
        )

        return syntax.TermList(terms=[class_stmt, create_class])

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is typed_terms.MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is typed_terms.MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError

    @override
    def codegen_stmt(self, setting: syntax.BackendSetting) -> list[ast.stmt]:
        return python_backend.generate_stmt(self, setting)
