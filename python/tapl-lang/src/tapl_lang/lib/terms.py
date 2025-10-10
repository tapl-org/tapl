# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, override

from tapl_lang.lib import python_backend

if TYPE_CHECKING:
    import ast
    from collections.abc import Callable, Generator

from tapl_lang.core import syntax, tapl_error


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
        return python_backend.codegen_ast(self.term, self._ensure_changer()(setting))

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        return python_backend.codegen_expr(self.term, self._ensure_changer()(setting))

    @override
    def codegen_stmt(self, setting: syntax.AstSetting) -> list[ast.stmt]:
        return python_backend.codegen_stmt(self.term, self._ensure_changer()(setting))


@dataclass
class ModeTerm(syntax.Term):
    name: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: self)

    def __repr__(self) -> str:
        return self.name


MODE_EVALUATE = ModeTerm(name='MODE_EVALUATE')
MODE_TYPECHECK = ModeTerm(name='MODE_TYPECHECK')
MODE_SAFE = syntax.Layers(layers=[MODE_EVALUATE, MODE_TYPECHECK])
SAFE_LAYER_COUNT = len(MODE_SAFE.layers)


def create_safe_ast_settings() -> list[syntax.AstSetting]:
    return [
        syntax.AstSetting(),
        syntax.AstSetting(),
    ]


def make_safe_term(term: syntax.Term) -> AstSettingTerm:
    def create_changer(setting: syntax.AstSetting) -> Callable[[syntax.AstSetting], syntax.AstSetting]:
        return lambda _: setting

    settings = create_safe_ast_settings()
    changers: list[syntax.Term] = [AstSettingChanger(changer=create_changer(setting)) for setting in settings]
    return AstSettingTerm(ast_setting_changer=syntax.Layers(layers=changers), term=term)
