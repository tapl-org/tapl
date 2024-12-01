# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# import ast

# from tapl_lang import parser
# from tapl_lang import parsertools as pt
# from tapl_lang import pythonlike_syntax as ps
# from tapl_lang.parser import Cursor, LocationTracker
# from tapl_lang.syntax import Term


# def parse_true(c: Cursor) -> Term | None:
#     tracker = LocationTracker(c)
#     if consume_text(c, 'True'):
#         return ps.Constant(tracker.location, value=True)
#     return None


# def parse_false(c: Cursor) -> Term | None:
#     tracker = LocationTracker(c)
#     if consume_text(c, 'False'):
#         return ps.Constant(tracker.location, value=False)
#     return None


# def parse_inversion_not(c: Cursor) -> Term | None:
#     tracker = LocationTracker(c)
#     if consume_text(c, 'not') and pt.expect_whitespaces(c) and (operand := consume_rule(c, 'atom')):
#         return ps.UnaryOp(tracker.location, ast.Not(), operand)
#     return None


# RULES: parser.GrammarRuleMap = {
#     'atom': [parse_true, parse_false],
# }
