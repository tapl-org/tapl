# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import override

from tapl_lang import parser
from tapl_lang.context import Context
from tapl_lang.pythonlike import expr, stmt
from tapl_lang.pythonlike import parser as pythonlike_parser
from tapl_lang.syntax import MODE_EVALUATE, Layers, Location, Position, Term


class PythonlikeContext(Context):
    @override
    def get_grammar(self, parent_stack: list[Term]) -> parser.Grammar:
        del parent_stack
        return pythonlike_parser.GRAMMAR

    @override
    def get_predef_layers(self) -> Layers:
        location = Location(start=Position(line=1, column=0))
        level = 0
        layers: list[Term] = [
            stmt.ImportFrom(location, 'tapl_lang.pythonlike.predef', [stmt.Alias(name='*')], level),
            stmt.Sequence(
                [
                    stmt.ImportFrom(
                        location, 'tapl_lang.pythonlike', [stmt.Alias(name='predef1', asname='predef')], level
                    ),
                    stmt.Assign(
                        location,
                        [expr.Name(mode=MODE_EVALUATE, location=location, id='scope0', ctx='store')],
                        expr.Call(
                            location,
                            expr.Attribute(
                                location,
                                expr.Name(mode=MODE_EVALUATE, location=location, id='predef', ctx='load'),
                                attr='Scope',
                                ctx='load',
                            ),
                            [
                                expr.Attribute(
                                    location=location,
                                    value=expr.Name(mode=MODE_EVALUATE, location=location, id='predef', ctx='load'),
                                    attr='predef_scope',
                                    ctx='load',
                                )
                            ],
                        ),
                    ),
                ]
            ),
        ]
        return Layers(layers)
