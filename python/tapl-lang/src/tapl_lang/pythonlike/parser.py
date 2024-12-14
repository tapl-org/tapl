# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import cast

from tapl_lang import parser, syntax
from tapl_lang.parser import Cursor, first_falsy, route, skip_whitespaces
from tapl_lang.pythonlike import syntax as ps
from tapl_lang.syntax import ErrorTerm, Layers, Term, TermWithLocation


def create_predef_type(location: syntax.Location, name: str) -> Term:
    return ps.Attribute(location, value=ps.Name(location, id='typelib', ctx=ast.Load()), attr=name, ctx=ast.Load())


@dataclass
class TokenName(TermWithLocation):
    value: str


@dataclass
class TokenNumber(TermWithLocation):
    value: int


@dataclass
class TokenPunct(TermWithLocation):
    value: str


PUNCT_SET = set('()')


def rule_token(c: Cursor) -> Term | None:
    skip_whitespaces(c)
    if c.is_end():
        return None
    tracker = c.start_location_tracker()

    def scan_name(char: str) -> Term:
        result = char
        c.move_to_next()
        while not c.is_end() and (char := c.current_char()).isalnum():
            result += char
            c.move_to_next()
        return TokenName(tracker.location, value=result)

    def scan_number(char: str) -> Term:
        c.move_to_next()
        number_str = char
        while not c.is_end() and (char := c.current_char()).isdigit():
            number_str += char
            c.move_to_next()
        return TokenNumber(tracker.location, value=int(number_str))

    char = c.current_char()
    if char.isalpha():
        return scan_name(char)
    if char.isdigit():
        return scan_number(char)
    if char in PUNCT_SET:
        c.move_to_next()
        return TokenPunct(tracker.location, value=char)
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


def rule_atom__true(c: Cursor) -> Term | None:
    if token := consume_name(c, 'True'):
        location = cast(TokenName, token).location
        return Layers([ps.Constant(location, value=True), create_predef_type(location, 'Bool')])
    return None


def rule_atom__false(c: Cursor) -> Term | None:
    if token := consume_name(c, 'False'):
        location = cast(TokenName, token).location
        return Layers([ps.Constant(location, value=False), create_predef_type(location, 'Bool')])
    return None


def rule_inversion__not(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if consume_name(c, 'not') and (operand := expect_rule(c, 'atom')):
        return ps.UnaryOp(tracker.location, ast.Not(), operand, mode=syntax.MODE_SAFE)
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
        return ps.BoolOp(tracker.location, ast.And(), values, mode=syntax.MODE_SAFE)
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
        return ps.BoolOp(tracker.location, ast.Or(), values, mode=syntax.MODE_SAFE)
    return first_falsy(left, right)


RULES: parser.GrammarRuleMap = {
    'token': [rule_token],
    'atom': [rule_atom__true, rule_atom__false],
    'inversion': [rule_inversion__not, route('atom')],
    'conjunction': [rule_conjunction__and, route('inversion')],
    'disjunction': [rule_disjunction__or, route('conjunction')],
}
