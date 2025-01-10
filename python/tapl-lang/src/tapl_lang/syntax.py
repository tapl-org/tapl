# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from tapl_lang.tapl_error import MismatchedLayerLengthError, TaplError


class Term:
    # TODO: not easy to understand, rename this method
    def __bool__(self):
        return True

    def get_errors(self) -> list['ErrorTerm']:
        raise NotImplementedError

    def add_child(self, child: 'Term') -> None:
        raise TaplError(
            f'The {self.__class__.__name__} class does not support adding a child class={child.__class__.__name__}'
        )

    def layer_agnostic(self) -> bool:
        return False

    def separate(self) -> 'Term':
        raise NotImplementedError

    def codegen_ast(self) -> ast.AST:
        raise NotImplementedError

    def codegen_expr(self) -> ast.expr:
        raise NotImplementedError

    def codegen_stmt(self) -> ast.stmt:
        raise NotImplementedError


@dataclass(frozen=True)
class Layers(Term):
    layers: list[Term]

    def __post_init__(self) -> None:
        if len(self.layers) <= 1:
            raise TaplError('Number of terms in Layers must be bigger than 1.')

    @override
    def get_errors(self) -> list['ErrorTerm']:
        result = []
        for layer in self.layers:
            result.extend(layer.get_errors())
        return result

    @override
    def separate(self) -> Term:
        for i in range(len(self.layers)):
            self.layers[i] = self.layers[i].separate()
        return self

    def codegen_ast(self) -> ast.AST:
        raise TaplError('Layers should be separated before generating AST code.')

    def codegen_expr(self) -> ast.expr:
        raise TaplError('Layers should be separated before generating AST code.')

    def codegen_stmt(self) -> ast.stmt:
        raise TaplError('Layers should be separated before generating AST code.')


class LayerSeparator:
    def __init__(self) -> None:
        self.layer_count: int = 0

    def separate(self, term: Term) -> Term:
        if term.layer_agnostic():
            return term
        separated = term.separate()
        expected_count = len(separated.layers) if isinstance(separated, Layers) else 1
        if self.layer_count == 0:
            self.layer_count = expected_count
        elif self.layer_count != expected_count:
            raise MismatchedLayerLengthError(
                message=f'Mismatched layer lengths, layer_count={self.layer_count}, expected_count={expected_count}'
            )
        return separated

    def extract_layer(self, index: int, term: Term) -> Term:
        if isinstance(term, Layers):
            return term.layers[index]
        if term.layer_agnostic():
            return term
        raise TaplError(f'LayerSeparator.extract_layer expects Layers class, but recieved {term.__class__.__name__}')

    def build(self, factory: Callable[[Callable[[Term], Term]], Term]) -> Term:
        if self.layer_count <= 1:
            return factory(lambda x: x)

        def create_extract_layer_fn(index: int) -> Callable[[Term], Term]:
            return lambda term: self.extract_layer(index, term)

        layers: list[Term] = [factory(create_extract_layer_fn(i)) for i in range(self.layer_count)]
        return Layers(layers)


@dataclass(frozen=True)
class Mode(Term):
    name: str

    @override
    def get_errors(self) -> list['ErrorTerm']:
        return []

    @override
    def separate(self) -> Term:
        return self


MODE_EVALUATE = Mode('evaluate')
MODE_TYPECHECK = Mode('type check')
MODE_SAFE = Layers([MODE_EVALUATE, MODE_TYPECHECK])


@dataclass(frozen=True)
class Position:
    line: int
    column: int

    def __repr__(self) -> str:
        return f'{self.line}:{self.column}'


@dataclass(frozen=True, kw_only=True)
class Location:
    start: Position | None = None
    end: Position | None = None

    def __repr__(self) -> str:
        start = repr(self.start) if self.start else '-'
        end = repr(self.end) if self.end else '-'
        return f'{start}|{end}'


@dataclass(frozen=True)
class TermWithLocation(Term):
    location: Location


@dataclass(frozen=True)
class ErrorTerm(TermWithLocation):
    message: str
    recovered: bool = False
    guess: Term | None = None

    def __bool__(self) -> bool:
        return self.recovered

    @override
    def get_errors(self) -> list['ErrorTerm']:
        return [self]

    @override
    def separate(self) -> Term:
        raise TaplError('ErrorTerm does not support separate.')
