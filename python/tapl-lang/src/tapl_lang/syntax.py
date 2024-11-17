# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any, Optional
from abc import ABC
import ast


class Location:
    def __init__(self, lineno: int, col_offset: int) -> None:
        self.lineno = lineno
        self.col_offset = col_offset
    
    def __repr__(self):
        return f'{self.lineno}:{self.col_offset}'


class Term(ABC):
    def __init__(self, location: Location) -> None:
        self.location = location

    def separable(self) -> bool:
        return False

    def get_ast(self) -> Optional[ast.AST]:
        return None


class SyntaxError(Term):
    def __init__(self, location: Location, error_text: str):
        super().__init__(location)
        self.error_text = error_text

    def __repr__(self) -> str:
        return f'term.SyntaxError({self.location},{self.error_text})'


def is_valid(term: Optional[Term]) -> bool:
    return term is not None and not isinstance(term, SyntaxError)


class Terminal(Term):
    def __init__(self, location: Location, value: Any):
        super().__init__(location)
        self.value = value


class Constant(Term):
    def __init__(self, location: Location, value):
        super().__init__(location)
        self.value = value

    def separable(self) -> bool:
        return False
    
    def get_ast(self) -> ast.AST:
        return ast.Constant(self.value)


class BinOp(Term):
    def __init__(self, location: Location, left, op, right):
        super().__init__(location)
        self.left = left
        self.op = op
        self.right = right

    def separable(self) -> bool:
        return False
    
    def get_ast(self) -> ast.AST:
        return ast.BinOp(self.left, self.op, self.right)
