# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Optional
from tapl_lang import peg, syntax
from tapl_lang.peg import Cursor, Output

# number  <- [0-9]+
# value   <- '(' expr ')'|^E / number|^E
# product <- product '*' value / value
# sum     <- sum '+' product / product
# expr    <- sum


class Number(syntax.Term):
    def __init__(self, location: syntax.Location, value: int) -> None:
        super().__init__(location)
        self.value = value
    
    def __repr__(self) -> str:
        return f'N{self.value}'


class BinOp(syntax.Term):
    def __init__(self, location: syntax.Location, left: syntax.Term, op: str, right: syntax.Term) -> None:
        super().__init__(location)
        self.left = left
        self.op = op
        self.right = right
    
    def __repr__(self) -> str:
        return f'B({self.left}{self.op}{self.right})'


def parse_number(c: Cursor) -> Optional[syntax.Term]:
    c.skip_whitespaces()
    text = c.engine.text
    p = c.pos
    number_str: str = ''
    while p < len(text) and text[p].isdigit():
        number_str += text[p]
        p += 1
    if number_str:
        c.pos = p
        return Number(c.get_location(), int(number_str))
    return None


def parse_value(c: Cursor) -> Optional[syntax.Term]:
    output = Output()
    if c.consume_text('(') and c.consume_rule('expr', output) and c.expect_text(')'):
        return output.value
    elif c.error:
        print(c.error)
        return c.error
    c.reset()
    if c.consume_rule('number', output):
        return output.value
    elif c.error:
        return c.error
    return c.create_syntax_error('Expected number')


def parse_product(c: Cursor) -> Optional[syntax.Term]:
    left, right = Output(), Output()
    if c.consume_rule('product', left) and c.consume_text('*') and c.expect_rule('product', right):
        return BinOp(c.get_location(), left.assert_value(), '*', right.assert_value())
    elif c.error:
        return c.error
    c.reset()
    if c.consume_rule('value', left):
        return left.value
    elif c.error:
        return c.error
    return None


def parse_sum(c: Cursor) -> Optional[syntax.Term]:
    left, right = Output(), Output()
    if c.consume_rule('sum', left) and c.consume_text('+') and c.expect_rule('sum', right):
        return BinOp(c.get_location(), left.assert_value(), '+', right.assert_value())
    elif c.error:
        return c.error
    c.reset()
    if c.consume_rule('product', left):
        return left.value
    elif c.error:
        return c.error
    return None


def parse_expr(c: Cursor) -> Optional[syntax.Term]:
    output = Output()
    if c.consume_rule('sum', output):
        return output.value
    elif c.error:
        return c.error
    return None


def parse_start(c: Cursor) -> Optional[syntax.Term]:
    output = Output()
    if c.expect_rule('expr', output) and c.skip_whitespaces():
        return output.value
    elif c.error:
        return c.error
    return None


RULES: peg.RuleMaps = {
    'number': parse_number,
    'value': parse_value,
    'product': parse_product,
    'sum': parse_sum,
    'expr': parse_expr,
    'start': parse_start,
}

def parse(text: str) -> syntax.Term:
    parsed_term = peg.parse(text, RULES, 'start')
    assert parsed_term is not None
    if isinstance(parsed_term, syntax.SyntaxError):
        raise RuntimeError(parsed_term.error_text)
    else:
        return parsed_term

def test_one_digit():
    parsed_term = parse("1")
    assert str(parsed_term) == 'N1'

def test_multi_digit():
    parsed_term = parse("154")
    assert str(parsed_term) == 'N154'

def test_multiplication():
    parsed_term = parse("2*3")
    assert str(parsed_term) == 'B(N2*N3)'

def test_summation():
    parsed_term = parse("2+3")
    assert str(parsed_term) == 'B(N2+N3)'

def test_expr1():
    parsed_term = parse("2*3+4")
    assert str(parsed_term) == 'B(B(N2*N3)+N4)'

def test_expr2():
    parsed_term = parse("2+3*4")
    assert str(parsed_term) == 'B(N2+B(N3*N4))'

def test_expr3():
    parsed_term = parse("(2+3)*4")
    assert str(parsed_term) == 'B(B(N2+N3)*N4)'

def test_whitespace():
    parsed_term = parse(" ( 2  + 3 ) *   4      ")
    assert str(parsed_term) == 'B(B(N2+N3)*N4)'

def test_expected_error():
    parsed_term = peg.parse("a", RULES, 'start')
    assert isinstance(parsed_term, syntax.SyntaxError)
    assert parsed_term.error_text == 'Expected number'

def test_expected_rparen_error():
    parsed_term = peg.parse("(1", RULES, 'start')
    assert isinstance(parsed_term, syntax.SyntaxError)
    assert parsed_term.error_text == 'Expected ")"'

