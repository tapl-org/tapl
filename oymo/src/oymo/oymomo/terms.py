# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Generator
from dataclasses import dataclass, field

from oymo.core import syntax

Term = syntax.Term
Location = syntax.Location

# An omitted form: the form is unknown.
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


@dataclass
class ByteArray(Term):
    value: bytes
    form: Term
    location: Location | None = field(default=None, compare=False)

    def children(self) -> Generator[Term, None, None]:
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


# Forms are terms. A named form such as `i32` is the byte array `'i32'` with an empty form.


def name_form(name: str) -> ByteArray:
    return ByteArray(name.encode('ascii'), form=Empty)


def form_name(form: Term) -> str | None:
    """The name of a named form: the text of a byte array with an empty form. None otherwise."""
    if isinstance(form, ByteArray) and form.form is Empty:
        try:
            return form.value.decode('ascii')
        except UnicodeDecodeError:
            return None
    return None


def struct_form(fields: list[tuple[str, Term]], location: Location | None = None) -> Struct:
    return Struct([Field(label, form) for label, form in fields], location)


def struct_fields(form: Term) -> list[tuple[str, Term]] | None:
    """The `(label, form)` pairs of a struct form. None otherwise."""
    if isinstance(form, Struct):
        return [(f.label, f.value) for f in form.fields]
    return None
