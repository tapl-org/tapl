# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass

from tapl_lang import parser
from tapl_lang.parser import Cursor, first_falsy, route, skip_whitespaces
from tapl_lang.pythonlike import syntax as ps
from tapl_lang.syntax import ErrorTerm, Location, Term


@dataclass
class TokenName(Term):
    value: str


@dataclass
class TokenNumber(Term):
    value: int


@dataclass
class TokenPunct(Term):
    value: str


PUNCT_SET = set('()')


def rule_token(c: Cursor) -> Term | None:
    def scan_name(char: str) -> Term:
        result = char
        c.move_to_next()
        while not c.is_end() and (char := c.current_char()).isalnum():
            result += char
            c.move_to_next()
        return TokenName(c.location, value=result)

    def scan_number(char: str) -> Term:
        c.move_to_next()
        number_str = char
        while not c.is_end() and (char := c.current_char()).isdigit():
            number_str += char
            c.move_to_next()
        return TokenNumber(c.location, value=int(number_str))

    skip_whitespaces(c)
    if c.is_end():
        return None
    c.mark_start_position()
    char = c.current_char()
    if char.isalpha():
        return scan_name(char)
    if char.isdigit():
        return scan_number(char)
    if char in PUNCT_SET:
        c.move_to_next()
        return TokenPunct(c.location, value=char)
    # Error
    return None


def consume_name(c: Cursor, name: str, *, expected: bool = False) -> Term | None:
    if expected:
        c.mark_start_position()
    term = c.consume_rule('token')
    if isinstance(term, TokenName) and term.value == name or not term and term is not None:
        return term
    if expected:
        location = term.location if term is not None else c.location
        return ErrorTerm(location, f'Expected "{name}", but found {term}')
    return None


def consume_punct(c: Cursor, punct: str, *, expected: bool = False) -> Term | None:
    if expected:
        c.mark_start_position()
    term = c.consume_rule('token')
    if isinstance(term, TokenPunct) and term.value == punct or not term and term is not None:
        return term
    if expected:
        location = term.location if term is not None else c.location
        return ErrorTerm(location, f'Expected "{punct}", but found {term}')
    return None


def rule_atom__true(c: Cursor) -> Term | None:
    if token := consume_name(c, 'True'):
        return ps.Constant(token.location, value=True)
    return None


def rule_atom__false(c: Cursor) -> Term | None:
    if token := consume_name(c, 'False'):
        return ps.Constant(token.location, value=False)
    return None


def rule_inversion__not(c: Cursor) -> Term | None:
    if consume_name(c, 'not') and (operand := c.expect_rule('atom')):
        return ps.UnaryOp(c.location, ast.Not(), operand)
    return None


def rule_conjuction__and(c: Cursor) -> Term | None:
    left, right = None, None
    values = None
    if (left := c.consume_rule('inversion')) and consume_name(c, 'and') and (right := c.expect_rule('inversion')):
        values = [left, right]
        while consume_name(c, 'and') and (right := c.consume_rule('inversion')):
            values.append(right)
        return ps.BoolOp(Location(start=left.location.start, end=right.location.end), ast.And(), values)
    return first_falsy(left, right)


def rule_disjunction__or(c: Cursor) -> Term | None:
    left, right = None, None
    values = None
    if (left := c.consume_rule('conjunction')) and consume_name(c, 'or') and (right := c.expect_rule('conjunction')):
        values = [left, right]
        while consume_name(c, 'or') and (right := c.consume_rule('conjunction')):
            values.append(right)
        return ps.BoolOp(Location(start=left.location.start, end=right.location.end), ast.Or(), values)
    return first_falsy(left, right)


RULES: parser.GrammarRuleMap = {
    'token': [rule_token],
    'atom': [rule_atom__true, rule_atom__false],
    'inversion': [rule_inversion__not, route('atom')],
    'conjuction': [rule_conjuction__and, route('inversion')],
    'disjunction': [rule_disjunction__or, route('conjuction')],
}
