# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Oymomo terms (semantics.tex, Section 2): `x | λx. t | t t | b | {lᵢ = tᵢ} | t.l`.

A `Variable` is a name as written; `reduction.resolve` turns each one into the
`BruijnIndex` of its binder.
"""

from collections.abc import Generator
from dataclasses import dataclass, field

from oymo.core import syntax

Term = syntax.Term
Location = syntax.Location


# Every `location` is left out of `==`, so a parsed term equals the same term built in code.
@dataclass
class Variable(Term):
    name: str
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield from ()


@dataclass
class BruijnIndex(Term):
    index: int
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield from ()


@dataclass
class Lambda(Term):
    """`λx. body`."""

    param_name: str
    body: Term
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.body


@dataclass
class Apply(Term):
    function: Term
    argument: Term
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.function
        yield self.argument


@dataclass
class Field:
    """`label = value`; an unlabeled field has the label `''`."""

    label: str
    value: Term
    location: Location | None = field(default=None, compare=False)


@dataclass
class Struct(Term):
    fields: list[Field]
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield from (f.value for f in self.fields)


@dataclass
class Project(Term):
    struct: Term
    label: str
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.struct


# A type such as `'i32'` is the byte array of its name.
@dataclass
class ByteArray(Term):
    value: bytes
    location: Location | None = field(default=None, compare=False)

    @classmethod
    def from_str(cls, text: str) -> 'ByteArray':
        """The UTF-8 bytes of `text`."""
        return cls(text.encode('utf-8'))

    @property
    def as_str(self) -> str | None:
        """The bytes decoded as UTF-8. None if they aren't valid UTF-8."""
        try:
            return self.value.decode('utf-8')
        except UnicodeDecodeError:
            return None

    def children(self) -> Generator[Term, None, None]:
        yield from ()
