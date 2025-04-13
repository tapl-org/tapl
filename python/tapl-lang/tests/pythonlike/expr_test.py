# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike import parser, predef, predef1
from tapl_lang.syntax import ErrorTerm, LayerSeparator

predef_layers = [predef, predef1]


def parse_expr(text: str, *, debug=False) -> list[ast.expr]:
    parsed = parse_text(text, Grammar(parser.RULES, 'expression'), debug=debug)
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    error_bucket: list[ErrorTerm] = []
    parsed.gather_errors(error_bucket)
    if error_bucket:
        messages = [e.message for e in error_bucket]
        raise SyntaxError('\n\n'.join(messages))
    separated = LayerSeparator(2).separate(parsed)
    return [layer.codegen_expr() for layer in separated.layers]


def run_expr(layer_index: int, expr: ast.expr, /, globals_=None, locals_=None):
    compiled_code = compile(ast.Expression(body=expr), filename='', mode='eval')
    return eval(compiled_code, globals=globals_ or predef_layers[layer_index].__dict__, locals=locals_ or {})


def expect_error(layer_index: int, expr: ast.expr) -> str:
    try:
        run_expr(layer_index, expr)
    except TypeError as e:
        return repr(e)
    else:
        return 'NO ERROR'


def test_constant_true():
    [expr1, expr2] = parse_expr('True')
    assert ast.unparse(expr1) == 'True'
    assert ast.unparse(expr2) == 'Bool'
    assert run_expr(1, expr2) == predef1.Bool
    assert run_expr(0, expr1) is True


def test_constant_number7():
    [expr1, expr2] = parse_expr('7')
    assert ast.unparse(expr1) == '7'
    assert ast.unparse(expr2) == 'Int'
    assert run_expr(1, expr2) == predef1.Int
    assert run_expr(0, expr1) == 7


def test_inversion_bool():
    [expr1, expr2] = parse_expr('not True')
    assert ast.unparse(expr1) == 'not True'
    assert ast.unparse(expr2) == 'Bool'
    assert run_expr(1, expr2) == predef1.Bool
    assert run_expr(0, expr1) is False


def test_inversion_number():
    [expr1, expr2] = parse_expr('not 0')
    assert ast.unparse(expr1) == 'not 0'
    assert ast.unparse(expr2) == 'Bool'
    assert run_expr(1, expr2) == predef1.Bool
    assert run_expr(0, expr1) is True


def test_conjuction_bool1():
    [expr1, expr2] = parse_expr('True and True')
    assert ast.unparse(expr1) == 'True and True'
    assert ast.unparse(expr2) == 'create_union(Bool, Bool)'
    assert run_expr(1, expr2) == predef1.Bool
    assert run_expr(0, expr1) is True


def test_conjuction_bool2():
    [expr1, expr2] = parse_expr('True and True     and    False')
    assert ast.unparse(expr1) == 'True and True and False'
    assert ast.unparse(expr2) == 'create_union(Bool, Bool, Bool)'
    assert run_expr(1, expr2) == predef1.Bool
    assert run_expr(0, expr1) is False


def test_conjuction_number1():
    [expr1, expr2] = parse_expr('3 and 4')
    assert ast.unparse(expr1) == '3 and 4'
    assert ast.unparse(expr2) == 'create_union(Int, Int)'
    assert run_expr(1, expr2) == predef1.Int
    assert run_expr(0, expr1) == 4


def test_conjuction_number2():
    [expr1, expr2] = parse_expr('0 and 4')
    assert ast.unparse(expr1) == '0 and 4'
    assert ast.unparse(expr2) == 'create_union(Int, Int)'
    assert run_expr(1, expr2) == predef1.Int
    assert run_expr(0, expr1) == 0


def test_conjuction_mix():
    [expr1, expr2] = parse_expr('True and 4')
    assert ast.unparse(expr1) == 'True and 4'
    assert ast.unparse(expr2) == 'create_union(Bool, Int)'
    assert run_expr(1, expr2) == predef1.create_union(predef1.Int, predef1.Bool)
    assert run_expr(0, expr1) == 4


def test_disjunction():
    [expr1, expr2] = parse_expr('True and True     and    False  or True')
    assert ast.unparse(expr1) == 'True and True and False or True'
    assert ast.unparse(expr2) == 'create_union(create_union(Bool, Bool, Bool), Bool)'
    assert run_expr(1, expr2) == predef1.Bool
    assert run_expr(0, expr1) is True


def test_term1():
    [expr1, expr2] = parse_expr('2 + 3')
    assert ast.unparse(expr1) == '2 + 3'
    assert ast.unparse(expr2) == 'Int + Int'
    assert run_expr(1, expr2) == predef1.Int
    assert run_expr(0, expr1) == 5


def test_term2():
    [expr1, expr2] = parse_expr('2 + True')
    assert ast.unparse(expr1) == '2 + True'
    assert ast.unparse(expr2) == 'Int + Bool'
    assert run_expr(1, expr2) == predef1.Int
    assert run_expr(0, expr1) == 3  # True is considered as 1 in Python


def test_term_error():
    [expr1, expr2] = parse_expr("2 + 'abc'")
    assert ast.unparse(expr1) == "2 + 'abc'"
    assert ast.unparse(expr2) == 'Int + Str'
    assert expect_error(1, expr2) == "TypeError('unsupported operand type(s) for +: Int and Str')"


def test_compare1():
    [expr1, expr2] = parse_expr('2 < 3')
    assert ast.unparse(expr1) == '2 < 3'
    assert ast.unparse(expr2) == 'Int < Int'
    assert run_expr(1, expr2) == predef1.Int
    assert run_expr(0, expr1) is True


def test_compare2():
    [expr1, expr2] = parse_expr('True < 0')
    assert ast.unparse(expr1) == 'True < 0'
    assert ast.unparse(expr2) == 'Bool < Int'
    assert run_expr(1, expr2) == predef1.Bool
    assert run_expr(0, expr1) is False


def test_var1():
    [expr1, expr2] = parse_expr('2 + x')
    assert ast.unparse(expr1) == '2 + x'
    assert ast.unparse(expr2) == 'Int + x'
    assert run_expr(1, expr2, locals_={'x': predef1.Int}) == predef1.Int
    assert run_expr(0, expr1, locals_={'x': 7}) == 9
