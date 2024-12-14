# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast
from typing import cast

from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike import parser
from tapl_lang.syntax import Layers, Term


def do_expr(text: str) -> list[ast.expr]:
    parsed = parse_text(text, Grammar(parser.RULES, 'disjunction'), log_cell_memo=False)
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    separated = parsed.separate()
    layers = cast(Layers, separated).layers
    return [layer.codegen_expr() for layer in layers]


def run2(term: Term):
    expr_ast = ast.Expression(body=term.codegen_expr())
    compiled_code = compile(expr_ast, filename='', mode='eval')
    return eval(compiled_code)


def test_constant_true():
    [expr1, expr2] = do_expr('True')
    assert ast.unparse(expr1) == 'True'
    assert ast.unparse(expr2) == 'typelib.Bool'


def test_inversion():
    [expr1, expr2] = do_expr('not True')
    assert ast.unparse(expr1) == 'not True'
    assert ast.unparse(expr2) == 'typelib.Bool'


# def test_conjuction1():
#     term = parse('True and True')
#     assert isinstance(term, syntax.BoolOp)
#     assert run(term) is True


# def test_conjuction2():
#     term = parse('True and True     and    False')
#     assert isinstance(term, syntax.BoolOp)
#     assert run(term) is False


# def test_disjunction():
#     term = parse('True and True     and    False  or True')
#     assert isinstance(term, syntax.BoolOp)
#     assert run(term) is True
