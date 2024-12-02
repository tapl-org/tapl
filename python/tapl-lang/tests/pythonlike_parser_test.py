# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang import pythonlike_syntax
from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike_parser import RULES
from tapl_lang.syntax import Term


def parse(text: str) -> Term | None:
    return parse_text(text, Grammar(RULES, 'atom'), log_cell_memo=True)


def test_constant_true():
    parsed_term = parse('True')
    assert isinstance(parsed_term, pythonlike_syntax.Constant)
    assert parsed_term.value is True
