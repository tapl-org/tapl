# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast
import re

import pytest

from tapl_lang.core import syntax
from tapl_lang.core.parser import Grammar, parse_text
from tapl_lang.lib import compiler, python_backend, scope, terms, typelib
from tapl_lang.pythonlike import grammar, predef, predef1, rule_names


def check_parsed_term(parsed: syntax.Term) -> None:
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    error_bucket: list[syntax.ErrorTerm] = compiler.gather_errors(parsed)
    if error_bucket:
        messages = [e.message for e in error_bucket]
        raise SyntaxError('\n\n'.join(messages))


def parse_expr(text: str, *, debug=False) -> list[ast.expr]:
    parsed = parse_text(text, Grammar(grammar.get_grammar().rule_map, rule_names.EXPRESSION), debug=debug)
    check_parsed_term(parsed)
    safe_term = compiler.make_safe_term(parsed)
    separated = syntax.LayerSeparator(2).build(lambda layer: layer(safe_term))
    return [
        python_backend.AstGenerator().generate_expr(layer, syntax.BackendSetting(scope_level=0)) for layer in separated
    ]


def evaluate(expr: ast.expr, locals_=None):
    compiled_code = compile(ast.Expression(body=expr), filename='', mode='eval')
    return eval(compiled_code, predef.__dict__, locals=locals_ or {})


def typecheck(expr: ast.expr, locals_=None):
    compiled_code = compile(ast.Expression(body=expr), filename='', mode='eval')
    scope0 = scope.Scope(parent=predef1.predef_scope)
    scope0.store_many__sa(locals_ or {})
    globals_ = {'s0': scope0}
    return eval(compiled_code, globals=globals_)


def expect_type_error(expr: ast.expr) -> str:
    try:
        typecheck(expr)
    except TypeError as e:
        return repr(e)
    else:
        return 'NO ERROR'


def test_constant_true():
    [expr1, expr2] = parse_expr('True')
    assert ast.unparse(expr1) == 'True'
    assert ast.unparse(expr2) == 's0.Bool'
    assert typecheck(expr2) is predef1.predef_scope.Bool
    assert evaluate(expr1) is True


def test_constant_number7():
    [expr1, expr2] = parse_expr('7')
    assert ast.unparse(expr1) == '7'
    assert ast.unparse(expr2) == 's0.Int'
    assert typecheck(expr2) is predef1.predef_scope.Int
    assert evaluate(expr1) == 7


def test_inversion_bool():
    [expr1, expr2] = parse_expr('not True')
    assert ast.unparse(expr1) == 'not True'
    assert ast.unparse(expr2) == 's0.Bool'
    assert typecheck(expr2) is predef1.predef_scope.Bool
    assert evaluate(expr1) is False


def test_inversion_number():
    [expr1, expr2] = parse_expr('not 0')
    assert ast.unparse(expr1) == 'not 0'
    assert ast.unparse(expr2) == 's0.Bool'
    assert typecheck(expr2) is predef1.predef_scope.Bool
    assert evaluate(expr1) is True


def test_negation_int():
    [expr1, expr2] = parse_expr('-7')
    assert ast.unparse(expr1) == '-7'
    assert ast.unparse(expr2) == '-s0.Int'
    assert typecheck(expr2) is predef1.predef_scope.Int
    assert evaluate(expr1) == -7


def test_negation_float():
    [expr1, expr2] = parse_expr('-7.3')
    assert ast.unparse(expr1) == '-7.3'
    assert ast.unparse(expr2) == '-s0.Float'
    assert typecheck(expr2) is predef1.predef_scope.Float
    assert evaluate(expr1) == -7.3


def test_conjuction_bool1():
    [expr1, expr2] = parse_expr('True and True')
    assert ast.unparse(expr1) == 'True and True'
    assert ast.unparse(expr2) == 's0.tapl_typing.create_union(s0.Bool, s0.Bool)'
    assert typecheck(expr2) is predef1.predef_scope.Bool
    assert evaluate(expr1) is True


def test_conjuction_bool2():
    [expr1, expr2] = parse_expr('True and True     and    False')
    assert ast.unparse(expr1) == 'True and True and False'
    assert ast.unparse(expr2) == 's0.tapl_typing.create_union(s0.Bool, s0.Bool, s0.Bool)'
    assert typecheck(expr2) is predef1.predef_scope.Bool
    assert evaluate(expr1) is False


def test_conjuction_number1():
    [expr1, expr2] = parse_expr('3 and 4')
    assert ast.unparse(expr1) == '3 and 4'
    assert ast.unparse(expr2) == 's0.tapl_typing.create_union(s0.Int, s0.Int)'
    assert typecheck(expr2) is predef1.predef_scope.Int
    assert evaluate(expr1) == 4


def test_conjuction_number2():
    [expr1, expr2] = parse_expr('0 and 4')
    assert ast.unparse(expr1) == '0 and 4'
    assert ast.unparse(expr2) == 's0.tapl_typing.create_union(s0.Int, s0.Int)'
    assert typecheck(expr2) is predef1.predef_scope.Int
    assert evaluate(expr1) == 0


def test_conjuction_mix():
    [expr1, expr2] = parse_expr('True and 4')
    assert ast.unparse(expr1) == 'True and 4'
    assert ast.unparse(expr2) == 's0.tapl_typing.create_union(s0.Bool, s0.Int)'
    assert typelib.check_type_equality(
        typecheck(expr2),
        predef1.predef_scope.tapl_typing.create_union(predef1.predef_scope.Int, predef1.predef_scope.Bool),
    )
    assert evaluate(expr1) == 4


def test_disjunction():
    [expr1, expr2] = parse_expr('True and True     and    False  or True')
    assert ast.unparse(expr1) == 'True and True and False or True'
    assert (
        ast.unparse(expr2)
        == 's0.tapl_typing.create_union(s0.tapl_typing.create_union(s0.Bool, s0.Bool, s0.Bool), s0.Bool)'
    )
    assert typelib.check_type_equality(typecheck(expr2), predef1.predef_scope.Bool)
    assert evaluate(expr1) is True


def test_term1():
    [expr1, expr2] = parse_expr('2 + 3')
    assert ast.unparse(expr1) == '2 + 3'
    assert ast.unparse(expr2) == 's0.Int + s0.Int'
    assert typelib.check_type_equality(typecheck(expr2), predef1.predef_scope.Int)
    assert evaluate(expr1) == 5


def test_term2():
    [expr1, expr2] = parse_expr('2 + True')
    assert ast.unparse(expr1) == '2 + True'
    assert ast.unparse(expr2) == 's0.Int + s0.Bool'
    with pytest.raises(TypeError, match=r'unsupported operand type\(s\) for \+: Int and Bool'):
        typecheck(expr2)


def test_term_error():
    [expr1, expr2] = parse_expr("2 + 'abc'")
    assert ast.unparse(expr1) == "2 + 'abc'"
    assert ast.unparse(expr2) == 's0.Int + s0.Str'
    assert (
        expect_type_error(expr2)
        == "TypeError('unsupported operand type(s) for +: Int and Str. Not equal: posonlyargs=[Int] arguments=[Str]')"
    )


def test_compare1():
    [expr1, expr2] = parse_expr('2 < 3')
    assert ast.unparse(expr1) == '2 < 3'
    assert ast.unparse(expr2) == 's0.Int < s0.Int'
    assert typelib.check_type_equality(typecheck(expr2), predef1.predef_scope.Bool)
    assert evaluate(expr1) is True


def test_compare2():
    [expr1, expr2] = parse_expr('True < 0')
    assert ast.unparse(expr1) == 'True < 0'
    assert ast.unparse(expr2) == 's0.Bool < s0.Int'
    with pytest.raises(
        TypeError,
        match=re.escape(
            'unsupported operand type(s) for <: Bool and Int. Not equal: posonlyargs=[Bool] arguments=[Int]'
        ),
    ):
        typecheck(expr2)


def test_var1():
    [expr1, expr2] = parse_expr('2 + x')
    assert ast.unparse(expr1) == '2 + x'
    assert ast.unparse(expr2) == 's0.Int + s0.x'
    assert typecheck(expr2, locals_={'x': predef1.predef_scope.Int}) == predef1.predef_scope.Int
    assert evaluate(expr1, locals_={'x': 7}) == 9


def test_term_repr():
    parsed = parse_text('2+x', Grammar(grammar.get_grammar().rule_map, rule_names.EXPRESSION))
    assert (
        str(parsed)
        == "BinOp(left=IntegerLiteral(value=2, mode=Layers(layers=[MODE_EVALUATE, MODE_TYPECHECK]), location=(1:0,1:1)), op='+', right=TypedName(id='x', ctx='load', mode=Layers(layers=[MODE_EVALUATE, MODE_TYPECHECK]), location=(1:2,1:3)), location=(1:0,1:3))"
    )


# XXX: Currently disabled test cases for double-layer parsing of function calls.
def skip_test_multi_layer_call():
    [expr1, expr2] = parse_expr('f(<3:Str>)')
    assert ast.unparse(expr1) == 'f(3)'
    assert ast.unparse(expr2) == 's0.f(s0.Str)'


def test_gather_errors():
    location = syntax.Location(start=syntax.Position(line=1, column=0))
    a = terms.IntegerLiteral(value=2, mode=terms.MODE_SAFE, location=location)
    b = terms.IntegerLiteral(value=3, mode=terms.MODE_SAFE, location=location)
    c = syntax.ErrorTerm('Expected number')
    d = terms.BinOp(b, '*', c, location=location)
    e = terms.BinOp(a, '+', d, location=location)
    error_bucket = compiler.gather_errors(e)
    assert len(error_bucket) == 1
    assert isinstance(error_bucket[0], syntax.ErrorTerm)
    assert error_bucket[0].message == 'Expected number'
