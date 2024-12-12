# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass

from tapl_lang.tapl_error import TaplError, MismatchedLayerLengthError
from tapl_lang.types import Type


class Term:

    # TODO not easy to understand, rename this method
    def __bool__(self):
        return True

    def has_error(self) -> bool:
        return False
    
    def add_child(self, child: 'Term') -> None:
        raise TaplError(f'The term class does not support adding a child class={self.__class__.__name__}')

    def separate(self) -> 'Term':
        raise TaplError(f'separate is not implemented yet, class={self.__class__.__name__}')
    
    def codegen(self) -> ast.AST:
        raise TabError(f'codegen is not implemented. {self.__class__.__name__}')


@dataclass
class Layers(Term):
    layers: list[Term]

    def __post_init__(self) -> None:
        if len(self.layers) <= 1:
            raise TaplError('Number of terms in Layers must be bigger than 1.')

    def has_error(self) -> bool:
        return any(layer.has_error() for layer in self.layers)

    def separate(self) -> Term:
        for i in range(len(self.layers)):
            self.layers[i] = self.layers[i].separate()
        return self
    
    def codegen(self) -> ast.AST:
        raise TaplError('Layers should be separated before generating AST code.')
    

class LayerSeparator:
    
    def __init__(self) -> None:
        self.layer_count: int | None = None
    
    def separate(self, term: Term) -> Term:
        separated = term.separate()
        expected_count = len(separated.layers) if isinstance(separated, Layers) else 1
        if self.layer_count is None:
            self.layer_count = expected_count
        elif self.layer_count != expected_count:
            raise MismatchedLayerLengthError()
        return separated
    
    def extract_layer(self, index: int, term: Term) -> Term:
        if isinstance(term, Layers):
            return term.layers[index]
        raise TaplError(f'LayerSeparator.extract_layer expects Layers class, but recieved {term.__class__.__name__}')

@dataclass
class Mode(Term):
    name: str

    def separate(self) -> Term:
        return self

MODE_EVALUATE = Mode('evaluate')
MODE_TYPECHECK = Mode('type check')
MODE_SAFE = Layers([MODE_EVALUATE, MODE_TYPECHECK])


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

