# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any, override

from tapl_lang.core import syntax


@dataclass
class Module(syntax.Term):
    body: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: Module(body=[layer(b) for b in self.body]))


# STATEMENTS


@dataclass
class FunctionDef(syntax.Term):
    location: syntax.Location
    name: str
    body: syntax.Term
    posonlyargs: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    vararg: str | None = None
    kwonlyargs: list[str] = field(default_factory=list)
    kw_defaults: list[syntax.Term] = field(default_factory=list)
    kwarg: str | None = None
    defaults: list[syntax.Term] = field(default_factory=list)

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.body
        yield from self.kw_defaults
        yield from self.defaults

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: FunctionDef(
                location=self.location,
                name=self.name,
                body=layer(self.body),
                posonlyargs=self.posonlyargs,
                args=self.args,
                vararg=self.vararg,
                kwonlyargs=self.kwonlyargs,
                kw_defaults=[layer(k) for k in self.kw_defaults],
                kwarg=self.kwarg,
                defaults=[layer(d) for d in self.defaults],
            )
        )


@dataclass
class ClassDef(syntax.Term):
    location: syntax.Location
    name: str
    bases: list[syntax.Term]
    body: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.bases
        yield from self.body

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: ClassDef(
                location=self.location,
                name=self.name,
                bases=[layer(b) for b in self.bases],
                body=[layer(b) for b in self.body],
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
    body: list[syntax.Term]
    orelse: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.target
        yield self.iter
        yield from self.body
        yield from self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: For(
                location=self.location,
                target=layer(self.target),
                iter=layer(self.iter),
                body=[layer(t) for t in self.body],
                orelse=[layer(t) for t in self.orelse],
            )
        )


@dataclass
class While(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: list[syntax.Term]
    orelse: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield from self.body
        yield from self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: While(
                location=self.location,
                test=layer(self.test),
                body=[layer(t) for t in self.body],
                orelse=[layer(t) for t in self.orelse],
            )
        )


@dataclass
class If(syntax.Term):
    location: syntax.Location
    test: syntax.Term
    body: list[syntax.Term]
    orelse: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.test
        yield from self.body
        yield from self.orelse

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: If(
                location=self.location,
                test=layer(self.test),
                body=[layer(t) for t in self.body],
                orelse=[layer(t) for t in self.orelse],
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


# EXPRESSIONS


@dataclass
class BoolOp(syntax.Term):
    location: syntax.Location
    op: str
    values: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.values

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BoolOp(location=self.location, op=self.op, values=[layer(v) for v in self.values])
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


@dataclass
class Name(syntax.Term):
    location: syntax.Location
    id: str
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Name(location=self.location, id=self.id, ctx=self.ctx))
