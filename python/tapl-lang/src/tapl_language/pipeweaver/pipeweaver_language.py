# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import dataclasses

from tapl_lang.core import parser, syntax
from tapl_lang.lib import terms
from tapl_lang.pythonlike import language, rule_names


@dataclasses.dataclass
class PipeToken(syntax.Term):
    pass


def _parse_pipe_token(c: parser.Cursor) -> syntax.Term:
    c.skip_whitespace()
    if c.consume_text('|>'):
        return PipeToken()
    return parser.ParseFailed


def _parse_pipe_call(c: parser.Cursor) -> syntax.Term:
    t = c.start_tracker()
    if (
        t.validate(argument := c.consume_rule(rule_names.EXPRESSION))
        and t.validate(operator := c.consume_rule(rule_names.TOKEN))
        and isinstance(operator, PipeToken)
        and t.validate(function := c.consume_rule(rule_names.DISJUNCTION))
    ):
        return terms.Call(func=function, args=[argument], keywords=[], location=t.location)
    return t.fail()


class PipeweaverLanguage(language.PythonlikeLanguage):
    def get_grammar(self, parent_stack: list[syntax.Term]) -> parser.Grammar:
        grammar = super().get_grammar(parent_stack).clone()
        grammar.rule_map[rule_names.TOKEN] = [_parse_pipe_token, *grammar.rule_map[rule_names.TOKEN]]
        grammar.rule_map[rule_names.EXPRESSION] = [_parse_pipe_call, *grammar.rule_map[rule_names.EXPRESSION]]
        return grammar
