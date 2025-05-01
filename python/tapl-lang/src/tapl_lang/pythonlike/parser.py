# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from tapl_lang.core import parser, syntax
from tapl_lang.core.parser import Cursor, route
from tapl_lang.pythonlike import expr, stmt

# https://docs.python.org/3/reference/grammar.html


@dataclass
class TokenKeyword(syntax.Term):
    location: syntax.Location
    value: str

    def repr__tapl(self) -> str:
        return f'TokenKeyword({self.location}, {self.value})'


@dataclass
class TokenName(syntax.Term):
    location: syntax.Location
    value: str

    def repr__tapl(self) -> str:
        return f'TokenName({self.location}, {self.value})'


@dataclass
class TokenString(syntax.Term):
    location: syntax.Location
    value: str

    def repr__tapl(self) -> str:
        return f'TokenString({self.location}, {self.value})'


@dataclass
class TokenNumber(syntax.Term):
    location: syntax.Location
    value: int

    def repr__tapl(self) -> str:
        return f'TokenNumber({self.location}, {self.value})'


@dataclass
class TokenPunct(syntax.Term):
    location: syntax.Location
    value: str

    def repr__tapl(self) -> str:
        return f'TokenPunct({self.location}, {self.value})'


@dataclass
class TokenEndOfText(syntax.Term):
    location: syntax.Location

    def repr__tapl(self) -> str:
        return f'TokenEndOfText({self.location})'


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


def skip_whitespaces(c: Cursor) -> None:
    while not c.is_end() and c.current_char().isspace():
        c.move_to_next()


def rule_token(c: Cursor) -> syntax.Term:
    skip_whitespaces(c)
    tracker = c.start_tracker()
    if c.is_end():
        return TokenEndOfText(tracker.location)

    def scan_name(char: str) -> syntax.Term:
        result = char
        while not c.is_end() and (char := c.current_char()) and (char.isalnum() or char == '_'):
            result += char
            c.move_to_next()
        if result in KEYWORDS:
            return TokenKeyword(tracker.location, value=result)
        return TokenName(tracker.location, value=result)

    def unterminated_string() -> syntax.Term:
        return syntax.ErrorTerm(
            message=f'unterminated string literal (detected at line {tracker.location.end.line}); perhaps you escaped the end quote?',
            location=tracker.location,
        )

    def scan_string() -> syntax.Term:
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

    def scan_number(char: str) -> syntax.Term:
        number_str = char
        while not c.is_end() and (char := c.current_char()).isdigit():
            number_str += char
            c.move_to_next()
        return TokenNumber(tracker.location, value=int(number_str))

    def scan_punct(char: str) -> syntax.Term:
        k = c.clone()
        char2: str | None = None
        char3: str | None = None
        if not k.is_end():
            char2 = k.current_char()
            k.move_to_next()
        if not k.is_end():
            char3 = k.current_char()
            k.move_to_next()
        if char2 is not None:
            if char3 is not None and (temp := char + char2 + char3) in PUNCT_SET:
                c.copy_from(k)
                return TokenPunct(tracker.location, value=temp)
            if (temp := char + char2) in PUNCT_SET:
                c.move_to_next()
                return TokenPunct(tracker.location, value=temp)
        # single-character punctuation
        return TokenPunct(tracker.location, value=char)

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
    return tracker.fail()


def consume_keyword(c: Cursor, keyword: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, TokenKeyword) and term.value == keyword:
        return term
    return t.fail()


def expect_keyword(c: Cursor, keyword: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, TokenKeyword) and term.value == keyword:
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected "{keyword}", but found {term}', location=t.location)


def consume_name(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, TokenName):
        return term
    return t.fail()


def expect_name(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, TokenName):
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected a name, but found {term}', location=t.location)


def consume_punct(c: Cursor, *puncts: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, TokenPunct) and term.value in puncts:
        return term
    return t.fail()


def expect_punct(c: Cursor, *puncts: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule('token')) and isinstance(term, TokenPunct) and term.value in puncts:
        return term
    puncts_text = ', '.join(f'"{p}"' for p in puncts)
    return t.captured_error or syntax.ErrorTerm(
        message=f'Expected {puncts_text}, but found {term}', location=t.location
    )


def expect_rule(c: Cursor, rule: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rule)):
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected rule "{rule}"', location=t.location)


# Primary elements
# ----------------


def scan_arguments(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    args = []
    if t.validate(first_arg := c.consume_rule('expression')):
        args.append(first_arg)
        k = c.clone()
        while t.validate(consume_punct(k, ',')) and t.validate(arg := expect_rule(k, 'expression')):
            c.copy_from(k)
            args.append(arg)
    return t.captured_error or syntax.Block(terms=args)


def rule_primary__call(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(func := c.consume_rule('primary'))
        and t.validate(consume_punct(c, '('))
        and t.validate(args := scan_arguments(c))
        and t.validate(expect_punct(c, ')'))
    ):
        return expr.Call(t.location, func, cast(syntax.Block, args).terms)
    return t.fail()


def build_rule_name(ctx: str) -> Callable[[Cursor], syntax.Term]:
    def rule(c: Cursor) -> syntax.Term:
        t = c.start_tracker()
        if t.validate(token := c.consume_rule('token')) and isinstance(token, TokenName):
            return expr.Name(location=token.location, id=token.value, ctx=ctx)
        return t.fail()

    return rule


def rule_atom__bool(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(token := c.consume_rule('token')) and isinstance(token, TokenKeyword):
        location = token.location
        if token.value in ('True', 'False'):
            value = token.value == 'True'
            return expr.BooleanLiteral(location, value=value)
        if token.value == 'None':
            return expr.NoneLiteral(location)
    return t.fail()


def rule_atom__string(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(token := c.consume_rule('token')) and isinstance(token, TokenString):
        return expr.StringLiteral(token.location, value=token.value)
    return t.fail()


def rule_atom__number(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(token := c.consume_rule('token')) and isinstance(token, TokenNumber):
        return expr.IntegerLiteral(token.location, value=token.value)
    return t.fail()


# Arithmetic operators
# --------------------


def rule_factor__unary(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(op := consume_punct(c, '+', '-', '~')) and t.validate(factor := expect_rule(c, 'factor')):
        return expr.UnaryOp(t.location, cast(TokenPunct, op).value, factor)
    return t.fail()


def rule_invalid_factor(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(consume_punct(c, '+', '-', '~'))
        and t.validate(consume_keyword(c, 'not'))
        and t.validate(c.consume_rule('factor'))
    ):
        return syntax.ErrorTerm(message="'not' after an operator must be parenthesized", location=t.location)
    return t.fail()


def rule_term__binary(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(left := c.consume_rule('term'))
        and t.validate(op := consume_punct(c, '*', '/', '//', '%'))
        and t.validate(right := expect_rule(c, 'factor'))
    ):
        return expr.BinOp(t.location, left, cast(TokenPunct, op).value, right)
    return t.fail()


def rule_sum__binary(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(left := c.consume_rule('sum'))
        and t.validate(op := consume_punct(c, '+', '-'))
        and t.validate(right := expect_rule(c, 'term'))
    ):
        return expr.BinOp(t.location, left, cast(TokenPunct, op).value, right)
    return t.fail()


# Comparison operators
# --------------------


def scan_operator(c: Cursor) -> str | None:
    first = c.consume_rule('token')
    if isinstance(first, TokenPunct) and first.value in ('==', '!=', '<=', '<', '>=', '>', 'in'):
        return first.value
    if isinstance(first, TokenKeyword):
        if first.value == 'not':
            second = c.consume_rule('token')
            if isinstance(second, TokenKeyword) and second.value == 'in':
                return 'not in'
            return None
        if first.value == 'is':
            second = c.consume_rule('token')
            if isinstance(second, TokenKeyword) and second.value == 'not':
                return 'is not'
            return 'is'
    return None


def rule_comparison(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(left := c.consume_rule('sum')):
        ops = []
        comparators = []
        k = c.clone()
        while (op := scan_operator(k)) and t.validate(comparator := expect_rule(k, 'sum')):
            c.copy_from(k)
            ops.append(op)
            comparators.append(comparator)
        if ops:
            return expr.Compare(t.location, left=left, ops=ops, comparators=comparators)
    return t.fail()


# EXPRESSIONS
# -----------


def rule_inversion__not(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(consume_keyword(c, 'not')) and t.validate(operand := expect_rule(c, 'comparison')):
        return expr.BoolNot(location=t.location, operand=operand)
    return t.fail()


def rule_conjunction__and(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(left := c.consume_rule('inversion')):
        values = [left]
        k = c.clone()
        while t.validate(consume_keyword(k, 'and')) and t.validate(right := expect_rule(k, 'inversion')):
            c.copy_from(k)
            values.append(right)
        if len(values) > 1:
            return expr.BoolOp(location=t.location, op='and', values=values)
    return t.fail()


def rule_disjunction__or(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(left := c.consume_rule('conjunction')):
        values = [left]
        k = c.clone()
        while t.validate(consume_keyword(k, 'or')) and t.validate(right := expect_rule(k, 'conjunction')):
            c.copy_from(k)
            values.append(right)
        if len(values) > 1:
            return expr.BoolOp(location=t.location, op='or', values=values)
    return t.fail()


# SIMPLE STATEMENTS
# =================


def rule_assignment(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(name := c.consume_rule('name_store'))
        and t.validate(consume_punct(c, '='))
        and t.validate(value := expect_rule(c, 'expression'))
    ):
        return stmt.Assign(t.location, targets=[name], value=value)
    return t.fail()


def rule_expression_statement(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(value := c.consume_rule('expression')):
        if hasattr(value, 'location'):
            location = value.location
        else:
            location = t.location
        return stmt.Expr(location=location, value=value)
    return t.fail()


def rule_return(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(consume_keyword(c, 'return')):
        if t.validate(value := c.consume_rule('expression')):
            return stmt.Return(t.location, value=value)
        return t.captured_error or stmt.Return(t.location, value=expr.NoneLiteral(t.location))
    return t.fail()


def rule_parameter(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(name := consume_name(c))
        and t.validate(consume_punct(c, ':'))
        and t.validate(param_type := expect_rule(c, 'expression'))
    ):
        param_name = cast(TokenName, name).value
        return stmt.Parameter(t.location, name=param_name, type_=syntax.Layers([stmt.Absence(), param_type]))
    return t.fail()


def scan_parameters(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    params = []
    if t.validate(first_param := c.consume_rule('parameter')):
        params.append(first_param)
        k = c.clone()
        while t.validate(consume_punct(k, ',')) and t.validate(param := expect_rule(k, 'parameter')):
            c.copy_from(k)
            params.append(param)
    return t.captured_error or syntax.Block(terms=params)


def rule_function_def(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(consume_keyword(c, 'def'))
        and t.validate(func_name := expect_name(c))
        and t.validate(expect_punct(c, '('))
        and t.validate(params := scan_parameters(c))
        and t.validate(expect_punct(c, ')'))
        and t.validate(expect_punct(c, ':'))
    ):
        name = cast(TokenName, func_name).value
        return stmt.FunctionDef(
            location=t.location,
            name=name,
            parameters=cast(syntax.Block, params).terms,
            body=syntax.Block([], delayed=True),
        )
    return t.fail()


def rule_if_stmt(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(consume_keyword(c, 'if'))
        and t.validate(test := expect_rule(c, 'expression'))
        and t.validate(expect_punct(c, ':'))
    ):
        return stmt.If(location=t.location, test=test, body=syntax.Block([], delayed=True), orelse=None)
    return t.fail()


def rule_else_stmt(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(consume_keyword(c, 'else')) and t.validate(expect_punct(c, ':')):
        return stmt.Else(location=t.location, body=syntax.Block([], delayed=True))
    return t.fail()


def parse_start(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(statement := expect_rule(c, 'statement')):
        skip_whitespaces(c)
        return statement
    return t.fail()


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
    'atom': [build_rule_name('load'), rule_atom__bool, rule_atom__string, rule_atom__number],
    'token': [rule_token],
    'statement': [
        route('assignment'),
        rule_expression_statement,
        route('return'),
        route('function_def'),
        route('if_stmt'),
        route('else_stmt'),
    ],
    'assignment': [rule_assignment],
    'return': [rule_return],
    'function_def': [rule_function_def],
    'parameter': [rule_parameter],
    'name_store': [build_rule_name('store')],
    'if_stmt': [rule_if_stmt],
    'else_stmt': [rule_else_stmt],
    'start': [parse_start],
}

GRAMMAR: parser.Grammar = parser.Grammar(rule_map=RULES, start_rule='start')
