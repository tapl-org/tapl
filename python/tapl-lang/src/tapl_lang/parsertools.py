# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.parser import Cursor, ParseFunction
from tapl_lang.syntax import ErrorTerm, Location, Term


def first_falsy(*args):
    """Returns the first falsy value from a list of arguments.

    Args:
        *args: A variable number of arguments.

    Returns:
        The first falsy argument, or None if none are found.
    """
    return next((arg for arg in args if not arg), None)


def consume_whitespaces(c: Cursor) -> bool:
    consumed = False
    while not c.is_end() and c.current_char().isspace():
        consumed = True
        c.move_to_next()
    return consumed


def expect_whitespaces(c: Cursor) -> bool | Term:
    start_pos = c.current_position()
    if consume_whitespaces(c):
        return True
    return ErrorTerm(Location(start=start_pos, end=c.current_position()), 'Expected whitespaces')


def consume_text(c: Cursor, text: str, *, keep_whitespaces: bool = False) -> bool:
    if not keep_whitespaces:
        consume_whitespaces(c)
    for char in text:
        if c.is_end():
            return False
        if c.current_char() != char:
            return False
        c.move_to_next()
    return True


def expect_text(c: Cursor, text: str) -> bool | Term:
    start_pos = c.current_position()
    if consume_text(c, text):
        return True
    return ErrorTerm(Location(start=start_pos, end=c.current_position()), f'Expected "{text}"')


def consume_rule(c: Cursor, rule: str, *, keep_whitespaces: bool = False) -> Term | None:
    if not keep_whitespaces:
        consume_whitespaces(c)
    return c.apply_rule(rule)


def expect_rule(c: Cursor, rule: str) -> Term | None:
    start_pos = c.current_position()
    term = consume_rule(c, rule)
    if term is not None:
        return term
    return ErrorTerm(Location(start=start_pos, end=c.current_position()), f'Expected rule "{rule}"')


def route(rule: str) -> ParseFunction:
    def parse(c: Cursor) -> Term | None:
        if term := consume_rule(c, rule):
            return term
        return first_falsy(term)

    return parse
