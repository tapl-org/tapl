# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import dataclasses
from collections.abc import Iterable
from typing import cast

from oymo.core import parser, syntax
from oymo.core.parser import Cursor
from oymo.oymomo import rule_names as rn
from oymo.oymomo import terms


@dataclasses.dataclass
class TokenName(syntax.Term):
    location: syntax.Location
    value: str


@dataclasses.dataclass
class TokenPunct(syntax.Term):
    location: syntax.Location
    value: str


@dataclasses.dataclass
class TokenEndOfText(syntax.Term):
    location: syntax.Location


_PUNCT_SET = {
    ':',
    '=',
    '->',
    '{',
    '}',
    ',',
}

_PUNCT_FIRST_CHARS = {c[0] for c in _PUNCT_SET}


def get_grammar() -> parser.Grammar:
    rules: parser.GrammarRuleMap = {}

    def add(name: str, ordered_parse_functions: Iterable[parser.ParseFunction | str]) -> None:
        if name in rules:
            raise ValueError(f'Rule {name} is already defined.')
        # TODO: Wrap ordered_parse_functions in an "tuple" to ensure internal immutability
        rules[name] = ordered_parse_functions

    add(rn.START, [_parse_start])
    add(rn.TOKEN, [_parse_token])
    add(rn.VARIABLE, [_parse_variable])
    add(rn.LAMBDA, [_parse_lambda])
    add(rn.APPLY, [_parse_apply])
    add(rn.RECORD, [_parse_record])

    return parser.Grammar(rule_map=rules, start_rule=rn.START)


def _expect_rule(c: Cursor, rule: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rule)):
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected rule "{rule}"', location=t.location)


def _consume_name(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, TokenName):
        return term
    return t.fail()


def _expect_name(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, TokenName):
        return term
    return t.captured_error or syntax.ErrorTerm(message=f'Expected a name, but found {term}', location=t.location)


def _consume_punct(c: Cursor, *puncts: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, TokenPunct) and term.value in puncts:
        return term
    return t.fail()


def _expect_punct(c: Cursor, *puncts: str) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(term := c.consume_rule(rn.TOKEN)) and isinstance(term, TokenPunct) and term.value in puncts:
        return term
    puncts_text = ', '.join(f'"{p}"' for p in puncts)
    return t.captured_error or syntax.ErrorTerm(
        message=f'Expected {puncts_text}, but found {term}', location=t.location
    )


def _parse_token(c: Cursor) -> syntax.Term:
    c.skip_whitespace()
    tracker = c.start_tracker()
    if c.is_end():
        return TokenEndOfText(tracker.location)

    def scan_name(char: str) -> syntax.Term:
        result = char
        while not c.is_end() and (char := c.current_char()) and (char.isalnum() or char == '_'):
            result += char
            c.move_to_next()
        return TokenName(tracker.location, value=result)

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
            if char3 is not None and (temp := char + char2 + char3) in _PUNCT_SET:
                c.copy_position_from(k)
                return TokenPunct(tracker.location, value=temp)
            if (temp := char + char2) in _PUNCT_SET:
                c.move_to_next()
                return TokenPunct(tracker.location, value=temp)
        # single-character punctuation
        return TokenPunct(tracker.location, value=char)

    char = c.current_char()
    c.move_to_next()
    if char.isalpha() or char == '_':
        return scan_name(char)
    if char in _PUNCT_FIRST_CHARS:
        return scan_punct(char)
    # Error
    return tracker.captured_error or syntax.ErrorTerm(
        message=f'Token Parsing: Unexpected character "{char}"', location=tracker.location
    )


def _parse_variable(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(name_token := _expect_name(c)):
        name = cast('TokenName', name_token).value
        return terms.Variable(name=name, location=t.location)
    return t.fail()


# a:i32 -> x
def _parse_lambda(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(param_name_ := _expect_name(c))
        and t.validate(_expect_punct(c, ':'))
        and t.validate(param_form_ := _expect_name(c))
        and t.validate(_expect_punct(c, '->'))
        and t.validate(body := _expect_rule(c, rn.VARIABLE))
    ):
        param_name = cast('TokenName', param_name_).value
        param_form = cast('TokenName', param_form_).value
        return terms.Lambda(
            param_name=param_name, param_form=terms.ScalarForm(name=param_form), body=body, location=t.location
        )
    return t.fail()


# f x
def _parse_apply(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(function := _expect_rule(c, rn.VARIABLE)) and t.validate(argument := _expect_rule(c, rn.VARIABLE)):
        return terms.Apply(function=function, argument=argument, location=t.location)
    return t.fail()


# a: i32 = x
def _scan_field(c: Cursor) -> terms.Field:
    t = c.start_tracker()
    if (
        t.validate(label_ := _consume_name(c))
        and t.validate(_expect_punct(c, ':'))
        and t.validate(form_ := _consume_name(c))
        and t.validate(_expect_punct(c, '='))
        and t.validate(value := _expect_rule(c, rn.VARIABLE))
    ):
        return terms.Field(
            label=cast('TokenName', label_).value,
            form=terms.ScalarForm(name=cast('TokenName', form_).value),
            value=value,
            location=t.location,
        )
    return t.fail()


# {}, {a: i32 = x, b: i32 = y,}
def _parse_record(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(_consume_punct(c, '{')):
        fields: list[terms.Field] = []
        while not c.is_end():
            k = c.clone()
            if t.validate(field := _scan_field(k)) and t.validate(_expect_punct(k, ',')):
                fields.append(field)
                c.copy_position_from(k)
            else:
                break
        if t.validate(_expect_punct(c, '}')):
            return terms.Record(fields=fields, location=t.location)
    return t.fail()


def _parse_start(c: Cursor) -> syntax.Term:
    t = c.start_tracker()
    if t.validate(expression := _expect_rule(c, rn.VARIABLE)):
        c.skip_whitespace()
        return expression
    return t.fail()
