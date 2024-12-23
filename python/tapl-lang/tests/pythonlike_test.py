# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast
from typing import cast

from tapl_lang import typelib as t
from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike import parser
from tapl_lang.syntax import Layers


def parse_expr(text: str, *, log_cell_memo=False) -> list[ast.expr]:
    parsed = parse_text(text, Grammar(parser.RULES, 'disjunction'), log_cell_memo=log_cell_memo)
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    if errors := parsed.get_errors():
        messages = [e.message for e in errors]
        raise SyntaxError('\n\n'.join(messages))
    separated = parsed.separate()
    layers = cast(Layers, separated).layers
    return [layer.codegen_expr() for layer in layers]


def run_expr(expr: ast.expr):
    compiled_code = compile(ast.Expression(body=expr), filename='', mode='eval')
    return eval(compiled_code)


def expect_error(expr: ast.expr) -> str:
    try:
        run_expr(expr)
    except TypeError as e:
        return repr(e)
    else:
        return 'NO ERROR'


def test_constant_true():
    [expr1, expr2] = parse_expr('True')
    assert ast.unparse(expr1) == 'True'
    assert ast.unparse(expr2) == 't.Bool_'
    assert run_expr(expr2) == t.Bool_
    assert run_expr(expr1) is True


def test_constant_number7():
    [expr1, expr2] = parse_expr('7')
    assert ast.unparse(expr1) == '7'
    assert ast.unparse(expr2) == 't.Int_'
    assert run_expr(expr2) == t.Int_
    assert run_expr(expr1) == 7


def test_inversion_bool():
    [expr1, expr2] = parse_expr('not True')
    assert ast.unparse(expr1) == 'not True'
    assert ast.unparse(expr2) == 't.Bool_'
    assert run_expr(expr2) == t.Bool_
    assert run_expr(expr1) is False


def test_inversion_number():
    [expr1, expr2] = parse_expr('not 0')
    assert ast.unparse(expr1) == 'not 0'
    assert ast.unparse(expr2) == 't.Bool_'
    assert run_expr(expr2) == t.Bool_
    assert run_expr(expr1) is True


def test_conjuction_bool1():
    [expr1, expr2] = parse_expr('True and True')
    assert ast.unparse(expr1) == 'True and True'
    assert ast.unparse(expr2) == 't.create_union(t.Bool_, t.Bool_)'
    assert run_expr(expr2) == t.Bool_
    assert run_expr(expr1) is True


def test_conjuction_bool2():
    [expr1, expr2] = parse_expr('True and True     and    False')
    assert ast.unparse(expr1) == 'True and True and False'
    assert ast.unparse(expr2) == 't.create_union(t.Bool_, t.Bool_, t.Bool_)'
    assert run_expr(expr2) == t.Bool_
    assert run_expr(expr1) is False


def test_conjuction_number1():
    [expr1, expr2] = parse_expr('3 and 4')
    assert ast.unparse(expr1) == '3 and 4'
    assert ast.unparse(expr2) == 't.create_union(t.Int_, t.Int_)'
    assert run_expr(expr2) == t.Int_
    assert run_expr(expr1) == 4


def test_conjuction_number2():
    [expr1, expr2] = parse_expr('0 and 4')
    assert ast.unparse(expr1) == '0 and 4'
    assert ast.unparse(expr2) == 't.create_union(t.Int_, t.Int_)'
    assert run_expr(expr2) == t.Int_
    assert run_expr(expr1) == 0


def test_conjuction_mix():
    [expr1, expr2] = parse_expr('True and 4')
    assert ast.unparse(expr1) == 'True and 4'
    assert ast.unparse(expr2) == 't.create_union(t.Bool_, t.Int_)'
    assert run_expr(expr2) == t.create_union(t.Int_, t.Bool_)
    assert run_expr(expr1) == 4


def test_disjunction():
    [expr1, expr2] = parse_expr('True and True     and    False  or True')
    assert ast.unparse(expr1) == 'True and True and False or True'
    assert ast.unparse(expr2) == 't.create_union(t.create_union(t.Bool_, t.Bool_, t.Bool_), t.Bool_)'
    assert run_expr(expr2) == t.Bool_
    assert run_expr(expr1) is True


def test_term1():
    [expr1, expr2] = parse_expr('2 + 3')
    assert ast.unparse(expr1) == '2 + 3'
    assert ast.unparse(expr2) == 't.Int_ + t.Int_'
    assert run_expr(expr2) == t.Int_
    assert run_expr(expr1) == 5


def test_term2():
    [expr1, expr2] = parse_expr('2 + True')
    assert ast.unparse(expr1) == '2 + True'
    assert ast.unparse(expr2) == 't.Int_ + t.Bool_'
    assert run_expr(expr2) == t.Int_
    assert run_expr(expr1) == 3  # True is considered as 1 in Python


def test_term_error():
    [expr1, expr2] = parse_expr("2 + 'abc'", log_cell_memo=True)
    assert ast.unparse(expr1) == "2 + 'abc'"
    assert ast.unparse(expr2) == 't.Int_ + t.Str_'
    assert expect_error(expr2) == "TypeError('unsupported operand type(s) for +: Int and Str')"
