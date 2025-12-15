# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import dataclasses
from collections.abc import Callable, Generator
from typing import Any, cast, override

from tapl_lang.core import syntax, tapl_error

################################################################################
# Python AST Terms
#
# These terms closely mirror the classes in the `ast` module.
# Keep them sorted as in https://docs.python.org/3/library/ast.html
################################################################################

type Identifier = str | Callable[[syntax.BackendSetting], str]


@dataclasses.dataclass
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


@dataclasses.dataclass
class FunctionDef(syntax.Term):
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
    location: syntax.Location = dataclasses.field(repr=False)

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
                location=self.location,
            )
        )


@dataclasses.dataclass
class ClassDef(syntax.Term):
    name: Identifier
    bases: list[syntax.Term]
    keywords: list[tuple[str, syntax.Term]]
    body: syntax.Term
    decorator_list: list[syntax.Term]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.bases
        yield from (t for _, t in self.keywords)
        yield self.body
        yield from self.decorator_list

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: ClassDef(
                name=self.name,
                bases=[layer(b) for b in self.bases],
                keywords=[(k, layer(v)) for k, v in self.keywords],
                body=layer(self.body),
                decorator_list=[layer(d) for d in self.decorator_list],
                location=self.location,
            )
        )


@dataclasses.dataclass
class Return(syntax.Term):
    value: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        if self.value is None:
            raise ValueError('Return statement must have a value')
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Return(value=layer(self.value), location=self.location))


@dataclasses.dataclass
class Delete(syntax.Term):
    targets: list[syntax.Term]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.targets

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Delete(targets=[layer(t) for t in self.targets], location=self.location))


@dataclasses.dataclass
class Assign(syntax.Term):
    targets: list[syntax.Term]
    value: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.targets
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Assign(
                targets=[layer(t) for t in self.targets], value=layer(self.value), location=self.location
            )
        )


@dataclasses.dataclass
class For(syntax.Term):
    target: syntax.Term
    iter: syntax.Term
    body: syntax.Term
    orelse: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

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
                target=layer(self.target),
                iter=layer(self.iter),
                body=layer(self.body),
                orelse=layer(self.orelse),
                location=self.location,
            )
        )


@dataclasses.dataclass
class While(syntax.Term):
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        yield self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: While(
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse),
                location=self.location,
            )
        )


@dataclasses.dataclass
class If(syntax.Term):
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield self.body
        yield self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: If(
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse),
                location=self.location,
            )
        )


@dataclasses.dataclass
class WithItem(syntax.Term):
    context_expr: syntax.Term
    optional_vars: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.context_expr
        yield self.optional_vars

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: WithItem(
                context_expr=layer(self.context_expr),
                optional_vars=layer(self.optional_vars),
            )
        )


@dataclasses.dataclass
class With(syntax.Term):
    items: list[syntax.Term]
    body: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.items
        yield self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: With(
                items=[layer(i) for i in self.items],
                body=layer(self.body),
                location=self.location,
            )
        )


@dataclasses.dataclass
class Raise(syntax.Term):
    exception: syntax.Term
    cause: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.exception
        yield self.cause

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Raise(
                exception=layer(self.exception),
                cause=layer(self.cause),
                location=self.location,
            )
        )


@dataclasses.dataclass
class Try(syntax.Term):
    body: syntax.Term
    handlers: list[syntax.Term]
    orelse: syntax.Term
    finalbody: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.body
        yield from self.handlers
        yield self.orelse
        yield self.finalbody

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Try(
                body=layer(self.body),
                handlers=[layer(h) for h in self.handlers],
                orelse=layer(self.orelse),
                finalbody=layer(self.finalbody),
                location=self.location,
            )
        )


@dataclasses.dataclass
class ExceptHandler(syntax.Term):
    exception_type: syntax.Term
    name: Identifier | None
    body: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.exception_type
        yield self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: ExceptHandler(
                exception_type=layer(self.exception_type),
                name=self.name,
                body=layer(self.body),
                location=self.location,
            )
        )


@dataclasses.dataclass
class Alias:
    name: str
    asname: str | None = None


@dataclasses.dataclass
class Import(syntax.Term):
    names: list[Alias]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda _: Import(names=[Alias(name=n.name, asname=n.asname) for n in self.names], location=self.location)
        )


@dataclasses.dataclass
class ImportFrom(syntax.Term):
    module: str | None
    names: list[Alias]
    level: int
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda _: ImportFrom(
                module=self.module,
                names=[Alias(name=n.name, asname=n.asname) for n in self.names],
                level=self.level,
                location=self.location,
            )
        )


@dataclasses.dataclass
class Expr(syntax.Term):
    value: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Expr(value=layer(self.value), location=self.location))


@dataclasses.dataclass
class Pass(syntax.Term):
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Pass(location=self.location))


################################################################################
# EXPRESSIONS


@dataclasses.dataclass
class BoolOp(syntax.Term):
    operator: str
    values: list[syntax.Term]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.values

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BoolOp(operator=self.operator, values=[layer(v) for v in self.values], location=self.location)
        )


# XXX: target of ast.NamedExpr accepts only ast.Name. This prevents us to assign attributes like s0.name := s0.Int. Figure out how to support that.
@dataclasses.dataclass
class NamedExpr(syntax.Term):
    target: syntax.Term
    value: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.target
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: NamedExpr(
                target=layer(self.target),
                value=layer(self.value),
                location=self.location,
            )
        )


@dataclasses.dataclass
class BinOp(syntax.Term):
    left: syntax.Term
    op: str
    right: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.left
        yield self.right

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BinOp(left=layer(self.left), op=self.op, right=layer(self.right), location=self.location)
        )


@dataclasses.dataclass
class UnaryOp(syntax.Term):
    op: str
    operand: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.operand

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: UnaryOp(op=self.op, operand=layer(self.operand), location=self.location))


@dataclasses.dataclass
class Set(syntax.Term):
    elements: list[syntax.Term]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Set(elements=[layer(v) for v in self.elements], location=self.location))


@dataclasses.dataclass
class Dict(syntax.Term):
    keys: list[syntax.Term]
    values: list[syntax.Term]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.keys
        yield from self.values

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Dict(
                keys=[layer(k) for k in self.keys],
                values=[layer(v) for v in self.values],
                location=self.location,
            )
        )


@dataclasses.dataclass
class Compare(syntax.Term):
    left: syntax.Term
    operators: list[str]
    comparators: list[syntax.Term]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.left
        yield from self.comparators

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Compare(
                left=layer(self.left),
                operators=self.operators,
                comparators=[layer(v) for v in self.comparators],
                location=self.location,
            )
        )


@dataclasses.dataclass
class Call(syntax.Term):
    func: syntax.Term
    args: list[syntax.Term]
    keywords: list[tuple[str, syntax.Term]]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.func
        yield from self.args
        yield from (v for _, v in self.keywords)

    @override
    def separate(self, ls) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Call(
                func=layer(self.func),
                args=[layer(v) for v in self.args],
                keywords=[(k, layer(v)) for k, v in self.keywords],
                location=self.location,
            )
        )


@dataclasses.dataclass
class Constant(syntax.Term):
    value: Any
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Constant(value=self.value, location=self.location))


@dataclasses.dataclass
class Attribute(syntax.Term):
    value: syntax.Term
    attr: Identifier
    ctx: str
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Attribute(value=layer(self.value), attr=self.attr, ctx=self.ctx, location=self.location)
        )


@dataclasses.dataclass
class Subscript(syntax.Term):
    value: syntax.Term
    slice: syntax.Term
    ctx: str
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value
        yield self.slice

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Subscript(
                value=layer(self.value),
                slice=layer(self.slice),
                ctx=self.ctx,
                location=self.location,
            )
        )


@dataclasses.dataclass
class Name(syntax.Term):
    id: Identifier
    ctx: str
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Name(id=self.id, ctx=self.ctx, location=self.location))


@dataclasses.dataclass
class List(syntax.Term):
    elements: list[syntax.Term]
    ctx: str
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: List(elements=[layer(v) for v in self.elements], ctx=self.ctx, location=self.location)
        )


@dataclasses.dataclass
class Tuple(syntax.Term):
    elements: list[syntax.Term]
    ctx: str
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Tuple(elements=[layer(v) for v in self.elements], ctx=self.ctx, location=self.location)
        )


@dataclasses.dataclass
class Slice(syntax.Term):
    lower: syntax.Term
    upper: syntax.Term
    step: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.lower
        yield self.upper
        yield self.step

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Slice(
                lower=layer(self.lower),
                upper=layer(self.upper),
                step=layer(self.step),
                location=self.location,
            )
        )


################################################################################
# Untyped Terms
#
# These terms extend the Python AST terms defined above.
################################################################################


@dataclasses.dataclass
class Select(syntax.Term):
    value: syntax.Term
    names: list[str]
    ctx: str
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Select(
                value=layer(self.value),
                names=self.names,
                ctx=self.ctx,
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if not self.names:
            return syntax.ErrorTerm(
                message='At least one name is required to select a path.',
                location=self.location,
            )
        value = self.value
        for i in range(len(self.names) - 1):
            value = Attribute(
                value=value,
                attr=self.names[i],
                ctx='load',
                location=self.location,
            )
        return Attribute(
            value=value,
            attr=self.names[-1],
            ctx=self.ctx,
            location=self.location,
        )


@dataclasses.dataclass
class Path(syntax.Term):
    names: list[str]
    # XXX: Find a better name for the ctx field. options: context, reference_mode
    ctx: str
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Path(names=self.names, ctx=self.ctx, mode=layer(self.mode), location=self.location)
        )

    @override
    def unfold(self) -> syntax.Term:
        if len(self.names) <= 1:
            return syntax.ErrorTerm(message='At least two names are required to create a path.', location=self.location)
        value: syntax.Term = TypedName(location=self.location, id=self.names[0], ctx='load', mode=self.mode)
        for i in range(1, len(self.names) - 1):
            value = Attribute(value=value, attr=self.names[i], ctx='load', location=self.location)
        return Attribute(value=value, attr=self.names[-1], ctx=self.ctx, location=self.location)


@dataclasses.dataclass
class BranchTyping(syntax.Term):
    branches: list[syntax.Term]
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.branches

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: BranchTyping(branches=[layer(b) for b in self.branches], location=self.location))

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
                targets=[
                    nested_scope(
                        Name(
                            id=lambda setting: setting.scope_name,
                            ctx='store',
                            location=self.location,
                        )
                    )
                ],
                value=Call(
                    func=Path(
                        names=['tapl_typing', 'fork_scope'],
                        ctx='load',
                        mode=MODE_TYPECHECK,
                        location=self.location,
                    ),
                    args=[
                        Name(
                            id=lambda setting: setting.forker_name,
                            ctx='load',
                            location=self.location,
                        )
                    ],
                    keywords=[],
                    location=self.location,
                ),
                location=self.location,
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
                        func=Path(
                            names=['tapl_typing', 'scope_forker'],
                            ctx='load',
                            mode=MODE_TYPECHECK,
                            location=self.location,
                        ),
                        args=[
                            Name(
                                id=lambda setting: setting.scope_name,
                                ctx='load',
                                location=self.location,
                            )
                        ],
                        keywords=[],
                        location=self.location,
                    ),
                    optional_vars=Name(
                        id=lambda setting: setting.forker_name,
                        ctx='store',
                        location=self.location,
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


@dataclasses.dataclass
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


@dataclasses.dataclass
class TypedName(syntax.Term):
    id: Identifier
    ctx: str
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedName(id=self.id, ctx=self.ctx, mode=layer(self.mode), location=self.location)
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return Name(id=self.id, ctx=self.ctx, location=self.location)
        if self.mode is MODE_TYPECHECK:
            return Attribute(
                value=Name(id=lambda setting: setting.scope_name, ctx='load', location=self.location),
                attr=self.id,
                ctx=self.ctx,
                location=self.location,
            )
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedAssign(syntax.Term):
    target_name: syntax.Term
    target_type: syntax.Term
    value: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

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
                target_name=layer(self.target_name),
                target_type=layer(self.target_type),
                value=layer(self.value),
                mode=layer(self.mode),
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return Assign(
                targets=[self.target_name],
                value=self.value,
                location=self.location,
            )
        if self.mode is MODE_TYPECHECK:
            expected = Assign(
                targets=[self.target_name],
                value=self.target_type,
                location=self.location,
            )
            assigned = Assign(targets=[self.target_name], value=self.value, location=self.location)
            return syntax.TermList(terms=[expected, assigned])
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class Literal(syntax.Term):
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    def typeit(self, ls: syntax.LayerSeparator, value: Any, type_id: str) -> list[syntax.Term]:
        if ls.layer_count != SAFE_LAYER_COUNT:
            raise ValueError('NoneLiteral must be separated in 2 layers')
        return [
            Constant(value=value, location=self.location),
            TypedName(id=type_id, ctx='load', mode=MODE_TYPECHECK, location=self.location),
        ]


@dataclasses.dataclass
class NoneLiteral(Literal):
    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=None, type_id='NoneType')


@dataclasses.dataclass
class BooleanLiteral(Literal):
    value: bool

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Bool')


@dataclasses.dataclass
class IntegerLiteral(Literal):
    value: int

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Int')


@dataclasses.dataclass
class FloatLiteral(Literal):
    value: float

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Float')


@dataclasses.dataclass
class StringLiteral(Literal):
    value: str

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Str')


@dataclasses.dataclass
class TypedList(syntax.Term):
    elements: list[syntax.Term]
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedList(
                elements=[layer(e) for e in self.elements],
                mode=layer(self.mode),
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return List(elements=self.elements, ctx='load', location=self.location)
        if self.mode is MODE_TYPECHECK:
            return Call(
                func=Path(
                    names=['tapl_typing', 'create_typed_list'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=self.elements,
                keywords=[],
                location=self.location,
            )
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedSet(syntax.Term):
    elements: list[syntax.Term]
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.elements
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedSet(
                elements=[layer(e) for e in self.elements],
                mode=layer(self.mode),
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return Set(
                elements=self.elements,
                location=self.location,
            )
        if self.mode is MODE_TYPECHECK:
            return Call(
                func=Path(
                    names=['tapl_typing', 'create_typed_set'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=self.elements,
                keywords=[],
                location=self.location,
            )
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedDict(syntax.Term):
    keys: list[syntax.Term]
    values: list[syntax.Term]
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.keys
        yield from self.values
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedDict(
                keys=[layer(k) for k in self.keys],
                values=[layer(v) for v in self.values],
                mode=layer(self.mode),
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return Dict(
                keys=self.keys,
                values=self.values,
                location=self.location,
            )
        if self.mode is MODE_TYPECHECK:
            return Call(
                func=Path(
                    names=['tapl_typing', 'create_typed_dict'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=[
                    List(
                        elements=self.keys,
                        ctx='load',
                        location=self.location,
                    ),
                    List(
                        elements=self.values,
                        ctx='load',
                        location=self.location,
                    ),
                ],
                keywords=[],
                location=self.location,
            )
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class BoolNot(syntax.Term):
    operand: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.operand
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BoolNot(operand=layer(self.operand), mode=layer(self.mode), location=self.location)
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return UnaryOp(
                op='not',
                operand=self.operand,
                location=self.location,
            )
        if self.mode is MODE_TYPECHECK:
            # unary not operator always returns Bool type
            return TypedName(
                id='Bool',
                ctx='load',
                mode=MODE_TYPECHECK,
                location=self.location,
            )
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedBoolOp(syntax.Term):
    operator: str
    values: list[syntax.Term]
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.values
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedBoolOp(
                operator=self.operator,
                values=[layer(v) for v in self.values],
                mode=layer(self.mode),
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return BoolOp(operator=self.operator, values=self.values, location=self.location)
        if self.mode is MODE_TYPECHECK:
            return Call(
                func=Path(
                    names=['tapl_typing', 'create_union'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=self.values,
                keywords=[],
                location=self.location,
            )
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedReturn(syntax.Term):
    value: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedReturn(value=layer(self.value), mode=layer(self.mode), location=self.location)
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return Return(
                value=self.value,
                location=self.location,
            )
        if self.mode is MODE_TYPECHECK:
            call = Call(
                func=Path(
                    names=['tapl_typing', 'add_return_type'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=[
                    Name(
                        id=lambda setting: setting.scope_name,
                        ctx='load',
                        location=self.location,
                    ),
                    self.value,
                ],
                keywords=[],
                location=self.location,
            )
            return Expr(
                value=call,
                location=self.location,
            )
        raise tapl_error.UnhandledError


# TODO: Add Parameters type to represent list of parameters which support posonly and kwonly args
@dataclasses.dataclass
class Parameter(syntax.Term):
    name: str
    type_: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.type_
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Parameter(
                name=self.name, type_=layer(self.type_), mode=layer(self.mode), location=self.location
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_TYPECHECK:
            return self.type_
        raise tapl_error.UnhandledError


# TODO: Implement posonly_args, regular_args, vararg, kwonly_args, kwarg, defaults if needed
@dataclasses.dataclass
class TypedFunctionDef(syntax.Term):
    name: str
    parameters: list[syntax.Term]
    return_type: syntax.Term
    body: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

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
                name=self.name,
                return_type=layer(self.return_type),
                parameters=[layer(p) for p in self.parameters],
                body=layer(self.body),
                mode=layer(self.mode),
                location=self.location,
            )
        )

    def unfold_evaluate(self) -> syntax.Term:
        if not all(cast(Parameter, p).type_ is syntax.Empty for p in self.parameters):
            raise tapl_error.TaplError('All parameter type must be Empty when generating function in evaluate mode.')

        return FunctionDef(
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
            location=self.location,
        )

    def unfold_typecheck_main(self, *, is_method: bool = False) -> syntax.Term:
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
                'parent__sa',
                Name(
                    id=lambda setting: setting.scope_name,
                    ctx='load',
                    location=self.location,
                ),
            )
        )
        keywords.extend(
            (
                name,
                Name(
                    id=name,
                    ctx='load',
                    location=self.location,
                ),
            )
            for name in param_names
        )
        new_scope = Assign(
            targets=[
                nested_scope(
                    Name(location=self.location, id=lambda setting: setting.scope_name, ctx='load'),
                )
            ],
            value=Call(
                func=Path(
                    names=['tapl_typing', 'create_scope'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=[],
                keywords=keywords,
                location=self.location,
            ),
            location=self.location,
        )
        tmp_function: syntax.Term = syntax.Empty
        set_return_type: syntax.Term = syntax.Empty
        if self.return_type is not syntax.Empty:
            params = [cast(Parameter, p).type_ for p in self.parameters]
            if is_method:
                params = params[1:]  # skip 'self' parameter type
            tmp_function = Assign(
                location=self.location,
                targets=[
                    TypedName(
                        id=self.name,
                        ctx='store',
                        mode=self.mode,
                        location=self.location,
                    )
                ],
                value=Call(
                    func=Path(
                        names=['tapl_typing', 'create_function'],
                        ctx='load',
                        mode=self.mode,
                        location=self.location,
                    ),
                    args=[
                        List(
                            elements=params,
                            ctx='load',
                            location=self.location,
                        ),
                        self.return_type,
                    ],
                    keywords=[],
                    location=self.location,
                ),
            )
            set_return_type = Expr(
                value=Call(
                    func=Path(
                        names=['tapl_typing', 'set_return_type'],
                        ctx='load',
                        mode=self.mode,
                        location=self.location,
                    ),
                    args=[
                        Name(
                            id=lambda setting: setting.scope_name,
                            ctx='load',
                            location=self.location,
                        ),
                        self.return_type,
                    ],
                    keywords=[],
                    location=self.location,
                ),
                location=self.location,
            )

        get_return_type = Return(
            value=Call(
                func=Path(
                    names=['tapl_typing', 'get_return_type'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=[
                    Name(
                        id=lambda setting: setting.scope_name,
                        ctx='load',
                        location=self.location,
                    )
                ],
                keywords=[],
                location=self.location,
            ),
            location=self.location,
        )

        return FunctionDef(
            name=self.name,
            posonlyargs=[],
            args=param_names,
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
            body=syntax.TermList(
                terms=[
                    new_scope,
                    nested_scope(syntax.TermList(terms=[tmp_function, set_return_type, self.body, get_return_type])),
                ]
            ),
            decorator_list=[],
            location=self.location,
        )

    def unfold_typecheck_type(self) -> syntax.Term:
        if not all(cast(Parameter, p).type_ is not syntax.Empty for p in self.parameters):
            raise tapl_error.TaplError(
                'All parameter type must not be Empty when generating function type in type-check mode.'
            )

        return Assign(
            targets=[
                TypedName(
                    id=self.name,
                    ctx='store',
                    mode=self.mode,
                    location=self.location,
                )
            ],
            value=Call(
                func=Path(
                    names=['tapl_typing', 'create_function'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=[
                    List(
                        elements=[cast(Parameter, p).type_ for p in self.parameters],
                        ctx='load',
                        location=self.location,
                    ),
                    Call(
                        func=Name(
                            id=self.name,
                            ctx='load',
                            location=self.location,
                        ),
                        args=[cast(Parameter, p).type_ for p in self.parameters],
                        keywords=[],
                        location=self.location,
                    ),
                ],
                keywords=[],
                location=self.location,
            ),
            location=self.location,
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.unfold_evaluate()
        if self.mode is MODE_TYPECHECK:
            return syntax.TermList(terms=[self.unfold_typecheck_main(), self.unfold_typecheck_type()])
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedIf(syntax.Term):
    test: syntax.Term
    body: syntax.Term
    elifs: list[tuple[syntax.Term, syntax.Term]]  # (test, body)
    orelse: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

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
                test=layer(self.test),
                body=layer(self.body),
                elifs=[(layer(test), layer(body)) for test, body in self.elifs],
                orelse=layer(self.orelse),
                mode=layer(self.mode),
                location=self.location,
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return If(
            test=self.test,
            body=self.body,
            orelse=self.orelse,
            location=self.location,
        )

    def codegen_typecheck(self) -> syntax.Term:
        true_side = syntax.TermList(
            terms=[
                Expr(
                    value=self.test,
                    location=self.location,
                ),
                self.body,
            ]
        )
        return BranchTyping(branches=[true_side, self.orelse], location=self.location)

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


@dataclasses.dataclass
class ElifSibling(syntax.SiblingTerm):
    test: syntax.Term
    body: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

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


@dataclasses.dataclass
class ElseSibling(syntax.SiblingTerm):
    body: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

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


@dataclasses.dataclass
class TypedWith(syntax.Term):
    items: list[syntax.Term]
    body: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.items
        yield self.body
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedWith(
                items=[layer(i) for i in self.items],
                body=layer(self.body),
                mode=layer(self.mode),
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        # XXX: Differentiate behavior between EVALUATE and TYPECHECK modes if needed, otherwise remove TypedWith
        if self.mode is MODE_EVALUATE:
            return With(
                items=self.items,
                body=self.body,
                location=self.location,
            )
        if self.mode is MODE_TYPECHECK:
            return With(
                items=self.items,
                body=self.body,
                location=self.location,
            )
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedWhile(syntax.Term):
    test: syntax.Term
    body: syntax.Term
    orelse: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

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
                test=layer(self.test),
                body=layer(self.body),
                orelse=layer(self.orelse),
                mode=layer(self.mode),
                location=self.location,
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return While(
            test=self.test,
            body=self.body,
            orelse=self.orelse,
            location=self.location,
        )

    def codegen_typecheck(self) -> syntax.Term:
        return TypedIf(
            test=self.test,
            body=self.body,
            elifs=[],
            orelse=self.orelse,
            mode=self.mode,
            location=self.location,
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedFor(syntax.Term):
    target: syntax.Term
    iter: syntax.Term
    body: syntax.Term
    orelse: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

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
                target=layer(self.target),
                iter=layer(self.iter),
                body=layer(self.body),
                orelse=layer(self.orelse),
                mode=layer(self.mode),
                location=self.location,
            )
        )

    def codegen_evaluate(self) -> syntax.Term:
        return For(
            target=self.target,
            iter=self.iter,
            body=self.body,
            orelse=self.orelse,
            location=self.location,
        )

    def codegen_typecheck(self) -> syntax.Term:
        iterator_type = Call(
            func=Attribute(
                value=self.iter,
                attr='__iter__',
                ctx='load',
                location=self.location,
            ),
            args=[],
            keywords=[],
            location=self.location,
        )
        item_type = Call(
            location=self.location,
            func=Attribute(
                value=iterator_type,
                attr='__next__',
                ctx='load',
                location=self.location,
            ),
            args=[],
            keywords=[],
        )
        assign_target = Assign(
            targets=[self.target],
            value=item_type,
            location=self.location,
        )
        for_branch = syntax.TermList(terms=[assign_target, self.body])
        return BranchTyping(
            branches=[for_branch, self.orelse],
            location=self.location,
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedTry(syntax.Term):
    body: syntax.Term
    handlers: list[syntax.Term]
    finalbody: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.body
        yield from self.handlers
        yield self.finalbody
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedTry(
                body=layer(self.body),
                handlers=[layer(h) for h in self.handlers],
                finalbody=layer(self.finalbody),
                mode=layer(self.mode),
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return Try(
                body=self.body,
                handlers=self.handlers,
                orelse=syntax.Empty,
                finalbody=self.finalbody,
                location=self.location,
            )
        if self.mode is MODE_TYPECHECK:
            # XXX: Implement type checking for Try statement's except and finally clauses
            return self.body
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class ExceptSibling(syntax.SiblingTerm):
    exception_type: syntax.Term
    name: str | None
    body: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.exception_type
        yield self.body

    @override
    def integrate_into(self, previous_siblings: list[syntax.Term]) -> None:
        term = previous_siblings[-1]
        if isinstance(term, syntax.ErrorTerm):
            return
        if not isinstance(term, TypedTry):
            error = syntax.ErrorTerm(
                'Except can only be integrated into typed Try.' + repr(term), location=self.location
            )
            previous_siblings.append(error)
        else:
            handler = ExceptHandler(
                exception_type=self.exception_type,
                name=self.name,
                body=self.body,
                location=self.location,
            )
            term.handlers.append(handler)


@dataclasses.dataclass
class FinallySibling(syntax.SiblingTerm):
    body: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.body

    @override
    def integrate_into(self, previous_siblings: list[syntax.Term]) -> None:
        term = previous_siblings[-1]
        if isinstance(term, syntax.ErrorTerm):
            return
        if not isinstance(term, TypedTry):
            error = syntax.ErrorTerm(
                'Finally can only be integrated into typed Try.' + repr(term), location=self.location
            )
            previous_siblings.append(error)
        elif term.finalbody is not syntax.Empty:
            error = syntax.ErrorTerm('A Try statement can only have one Finally clause.', location=self.location)
            previous_siblings.append(error)
        else:
            term.finalbody = self.body


@dataclasses.dataclass
class TypedImport(syntax.Term):
    names: list[Alias]
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedImport(
                names=self.names,
                mode=layer(self.mode),
                location=self.location,
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return Import(location=self.location, names=self.names)
        if self.mode is MODE_TYPECHECK:
            if len(self.names) > 1:
                raise tapl_error.TaplError('Import does not support multiple names yet.')  # XXX: Support multiple names
            return Expr(
                value=Call(
                    location=self.location,
                    func=Path(
                        names=['tapl_typing', 'import_module'],
                        ctx='load',
                        mode=self.mode,
                        location=self.location,
                    ),
                    args=[
                        Name(
                            id=lambda setting: setting.scope_name,
                            ctx='load',
                            location=self.location,
                        ),
                        List(
                            elements=[Constant(location=self.location, value=self.names[0].name)],
                            ctx='load',
                            location=self.location,
                        ),
                    ],
                    keywords=[],
                ),
                location=self.location,
            )
        raise tapl_error.UnhandledError


@dataclasses.dataclass
class TypedClassDef(syntax.Term):
    name: str
    bases: list[syntax.Term]
    body: syntax.Term
    mode: syntax.Term
    location: syntax.Location = dataclasses.field(repr=False)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.bases
        yield self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: TypedClassDef(
                name=self.name,
                bases=[layer(b) for b in self.bases],
                body=layer(self.body),
                mode=layer(self.mode),
                location=self.location,
            )
        )

    def _class_name(self) -> str:
        return f'{self.name}_'

    def codegen_evaluate(self) -> syntax.Term:
        return ClassDef(
            name=self._class_name(),
            bases=self.bases,
            keywords=[],
            body=self.body,
            decorator_list=[],
            location=self.location,
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
                body.append(item.unfold_typecheck_main(is_method=True))
            else:
                body.append(item)
        class_stmt = ClassDef(
            name=class_name,
            bases=self.bases,
            keywords=[],
            body=syntax.TermList(terms=body),
            decorator_list=[],
            location=self.location,
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
                    elements=[
                        Constant(
                            value=method.name,
                            location=self.location,
                        ),
                        List(
                            elements=tail_args,
                            ctx='load',
                            location=self.location,
                        ),
                    ],
                    ctx='load',
                    location=self.location,
                )
            )

        create_class = Assign(
            targets=[
                Tuple(
                    elements=[
                        TypedName(
                            id=instance_name,
                            ctx='store',
                            mode=self.mode,
                            location=self.location,
                        ),
                        TypedName(
                            id=class_name,
                            ctx='store',
                            mode=self.mode,
                            location=self.location,
                        ),
                    ],
                    ctx='store',
                    location=self.location,
                )
            ],
            value=Call(
                func=Path(
                    names=['tapl_typing', 'create_class'],
                    ctx='load',
                    mode=self.mode,
                    location=self.location,
                ),
                args=[],
                keywords=[
                    (
                        'cls',
                        Name(
                            id=class_name,
                            ctx='load',
                            location=self.location,
                        ),
                    ),
                    (
                        'init_args',
                        List(
                            elements=constructor_args,
                            ctx='load',
                            location=self.location,
                        ),
                    ),
                    (
                        'methods',
                        List(
                            elements=method_types,
                            ctx='load',
                            location=self.location,
                        ),
                    ),
                ],
                location=self.location,
            ),
            location=self.location,
        )

        return syntax.TermList(terms=[class_stmt, create_class])

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise tapl_error.UnhandledError
