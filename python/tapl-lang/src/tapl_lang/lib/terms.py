# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from tapl_lang.core import syntax


def create_safe_ast_settings() -> list[syntax.AstSetting]:
    return [
        syntax.AstSetting(scope_level=0),
        syntax.AstSetting(scope_level=0),
    ]


def make_safe_term(term: syntax.Term) -> syntax.Term:
    def create_changer(setting: syntax.AstSetting) -> Callable[[syntax.AstSetting], syntax.AstSetting]:
        return lambda _: setting

    settings = [
        syntax.AstSetting(scope_level=0),
        syntax.AstSetting(scope_level=0),
    ]
    changers: list[syntax.Term] = [syntax.AstSettingChanger(changer=create_changer(setting)) for setting in settings]
    return syntax.BackendSettingTerm(backend_setting_changer=syntax.Layers(layers=changers), term=term)
