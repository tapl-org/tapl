# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, cast, override

from tapl_lang.core import syntax, tapl_error
from tapl_lang.lib import terms2

################################################################################
# Untyped Terms
#
# These terms extend the Python AST terms defined above.
################################################################################


@dataclass
class Select(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    names: list[str]
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Select(
                location=self.location,
                value=layer(self.value),
                names=self.names,
                ctx=self.ctx,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if not self.names:
            return syntax.ErrorTerm(location=self.location, message='At least one name is required to select a path.')
        value = self.value
        for i in range(len(self.names) - 1):
            value = terms2.Attribute(location=self.location, value=value, attr=self.names[i], ctx='load')
        return terms2.Attribute(location=self.location, value=value, attr=self.names[-1], ctx=self.ctx)


@dataclass
class Path(syntax.Term):
    location: syntax.Location
    names: list[str]
    ctx: str
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Path(location=self.location, names=self.names, ctx=self.ctx, mode=layer(self.mode))
        )

    @override
    def unfold(self) -> syntax.Term:
        if len(self.names) <= 1:
            return syntax.ErrorTerm(location=self.location, message='At least two names are required to create a path.')
        value: syntax.Term = TypedName(location=self.location, id=self.names[0], ctx='load', mode=self.mode)
        for i in range(1, len(self.names) - 1):
            value = terms2.Attribute(location=self.location, value=value, attr=self.names[i], ctx='load')
        return terms2.Attribute(location=self.location, value=value, attr=self.names[-1], ctx=self.ctx)


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
            return terms2.Assign(
                location=self.location,
                targets=[
                    nested_scope(
                        terms2.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='store')
                    )
                ],
                value=terms2.Call(
                    location=self.location,
                    func=Path(
                        location=self.location,
                        names=['api__tapl', 'fork_scope'],
                        ctx='load',
                        mode=MODE_TYPECHECK,
                    ),
                    args=[terms2.Name(location=self.location, id=lambda setting: setting.forker_name, ctx='load')],
                    keywords=[],
                ),
            )

        body: list[syntax.Term] = []
        for b in self.branches:
            body.append(new_scope())
            body.append(nested_scope(b))

        return terms2.With(
            location=self.location,
            items=[
                terms2.WithItem(
                    context_expr=terms2.Call(
                        location=self.location,
                        func=Path(
                            location=self.location,
                            names=['api__tapl', 'scope_forker'],
                            ctx='load',
                            mode=MODE_TYPECHECK,
                        ),
                        args=[terms2.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load')],
                        keywords=[],
                    ),
                    optional_vars=terms2.Name(
                        location=self.location, id=lambda setting: setting.forker_name, ctx='store'
                    ),
                )
            ],
            body=syntax.TermList(terms=body),
        )


################################################################################
# Typed Terms
#
# These terms add a type layer to enable type checking.
################################################################################


@dataclass
class ModeTerm(syntax.Term):
    name: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: self)

    def __repr__(self) -> str:
        return self.name


MODE_EVALUATE = ModeTerm(name='MODE_EVALUATE')
MODE_TYPECHECK = ModeTerm(name='MODE_TYPECHECK')
MODE_SAFE = syntax.Layers(layers=[MODE_EVALUATE, MODE_TYPECHECK])
SAFE_LAYER_COUNT = len(MODE_SAFE.layers)


# FIXME: Find different names fro typed terms to distinguish from untyped terms
@dataclass
class TypedName(syntax.Term):
    location: syntax.Location
    id: str  # FIXME: should be identifier
    ctx: str
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedName(location=self.location, id=self.id, ctx=self.ctx, mode=layer(self.mode))
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return terms2.Name(location=self.location, id=self.id, ctx=self.ctx)
        if self.mode is MODE_TYPECHECK:
            return terms2.Attribute(
                location=self.location,
                value=terms2.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                attr=self.id,
                ctx=self.ctx,
            )
        raise tapl_error.UnhandledError


@dataclass
class Literal(syntax.Term):
    location: syntax.Location

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    def typeit(self, ls: syntax.LayerSeparator, value: Any, type_id: str) -> list[syntax.Term]:
        if ls.layer_count != SAFE_LAYER_COUNT:
            raise ValueError('NoneLiteral must be separated in 2 layers')
        return [
            terms2.Constant(location=self.location, value=value),
            TypedName(location=self.location, id=type_id, ctx='load', mode=MODE_TYPECHECK),
        ]


@dataclass
class NoneLiteral(Literal):
    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=None, type_id='NoneType')


@dataclass
class BooleanLiteral(Literal):
    value: bool

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Bool')


@dataclass
class IntegerLiteral(Literal):
    value: int

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Int')


@dataclass
class FloatLiteral(Literal):
    value: float

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Float')


@dataclass
class StringLiteral(Literal):
    value: str

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Str')


@dataclass
class ListIntLiteral(Literal):
    location: syntax.Location

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: ListIntLiteral(location=self.location))

    @override
    def unfold(self) -> syntax.Term:
        return terms2.List(location=self.location, elts=[], ctx='load')


@dataclass
class BoolNot(syntax.Term):
    location: syntax.Location
    operand: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.operand
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BoolNot(location=self.location, operand=layer(self.operand), mode=layer(self.mode))
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return terms2.UnaryOp(location=self.location, op='not', operand=self.operand)
        if self.mode is MODE_TYPECHECK:
            # unary not operator always returns Bool type
            return TypedName(location=self.location, id='Bool', ctx='load', mode=MODE_TYPECHECK)
        raise tapl_error.UnhandledError


@dataclass
class TypedBoolOp(syntax.Term):
    location: syntax.Location
    op: str
    values: list[syntax.Term]
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.values
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedBoolOp(
                location=self.location, op=self.op, values=[layer(v) for v in self.values], mode=layer(self.mode)
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return terms2.BoolOp(location=self.location, op=self.op, values=self.values)
        if self.mode is MODE_TYPECHECK:
            return terms2.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_union'], ctx='load', mode=self.mode),
                args=self.values,
                keywords=[],
            )
        raise tapl_error.UnhandledError


@dataclass
class TypedReturn(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedReturn(location=self.location, value=layer(self.value), mode=layer(self.mode))
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return terms2.Return(location=self.location, value=self.value)
        if self.mode is MODE_TYPECHECK:
            call = terms2.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'add_return_type'], ctx='load', mode=self.mode),
                args=[
                    terms2.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                    self.value,
                ],
                keywords=[],
            )
            return terms2.Expr(location=self.location, value=call)
        raise tapl_error.UnhandledError


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

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_TYPECHECK:
            return self.type_
        raise tapl_error.UnhandledError


@dataclass
class TypedFunctionDef(syntax.Term):
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
            lambda layer: TypedFunctionDef(
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

        return terms2.FunctionDef(
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
                terms2.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
            )
        )
        keywords.extend((name, terms2.Name(location=self.location, id=name, ctx='load')) for name in param_names)
        new_scope = terms2.Assign(
            location=self.location,
            targets=[
                nested_scope(
                    terms2.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                )
            ],
            value=terms2.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_scope'], ctx='load', mode=self.mode),
                args=[],
                keywords=keywords,
            ),
        )

        return_type = terms2.Return(
            location=self.location,
            value=terms2.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'get_return_type'], ctx='load', mode=self.mode),
                args=[terms2.Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load')],
                keywords=[],
            ),
        )

        return terms2.FunctionDef(
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

        return terms2.Assign(
            location=self.location,
            targets=[TypedName(location=self.location, id=self.name, ctx='store', mode=self.mode)],
            value=terms2.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_function'], ctx='load', mode=self.mode),
                args=[
                    terms2.List(
                        location=self.location,
                        elts=[cast(Parameter, p).type_ for p in self.parameters],
                        ctx='load',
                    ),
                    terms2.Call(
                        location=self.location,
                        func=terms2.Name(location=self.location, id=self.name, ctx='load'),
                        args=[cast(Parameter, p).type_ for p in self.parameters],
                        keywords=[],
                    ),
                ],
                keywords=[],
            ),
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.unfold_evaluate()
        if self.mode is MODE_TYPECHECK:
            return syntax.TermList(terms=[self.unfold_typecheck_main(), self.unfold_typecheck_type()])
        raise tapl_error.UnhandledError


@dataclass
class TypedIf(syntax.Term):
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
            lambda layer: TypedIf(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return terms2.If(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        true_side = syntax.TermList(terms=[terms2.Expr(location=self.location, value=self.test), self.body])
        false_side = self.orelse if self.orelse is not None else syntax.TermList(terms=[])
        return BranchTyping(location=self.location, branches=[true_side, false_side])

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclass
class ElseSibling(syntax.SiblingTerm):
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
        if not isinstance(term, TypedIf):
            error = syntax.ErrorTerm('Else can only be integrated into If.' + repr(term), location=self.location)
            previous_siblings.append(error)
        elif term.orelse is not None:
            error = syntax.ErrorTerm('An If statement can only have one Else clause.', location=self.location)
            previous_siblings.append(error)
        else:
            term.orelse = self.body


@dataclass
class TypedWhile(syntax.Term):
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
            lambda layer: TypedWhile(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return terms2.While(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        return TypedIf(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse,
            mode=self.mode,
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclass
class TypedFor(syntax.Term):
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
            lambda layer: TypedFor(
                location=self.location,
                target=layer(self.target),
                iter=layer(self.iter),
                body=layer(self.body),
                orelse=layer(self.orelse) if self.orelse is not None else None,
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return terms2.For(
            location=self.location,
            target=self.target,
            iter=self.iter,
            body=self.body,
            orelse=self.orelse if self.orelse is not None else syntax.TermList(terms=[]),
        )

    def codegen_typecheck(self) -> syntax.Term:
        iterator_type = terms2.Call(
            location=self.location,
            func=terms2.Attribute(location=self.location, value=self.iter, attr='__iter__', ctx='load'),
            args=[],
            keywords=[],
        )
        item_type = terms2.Call(
            location=self.location,
            func=terms2.Attribute(location=self.location, value=iterator_type, attr='__next__', ctx='load'),
            args=[],
            keywords=[],
        )
        assign_target = terms2.Assign(
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
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclass
class TypedClassDef(syntax.Term):
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
            lambda layer: TypedClassDef(
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
        return terms2.ClassDef(
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
        methods: list[TypedFunctionDef] = []
        constructor_args = []
        for item in self.body.children():
            if isinstance(item, TypedFunctionDef):
                if item.name == '__init__':
                    constructor_args = item.parameters[1:]
                else:
                    methods.append(item)
                body.append(item.unfold_typecheck_main())
            else:
                body.append(item)
        class_stmt = terms2.ClassDef(
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
                terms2.Tuple(
                    location=self.location,
                    elts=[
                        terms2.Constant(location=self.location, value=method.name),
                        terms2.List(location=self.location, elts=tail_args, ctx='load'),
                    ],
                    ctx='load',
                )
            )

        create_class = terms2.Assign(
            location=self.location,
            targets=[
                terms2.Tuple(
                    location=self.location,
                    elts=[
                        TypedName(location=self.location, id=instance_name, ctx='store', mode=self.mode),
                        TypedName(location=self.location, id=class_name, ctx='store', mode=self.mode),
                    ],
                    ctx='store',
                )
            ],
            value=terms2.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_class'], ctx='load', mode=self.mode),
                args=[],
                keywords=[
                    ('cls', terms2.Name(location=self.location, id=class_name, ctx='load')),
                    ('init_args', terms2.List(location=self.location, elts=constructor_args, ctx='load')),
                    ('methods', terms2.List(location=self.location, elts=method_types, ctx='load')),
                ],
            ),
        )

        return syntax.TermList(terms=[class_stmt, create_class])

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError
