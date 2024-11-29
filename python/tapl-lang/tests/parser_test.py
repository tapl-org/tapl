# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass

from tapl_lang import parser, syntax
from tapl_lang import parsertools as pt
from tapl_lang.parser import Cursor
from tapl_lang.syntax import Term, TermInfo


@dataclass
class Number(Term):
    value: int


@dataclass
class BinOp(Term):
    left: Term
    op: str
    right: Term


def parse_number(c: Cursor) -> Term | None:
    start_pos = c.current_position()
    number_str: str = ''
    while not c.is_end() and c.current_char().isdigit():
        number_str += c.current_char()
        c.move_to_next()
    if number_str:
        return Number(TermInfo(start=start_pos, end=c.current_position()), int(number_str))
    return None


def parse_value__expr(c: Cursor) -> Term | None:
    expr, rparen = None, None
    if pt.consume_text(c, '(') and (expr := pt.consume_rule(c, 'expr')) and (rparen := pt.expect_text(c, ')')):
        return expr
    return pt.first_falsy(expr, rparen)


def parse_value__number(c: Cursor) -> Term | None:
    if number := pt.consume_rule(c, 'number'):
        return number
    return pt.first_falsy(number)


def parse_value__error(c: Cursor) -> syntax.Term | None:
    return syntax.ErrorTerm(TermInfo(start=c.current_position()), 'Expected number')


def parse_product__binop(c: Cursor) -> syntax.Term | None:
    start_pos = c.current_position()
    left, right = None, None
    if (left := pt.consume_rule(c, 'product')) and pt.consume_text(c, '*') and (right := pt.expect_rule(c, 'product')):
        info = TermInfo(start=start_pos, end=c.current_position())
        return BinOp(info, left, '*', right)
    return pt.first_falsy(left, right)


def parse_product__value(c: Cursor) -> syntax.Term | None:
    if value := pt.consume_rule(c, 'value'):
        return value
    return pt.first_falsy(value)


def parse_sum__binop(c: Cursor) -> syntax.Term | None:
    start_pos = c.current_position()
    left, right = None, None
    if (left := pt.consume_rule(c, 'sum')) and pt.consume_text(c, '+') and (right := pt.expect_rule(c, 'sum')):
        info = TermInfo(start=start_pos, end=c.current_position())
        return BinOp(info, left, '+', right)
    return pt.first_falsy(left, right)


def parse_sum__product(c: Cursor) -> syntax.Term | None:
    if product := pt.consume_rule(c, 'product'):
        return product
    return pt.first_falsy(product)


def parse_expr(c: Cursor) -> syntax.Term | None:
    if sum_term := pt.consume_rule(c, 'sum'):
        return sum_term
    return pt.first_falsy(sum_term)


def parse_start(c: Cursor) -> syntax.Term | None:
    if expr := pt.expect_rule(c, 'expr'):
        pt.consume_whitespaces(c)
        return expr
    return pt.first_falsy(expr)


# number  <- [0-9]+
# value   <- '(' expr (')'|^E) / number / |^E
# product <- product '*' value / value
# sum     <- sum '+' product / product
# expr    <- sum

RULES: parser.GrammarRuleMap = {
    'number': [parse_number],
    'value': [parse_value__expr, parse_value__number, parse_value__error],
    'product': [parse_product__binop, parse_product__value],
    'sum': [parse_sum__binop, parse_sum__product],
    'expr': [parse_expr],
    'start': [parse_start],
}


def parse(text: str) -> syntax.Term | None:
    return parser.parse_text(text, parser.Grammar(RULES, 'start'), log_cell_memo=True)


def dump(term: Term | None) -> str:
    if isinstance(term, Number):
        return f'N{term.value}'
    if isinstance(term, BinOp):
        left = dump(term.left)
        right = dump(term.right)
        return f'B({left}{term.op}{right})'
    return str(term)


def test_one_digit():
    parsed_term = parse('1')
    assert dump(parsed_term) == 'N1'


def test_multi_digit():
    parsed_term = parse('154')
    assert dump(parsed_term) == 'N154'


def test_multiplication():
    parsed_term = parse('2*3')
    assert dump(parsed_term) == 'B(N2*N3)'


def test_summation():
    parsed_term = parse('2+3')
    assert dump(parsed_term) == 'B(N2+N3)'


def test_expr1():
    parsed_term = parse('2*3+4')
    assert dump(parsed_term) == 'B(B(N2*N3)+N4)'


def test_expr2():
    parsed_term = parse('2+3*4')
    assert dump(parsed_term) == 'B(N2+B(N3*N4))'


def test_expr3():
    parsed_term = parse('(2+3)*4')
    assert dump(parsed_term) == 'B(B(N2+N3)*N4)'


def test_whitespace():
    parsed_term = parse(' ( 2  + 3 ) *   4      ')
    assert dump(parsed_term) == 'B(B(N2+N3)*N4)'


def test_expected_error():
    parsed_term = parse('a')
    assert isinstance(parsed_term, syntax.ErrorTerm)
    assert parsed_term.message == 'Expected number'


def test_expected_rparen_error():
    parsed_term = parse('(1')
    assert isinstance(parsed_term, syntax.ErrorTerm)
    assert parsed_term.message == 'Expected ")"'


def test_multiline():
    parsed_term = parse(' ( 2 \n + 3 ) * \n  4      ')
    assert dump(parsed_term) == 'B(B(N2+N3)*N4)'
