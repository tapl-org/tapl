# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, override

if TYPE_CHECKING:
    import ast
    from collections.abc import Callable, Generator

from tapl_lang.core.syntax import AstSetting, CodeMode, ErrorTerm, LayerSeparator, ScopeMode, Term
from tapl_lang.core.tapl_error import TaplError


# Used when a term depends on a Block to be merged into it.
# For example: # An else statement must be merged into the preceding sibling if statement.
class DependentTerm(Term):
    def merge_into(self, parent_block: Block) -> None:
        """Merges this term into the terms of specified parent block."""
        del parent_block
        raise TaplError(f'{self.__class__.__name__}.merge_into is not implemented.')


@dataclass
class Block(Term):
    terms: list[Term]
    # Indicates a delayed term list, useful when its initialization depends on child chunk parsing.
    # For example: if, elif, else, for, and while statements.
    delayed: bool = False

    @override
    def children(self) -> Generator[Term, None, None]:
        yield from self.terms

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        return ls.build(lambda layer: Block(terms=[layer(s) for s in self.terms], delayed=self.delayed))

    @override
    def codegen_stmt(self, setting) -> list[ast.stmt]:
        if self.delayed:
            raise TaplError('Block is delayed and cannot be used for code generation.')
        return [s for b in self.terms for s in b.codegen_stmt(setting)]


def find_delayed_block(term: Term) -> Block | None:
    delayed_block: Block | None = None

    def loop(t: Term) -> None:
        nonlocal delayed_block
        if isinstance(t, Block) and t.delayed:
            if delayed_block is None:
                delayed_block = t
            else:
                raise TaplError('Multiple delayed blocks found.')
        for child in t.children():
            loop(child)

    loop(term)
    return delayed_block


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
    def children(self) -> Generator[Term, None, None]:
        yield from self.layers

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


@dataclass
class RearrangeLayers(Term):
    term: Term
    layer_indices: list[int]

    @override
    def children(self) -> Generator[Term, None, None]:
        yield self.term

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
    def children(self) -> Generator[Term, None, None]:
        yield self.term


def gather_errors(term: Term) -> list[ErrorTerm]:
    error_bucket: list[ErrorTerm] = []

    def gather_errors_recursive(t: Term) -> None:
        if isinstance(t, ErrorTerm):
            error_bucket.append(t)
        if isinstance(t, Block) and t.delayed:
            error = ErrorTerm(
                message='Block term is still delayed and not initialized yet. Expecting its body to be set.',
            )
            error_bucket.append(error)
        for child in t.children():
            gather_errors_recursive(child)

    gather_errors_recursive(term)
    return error_bucket


@dataclass
class AstSettingChanger(Term):
    changer: Callable[[AstSetting], AstSetting]

    @override
    def children(self) -> Generator[Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        return ls.build(lambda _: AstSettingChanger(changer=self.changer))


@dataclass
class AstSettingTerm(Term):
    ast_setting_changer: Term
    term: Term

    @override
    def children(self) -> Generator[Term, None, None]:
        yield self.ast_setting_changer
        yield self.term

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


SAFE_LAYER_COUNT = len(create_safe_ast_settings())


def make_safe_term(term: Term) -> AstSettingTerm:
    def create_changer(setting: AstSetting) -> Callable[[AstSetting], AstSetting]:
        return lambda _: setting

    settings = create_safe_ast_settings()
    changers: list[Term] = [AstSettingChanger(changer=create_changer(setting)) for setting in settings]
    return AstSettingTerm(ast_setting_changer=Layers(layers=changers), term=term)
