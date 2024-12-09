# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang.pythonlike import syntax
from tapl_lang.syntax import Location, Term
from tapl_lang.tapl_error import TaplError


def with_location(tree: ast.expr, loc: Location) -> ast.expr:
    if loc.start:
        tree.lineno = loc.start.line
        tree.col_offset = loc.start.column
    if loc.end:
        tree.end_lineno = loc.end.line
        tree.end_col_offset = loc.end.column
    return tree


class Codegen:
    def generate_expr(self, term: Term) -> ast.expr:
        if term.separable():
            raise TaplError('Cannot generate AST from separable term.')
        if term.has_error():
            raise TaplError('Cannot generate AST from term which has error.')
        match term:
            case syntax.Constant(loc, value):
                return with_location(ast.Constant(value), loc)
            case syntax.UnaryOp(loc, op, operand):
                return with_location(ast.UnaryOp(op, self.generate_expr(operand)), loc)
            case syntax.BoolOp(loc, op, values):
                vals = [self.generate_expr(t) for t in values]
                return with_location(ast.BoolOp(op, vals), loc)
            case _:
                raise TaplError(f'Not supported term. class_name={term.__class__.__name__}')


def gen_eval(term: Term) -> ast.Expression:
    body = Codegen().generate_expr(term)
    # print(f'{body.lineno}:{body.col_offset} - {body.end_lineno}:{body.end_col_offset}')
    return ast.Expression(body=body)
