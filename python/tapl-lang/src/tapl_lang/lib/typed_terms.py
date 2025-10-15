# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, override

from tapl_lang.core import syntax, tapl_error
from tapl_lang.lib import untyped_terms


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
class Name(syntax.Term):
    location: syntax.Location
    id: str
    ctx: str
    mode: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.mode

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Name(location=self.location, id=self.id, ctx=self.ctx, mode=layer(self.mode)))

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return untyped_terms.Name(location=self.location, id=self.id, ctx=self.ctx)
        if self.mode is MODE_TYPECHECK:
            # FIXME: hard code scope_name, should be set in setting #refactor
            return untyped_terms.create_path(
                location=self.location, names=[lambda setting: setting.scope_name, self.id], ctx=self.ctx
            )
        raise tapl_error.UnhandledError


@dataclass
class Attribute(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    attr: str
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Attribute(location=self.location, value=layer(self.value), attr=self.attr, ctx=self.ctx)
        )

    # TODO: Attribute must have a type layer to check attribute exists or not. find a test case first. should have? maybe scope should support this.
    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Attribute(location=self.location, value=self.value, attr=self.attr, ctx=self.ctx)


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
        value: syntax.Term = Name(location=self.location, id=self.names[0], ctx='load', mode=self.mode)
        for i in range(1, len(self.names) - 1):
            value = Attribute(location=self.location, value=value, attr=self.names[i], ctx='load')
        return Attribute(location=self.location, value=value, attr=self.names[-1], ctx=self.ctx)


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
            untyped_terms.Constant(location=self.location, value=value),
            Name(location=self.location, id=type_id, ctx='load', mode=MODE_TYPECHECK),
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
        return untyped_terms.List(location=self.location, elts=[], ctx='load')


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

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.UnaryOp(location=self.location, op=self.op, operand=self.operand)


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
            return untyped_terms.UnaryOp(location=self.location, op='not', operand=self.operand)
        if self.mode is MODE_TYPECHECK:
            # unary not operator always returns Bool type
            return Name(location=self.location, id='Bool', ctx='load', mode=MODE_TYPECHECK)
        raise tapl_error.UnhandledError


@dataclass
class BoolOp(syntax.Term):
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
            lambda layer: BoolOp(
                location=self.location, op=self.op, values=[layer(v) for v in self.values], mode=layer(self.mode)
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        if self.mode is MODE_EVALUATE:
            return untyped_terms.BoolOp(location=self.location, op=self.op, values=self.values)
        if self.mode is MODE_TYPECHECK:
            return untyped_terms.Call(
                location=self.location,
                func=Path(location=self.location, names=['api__tapl', 'create_union'], ctx='load', mode=self.mode),
                args=self.values,
                keywords=[],
            )
        raise tapl_error.UnhandledError


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

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.BinOp(location=self.location, left=self.left, op=self.op, right=self.right)


@dataclass
class Compare(syntax.Term):
    location: syntax.Location
    left: syntax.Term
    ops: list[str]
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
                ops=self.ops,
                comparators=[layer(v) for v in self.comparators],
            )
        )

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Compare(location=self.location, left=self.left, ops=self.ops, comparators=self.comparators)


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

    @override
    def unfold(self) -> syntax.Term:
        return untyped_terms.Call(location=self.location, func=self.func, args=self.args, keywords=self.keywords)
