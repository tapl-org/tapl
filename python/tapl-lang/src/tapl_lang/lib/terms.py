# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import Any, cast, override

from tapl_lang.core import syntax, tapl_error

################################################################################
# Python AST Terms
#
# These terms closely mirror the classes in the `ast` module.
# Keep them sorted as in https://docs.python.org/3/library/ast.html
################################################################################

type Identifier = str | Callable[[syntax.BackendSetting], str]


@dataclass
class Module(syntax.Term):
    body: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Module(body=[layer(b) for b in self.body]))


################################################################################
# STATEMENTS

# TODO: move the location to the end of the dataclass fields for readability.


@dataclass
class FunctionDef(syntax.Term):
    location: syntax.Location
    name: Identifier
    posonlyargs: list[str]
    args: list[str]
    vararg: str | None
    kwonlyargs: list[str]
    kw_defaults: list[syntax.Term]
    kwarg: str | None
    defaults: list[syntax.Term]
    body: syntax.Term
    decorator_list: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.kw_defaults
        yield from self.defaults
        yield self.body
        yield from self.decorator_list

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: FunctionDef(
                location=self.location,
                name=self.name,
                posonlyargs=self.posonlyargs,
                args=self.args,
                vararg=self.vararg,
                kwonlyargs=self.kwonlyargs,
                kw_defaults=[layer(k) for k in self.kw_defaults],
                kwarg=self.kwarg,
                defaults=[layer(d) for d in self.defaults],
                body=layer(self.body),
                decorator_list=[layer(d) for d in self.decorator_list],
            )
        )


@dataclass
class ClassDef(syntax.Term):
    location: syntax.Location
    name: Identifier
    bases: list[syntax.Term]
    keywords: list[tuple[str, syntax.Term]]
    body: list[syntax.Term]
    decorator_list: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.bases
        yield from (t for _, t in self.keywords)
        yield from self.body
        yield from self.decorator_list

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: ClassDef(
                location=self.location,
                name=self.name,
                bases=[layer(b) for b in self.bases],
                keywords=[(k, layer(v)) for k, v in self.keywords],
                body=[layer(b) for b in self.body],
                decorator_list=[layer(d) for d in self.decorator_list],
            )
        )


@dataclass
class Return(syntax.Term):
    location: syntax.Location
    value: syntax.Term | None

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        if self.value is not None:
            yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Return(location=self.location, value=layer(self.value) if self.value else None))


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


@dataclass
class For(syntax.Term):
    location: syntax.Location
    target: syntax.Term
    iter: syntax.Term
    body: syntax.Term
    orelse: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.target
        yield self.iter
        yield self.body
        yield self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: For(
                location=self.location,
                target=layer(self.target),
                iter=layer(self.iter),
                body=layer(self.body),
                orelse=layer(self.orelse),
            )
        )


@dataclass
class While(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        yield self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: While(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse),
            )
        )


@dataclass
class If(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        yield self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: If(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse),
            )
        )


@dataclass
class WithItem:
    context_expr: syntax.Term
    optional_vars: syntax.Term | None = None


@dataclass
class With(syntax.Term):
    location: syntax.Location
    items: list[WithItem]
    body: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        for item in self.items:
            yield item.context_expr
            if item.optional_vars is not None:
                yield item.optional_vars
        yield self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: With(
                location=self.location,
                items=[
                    WithItem(
                        context_expr=layer(t.context_expr),
                        optional_vars=layer(t.optional_vars) if t.optional_vars is not None else None,
                    )
                    for t in self.items
                ],
                body=layer(self.body),
            )
        )


@dataclass
class Raise(syntax.Term):
    location: syntax.Location
    exception: syntax.Term
    cause: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.exception
        yield self.cause

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Raise(
                location=self.location,
                exception=layer(self.exception),
                cause=layer(self.cause),
            )
        )


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


@dataclass
class Pass(syntax.Term):
    location: syntax.Location

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Pass(location=self.location))


################################################################################
# EXPRESSIONS


@dataclass
class BoolOp(syntax.Term):
    location: syntax.Location
    operator: str
    values: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.values

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BoolOp(location=self.location, operator=self.operator, values=[layer(v) for v in self.values])
        )


@dataclass
class NamedExpr(syntax.Term):
    location: syntax.Location
    target: syntax.Term
    value: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.target
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: NamedExpr(
                location=self.location,
                target=layer(self.target),
                value=layer(self.value),
            )
        )


@dataclass
class BinOp(syntax.Term):
    location: syntax.Location
    left: syntax.Term
    op: str
    right: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.left
        yield self.right

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BinOp(location=self.location, left=layer(self.left), op=self.op, right=layer(self.right))
        )


@dataclass
class UnaryOp(syntax.Term):
    location: syntax.Location
    op: str
    operand: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.operand

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: UnaryOp(location=self.location, op=self.op, operand=layer(self.operand)))


@dataclass
class Set(syntax.Term):
    location: syntax.Location
    elements: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Set(location=self.location, elements=[layer(v) for v in self.elements]))


@dataclass
class Dict(syntax.Term):
    location: syntax.Location
    keys: list[syntax.Term]
    values: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.keys
        yield from self.values

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Dict(
                location=self.location,
                keys=[layer(k) for k in self.keys],
                values=[layer(v) for v in self.values],
            )
        )


@dataclass
class Compare(syntax.Term):
    location: syntax.Location
    left: syntax.Term
    operators: list[str]
    comparators: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.left
        yield from self.comparators

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Compare(
                location=self.location,
                left=layer(self.left),
                operators=self.operators,
                comparators=[layer(v) for v in self.comparators],
            )
        )


@dataclass
class Call(syntax.Term):
    location: syntax.Location
    func: syntax.Term
    args: list[syntax.Term]
    keywords: list[tuple[str, syntax.Term]]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.func
        yield from self.args
        yield from (v for _, v in self.keywords)

    @override
    def separate(self, ls) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Call(
                location=self.location,
                func=layer(self.func),
                args=[layer(v) for v in self.args],
                keywords=[(k, layer(v)) for k, v in self.keywords],
            )
        )


@dataclass
class Constant(syntax.Term):
    location: syntax.Location
    value: Any

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Constant(location=self.location, value=self.value))


@dataclass
class Attribute(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    attr: Identifier
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Attribute(location=self.location, value=layer(self.value), attr=self.attr, ctx=self.ctx)
        )


@dataclass
class Subscript(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    slice: syntax.Term
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value
        yield self.slice

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Subscript(
                location=self.location,
                value=layer(self.value),
                slice=layer(self.slice),
                ctx=self.ctx,
            )
        )


@dataclass
class Name(syntax.Term):
    location: syntax.Location
    id: Identifier
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Name(location=self.location, id=self.id, ctx=self.ctx))


@dataclass
class List(syntax.Term):
    location: syntax.Location
    elements: list[syntax.Term]
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: List(location=self.location, elements=[layer(v) for v in self.elements], ctx=self.ctx)
        )


@dataclass
class Tuple(syntax.Term):
    location: syntax.Location
    elements: list[syntax.Term]
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Tuple(location=self.location, elements=[layer(v) for v in self.elements], ctx=self.ctx)
        )


@dataclass
class Slice(syntax.Term):
    location: syntax.Location
    lower: syntax.Term
    upper: syntax.Term
    step: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.lower
        yield self.upper
        yield self.step

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Slice(
                location=self.location,
                lower=layer(self.lower),
                upper=layer(self.upper),
                step=layer(self.step),
            )
        )


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
            value = Attribute(location=self.location, value=value, attr=self.names[i], ctx='load')
        return Attribute(location=self.location, value=value, attr=self.names[-1], ctx=self.ctx)


@dataclass
class Path(syntax.Term):
    location: syntax.Location
    names: list[str]
    # TODO: Find a better name for the ctx field. options: context, reference_mode
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
            value = Attribute(location=self.location, value=value, attr=self.names[i], ctx='load')
        return Attribute(location=self.location, value=value, attr=self.names[-1], ctx=self.ctx)


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
                    nested_scope(Name(location=self.location, id=lambda setting: setting.scope_name, ctx='store'))
                ],
                value=Call(
                    location=self.location,
                    func=Path(
                        location=self.location,
                        names=['tapl_typing', 'fork_scope'],
                        ctx='load',
                        mode=MODE_TYPECHECK,
                    ),
                    args=[Name(location=self.location, id=lambda setting: setting.forker_name, ctx='load')],
                    keywords=[],
                ),
            )

        body: list[syntax.Term] = []
        for b in self.branches:
            body.append(new_scope())
            body.append(nested_scope(b))

        return With(
            location=self.location,
            items=[
                WithItem(
                    context_expr=Call(
                        location=self.location,
                        func=Path(
                            location=self.location,
                            names=['tapl_typing', 'scope_forker'],
                            ctx='load',
                            mode=MODE_TYPECHECK,
                        ),
                        args=[Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load')],
                        keywords=[],
                    ),
                    optional_vars=Name(location=self.location, id=lambda setting: setting.forker_name, ctx='store'),
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


@dataclass
class TypedName(syntax.Term):
    location: syntax.Location
    id: Identifier
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
            return Name(location=self.location, id=self.id, ctx=self.ctx)
        if self.mode is MODE_TYPECHECK:
            return Attribute(
                location=self.location,
                value=Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                attr=self.id,
                ctx=self.ctx,
            )
        raise tapl_error.UnhandledError


@dataclass
class TypedAssign(syntax.Term):
    location: syntax.Location
    target_name: syntax.Term
    target_type: syntax.Term
    value: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.target_name
        yield self.target_type
        yield self.value
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedAssign(
                location=self.location,
                target_name=layer(self.target_name),
                target_type=layer(self.target_type),
                value=layer(self.value),
                mode=layer(self.mode),
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return Assign(
                location=self.location,
                targets=[self.target_name],
                value=self.value,
            )
        if self.mode is MODE_TYPECHECK:
            expected = Assign(location=self.location, targets=[self.target_name], value=self.target_type)
            assigned = Assign(location=self.location, targets=[self.target_name], value=self.value)
            return syntax.TermList(terms=[expected, assigned])
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
            Constant(location=self.location, value=value),
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
class TypedList(syntax.Term):
    location: syntax.Location
    elements: list[syntax.Term]
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedList(
                location=self.location,
                elements=[layer(e) for e in self.elements],
                mode=layer(self.mode),
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return List(location=self.location, elements=self.elements, ctx='load')
        if self.mode is MODE_TYPECHECK:
            return Call(
                location=self.location,
                func=Path(
                    location=self.location,
                    names=['tapl_typing', 'create_typed_list'],
                    ctx='load',
                    mode=self.mode,
                ),
                args=self.elements,
                keywords=[],
            )
        raise tapl_error.UnhandledError


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
            return UnaryOp(location=self.location, op='not', operand=self.operand)
        if self.mode is MODE_TYPECHECK:
            # unary not operator always returns Bool type
            return TypedName(location=self.location, id='Bool', ctx='load', mode=MODE_TYPECHECK)
        raise tapl_error.UnhandledError


@dataclass
class TypedBoolOp(syntax.Term):
    location: syntax.Location
    operator: str
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
                location=self.location,
                operator=self.operator,
                values=[layer(v) for v in self.values],
                mode=layer(self.mode),
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return BoolOp(location=self.location, operator=self.operator, values=self.values)
        if self.mode is MODE_TYPECHECK:
            return Call(
                location=self.location,
                func=Path(location=self.location, names=['tapl_typing', 'create_union'], ctx='load', mode=self.mode),
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
            return Return(location=self.location, value=self.value)
        if self.mode is MODE_TYPECHECK:
            call = Call(
                location=self.location,
                func=Path(location=self.location, names=['tapl_typing', 'add_return_type'], ctx='load', mode=self.mode),
                args=[
                    Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                    self.value,
                ],
                keywords=[],
            )
            return Expr(location=self.location, value=call)
        raise tapl_error.UnhandledError


# TODO: Add Parameters type to represent list of parameters which support posonly and kwonly args
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


# TODO: Implement posonly_args, regular_args, vararg, kwonly_args, kwarg, defaults if needed
@dataclass
class TypedFunctionDef(syntax.Term):
    location: syntax.Location
    name: str
    parameters: list[syntax.Term]
    return_type: syntax.Term
    body: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.parameters
        yield self.return_type
        yield self.body
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedFunctionDef(
                location=self.location,
                name=self.name,
                return_type=layer(self.return_type),
                parameters=[layer(p) for p in self.parameters],
                body=layer(self.body),
                mode=layer(self.mode),
            )
        )

    def unfold_evaluate(self) -> syntax.Term:
        if not all(cast(Parameter, p).type_ is syntax.Empty for p in self.parameters):
            raise tapl_error.TaplError('All parameter type must be Empty when generating function in evaluate mode.')

        return FunctionDef(
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
                Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
            )
        )
        keywords.extend((name, Name(location=self.location, id=name, ctx='load')) for name in param_names)
        new_scope = Assign(
            location=self.location,
            targets=[
                nested_scope(
                    Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                )
            ],
            value=Call(
                location=self.location,
                func=Path(location=self.location, names=['tapl_typing', 'create_scope'], ctx='load', mode=self.mode),
                args=[],
                keywords=keywords,
            ),
        )
        set_return_type: syntax.Term = syntax.Empty
        if self.return_type is not syntax.Empty:
            set_return_type = Expr(
                location=self.location,
                value=Call(
                    location=self.location,
                    func=Path(
                        location=self.location, names=['tapl_typing', 'set_return_type'], ctx='load', mode=self.mode
                    ),
                    args=[
                        Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                        self.return_type,
                    ],
                    keywords=[],
                ),
            )

        get_return_type = Return(
            location=self.location,
            value=Call(
                location=self.location,
                func=Path(location=self.location, names=['tapl_typing', 'get_return_type'], ctx='load', mode=self.mode),
                args=[Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load')],
                keywords=[],
            ),
        )

        return FunctionDef(
            location=self.location,
            name=self.name,
            posonlyargs=[],
            args=param_names,
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
            body=syntax.TermList(
                terms=[new_scope, nested_scope(syntax.TermList(terms=[set_return_type, self.body, get_return_type]))]
            ),
            decorator_list=[],
        )

    def unfold_typecheck_type(self) -> syntax.Term:
        if not all(cast(Parameter, p).type_ is not syntax.Empty for p in self.parameters):
            raise tapl_error.TaplError(
                'All parameter type must not be Empty when generating function type in type-check mode.'
            )

        return Assign(
            location=self.location,
            targets=[TypedName(location=self.location, id=self.name, ctx='store', mode=self.mode)],
            value=Call(
                location=self.location,
                func=Path(location=self.location, names=['tapl_typing', 'create_function'], ctx='load', mode=self.mode),
                args=[
                    List(
                        location=self.location,
                        elements=[cast(Parameter, p).type_ for p in self.parameters],
                        ctx='load',
                    ),
                    Call(
                        location=self.location,
                        func=Name(location=self.location, id=self.name, ctx='load'),
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
    elifs: list[tuple[syntax.Term, syntax.Term]]  # (test, body)
    orelse: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        for test, body in self.elifs:
            yield test
            yield body
        yield self.orelse
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedIf(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                elifs=[(layer(test), layer(body)) for test, body in self.elifs],
                orelse=layer(self.orelse),
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return If(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse,
        )

    def codegen_typecheck(self) -> syntax.Term:
        true_side = syntax.TermList(terms=[Expr(location=self.location, value=self.test), self.body])
        return BranchTyping(location=self.location, branches=[true_side, self.orelse])

    @override
    def unfold(self) -> syntax.Term:
        # TODO: handle elifs
        if self.elifs:
            raise tapl_error.UnhandledError('Elif clauses are not yet supported in TypedIf unfold.')
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclass
class ElifSibling(syntax.SiblingTerm):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body

    @override
    def integrate_into(self, previous_siblings: list[syntax.Term]) -> None:
        term = previous_siblings[-1]
        if isinstance(term, syntax.ErrorTerm):
            return
        if not isinstance(term, TypedIf):
            error = syntax.ErrorTerm('Elif can only be integrated into If.' + repr(term), location=self.location)
            previous_siblings.append(error)
        else:
            term.elifs.append((self.test, self.body))


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
        elif term.orelse is not syntax.Empty:
            error = syntax.ErrorTerm('An If statement can only have one Else clause.', location=self.location)
            previous_siblings.append(error)
        else:
            term.orelse = self.body


@dataclass
class TypedWhile(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        yield self.orelse
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedWhile(
                location=self.location,
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse),
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return While(
            location=self.location,
            test=self.test,
            body=self.body,
            orelse=self.orelse,
        )

    def codegen_typecheck(self) -> syntax.Term:
        return TypedIf(
            location=self.location,
            test=self.test,
            body=self.body,
            elifs=[],
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
    orelse: syntax.Term
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.target
        yield self.iter
        yield self.body
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
                orelse=layer(self.orelse),
                mode=layer(self.mode),
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return For(
            location=self.location,
            target=self.target,
            iter=self.iter,
            body=self.body,
            orelse=self.orelse,
        )

    def codegen_typecheck(self) -> syntax.Term:
        iterator_type = Call(
            location=self.location,
            func=Attribute(location=self.location, value=self.iter, attr='__iter__', ctx='load'),
            args=[],
            keywords=[],
        )
        item_type = Call(
            location=self.location,
            func=Attribute(location=self.location, value=iterator_type, attr='__next__', ctx='load'),
            args=[],
            keywords=[],
        )
        assign_target = Assign(
            location=self.location,
            targets=[self.target],
            value=item_type,
        )
        for_branch = syntax.TermList(terms=[assign_target, self.body])
        return BranchTyping(
            location=self.location,
            branches=[for_branch, self.orelse],
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
        return ClassDef(
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
        class_stmt = ClassDef(
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
                and method.parameters[0].type_ is syntax.Empty
            ):
                raise tapl_error.TaplError(
                    f'First parameter of method {method.name} in class {class_name} must be self with no type annotation.'
                )
            tail_args = method.parameters[1:]
            method_types.append(
                Tuple(
                    location=self.location,
                    elements=[
                        Constant(location=self.location, value=method.name),
                        List(location=self.location, elements=tail_args, ctx='load'),
                    ],
                    ctx='load',
                )
            )

        create_class = Assign(
            location=self.location,
            targets=[
                Tuple(
                    location=self.location,
                    elements=[
                        TypedName(location=self.location, id=instance_name, ctx='store', mode=self.mode),
                        TypedName(location=self.location, id=class_name, ctx='store', mode=self.mode),
                    ],
                    ctx='store',
                )
            ],
            value=Call(
                location=self.location,
                func=Path(location=self.location, names=['tapl_typing', 'create_class'], ctx='load', mode=self.mode),
                args=[],
                keywords=[
                    ('cls', Name(location=self.location, id=class_name, ctx='load')),
                    ('init_args', List(location=self.location, elements=constructor_args, ctx='load')),
                    ('methods', List(location=self.location, elements=method_types, ctx='load')),
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
