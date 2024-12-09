# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass

from tapl_lang import parser, syntax
from tapl_lang.parser import Cursor, first_falsy, route, skip_whitespaces
from tapl_lang.syntax import Location, Position, Term


@dataclass
class Punct(Term):
    value: str


@dataclass
class Number(Term):
    value: int


@dataclass
class BinOp(Term):
    left: Term
    op: str
    right: Term


PUNCT_SET = set('()+*')


def parse_token(c: Cursor) -> Term | None:
    skip_whitespaces(c)
    if c.is_end():
        return None
    c.mark_start_position()
    char = c.current_char()
    # Number
    if char.isdigit():
        c.move_to_next()
        number_str = char
        while not c.is_end() and (char := c.current_char()).isdigit():
            number_str += char
            c.move_to_next()
        return Number(c.location, int(number_str))
    # Punctuation
    if char in PUNCT_SET:
        c.move_to_next()
        return Punct(c.location, value=char)
    # Error
    return None


def consume_punct(c: Cursor, punct: str, *, expected: bool = False) -> Term | None:
    if expected:
        c.mark_start_position()
    term = c.consume_rule('token')
    if isinstance(term, Punct) and term.value == punct or not term and term is not None:
        return term
    if expected:
        location = term.location if term is not None else c.location
        return syntax.ErrorTerm(location, f'Expected "{punct}", but found {term}')
    return None


def consume_number(c: Cursor, *, expected: bool = False) -> Term | None:
    term = c.consume_rule('token')
    if isinstance(term, Number) or not term and term is not None:
        return term
    if expected:
        location = term.location if term is not None else c.location
        return syntax.ErrorTerm(location, f'Expected number, but found {term}')
    return None


def expect_rule(c: Cursor, rule: str) -> Term | None:
    c.mark_start_position()
    term = c.consume_rule(rule)
    if term is not None:
        return term
    return syntax.ErrorTerm(c.location, f'Expected rule "{rule}"')


def parse_value__expr(c: Cursor) -> Term | None:
    expr, rparen = None, None
    if consume_punct(c, '(') and (expr := c.consume_rule('expr')) and (rparen := consume_punct(c, ')', expected=True)):
        return expr
    return first_falsy(expr, rparen)


def parse_value__number(c: Cursor) -> Term | None:
    return consume_number(c)


def parse_value__error(c: Cursor) -> syntax.Term | None:
    return syntax.ErrorTerm(Location(start=c.current_position()), 'Expected number')


def parse_product__binop(c: Cursor) -> syntax.Term | None:
    left, right = None, None
    if (left := c.consume_rule('product')) and consume_punct(c, '*') and (right := expect_rule(c, 'product')):
        location = Location(start=left.location.start, end=right.location.end)
        return BinOp(location, left, '*', right)
    return first_falsy(left, right)


def parse_sum__binop(c: Cursor) -> syntax.Term | None:
    left, right = None, None
    if (left := c.consume_rule('sum')) and consume_punct(c, '+') and (right := expect_rule(c, 'sum')):
        location = Location(start=left.location.start, end=right.location.end)
        return BinOp(location, left, '+', right)
    return first_falsy(left, right)


def parse_start(c: Cursor) -> syntax.Term | None:
    if expr := expect_rule(c, 'expr'):
        skip_whitespaces(c)
        return expr
    return first_falsy(expr)


# number  <- [0-9]+
# value   <- '(' expr (')'|^E) / number / |^E
# product <- product '*' value / value
# sum     <- sum '+' product / product
# expr    <- sum

RULES: parser.GrammarRuleMap = {
    'token': [parse_token],
    'value': [parse_value__expr, parse_value__number, parse_value__error],
    'product': [parse_product__binop, route('value')],
    'sum': [parse_sum__binop, route('product')],
    'expr': [route('sum')],
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
        start=Position(line=1, column=1), end=Position(line=1, column=4), filename=None
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
    assert parsed_term.message == 'Expected ")", but found None'


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
    assert parsed_term.message == 'Not all text consumed 1:2/1:2.'
