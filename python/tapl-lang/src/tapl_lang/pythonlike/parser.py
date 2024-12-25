# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass
from typing import cast

from tapl_lang import parser, syntax
from tapl_lang.parser import Cursor, first_falsy, route, skip_whitespaces
from tapl_lang.pythonlike import expr as ps
from tapl_lang.syntax import ErrorTerm, Layers, Term, TermWithLocation


def create_term_predef_type(location: syntax.Location, name: str) -> Term:
    return ps.Attribute(location, value=ps.Name(location, id='t', ctx='load'), attr=name, ctx='load')


@dataclass(frozen=True)
class TokenName(TermWithLocation):
    value: str


@dataclass(frozen=True)
class TokenString(TermWithLocation):
    value: str


@dataclass(frozen=True)
class TokenNumber(TermWithLocation):
    value: int


@dataclass(frozen=True)
class TokenPunct(TermWithLocation):
    value: str


@dataclass(frozen=True)
class TokenEndOfText(TermWithLocation):
    pass


# https://github.com/python/cpython/blob/main/Parser/token.c
PUNCT_SET = {
    '!',
    '%',
    '&',
    '(',
    ')',
    '*',
    '+',
    ',',
    '-',
    '.',
    '/',
    ':',
    ';',
    '<',
    '=',
    '>',
    '@',
    '[',
    ']',
    '^',
    '{',
    '|',
    '}',
    '~',
    '!=',
    '%=',
    '&=',
    '**',
    '*=',
    '+=',
    '-=',
    '->',
    '//',
    '/=',
    ':=',
    '<<',
    '<=',
    '<>',
    '==',
    '>=',
    '>>',
    '@=',
    '^=',
    '|=',
    '**=',
    '...',
    '//=',
    '<<=',
    '>>=',
}


def rule_token(c: Cursor) -> Term | None:
    skip_whitespaces(c)
    tracker = c.start_location_tracker()
    if c.is_end():
        return TokenEndOfText(tracker.location)

    def scan_name(char: str) -> Term:
        result = char
        while not c.is_end() and (char := c.current_char()).isalnum():
            result += char
            c.move_to_next()
        return TokenName(tracker.location, value=result)

    def unterminated_string() -> Term:
        return ErrorTerm(
            tracker.location,
            f'unterminated string literal (detected at line {tracker.location.end.line}); perhaps you escaped the end quote?',
        )

    def scan_string() -> Term:
        result = ''
        if c.is_end():
            return unterminated_string()
        while (char := c.current_char()) != "'":
            result += char
            c.move_to_next()
            if c.is_end():
                return unterminated_string()
        c.move_to_next()  # consume quote
        return TokenString(tracker.location, result)

    def scan_number(char: str) -> Term:
        number_str = char
        while not c.is_end() and (char := c.current_char()).isdigit():
            number_str += char
            c.move_to_next()
        return TokenNumber(tracker.location, value=int(number_str))

    def scan_punct(char: str) -> Term:
        punct = char
        if not c.is_end() and (char := c.current_char()) and (temp := punct + char) in PUNCT_SET:
            punct = temp
        if not c.is_end() and (char := c.current_char()) and (temp := punct + char) in PUNCT_SET:
            punct = temp
        return TokenPunct(tracker.location, value=punct)

    char = c.current_char()
    c.move_to_next()
    if char.isalpha():
        return scan_name(char)
    if char == "'":
        return scan_string()
    if char.isdigit():
        return scan_number(char)
    if char in PUNCT_SET:
        return scan_punct(char)
    # Error
    return None


def is_error_term(term: Term | None) -> bool:
    return term is not None and not term


def consume_name(c: Cursor, name: str, *, expected: bool = False) -> Term | None:
    tracker = c.start_location_tracker()
    term = c.consume_rule('token')
    if isinstance(term, TokenName) and term.value == name or is_error_term(term):
        return term
    if expected:
        return ErrorTerm(tracker.location, f'Expected "{name}", but found {term}')
    return None


def consume_punct(c: Cursor, punct: str, *, expected: bool = False) -> Term | None:
    tracker = c.start_location_tracker()
    term = c.consume_rule('token')
    if isinstance(term, TokenPunct) and term.value == punct or is_error_term(term):
        return term
    if expected:
        return ErrorTerm(tracker.location, f'Expected "{punct}", but found {term}')
    return None


def expect_rule(c: Cursor, rule: str) -> Term | None:
    tracker = c.start_location_tracker()
    term = c.consume_rule(rule)
    if term is not None:
        return term
    return ErrorTerm(tracker.location, f'Expected rule "{rule}"')


# Primary elements
# ----------------


# TODO: merge rule_atom__true and rule_atom__false to rule_atom__bool
def rule_atom__true(c: Cursor) -> Term | None:
    if token := consume_name(c, 'True'):
        location = cast(TokenName, token).location
        return Layers([ps.Constant(location, value=True), create_term_predef_type(location, 'Bool_')])
    return None


def rule_atom__false(c: Cursor) -> Term | None:
    if token := consume_name(c, 'False'):
        location = cast(TokenName, token).location
        return Layers([ps.Constant(location, value=False), create_term_predef_type(location, 'Bool_')])
    return None


def rule_atom__string(c: Cursor) -> Term | None:
    token = c.consume_rule('token')
    if isinstance(token, TokenString):
        location = cast(TokenString, token).location
        return Layers([ps.Constant(location, value=token.value), create_term_predef_type(location, 'Str_')])
    return None


def rule_atom__number(c: Cursor) -> Term | None:
    token = c.consume_rule('token')
    if isinstance(token, TokenNumber):
        location = cast(TokenNumber, token).location
        return Layers([ps.Constant(location, value=token.value), create_term_predef_type(location, 'Int_')])
    return None


# Arithmetic operators
# --------------------


def rule_factor__unary(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if (
        (op := c.consume_rule('token'))
        and isinstance(op, TokenPunct)
        and op.value in ['+', '-', '~']
        and (factor := expect_rule(c, 'factor'))
    ):
        return ps.UnaryOp(tracker.location, op.value, factor, mode=syntax.MODE_SAFE)
    return None


def rule_term__binary(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if (
        (left := c.consume_rule('term'))
        and (op := c.consume_rule('token'))
        and isinstance(op, TokenPunct)
        and op.value in ['*', '/', '//', '%']
        and (right := expect_rule(c, 'factor'))
    ):
        return ps.BinOp(tracker.location, left, op.value, right)
    return None


def rule_sum__binary(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if (
        (left := c.consume_rule('sum'))
        and (op := c.consume_rule('token'))
        and isinstance(op, TokenPunct)
        and op.value in ['+', '-']
        and (right := expect_rule(c, 'term'))
    ):
        return ps.BinOp(tracker.location, left, op.value, right)
    return None


# EXPRESSIONS
# -----------


def rule_inversion__not(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if consume_name(c, 'not') and (operand := expect_rule(c, 'atom')):
        return ps.UnaryOp(tracker.location, 'not', operand, mode=syntax.MODE_SAFE)
    return None


def rule_conjunction__and(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    left, right = None, None
    values = None
    if (left := c.consume_rule('inversion')) and consume_name(c, 'and') and (right := expect_rule(c, 'inversion')):
        values = [left, right]
        k = c.clone()
        while consume_name(k, 'and') and (right := k.consume_rule('inversion')):
            values.append(right)
            c.copy_from(k)
        return ps.BoolOp(tracker.location, 'and', values, mode=syntax.MODE_SAFE)
    return first_falsy(left, right)


def rule_disjunction__or(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    left, right = None, None
    values = None
    if (left := c.consume_rule('conjunction')) and consume_name(c, 'or') and (right := expect_rule(c, 'conjunction')):
        values = [left, right]
        k = c.clone()
        while consume_name(k, 'or') and (right := k.consume_rule('conjunction')):
            values.append(right)
            c.copy_from(k)
        return ps.BoolOp(tracker.location, 'or', values, mode=syntax.MODE_SAFE)
    return first_falsy(left, right)


# ========================= START OF INVALID RULES =======================


def rule_invalid_factor(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    token = c.consume_rule('token')
    if (
        isinstance(token, TokenPunct)
        and token.value in ('+', '-', '~')
        and consume_punct(c, 'not')
        and c.consume_rule('factor')
    ):
        return ErrorTerm(tracker.location, "'not' after an operator must be parenthesized")
    return None


RULES: parser.GrammarRuleMap = {
    'disjunction': [rule_disjunction__or, route('conjunction')],
    'conjunction': [rule_conjunction__and, route('inversion')],
    'inversion': [rule_inversion__not, route('sum')],
    'sum': [rule_sum__binary, route('term')],
    'term': [rule_term__binary, rule_invalid_factor, route('factor')],
    'factor': [rule_factor__unary, route('atom')],
    'atom': [rule_atom__true, rule_atom__false, rule_atom__string, rule_atom__number],
    'token': [rule_token],
}
