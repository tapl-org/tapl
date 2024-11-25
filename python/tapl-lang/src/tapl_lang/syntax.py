# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass


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

    def separable(self) -> bool:
        return False


@dataclass
class ErrorTerm(Term):
    message: str
    recovered: bool = False
    guess: Term | None = None

    def __bool__(self) -> bool:
        return self.recovered
