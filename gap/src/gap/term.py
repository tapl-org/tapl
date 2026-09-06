# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The Gap AST of gap/spec.md.

Binders are de Bruijn indexes, so substitution needs no renaming. A variable
occurrence is `Bound` when some enclosing `Abs` binds it and `Free` otherwise;
a `Free` is what makes a neutral term residual. `Abs.param` and `Bound.hint`
carry the written name for the printer only, so they are excluded from
equality: `(lambda x x)` and `(lambda y y)` are the same term. Labels are not
names, and records compare by label.
"""

import enum
from dataclasses import dataclass, field


class BitsKind(enum.Enum):
    INTEGER = 'integer'
    STRING = 'string'
    HEX = 'hex'


@dataclass(frozen=True)
class Bound:
    """Variable bound by an enclosing lambda; `index` counts lambdas outward from 0."""

    index: int
    hint: str = field(default='', compare=False)


@dataclass(frozen=True)
class Free:
    """Variable no lambda binds, such as `env` in an open term."""

    name: str


@dataclass(frozen=True)
class Abs:
    param: str = field(compare=False)
    body: 'Term'


@dataclass(frozen=True)
class App:
    function: 'Term'
    argument: 'Term'


@dataclass(frozen=True)
class Field:
    label: str
    term: 'Term'


@dataclass(frozen=True)
class Record:
    fields: tuple[Field, ...]  # written order, kept everywhere


@dataclass(frozen=True)
class Proj:
    subject: 'Term'
    label: str


@dataclass(frozen=True)
class Fix:
    term: 'Term'


@dataclass(frozen=True)
class If:
    condition: 'Term'
    consequent: 'Term'
    alternative: 'Term'


@dataclass(frozen=True)
class Bits:
    kind: BitsKind
    text: str  # the token as written; hex width and string bytes are significant

    @property
    def is_zero(self) -> bool:
        """Zero means every bit is zero, whatever the kind: 0, 0x00000000, and "" are all zero."""
        match self.kind:
            case BitsKind.INTEGER:
                return int(self.text) == 0
            case BitsKind.STRING:
                return all(character == '\x00' for character in self.text[1:-1])
            case BitsKind.HEX:
                return all(digit == '0' for digit in self.text[2:])


type Term = Bound | Free | Abs | App | Record | Proj | Fix | If | Bits


def shift(term: Term, distance: int, cutoff: int = 0) -> Term:
    """Add `distance` to every `Bound` index at or above `cutoff`, leaving inner binders alone."""
    match term:
        case Bound(index, hint):
            return Bound(index + distance, hint) if index >= cutoff else term
        case Free() | Bits():
            return term
        case Abs(param, body):
            return Abs(param, shift(body, distance, cutoff + 1))
        case App(function, argument):
            return App(shift(function, distance, cutoff), shift(argument, distance, cutoff))
        case Record(fields):
            return Record(tuple(Field(field.label, shift(field.term, distance, cutoff)) for field in fields))
        case Proj(subject, label):
            return Proj(shift(subject, distance, cutoff), label)
        case Fix(inner):
            return Fix(shift(inner, distance, cutoff))
        case If(condition, consequent, alternative):
            return If(
                shift(condition, distance, cutoff),
                shift(consequent, distance, cutoff),
                shift(alternative, distance, cutoff),
            )


def substitute(term: Term, index: int, replacement: Term) -> Term:
    """Replace `Bound(index)` with `replacement`, shifting it as it passes under binders."""
    match term:
        case Bound(bound_index, _):
            return replacement if bound_index == index else term
        case Free() | Bits():
            return term
        case Abs(param, body):
            return Abs(param, substitute(body, index + 1, shift(replacement, 1)))
        case App(function, argument):
            return App(substitute(function, index, replacement), substitute(argument, index, replacement))
        case Record(fields):
            return Record(tuple(Field(field.label, substitute(field.term, index, replacement)) for field in fields))
        case Proj(subject, label):
            return Proj(substitute(subject, index, replacement), label)
        case Fix(inner):
            return Fix(substitute(inner, index, replacement))
        case If(condition, consequent, alternative):
            return If(
                substitute(condition, index, replacement),
                substitute(consequent, index, replacement),
                substitute(alternative, index, replacement),
            )


def substitute_top(body: Term, argument: Term) -> Term:
    """[x ↦ argument] body, for the `x` the immediately enclosing lambda binds."""
    return shift(substitute(body, 0, shift(argument, 1)), -1)


def free_names(term: Term) -> set[str]:
    """FV(t): the names nothing binds. Labels are not terms, so they never appear."""
    match term:
        case Free(name):
            return {name}
        case Bound() | Bits():
            return set()
        case Abs(_, body):
            return free_names(body)
        case App(function, argument):
            return free_names(function) | free_names(argument)
        case Record(fields):
            return set().union(*(free_names(field.term) for field in fields))
        case Proj(subject, _):
            return free_names(subject)
        case Fix(inner):
            return free_names(inner)
        case If(condition, consequent, alternative):
            return free_names(condition) | free_names(consequent) | free_names(alternative)
