# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import cast, override

from tapl_lang.tapl_error import TaplError


class Term:
    # This creates a syntactic sugar when using within an if clause of the parser rules to determine if the term was successfully parsed.
    # Example: if term := ErrorTerm('some error'): 'parse succeeded' else: 'parse failed'
    # Despite the term having a value, the flow proceeds to the else part of the if statement.
    def __bool__(self):
        return True

    def get_errors(self) -> list['ErrorTerm']:
        raise NotImplementedError

    def add_child(self, child: 'Term') -> None:
        raise TaplError(
            f'The {self.__class__.__name__} class does not support adding a child class={child.__class__.__name__}'
        )

    def separate(self, ls: 'LayerSeparator') -> 'Layers':
        # TODO: change this to raise NotImplementedError
        return ls.replicate(self)

    def codegen_ast(self) -> ast.AST:
        raise TaplError(f'codegen_ast is not implemented in {self.__class__.__name__}')

    def codegen_expr(self) -> ast.expr:
        raise TaplError(f'codegen_expr is not implemented in {self.__class__.__name__}')

    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        raise TaplError(f'codegen_stmt is not implemented in {self.__class__.__name__}')


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
    def separate(self, ls: 'LayerSeparator') -> 'Layers':
        actual_count = len(self.layers)
        if actual_count != ls.layer_count:
            raise TaplError(f'Mismatched layer lengths, actual_count={actual_count}, expected_count={ls.layer_count}')
        return self

    def codegen_ast(self) -> ast.AST:
        raise TaplError('Layers should be separated before generating AST code.')

    def codegen_expr(self) -> ast.expr:
        raise TaplError('Layers should be separated before generating AST code.')

    def codegen_stmt(self) -> ast.stmt | list[ast.stmt]:
        raise TaplError('Layers should be separated before generating AST code.')


@dataclass(frozen=True)
class Realm(Term):
    layer_count: int
    term: Term

    @override
    def get_errors(self):
        return self.term.get_errors()


class LayerSeparator:
    def __init__(self, layer_count: int) -> None:
        if layer_count <= 1:
            raise TaplError('layer_count must be equal or greater than 2.')
        self.layer_count = layer_count

    def replicate(self, term: Term) -> Layers:
        return Layers(layers=[term for _ in range(self.layer_count)])

    def build(self, factory: Callable[[Callable[[Term], Term]], Term]) -> Layers:
        memo = []
        memo_index = [0]

        def extract_layer(index: int, term: Term) -> Term:
            if index == 0:
                memo.append((term, term.separate(self)))
            t, s = memo[memo_index[0]]
            memo_index[0] += 1
            if t is not term:
                raise TaplError('layer function call order is changed.')
            return cast(Layers, s).layers[index]

        def create_extract_layer_fn(index: int) -> Callable[[Term], Term]:
            return lambda term: extract_layer(index, term)

        layers: list[Term] = []
        for i in range(self.layer_count):
            memo_index[0] = 0
            layers.append(factory(create_extract_layer_fn(i)))
        return Layers(layers)

    def separate(self, term: Term) -> Layers:
        return self.build(lambda layer: layer(term))


@dataclass(frozen=True)
class Mode(Term):
    name: str

    @override
    def get_errors(self) -> list['ErrorTerm']:
        return []


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

    def locate(self, *nodes: ast.expr | ast.stmt) -> None:
        if self.start:
            for node in nodes:
                node.lineno = self.start.line
                node.col_offset = self.start.column
        if self.end:
            for node in nodes:
                node.end_lineno = self.end.line
                node.end_col_offset = self.end.column


@dataclass(frozen=True)
class TermWithLocation(Term):
    location: Location

    def locate(self, *nodes: ast.expr | ast.stmt) -> None:
        self.location.locate(*nodes)


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
    def separate(self, ls: LayerSeparator) -> Layers:
        raise TaplError('ErrorTerm does not support separate.')


def flatten_statements(statements: Iterable[ast.stmt | list[ast.stmt]]) -> list[ast.stmt]:
    result = []
    for s in statements:
        if isinstance(s, list):
            result.extend(s)
        else:
            result.append(s)
    return result
