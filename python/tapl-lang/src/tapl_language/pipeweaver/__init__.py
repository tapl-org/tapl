# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import dataclasses
from typing import override

from tapl_lang.core import parser, syntax
from tapl_lang.lib import terms
from tapl_lang.pythonlike import language, rule_names


@dataclasses.dataclass
class PipeToken(syntax.Term):
    location: syntax.Location


def _parse_pipe_token(c: parser.Cursor) -> syntax.Term:
    c.skip_whitespace()
    t = c.start_tracker()
    if c.is_end():
        return t.fail()
    char1 = c.current_char()
    c.move_to_next()
    if not c.is_end():
        char2 = c.current_char()
        c.move_to_next()
        if char1 == '|' and char2 == '>':
            c.copy_position_from(c)
            return PipeToken(location=t.location)
    return t.fail()


def _parse_pipe_call(c: parser.Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(arg := c.consume_rule(rule_names.EXPRESSION))
        and t.validate(op := c.consume_rule(rule_names.TOKEN))
        and isinstance(op, PipeToken)
        and t.validate(func := c.consume_rule(rule_names.DISJUNCTION))
    ):
        return terms.Call(func=func, args=[arg], keywords=[], location=t.location)
    return t.fail()


class PipeweaverLanguage(language.PythonlikeLanguage):
    @override
    def get_grammar(self, parent_stack: list[syntax.Term]) -> parser.Grammar:
        pythonlike_grammar = super().get_grammar(parent_stack)
        # Add additional rules or modifications to the grammar here
        rule_map = pythonlike_grammar.rule_map.copy()
        rule_map[rule_names.TOKEN] = [_parse_pipe_token] + rule_map[rule_names.TOKEN]
        rule_map[rule_names.EXPRESSION] = [_parse_pipe_call] + rule_map[rule_names.EXPRESSION]
        return parser.Grammar(
            rule_map=rule_map,
            start_rule=pythonlike_grammar.start_rule,
        )


def get_language():
    return PipeweaverLanguage()
