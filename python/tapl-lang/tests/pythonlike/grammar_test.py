# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.core import parser, syntax
from tapl_lang.lib import terms
from tapl_lang.pythonlike import grammar
from tapl_lang.pythonlike import rule_names as rn


def parse_expr(text: str, start_rule: str, *, debug=False) -> syntax.Term:
    return parser.parse_text(text, grammar=parser.Grammar(grammar.get_grammar().rule_map, start_rule), debug=debug)


def create_loc(start_line: int, start_col: int, end_line: int, end_col: int) -> syntax.Location:
    return syntax.Location(
        start=syntax.Position(line=start_line, column=start_col), end=syntax.Position(line=end_line, column=end_col)
    )


def test_simple_stmt__pass():
    actual = parse_expr('pass', rn.PASS_STMT)
    expected = terms.Pass(location=create_loc(1, 0, 1, 4))
    assert actual == expected
