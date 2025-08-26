# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, override

from tapl_lang.core import tapl_error

if TYPE_CHECKING:
    import ast
    from collections.abc import Callable, Generator


class Term:
    def children(self) -> Generator[Term, None, None]:
        """Yields the child terms of this term for tree traversal or visitor operations."""
        raise tapl_error.TaplError(f'{self.__class__.__name__}.children is not implemented.')

    def separate(self, ls: LayerSeparator) -> list[Term]:
        """Separate the term into layers based on the number of layers specified by the LayerSeparator."""
        del ls
        raise tapl_error.TaplError(f'The {self.__class__.__name__} class does not support separate.')

    def codegen_ast(self, setting: AstSetting) -> ast.AST:
        """Generates the AST representation of this term."""
        del setting
        raise tapl_error.TaplError(f'codegen_ast is not implemented in {self.__class__.__name__}')

    def codegen_expr(self, setting: AstSetting) -> ast.expr:
        """Generates the expression AST representation of this term."""
        del setting
        raise tapl_error.TaplError(f'codegen_expr is not implemented in {self.__class__.__name__}')

    def codegen_stmt(self, setting: AstSetting) -> list[ast.stmt]:
        """Generates the statement AST representation of this term."""
        del setting
        raise tapl_error.TaplError(f'codegen_stmt is not implemented in {self.__class__.__name__}')

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'


class LayerSeparator:
    def __init__(self, layer_count: int) -> None:
        if layer_count <= 1:
            raise tapl_error.TaplError('layer_count must be equal or greater than 2 to separate.')
        self.layer_count = layer_count

    def build(self, factory: Callable[[Callable[[Term], Term]], Term]) -> list[Term]:
        # Memorize the order of extract_layer calls to ensure consistent layer processing.
        memo: list[tuple[Term, list[Term]]] = []
        memo_index = [0]

        def extract_layer(index: int, term: Term) -> Term:
            if index == 0:
                memo.append((term, term.separate(self)))
            original_term, layers = memo[memo_index[0]]
            memo_index[0] += 1
            if original_term is not term:
                raise tapl_error.TaplError('layer function call order is changed.')
            return layers[index]

        def create_extract_layer_fn(index: int) -> Callable[[Term], Term]:
            return lambda term: extract_layer(index, term)

        layers: list[Term] = []
        for i in range(self.layer_count):
            memo_index[0] = 0
            layers.append(factory(create_extract_layer_fn(i)))
        return layers


class CodeMode(Enum):
    EVALUATE = 1  # For generating a evaluating code
    TYPECHECK = 2  # For generating a type-checking code


class ScopeMode(Enum):
    NATIVE = 1  # Variables are handled natively
    MANUAL = 2  # Variables are managed manually (e.g., in a scope)


@dataclass
class AstSetting:
    code_mode: CodeMode = CodeMode.EVALUATE
    scope_mode: ScopeMode = ScopeMode.NATIVE
    scope_level: int = 0

    @property
    def code_evaluate(self) -> bool:
        return self.code_mode == CodeMode.EVALUATE

    @property
    def code_typecheck(self) -> bool:
        return self.code_mode == CodeMode.TYPECHECK

    @property
    def scope_native(self) -> bool:
        return self.scope_mode == ScopeMode.NATIVE

    @property
    def scope_manual(self) -> bool:
        return self.scope_mode == ScopeMode.MANUAL

    def clone(
        self, code_mode: CodeMode | None = None, scope_mode: ScopeMode | None = None, scope_level: int | None = None
    ) -> AstSetting:
        return AstSetting(
            code_mode=code_mode or self.code_mode,
            scope_mode=scope_mode or self.scope_mode,
            scope_level=scope_level or self.scope_level,
        )

    # TODO: AstSetting is not the right place for scope_name and forker_name function
    @property
    def scope_name(self) -> str:
        return f's{self.scope_level}'

    @property
    def forker_name(self) -> str:
        return f'f{self.scope_level}'


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
    message: str
    location: Location | None = None
    recovered: bool = False
    guess: Term | None = None

    @override
    def children(self) -> Generator[Term, None, None]:
        yield from ()

    @override
    def __repr__(self) -> str:
        if self.location:
            return f'{self.location} {self.message}'
        return self.message
