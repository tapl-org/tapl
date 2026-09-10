# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import enum
from dataclasses import dataclass


class Kind(enum.Enum):
    Var = 'var'
    Lambda = 'lambda'
    Apply = 'apply'
    Record = 'record'
    Get = 'get'
    Fix = 'fix'
    If = 'if'
    Bits = 'bits'


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
    fields: list[tuple[str, Term]]

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
    false: Term

    def kind(self) -> Kind:
        return Kind.If


@dataclass
class Bits(Term):
    value: bytes  # base64 encoded in text form
    layout: str  # i32, u32, 10xi8, etc.

    def kind(self) -> Kind:
        return Kind.Bits
