# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, cast, override

from tapl_lang.tapl_error import TaplError

if TYPE_CHECKING:
    import ast
    from collections.abc import Callable


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
    def scope_native(self) -> bool:
        return self.scope_mode == ScopeMode.NATIVE

    @property
    def scope_manual(self) -> bool:
        return self.scope_mode == ScopeMode.MANUAL

    @property
    def code_evaluate(self) -> bool:
        return self.code_mode == CodeMode.EVALUATE

    @property
    def code_typecheck(self) -> bool:
        return self.code_mode == CodeMode.TYPECHECK

    def clone(
        self, code_mode: CodeMode | None = None, scope_mode: ScopeMode | None = None, scope_level: int | None = None
    ) -> AstSetting:
        return AstSetting(
            code_mode=code_mode or self.code_mode,
            scope_mode=scope_mode or self.scope_mode,
            scope_level=scope_level or self.scope_level,
        )

    def get_current_scope_name(self) -> str:
        return f'scope{self.scope_level}'


class Term:
    # TODO: convert to a walk to traverse the tree
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        del error_bucket
        raise TaplError(f'gather_errors is not implemented in {self.__class__.__name__}')

    def add_child(self, child: Term) -> None:
        raise TaplError(
            f'The {self.__class__.__name__} class does not support adding a child class={child.__class__.__name__}'
        )

    def separate(self, ls: LayerSeparator) -> list[Term]:
        del ls
        raise TaplError(f'The {self.__class__.__name__} class does not support separate.')

    def codegen_ast(self, setting: AstSetting) -> ast.AST:
        del setting
        raise TaplError(f'codegen_ast is not implemented in {self.__class__.__name__}')

    def codegen_expr(self, setting: AstSetting) -> ast.expr:
        del setting
        raise TaplError(f'codegen_expr is not implemented in {self.__class__.__name__}')

    def codegen_stmt(self, setting: AstSetting) -> list[ast.stmt]:
        del setting
        raise TaplError(f'codegen_stmt is not implemented in {self.__class__.__name__}')

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'


@dataclass
class AstSettingChanger(Term):
    changer: Callable[[AstSetting], AstSetting]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        return ls.build(lambda _: AstSettingChanger(changer=self.changer))


@dataclass
class AstSettingTerm(Term):
    ast_setting_changer: Term
    term: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.ast_setting_changer.gather_errors(error_bucket)
        self.term.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        return ls.build(
            lambda layer: AstSettingTerm(ast_setting_changer=layer(self.ast_setting_changer), term=layer(self.term))
        )

    def _ensure_changer(self) -> Callable[[AstSetting], AstSetting]:
        if not isinstance(self.ast_setting_changer, AstSettingChanger):
            raise TaplError(
                f'Expected setting to be an instance of AstSetting, got {type(self.ast_setting_changer).__name__}'
            )
        return cast(AstSettingChanger, self.ast_setting_changer).changer

    @override
    def codegen_ast(self, setting: AstSetting) -> ast.AST:
        return self.term.codegen_ast(self._ensure_changer()(setting))

    @override
    def codegen_expr(self, setting: AstSetting) -> ast.expr:
        return self.term.codegen_expr(self._ensure_changer()(setting))

    @override
    def codegen_stmt(self, setting: AstSetting) -> list[ast.stmt]:
        return self.term.codegen_stmt(self._ensure_changer()(setting))


def create_safe_ast_settings() -> list[AstSetting]:
    return [
        AstSetting(code_mode=CodeMode.EVALUATE, scope_mode=ScopeMode.NATIVE),
        AstSetting(code_mode=CodeMode.TYPECHECK, scope_mode=ScopeMode.MANUAL),
    ]


def make_safe_term(term: Term) -> AstSettingTerm:
    def create_changer(setting: AstSetting) -> Callable[[AstSetting], AstSetting]:
        return lambda _: setting

    settings = create_safe_ast_settings()
    changers: list[Term] = [AstSettingChanger(changer=create_changer(setting)) for setting in settings]
    return AstSettingTerm(ast_setting_changer=Layers(layers=changers), term=term)


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
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        for layer in self.layers:
            layer.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        self._validate_layer_count()
        actual_count = len(self.layers)
        if actual_count != ls.layer_count:
            raise TaplError(f'Mismatched layer lengths, actual_count={actual_count}, expected_count={ls.layer_count}')
        return self.layers

    @override
    def codegen_ast(self, setting: AstSetting) -> ast.AST:
        raise TaplError('Layers should be separated before generating AST code.')

    @override
    def codegen_expr(self, setting: AstSetting) -> ast.expr:
        raise TaplError('Layers should be separated before generating AST code.')

    @override
    def codegen_stmt(self, setting: AstSetting) -> list[ast.stmt]:
        raise TaplError('Layers should be separated before generating AST code.')


class LayerSeparator:
    def __init__(self, layer_count: int) -> None:
        if layer_count <= 1:
            raise TaplError('layer_count must be equal or greater than 2 to separate.')
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
                raise TaplError('layer function call order is changed.')
            return layers[index]

        def create_extract_layer_fn(index: int) -> Callable[[Term], Term]:
            return lambda term: extract_layer(index, term)

        layers: list[Term] = []
        for i in range(self.layer_count):
            memo_index[0] = 0
            layers.append(factory(create_extract_layer_fn(i)))
        return layers

    def separate(self, term: Term) -> list[Term]:
        return self.build(lambda layer: layer(term))


@dataclass
class RearrangeLayers(Term):
    term: Term
    layer_indices: list[int]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.term.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        layers = ls.build(lambda layer: layer(self.term))
        result = []
        for i in self.layer_indices:
            if i >= len(layers):
                raise TaplError(f'Layer index {i} out of range for layers {layers}')
            result.append(layers[i])
        return result


@dataclass
class Realm(Term):
    layer_count: int
    term: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
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
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        error_bucket.append(self)
