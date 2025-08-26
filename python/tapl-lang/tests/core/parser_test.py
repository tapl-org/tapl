# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass

from tapl_lang.core import parser, syntax
from tapl_lang.core.parser import Cursor, route
from tapl_lang.core.syntax import Location, Position, Term


@dataclass
class Punct(Term):
    location: Location
    value: str


@dataclass
class Number(Term):
    location: Location
    value: int


@dataclass
class BinOp(Term):
    location: Location
    left: Term
    op: str
    right: Term


class EndOfText(Term):
    def __str__(self) -> str:
        return 'EndOfText'


PUNCT_SET = set('()+*')


def skip_whitespaces(c: Cursor) -> None:
    while not c.is_end() and c.current_char().isspace():
        c.move_to_next()


def parse_token(c: Cursor) -> Term:
    skip_whitespaces(c)
    t = c.start_tracker()
    if c.is_end():
        return EndOfText()
    char = c.current_char()
    # Number
    if char.isdigit():
        c.move_to_next()
        number_str = char
        while not c.is_end() and (char := c.current_char()).isdigit():
            number_str += char
            c.move_to_next()
        return Number(t.location, int(number_str))
    # Punctuation
    if char in PUNCT_SET:
        c.move_to_next()
        return Punct(t.location, value=char)
    return t.fail()


def consume_punct(c: Cursor, *puncts: str) -> Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, Punct) and term.value in puncts:
        return term
    return t.fail()


def expect_punct(c: Cursor, *puncts: str) -> Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, Punct) and term.value in puncts:
        return term
    puncts_text = ', '.join(f'"{p}"' for p in puncts)
    return t.captured_error or syntax.ErrorTerm(
        message=f'Expected {puncts_text}, but found {term}', location=t.location
    )


def consume_number(c: Cursor) -> Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, Number):
        return term
    return t.fail()


def expect_number(c: Cursor) -> Term:
    t = c.start_tracker()
    if t.validate(term := consume_number(c)):
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected number, but found {term}', location=t.location)


def expect_rule(c: Cursor, rule: str) -> Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rule)):
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected rule "{rule}"', location=t.location)


def parse_value__expr(c: Cursor) -> Term:
    t = c.start_tracker()
    if (
        t.validate(consume_punct(c, '('))
        and t.validate(expr := expect_rule(c, 'expr'))
        and t.validate(expect_punct(c, ')'))
    ):
        return expr
    return t.fail()


def parse_value__number(c: Cursor) -> Term:
    return consume_number(c)


def parse_value__error(c: Cursor) -> syntax.Term:
    return syntax.ErrorTerm(message='Expected number', location=Location(start=c.current_position()))


def parse_product__binop(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(left := c.consume_rule('product'))
        and t.validate(consume_punct(c, '*'))
        and t.validate(right := expect_rule(c, 'product'))
    ):
        return BinOp(t.location, left, '*', right)
    return t.fail()


def parse_sum__binop(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(left := c.consume_rule('sum'))
        and t.validate(consume_punct(c, '+'))
        and t.validate(right := expect_rule(c, 'sum'))
    ):
        return BinOp(t.location, left, '+', right)
    return t.fail()


def parse_start(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(expr := expect_rule(c, 'expr')):
        skip_whitespaces(c)
        return expr
    return t.fail()


def parse_none(c: Cursor):
    del c


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
    'none': [parse_none],
}


def parse(text: str, *, debug: bool = False) -> syntax.Term:
    return parser.parse_text(text, parser.Grammar(RULES, 'start'), debug=debug)


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
    assert dump(parsed_term) == 'B(B(N2+N3)*N4)'
    assert parsed_term.left.location == Location(start=Position(line=1, column=1), end=Position(line=1, column=4))


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
    assert parsed_term.message == 'Expected ")", but found EndOfText'


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
    assert parsed_term.message == 'chunk[line:1] Not all text consumed: indices 0:1/1:0.'


def test_rule_function_returns_none():
    parsed_term = parser.parse_text('1', parser.Grammar(RULES, 'none'))
    assert isinstance(parsed_term, syntax.ErrorTerm)
    assert parsed_term.message == 'PegEngine: rule=none:0 returned None.'


def test_error_syntax():
    parsed_term = parse('2 + (3')
    assert isinstance(parsed_term, syntax.ErrorTerm)
    assert parsed_term.message == 'Expected ")", but found EndOfText'
