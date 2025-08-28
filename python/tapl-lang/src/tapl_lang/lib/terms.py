# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, override

if TYPE_CHECKING:
    import ast
    from collections.abc import Callable, Generator

from tapl_lang.core import syntax, tapl_error


class Layers(syntax.Term):
    def __init__(self, layers: list[syntax.Term]) -> None:
        self.layers = layers
        self._validate_layer_count()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.layers})'

    def _validate_layer_count(self) -> None:
        if len(self.layers) <= 1:
            raise tapl_error.TaplError('Number of layers must be equal or greater than 2.')

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.layers

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        self._validate_layer_count()
        actual_count = len(self.layers)
        if actual_count != ls.layer_count:
            raise tapl_error.TaplError(
                f'Mismatched layer lengths, actual_count={actual_count}, expected_count={ls.layer_count}'
            )
        return self.layers

    @override
    def codegen_ast(self, setting: syntax.AstSetting) -> ast.AST:
        raise tapl_error.TaplError('Layers should be separated before generating AST code.')

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        raise tapl_error.TaplError('Layers should be separated before generating AST code.')

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        raise tapl_error.TaplError('Layers should be separated before generating AST code.')


@dataclass
class RearrangeLayers(syntax.Term):
    term: syntax.Term
    layer_indices: list[int]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.term

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        layers = ls.build(lambda layer: layer(self.term))
        result = []
        for i in self.layer_indices:
            if i >= len(layers):
                raise tapl_error.TaplError(f'Layer index {i} out of range for layers {layers}')
            result.append(layers[i])
        return result


@dataclass
class Realm(syntax.Term):
    layer_count: int
    term: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.term


def gather_errors(term: syntax.Term) -> list[syntax.ErrorTerm]:
    error_bucket: list[syntax.ErrorTerm] = []

    def gather_errors_recursive(t: syntax.Term) -> None:
        if isinstance(t, syntax.ErrorTerm):
            error_bucket.append(t)
        for child in t.children():
            gather_errors_recursive(child)

    gather_errors_recursive(term)
    return error_bucket


@dataclass
class AstSettingChanger(syntax.Term):
    changer: Callable[[syntax.AstSetting], syntax.AstSetting]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: AstSettingChanger(changer=self.changer))


@dataclass
class AstSettingTerm(syntax.Term):
    ast_setting_changer: syntax.Term
    term: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.ast_setting_changer
        yield self.term

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: AstSettingTerm(ast_setting_changer=layer(self.ast_setting_changer), term=layer(self.term))
        )

    def _ensure_changer(self) -> Callable[[syntax.AstSetting], syntax.AstSetting]:
        if not isinstance(self.ast_setting_changer, AstSettingChanger):
            raise tapl_error.TaplError(
                f'Expected setting to be an instance of AstSetting, got {type(self.ast_setting_changer).__name__}'
            )
        return cast(AstSettingChanger, self.ast_setting_changer).changer

    @override
    def codegen_ast(self, setting: syntax.AstSetting) -> ast.AST:
        return self.term.codegen_ast(self._ensure_changer()(setting))

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        return self.term.codegen_expr(self._ensure_changer()(setting))

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return self.term.codegen_stmt(self._ensure_changer()(setting))


def create_safe_ast_settings() -> list[syntax.AstSetting]:
    return [
        syntax.AstSetting(code_mode=syntax.CodeMode.EVALUATE, scope_mode=syntax.ScopeMode.NATIVE),
        syntax.AstSetting(code_mode=syntax.CodeMode.TYPECHECK, scope_mode=syntax.ScopeMode.MANUAL),
    ]


SAFE_LAYER_COUNT = len(create_safe_ast_settings())


def make_safe_term(term: syntax.Term) -> AstSettingTerm:
    def create_changer(setting: syntax.AstSetting) -> Callable[[syntax.AstSetting], syntax.AstSetting]:
        return lambda _: setting

    settings = create_safe_ast_settings()
    changers: list[syntax.Term] = [AstSettingChanger(changer=create_changer(setting)) for setting in settings]
    return AstSettingTerm(ast_setting_changer=Layers(layers=changers), term=term)
