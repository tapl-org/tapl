# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import enum
from dataclasses import dataclass, field

from tapl_lang.tapl_error import TaplError


class Term:
    def __bool__(self):
        return True

    def add_child(self, child: 'Term') -> None:
        raise TaplError(f'The term class does not support adding a child class={child.__class__.__name__}')

    def separable(self) -> bool:
        return False

    def has_error(self) -> bool:
        return False


class RunModes(Term, enum.Enum):
    EVALUATE = Term()
    # ruff: noqa: PIE796
    TYPE_CHECK = Term()


@dataclass(frozen=True)
class Position:
    line: int
    column: int


@dataclass(frozen=True, kw_only=True)
class Location:
    start: Position | None = None
    end: Position | None = None


@dataclass
class TermWithLocation(Term):
    location: Location


@dataclass
class ErrorTerm(TermWithLocation):
    message: str
    recovered: bool = False
    guess: Term | None = None

    def __bool__(self) -> bool:
        return self.recovered

    def has_error(self):
        return True


@dataclass
class Sequence:
    terms: list[Term] = field(default_factory=list)

    def add_child(self, element: Term) -> None:
        self.terms.append(element)

    def has_error(self) -> bool:
        return any(term.has_error() for term in self.terms)


@dataclass
class Tiered:
    low: Term
    high: Term

    def separable(self) -> bool:
        return True

    def has_error(self) -> bool:
        return self.low.has_error() or self.high.has_error()
