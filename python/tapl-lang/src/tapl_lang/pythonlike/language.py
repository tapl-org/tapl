# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import override

from tapl_lang.core import parser, syntax
from tapl_lang.core.language import Language
from tapl_lang.lib import terms2
from tapl_lang.pythonlike import grammar as pythonlike_grammar

IMPORT_LEVEL = 0


class PythonlikeLanguage(Language):
    @override
    def get_grammar(self, parent_stack: list[syntax.Term]) -> parser.Grammar:
        del parent_stack
        return pythonlike_grammar.get_grammar()

    def create_header_for_evaluate_layer(self) -> syntax.Term:
        location = syntax.Location(start=syntax.Position(line=1, column=0))
        return terms2.ImportFrom(location, 'tapl_lang.pythonlike.predef', [terms2.Alias(name='*')], IMPORT_LEVEL)

    def create_header_for_typecheck_layer(self) -> syntax.Term:
        location = syntax.Location(start=syntax.Position(line=1, column=0))
        return syntax.TermList(
            [
                terms2.ImportFrom(
                    location,
                    'tapl_lang.pythonlike.predef1',
                    [terms2.Alias(name='predef_proxy', asname='s0')],
                    IMPORT_LEVEL,
                ),
            ]
        )

    @override
    def get_predef_headers(self) -> list[syntax.Term]:
        headers: list[syntax.Term] = [
            self.create_header_for_evaluate_layer(),
            self.create_header_for_typecheck_layer(),
        ]
        return headers
