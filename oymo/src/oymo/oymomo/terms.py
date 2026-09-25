# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Generator
from dataclasses import dataclass

from oymo.core import syntax

Term = syntax.Term
Location = syntax.Location


class Form:
    pass


@dataclass
class UnknownForm(Form):
    pass


@dataclass
class ScalarForm(Form):
    name: str


@dataclass
class RecordForm(Form):
    fields: list[tuple[str, Form]]


@dataclass
class Variable(Term):
    name: str
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield from ()


@dataclass
class BruijnIndex(Term):
    index: int

    def children(self) -> Generator[Term, None, None]:
        yield from ()


@dataclass
class Lambda(Term):
    param_name: str
    param_form: Form
    body: Term
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield self.body


@dataclass
class Apply(Term):
    function: Term
    argument: Term
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield self.function
        yield self.argument


@dataclass
class Field(Term):
    label: str
    value: Term
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield self.value


@dataclass
class Record(Term):
    fields: list[Field]
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield from self.fields


@dataclass
class Select(Term):
    record: Term
    label: str
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield self.record


@dataclass
class If(Term):
    condition: Term
    then_clause: Term
    else_clause: Term
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield self.condition
        yield self.then_clause
        yield self.else_clause


@dataclass
class Fix(Term):
    function: Term
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield self.function


@dataclass
class Integer(Term):
    value: int
    form: Form
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield from ()


@dataclass
class String(Term):
    value: str
    form: Form
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield from ()


@dataclass
class ByteArray(Term):
    value: bytes
    form: Form
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield from ()
