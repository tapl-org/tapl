# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.core import parser, syntax
from tapl_lang.core.language import Language
from tapl_lang.lib import terms
from tapl_lang.pythonlike import grammar as pythonlike_grammar

IMPORT_LEVEL = 0

GRAMMAR = pythonlike_grammar.get_grammar()


class PythonlikeLanguage(Language):
    def get_grammar(self, parent_stack: list[syntax.Term]) -> parser.Grammar:
        del parent_stack
        return GRAMMAR

    def create_header_for_evaluate_layer(self) -> syntax.Term:
        location = syntax.Location(start=syntax.Position(line=1, column=0))
        return terms.ImportFrom('tapl_lang.pythonlike.predef', [terms.Alias(name='*')], IMPORT_LEVEL, location=location)

    def create_header_for_typecheck_layer(self) -> syntax.Term:
        location = syntax.Location(start=syntax.Position(line=1, column=0))
        return syntax.TermList(
            [
                terms.ImportFrom(
                    'tapl_lang.lib',
                    [terms.Alias(name='tapl_typing')],
                    IMPORT_LEVEL,
                    location=location,
                ),
                terms.ImportFrom(
                    'tapl_lang.pythonlike.predef1',
                    [terms.Alias(name='predef_scope', asname='predef_scope__sa')],
                    IMPORT_LEVEL,
                    location=location,
                ),
                terms.Assign(
                    targets=[terms.Name(location=location, id=lambda setting: setting.scope_name, ctx='store')],
                    value=terms.Call(
                        location=location,
                        func=terms.Path(
                            location=location,
                            names=['tapl_typing', 'create_scope'],
                            ctx='load',
                            mode=terms.MODE_EVALUATE,
                        ),
                        args=[],
                        keywords=[
                            (
                                'parent__sa',
                                terms.Name(location=location, id='predef_scope__sa', ctx='load'),
                            )
                        ],
                    ),
                    location=location,
                ),
            ]
        )

    def get_predef_headers(self) -> list[syntax.Term]:
        headers: list[syntax.Term] = [
            self.create_header_for_evaluate_layer(),
            self.create_header_for_typecheck_layer(),
        ]
        return headers
