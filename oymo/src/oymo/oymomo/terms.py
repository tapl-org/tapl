# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo import core

from dataclasses import dataclass

class Form:
    pass

@dataclass
class ScalarForm(Form):
    name: str

@dataclass
class RecordForm(Form):
    fields: list[tuple[str, Form]]

@dataclass
class Variable(core.Term):
    name: str

class BruijnIndex(core.Term):
    index: int

class Lambda(core.Term):
    param_name: str
    param_form: Form
    body: core.Term

class Apply(core.Term):
    function: core.Term
    argument: core.Term

class Fix(core.Term):
    body: core.Term

class Record(core.Term):
    fields: list[tuple[str, core.Term]]

class Select(core.Term):
    record: core.Term
    label: str

class If(core.Term):
    condition: core.Term
    then_clause: core.Term
    else_clause: core.Term

class Bits(core.Term):
    data: bytes
    form: Form