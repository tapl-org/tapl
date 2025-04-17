# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import cast, override

from tapl_lang.tapl_error import TaplError

_SCOPE_LEVEL: ContextVar[int] = ContextVar('scope_name', default=0)


@contextmanager
def new_scope_name() -> Generator[None, None, None]:
    old_level = _SCOPE_LEVEL.get()
    _SCOPE_LEVEL.set(old_level + 1)
    try:
        yield
    finally:
        _SCOPE_LEVEL.set(old_level)


def get_scope_name() -> str:
    return f'scope{_SCOPE_LEVEL.get()}'


class Term:
    def gather_errors(self, error_bucket: list['ErrorTerm']) -> None:
        del error_bucket
        raise TaplError(f'gather_errors is not implemented in {self.__class__.__name__}')

    def add_child(self, child: 'Term') -> None:
        raise TaplError(
            f'The {self.__class__.__name__} class does not support adding a child class={child.__class__.__name__}'
        )

    def separate(self, ls: 'LayerSeparator') -> 'Layers':
        del ls
        raise TaplError(f'The {self.__class__.__name__} class does not support separate.')

    def codegen_ast(self) -> ast.AST:
        raise TaplError(f'codegen_ast is not implemented in {self.__class__.__name__}')

    def codegen_expr(self) -> ast.expr:
        raise TaplError(f'codegen_expr is not implemented in {self.__class__.__name__}')

    def codegen_stmt(self) -> list[ast.stmt]:
        raise TaplError(f'codegen_stmt is not implemented in {self.__class__.__name__}')

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'


class Layers(Term):
    def __init__(self, layers: list[Term]) -> None:
        self.layers = layers
        self._validate_layer_count()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.layers})'

    def _validate_layer_count(self) -> None:
        if len(self.layers) <= 1:
            raise TaplError('Number of layers must be equal or greater than 2.')

    @override
    def gather_errors(self, error_bucket: list['ErrorTerm']) -> None:
        for layer in self.layers:
            layer.gather_errors(error_bucket)

    @override
    def separate(self, ls: 'LayerSeparator') -> 'Layers':
        self._validate_layer_count()
        actual_count = len(self.layers)
        if actual_count != ls.layer_count:
            raise TaplError(f'Mismatched layer lengths, actual_count={actual_count}, expected_count={ls.layer_count}')
        return self

    def codegen_ast(self) -> ast.AST:
        raise TaplError('Layers should be separated before generating AST code.')

    def codegen_expr(self) -> ast.expr:
        raise TaplError('Layers should be separated before generating AST code.')

    def codegen_stmt(self) -> list[ast.stmt]:
        raise TaplError('Layers should be separated before generating AST code.')


class LayerSeparator:
    def __init__(self, layer_count: int) -> None:
        if layer_count <= 1:
            raise TaplError('layer_count must be equal or greater than 2 to separate.')
        self.layer_count = layer_count

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


@dataclass
class RearrangeLayers(Term):
    term: Term
    layer_indices: list[int]

    @override
    def gather_errors(self, error_bucket: list['ErrorTerm']) -> None:
        self.term.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        layers = ls.build(lambda layer: layer(self.term))
        result = []
        for i in self.layer_indices:
            if i >= len(layers.layers):
                raise TaplError(f'Layer index {i} out of range for layers {layers.layers}')
            result.append(layers.layers[i])
        return Layers(result)


@dataclass
class Realm(Term):
    layer_count: int
    term: Term

    @override
    def gather_errors(self, error_bucket: list['ErrorTerm']) -> None:
        self.term.gather_errors(error_bucket)


@dataclass
class Position:
    line: int
    column: int

    def __repr__(self) -> str:
        return f'{self.line}:{self.column}'


@dataclass
class Location:
    start: Position
    end: Position | None = None

    def __repr__(self) -> str:
        start = repr(self.start) if self.start else '-'
        end = repr(self.end) if self.end else '-'
        return f'({start},{end})'

    def locate(self, *nodes: ast.expr | ast.stmt) -> None:
        for node in nodes:
            node.lineno = self.start.line
            node.col_offset = self.start.column
        if self.end:
            for node in nodes:
                node.end_lineno = self.end.line
                node.end_col_offset = self.end.column


@dataclass
class ErrorTerm(Term):
    location: Location
    message: str
    recovered: bool = False
    guess: Term | None = None

    @override
    def gather_errors(self, error_bucket: list['ErrorTerm']) -> None:
        error_bucket.append(self)


class Mode(Term):
    def __init__(self, name: str) -> None:
        self.name = name

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    def separate(self, ls: 'LayerSeparator') -> Layers:
        return ls.build(lambda _: Mode(name=self.name))

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name})'


MODE_EVALUATE = Mode('evaluate')
MODE_TYPECHECK = Mode('typecheck')
MODE_SAFE = Layers([MODE_EVALUATE, MODE_TYPECHECK])


@dataclass
class TypedExpression(Term):
    mode: Term

    def codegen_evaluate(self) -> ast.expr:
        raise TaplError(f'codegen_evaluate is not implemented in {self.__class__.__name__}')

    def codegen_typecheck(self) -> ast.expr:
        raise TaplError(f'codegen_typecheck is not implemented in {self.__class__.__name__}')

    @override
    def codegen_expr(self) -> ast.expr:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise TaplError(f'Undefined run mode: {self.mode} term={self.__class__.__name__}')


@dataclass
class TypedStatement(Term):
    mode: Term

    def codegen_evaluate(self) -> list[ast.stmt]:
        raise TaplError(f'codegen_stmt_evaluate is not implemented in {self.__class__.__name__}')

    def codegen_typecheck(self) -> list[ast.stmt]:
        raise TaplError(f'codegen_stmt_typecheck is not implemented in {self.__class__.__name__}')

    @override
    def codegen_stmt(self) -> list[ast.stmt]:
        if self.mode is MODE_EVALUATE:
            return self.codegen_evaluate()
        if self.mode is MODE_TYPECHECK:
            return self.codegen_typecheck()
        raise TaplError(f'Run mode not found. {self.mode} term={self.__class__.__name__}')
