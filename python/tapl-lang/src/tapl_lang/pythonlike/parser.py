# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from tapl_lang import parser, syntax
from tapl_lang.parser import Cursor, first_falsy, route, skip_whitespaces
from tapl_lang.pythonlike import expr as ps
from tapl_lang.pythonlike import stmt
from tapl_lang.syntax import ErrorTerm, Layers, Term, TermWithLocation

# https://docs.python.org/3/reference/grammar.html


# TODO: Create a term for each literal type
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

KEYWORDS = {
    'and',
    'as',
    'assert',
    'async',
    'await',
    'break',
    'class',
    'continue',
    'def',
    'del',
    'elif',
    'else',
    'except',
    'False',
    'finally',
    'for',
    'from',
    'global',
    'if',
    'import',
    'in',
    'is',
    'lambda',
    'None',
    'nonlocal',
    'not',
    'or',
    'pass',
    'raise',
    'return',
    'True',
    'try',
    'while',
    'with',
    'yield',
}


def rule_token(c: Cursor) -> Term | None:
    skip_whitespaces(c)
    tracker = c.start_location_tracker()
    if c.is_end():
        return TokenEndOfText(tracker.location)

    def scan_name(char: str) -> Term:
        result = char
        while not c.is_end() and (char := c.current_char()) and (char.isalnum() or char == '_'):
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
        # two-character punctuation
        if not c.is_end() and (char := c.current_char()) and (temp := punct + char) in PUNCT_SET:
            punct = temp
        # three-character punctuation
        if not c.is_end() and (char := c.current_char()) and (temp := punct + char) in PUNCT_SET:
            punct = temp
        return TokenPunct(tracker.location, value=punct)

    char = c.current_char()
    c.move_to_next()
    if char.isalpha() or char == '_':
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


def scan_arguments(c: Cursor) -> list[Term]:
    if first_arg := c.consume_rule('expression'):
        args = [first_arg]
        k = c.clone()
        while consume_punct(k, ',') and (arg := expect_rule(k, 'expression')):
            c.copy_from(k)
            args.append(arg)
    return []


def rule_primary__call(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if (
        (func := c.consume_rule('primary'))
        and consume_punct(c, '(')
        and (args := scan_arguments(c))
        and consume_punct(c, ')', expected=True)
    ):
        return ps.Call(tracker.location, func, args)
    return None


def build_rule_atom__name(ctx: str) -> Callable[[Cursor], Term | None]:
    def rule(c: Cursor) -> Term | None:
        token = c.consume_rule('token')
        if isinstance(token, TokenName) and token.value not in KEYWORDS:
            return ps.Name(token.location, token.value, ctx)
        return None

    return rule


def rule_atom__bool(c: Cursor) -> Term | None:
    token = c.consume_rule('token')
    if isinstance(token, TokenName):
        location = token.location
        if token.value in ('True', 'False'):
            value = token.value == 'True'
            return Layers([ps.Constant(location, value=value), create_term_predef_type(location, 'Bool_')])
        if token.value == 'None':
            return Layers([ps.Constant(location, value=None), create_term_predef_type(location, 'NoneType_')])
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


# Comparison operators
# --------------------


def scan_operator(c: Cursor):
    if (first := c.consume_rule('token')) and isinstance(first, TokenPunct):
        if first.value in ('==', '!=', '<=', '<', '>=', '>', 'in'):
            return first.value
        if first.value == 'not':
            if consume_punct(c, 'in'):
                return 'not in'
            return None
        if first.value == 'is':
            k = c.clone()
            if consume_punct(k, 'not'):
                c.copy_from(k)
                return 'is not'
            return 'is'
    return None


def rule_comparison(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if left := c.consume_rule('sum'):
        ops = []
        comparators = []
        k = c.clone()
        while (op := scan_operator(k)) and (comparator := k.consume_rule('sum')):
            c.copy_from(k)
            ops.append(op)
            comparators.append(comparator)
        if ops:
            return ps.Compare(tracker.location, left=left, ops=ops, comparators=comparators)
    return None


# EXPRESSIONS
# -----------


def rule_inversion__not(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if consume_name(c, 'not') and (operand := expect_rule(c, 'comparison')):
        return ps.UnaryOp(tracker.location, 'not', operand, mode=syntax.MODE_SAFE)
    return None


def rule_conjunction__and(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    left, right = None, None
    if left := c.consume_rule('inversion'):
        values = [left]
        k = c.clone()
        while consume_name(k, 'and') and (right := k.consume_rule('inversion')):
            c.copy_from(k)
            values.append(right)
        if len(values) > 1:
            return ps.BoolOp(tracker.location, 'and', values, mode=syntax.MODE_SAFE)
    return first_falsy(left, right)


def rule_disjunction__or(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    left, right = None, None
    if left := c.consume_rule('conjunction'):
        values = [left]
        k = c.clone()
        while consume_name(k, 'or') and (right := k.consume_rule('conjunction')):
            c.copy_from(k)
            values.append(right)
        if len(values) > 1:
            return ps.BoolOp(tracker.location, 'or', values, mode=syntax.MODE_SAFE)
    return first_falsy(left, right)


# SIMPLE STATEMENTS
# =================


def rule_assignment(c: Cursor) -> Term | None:
    tracker = c.start_location_tracker()
    if (name := c.consume_rule('name_store')) and consume_punct(c, '=') and (value := expect_rule(c, 'expression')):
        return stmt.Assign(tracker.location, targets=[name], value=value)
    return first_falsy(name, value)


RULES: parser.GrammarRuleMap = {
    'expression': [route('disjunction')],
    'disjunction': [rule_disjunction__or, route('conjunction')],
    'conjunction': [rule_conjunction__and, route('inversion')],
    'inversion': [rule_inversion__not, route('comparison')],
    'comparison': [rule_comparison, route('sum')],
    'sum': [rule_sum__binary, route('term')],
    'term': [rule_term__binary, rule_invalid_factor, route('factor')],
    'factor': [rule_factor__unary, route('primary')],
    'primary': [rule_primary__call, route('atom')],
    'atom': [build_rule_atom__name('load'), rule_atom__bool, rule_atom__string, rule_atom__number],
    'token': [rule_token],
    'statement': [route('assignment')],
    'assignment': [rule_assignment],
    'name_store': [build_rule_atom__name('store')],
}
