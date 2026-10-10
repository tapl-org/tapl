# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Generator
from dataclasses import dataclass, field

from oymo.core import syntax

Term = syntax.Term
Location = syntax.Location

# An omitted form: not written.
Empty = syntax.Empty


# Every `location` is left out of `==`, so a parsed form equals the same form built in code.
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
    param_name: str
    param_form: Term
    body: Term
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.param_form
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


@dataclass
class If(Term):
    condition: Term
    then_clause: Term
    else_clause: Term
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.condition
        yield self.then_clause
        yield self.else_clause


@dataclass
class Fix(Term):
    function: Term
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.function


# Only bytes. `[01] : 'i8'` is `Formed(ByteArray([01]), 'i8')`.
# Forms are terms. A named form such as `i32` is the byte array `'i32'`.
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


# `term : form`: `term`, formed as `form`.
@dataclass
class Formed(Term):
    term: Term
    form: Term
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.term
        yield self.form


# `P => R`: the form of a function from `P` to `R`.
@dataclass
class FunctionForm(Term):
    param: Term
    result: Term
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.param
        yield self.result
