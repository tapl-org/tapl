# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import override

from tapl_lang import parser, syntax
from tapl_lang.context import Context
from tapl_lang.pythonlike import expr, stmt
from tapl_lang.pythonlike import parser as pythonlike_parser

IMPORT_LEVEL = 0


class PythonlikeContext(Context):
    @override
    def get_grammar(self, parent_stack: list[syntax.Term]) -> parser.Grammar:
        del parent_stack
        return pythonlike_parser.GRAMMAR

    def create_header_for_evaluate_layer(self) -> syntax.Term:
        location = syntax.Location(start=syntax.Position(line=1, column=0))
        return stmt.ImportFrom(location, 'tapl_lang.pythonlike.predef', [stmt.Alias(name='*')], IMPORT_LEVEL)

    def create_header_for_typecheck_layer(self) -> syntax.Term:
        location = syntax.Location(start=syntax.Position(line=1, column=0))
        scope0 = stmt.Assign(
            location,
            [expr.Name(location=location, id='scope0', ctx='store')],
            expr.Call(
                location,
                expr.Attribute(
                    location,
                    expr.Name(location=location, id='predef', ctx='load'),
                    attr='Scope',
                    ctx='load',
                ),
                [
                    expr.Attribute(
                        location=location,
                        value=expr.Name(location=location, id='predef', ctx='load'),
                        attr='predef_scope',
                        ctx='load',
                    )
                ],
            ),
        )
        return stmt.Sequence(
            [
                stmt.ImportFrom(
                    location, 'tapl_lang.pythonlike', [stmt.Alias(name='predef1', asname='predef')], IMPORT_LEVEL
                ),
                syntax.AstSettingTerm(
                    ast_setting_changer=syntax.AstSettingChanger(
                        lambda setting: setting.clone(scope_mode=syntax.ScopeMode.NATIVE)
                    ),
                    term=scope0,
                ),
            ]
        )

    @override
    def get_predef_layers(self) -> syntax.Layers:
        layers: list[syntax.Term] = [
            self.create_header_for_evaluate_layer(),
            self.create_header_for_typecheck_layer(),
        ]
        return syntax.Layers(layers)
