# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

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


@dataclass
class BruijnIndex(Term):
    index: int


@dataclass
class Lambda(Term):
    param_name: str
    param_form: Form
    body: Term
    location: Location


@dataclass
class Apply(Term):
    function: Term
    argument: Term
    location: Location


@dataclass
class Field(Term):
    label: str
    form: Form
    value: Term
    location: Location


@dataclass
class Record(Term):
    fields: list[Field]
    location: Location


@dataclass
class Select(Term):
    record: Term
    label: str
    location: Location


@dataclass
class If(Term):
    condition: Term
    then_clause: Term
    else_clause: Term
    location: Location


@dataclass
class Fix(Term):
    function: Term
    location: Location


@dataclass
class Integer(Term):
    value: int
    form: Form
    location: Location


@dataclass
class String(Term):
    value: str
    form: Form
    location: Location


@dataclass
class ByteArray(Term):
    value: bytes
    form: Form
    location: Location
