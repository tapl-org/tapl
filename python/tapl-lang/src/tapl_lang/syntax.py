# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass, field

from tapl_lang.tapl_error import TaplError


@dataclass(frozen=True)
class Position:
    line: int
    column: int


@dataclass(kw_only=True)
class TermInfo:
    start: Position | None = None
    end: Position | None = None


@dataclass
class Term:
    info: TermInfo

    def __bool__(self):
        return True

    def add_child(self, child: 'Term') -> None:
        raise TaplError(f'The term class does not support adding a child class={child.__class__.__name__}')

    def separable(self) -> bool:
        return False


@dataclass
class ErrorTerm(Term):
    message: str
    recovered: bool = False
    guess: Term | None = None

    def __bool__(self) -> bool:
        return self.recovered


@dataclass
class Sequence:
    terms: list[Term] = field(default_factory=list)

    def add_child(self, element: Term) -> None:
        self.terms.append(element)
