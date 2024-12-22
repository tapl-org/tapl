# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any

from tapl_lang.syntax import MODE_EVALUATE, MODE_TYPECHECK, LayerSeparator, Location, Term, TermWithLocation
from tapl_lang.tapl_error import TaplError


def with_location(tree: ast.expr, loc: Location) -> ast.expr:
    if loc.start:
        tree.lineno = loc.start.line
        tree.col_offset = loc.start.column
    if loc.end:
        tree.end_lineno = loc.end.line
        tree.end_col_offset = loc.end.column
    return tree


def ast_op(op, loc: Location) -> ast.expr:
    ast_module = with_location(ast.Name(id='ast', ctx=ast.Load()), loc)
    ast_op = with_location(ast.Attribute(value=ast_module, attr=op.__class__.__name__, ctx=ast.Load()), loc)
    return with_location(ast.Call(func=ast_op, args=[]), loc)


def ast_typelib_attribute(attr: str, loc: Location) -> ast.expr:
    ast_name = with_location(ast.Name(id='t', ctx=ast.Load()), loc)
    return with_location(ast.Attribute(value=ast_name, attr=attr, ctx=ast.Load()), loc)


def ast_typelib_call(function_name: str, args: list[ast.expr], loc: Location) -> ast.expr:
    return with_location(ast.Call(func=ast_typelib_attribute(function_name, loc), args=args), loc)


def ast_method_call(value: ast.expr, method_name: str, args: list[ast.expr], loc: Location) -> ast.expr:
    func = with_location(ast.Attribute(value=value, attr=method_name, ctx=ast.Load()), loc)
    return with_location(ast.Call(func=func, args=args), loc)


@dataclass(frozen=True)
class Constant(TermWithLocation):
    value: Any

    def has_error(self) -> bool:
        return False

    def separate(self) -> Term:
        return self

    def codegen_expr(self) -> ast.expr:
        return with_location(ast.Constant(self.value), self.location)


@dataclass(frozen=True)
class Name(TermWithLocation):
    id: str
    ctx: ast.expr_context

    def has_error(self):
        return False

    def separate(self):
        return self

    def codegen_expr(self):
        return with_location(ast.Name(id=self.id, ctx=self.ctx), self.location)


@dataclass(frozen=True)
class Attribute(TermWithLocation):
    value: Term
    attr: str
    ctx: ast.expr_context

    def has_error(self):
        return self.value.has_error()

    def separate(self) -> Term:
        ls = LayerSeparator()
        value = ls.separate(self.value)
        return ls.build(lambda layer: Attribute(self.location, layer(value), self.attr, self.ctx))

    # TODO: Attribute must have a type layer to check attribute exists or not
    def codegen_expr(self) -> ast.expr:
        return with_location(ast.Attribute(self.value.codegen_expr(), attr=self.attr, ctx=self.ctx), self.location)


@dataclass(frozen=True)
class UnaryOp(TermWithLocation):
    op: ast.unaryop
    operand: Term
    mode: Term

    def has_error(self):
        return self.operand.has_error() or self.mode.has_error()

    def separate(self) -> Term:
        ls = LayerSeparator()
        operand = ls.separate(self.operand)
        mode = ls.separate(self.mode)
        return ls.build(lambda layer: UnaryOp(self.location, self.op, layer(operand), layer(mode)))

    def codegen_expr(self) -> ast.expr:
        print(self.op)
        print(self.mode)
        operand = self.operand.codegen_expr()
        if self.mode is MODE_TYPECHECK and isinstance(self.op, ast.Not):
            # unary not operator always returns Bool type
            return ast_typelib_attribute('Bool', self.location)
        return with_location(ast.UnaryOp(self.op, operand), self.location)


@dataclass(frozen=True)
class BoolOp(TermWithLocation):
    op: ast.boolop
    values: list[Term]
    mode: Term

    def has_error(self) -> bool:
        return any(v.has_error() for v in self.values) or self.mode.has_error()

    def separate(self) -> Term:
        ls = LayerSeparator()
        values = [ls.separate(v) for v in self.values]
        mode = ls.separate(self.mode)
        return ls.build(lambda layer: BoolOp(self.location, self.op, [layer(v) for v in values], layer(mode)))

    def codegen_expr(self) -> ast.expr:
        if self.mode is MODE_EVALUATE:
            return with_location(ast.BoolOp(self.op, [v.codegen_expr() for v in self.values]), self.location)
        if self.mode is MODE_TYPECHECK:
            return ast_typelib_call('create_union', [v.codegen_expr() for v in self.values], self.location)
        raise TaplError(f'Run mode not found. {self.mode} term={self.__class__.__name__}')


@dataclass(frozen=True)
class Compare(TermWithLocation):
    left: Term
    ops: list[ast.cmpop]
    comparators: list[Term]
    mode: Term

    def has_error(self):
        return self.left.has_error() or any(v.has_error() for v in self.comparators)

    def separate(self) -> Term:
        ls = LayerSeparator()
        left = ls.separate(self.left)
        comparators = [ls.separate(v) for v in self.comparators]
        mode = ls.separate(self.mode)
        return ls.build(
            lambda layer: Compare(self.location, layer(left), self.ops, [layer(v) for v in comparators], layer(mode))
        )

    def codegen_expr(self) -> ast.expr:
        if self.mode is MODE_EVALUATE:
            return with_location(
                ast.Compare(self.left.codegen_expr(), self.ops, [v.codegen_expr() for v in self.comparators]),
                self.location,
            )
        if self.mode is MODE_TYPECHECK:
            args = [self.left.codegen_expr(), self.ops, [v.codegen_expr() for v in self.comparators]]
            return ast_typelib_call('tc_compare', args, self.location)
        raise TaplError(f'Run mode not found. {self.mode} term={self.__class__.__name__}')
