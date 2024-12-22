# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast
from typing import cast

from tapl_lang import typelib as t
from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike import parser
from tapl_lang.syntax import Layers


def parse_expr(text: str) -> list[ast.expr]:
    parsed = parse_text(text, Grammar(parser.RULES, 'disjunction'), log_cell_memo=False)
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    separated = parsed.separate()
    layers = cast(Layers, separated).layers
    return [layer.codegen_expr() for layer in layers]


def run_expr(expr: ast.expr):
    compiled_code = compile(ast.Expression(body=expr), filename='', mode='eval')
    return eval(compiled_code)


def test_constant_true():
    [expr1, expr2] = parse_expr('True')
    assert ast.unparse(expr1) == 'True'
    assert ast.unparse(expr2) == 't.Bool'
    assert run_expr(expr2) == t.Bool
    assert run_expr(expr1) is True


def test_inversion():
    [expr1, expr2] = parse_expr('not True')
    assert ast.unparse(expr1) == 'not True'
    assert ast.unparse(expr2) == 't.Bool'
    assert run_expr(expr2) == t.Bool
    assert run_expr(expr1) is False


def test_conjuction1():
    [expr1, expr2] = parse_expr('True and True')
    assert ast.unparse(expr1) == 'True and True'
    assert ast.unparse(expr2) == 't.create_union(t.Bool, t.Bool)'
    assert run_expr(expr2) == t.Bool
    assert run_expr(expr1) is True


def test_conjuction2():
    [expr1, expr2] = parse_expr('True and True     and    False')
    assert ast.unparse(expr1) == 'True and True and False'
    assert ast.unparse(expr2) == 't.create_union(t.Bool, t.Bool, t.Bool)'
    assert run_expr(expr2) == t.Bool
    assert run_expr(expr1) is False


def test_disjunction():
    [expr1, expr2] = parse_expr('True and True     and    False  or True')
    assert ast.unparse(expr1) == 'True and True and False or True'
    assert ast.unparse(expr2) == 't.create_union(t.create_union(t.Bool, t.Bool, t.Bool), t.Bool)'
    assert run_expr(expr2) == t.Bool
    assert run_expr(expr1) is True
