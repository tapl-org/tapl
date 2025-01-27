# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import override

from tapl_lang import parser
from tapl_lang.context import Context
from tapl_lang.pythonlike import parser as pythonlike_parser
from tapl_lang.pythonlike import stmt
from tapl_lang.syntax import Layers, Location, Position, Term


class PythonlikeContext(Context):
    @override
    def get_grammar(self, parent_stack: list[Term]) -> parser.Grammar:
        del parent_stack
        return pythonlike_parser.GRAMMAR

    @override
    def get_predef_layers(self) -> Layers:
        location = Location(start=Position(line=1, column=0))
        module0 = 'tapl_lang.pythonlike.predef0'
        module1 = 'tapl_lang.pythonlike.predef1'
        names = [stmt.Alias(name='*')]
        level = 0
        layers: list[Term] = [
            stmt.ImportFrom(location, module0, names, level),
            stmt.ImportFrom(location, module1, names, level),
        ]
        return Layers(layers)
