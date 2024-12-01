# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang import parser
from tapl_lang import pythonlike_syntax as ps
from tapl_lang.parser import Cursor, LocationTracker
from tapl_lang.parsertools import consume_text as ctext
from tapl_lang.syntax import Term


def parse_true(c: Cursor) -> Term | None:
    tracker = LocationTracker(c)
    if ctext(c, 'True'):
        return ps.Constant(tracker.location, value=True)
    return None


def parse_false(c: Cursor) -> Term | None:
    tracker = LocationTracker(c)
    if ctext(c, 'False'):
        return ps.Constant(tracker.location, value=False)
    return None


RULES: parser.GrammarRuleMap = {
    'atom': [parse_true, parse_false],
}
