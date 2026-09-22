# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass

from oymo.core import syntax


class Form:
    pass


@dataclass
class ScalarForm(Form):
    name: str


@dataclass
class RecordForm(Form):
    fields: list[tuple[str, Form]]


@dataclass
class Variable(syntax.Term):
    name: str
    location: syntax.Location


@dataclass
class BruijnIndex(syntax.Term):
    index: int


@dataclass
class Lambda(syntax.Term):
    param_name: str
    param_form: Form
    body: syntax.Term
    location: syntax.Location


@dataclass
class Apply(syntax.Term):
    function: syntax.Term
    argument: syntax.Term


@dataclass
class Record(syntax.Term):
    fields: list[tuple[str, syntax.Term]]


@dataclass
class Select(syntax.Term):
    record: syntax.Term
    label: str


@dataclass
class If(syntax.Term):
    condition: syntax.Term
    then_clause: syntax.Term
    else_clause: syntax.Term


@dataclass
class Bits(syntax.Term):
    data: bytes
    form: Form
