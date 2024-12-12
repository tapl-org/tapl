# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast
from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike import codegen, parser, syntax
from tapl_lang.syntax import Term


def parse(text: str) -> Term | None:
    return parse_text(text, Grammar(parser.RULES, 'disjunction'), log_cell_memo=False)


def run(term: Term):
    expr_ast = ast.Expression(body=term.codegen())
    compiled_code = compile(expr_ast, filename='', mode='eval')
    return eval(compiled_code)


def test_constant_true():
    term = parse('True')
    assert isinstance(term, syntax.Constant)
    assert term.value is True


def test_inversion():
    term = parse('not True')
    assert isinstance(term, syntax.UnaryOp)
    assert run(term) is False


def test_conjuction1():
    term = parse('True and True')
    assert isinstance(term, syntax.BoolOp)
    assert run(term) is True


def test_conjuction2():
    term = parse('True and True     and    False')
    assert isinstance(term, syntax.BoolOp)
    assert run(term) is False


def test_disjunction():
    term = parse('True and True     and    False  or True')
    assert isinstance(term, syntax.BoolOp)
    assert run(term) is True
