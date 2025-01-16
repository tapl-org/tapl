# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang import parser
from tapl_lang.context import Context
from tapl_lang.pythonlike import parser as pythonlike_parser
from tapl_lang.syntax import Term


class PythonlikeContext(Context):
    def get_grammar(self, parent_stack: list[Term]) -> parser.Grammar:
        del parent_stack
        return pythonlike_parser.GRAMMAR
