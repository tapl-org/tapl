# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass

import enum

class Kind(enum.Enum):
    Var = enum.auto()
    Lambda = enum.auto()
    Apply = enum.auto()
    Record = enum.auto()
    Get = enum.auto()
    Fix = enum.auto()
    If = enum.auto()
    Bits = enum.auto()


class Term:

    def kind(self) -> Kind:
        raise NotImplementedError
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}'

@dataclass
class Var(Term):
    name: str
    bruijn: int = -1
    context_length: int = -1

    def kind(self) -> Kind:
        return Kind.Var

@dataclass
class Lambda(Term):
    parameter: str
    body: Term

    def kind(self) -> Kind:
        return Kind.Lambda

@dataclass
class Apply(Term):
    function: Term
    argument: Term

    def kind(self) -> Kind:
        return Kind.Apply

@dataclass
class Record(Term):
    fields: list[(str,Term)]

    def kind(self) -> Kind:
        return Kind.Record

@dataclass
class Get(Term):
    record: Term
    field: str

    def kind(self) -> Kind:
        return Kind.Get

@dataclass
class Fix(Term):
    body: Term

    def kind(self) -> Kind:
        return Kind.Fix

@dataclass
class If(Term):
    condition: Term
    true: Term
    else: Term

    def kind(self) -> Kind:
        return Kind.If

@dataclass
class Bits(Term):
    value: int | str | bytes
    format: str

    def kind(self) -> Kind:
        return Kind.Bits