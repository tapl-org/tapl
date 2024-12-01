# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass

from tapl_lang import parser, syntax
from tapl_lang import parsertools as pt
from tapl_lang.parser import Cursor, LocationTracker
from tapl_lang.syntax import Location, Position, Term


@dataclass
class Number(Term):
    value: int


@dataclass
class BinOp(Term):
    left: Term
    op: str
    right: Term


def parse_number(c: Cursor) -> Term | None:
    tracker = LocationTracker(c)
    number_str: str = ''
    while not c.is_end() and c.current_char().isdigit():
        number_str += c.current_char()
        c.move_to_next()
    if number_str:
        return Number(tracker.location, int(number_str))
    return None


def parse_value__expr(c: Cursor) -> Term | None:
    expr, rparen = None, None
    if pt.consume_text(c, '(') and (expr := pt.consume_rule(c, 'expr')) and (rparen := pt.expect_text(c, ')')):
        return expr
    return pt.first_falsy(expr, rparen)


def parse_value__error(c: Cursor) -> syntax.Term | None:
    return syntax.ErrorTerm(Location(start=c.current_position()), 'Expected number')


def parse_product__binop(c: Cursor) -> syntax.Term | None:
    tracker = LocationTracker(c)
    left, right = None, None
    if (left := pt.consume_rule(c, 'product')) and pt.consume_text(c, '*') and (right := pt.expect_rule(c, 'product')):
        return BinOp(tracker.location, left, '*', right)
    return pt.first_falsy(left, right)


def parse_sum__binop(c: Cursor) -> syntax.Term | None:
    tracker = LocationTracker(c)
    left, right = None, None
    if (left := pt.consume_rule(c, 'sum')) and pt.consume_text(c, '+') and (right := pt.expect_rule(c, 'sum')):
        return BinOp(tracker.location, left, '+', right)
    return pt.first_falsy(left, right)


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
    'value': [parse_value__expr, pt.route('number'), parse_value__error],
    'product': [parse_product__binop, pt.route('value')],
    'sum': [parse_sum__binop, pt.route('product')],
    'expr': [pt.route('sum')],
    'start': [parse_start],
}


def parse(text: str) -> syntax.Term | None:
    return parser.parse_text(text, parser.Grammar(RULES, 'start'), log_cell_memo=False)


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


def test_expr3_and_location():
    parsed_term = parse('(2+3)*4')
    assert parsed_term.left.location == Location(
        start=Position(line=1, column=2), end=Position(line=1, column=5), filename=None
    )
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


def test_empty_text():
    parsed_term = parse('')
    assert isinstance(parsed_term, syntax.ErrorTerm)
    assert parsed_term.message == 'Empty text.'


def test_not_all_text_consumed():
    parsed_term = parse('1(')
    assert isinstance(parsed_term, syntax.ErrorTerm)
    assert parsed_term.message == 'Not all text consumed 1:2/2:1.'
