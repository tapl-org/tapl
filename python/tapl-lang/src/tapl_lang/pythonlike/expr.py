# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any

from tapl_lang.syntax import MODE_EVALUATE, MODE_TYPECHECK, ErrorTerm, LayerSeparator, Location, Term, TermWithLocation
from tapl_lang.tapl_error import TaplError

UNARY_OP_MAP: dict[str, ast.unaryop] = {'+': ast.UAdd(), '-': ast.USub(), '~': ast.Invert(), 'not': ast.Not()}
BIN_OP_MAP: dict[str, ast.operator] = {
    '+': ast.Add(),
    '-': ast.Sub(),
    '*': ast.Mult(),
    '/': ast.Div(),
    '//': ast.FloorDiv(),
    '%': ast.Mod(),
}
BOOL_OP_MAP: dict[str, ast.boolop] = {'and': ast.And(), 'or': ast.Or()}
COMPARE_OP_MAP: dict[str, ast.cmpop] = {
    '==': ast.Eq(),
    '!=': ast.NotEq(),
    '<': ast.Lt(),
    '<=': ast.LtE(),
    '>': ast.Gt(),
    '>=': ast.GtE(),
    'is': ast.Is(),
    'is not': ast.IsNot(),
    'in': ast.In(),
    'not in': ast.NotIn(),
}
EXPR_CONTEXT_MAP: dict[str, ast.expr_context] = {'load': ast.Load(), 'store': ast.Store(), 'del': ast.Del()}


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

    def get_errors(self) -> list[ErrorTerm]:
        return []

    def separate(self) -> Term:
        return self

    def codegen_expr(self) -> ast.expr:
        return with_location(ast.Constant(self.value), self.location)


@dataclass(frozen=True)
class Name(TermWithLocation):
    id: str
    ctx: str

    def get_errors(self) -> list[ErrorTerm]:
        return []

    def separate(self) -> Term:
        return self

    def codegen_expr(self) -> ast.expr:
        return with_location(ast.Name(id=self.id, ctx=EXPR_CONTEXT_MAP[self.ctx]), self.location)


@dataclass(frozen=True)
class Attribute(TermWithLocation):
    value: Term
    attr: str
    ctx: str

    def get_errors(self) -> list[ErrorTerm]:
        return self.value.get_errors()

    def separate(self) -> Term:
        ls = LayerSeparator()
        value = ls.separate(self.value)
        return ls.build(lambda layer: Attribute(self.location, layer(value), self.attr, self.ctx))

    # TODO: Attribute must have a type layer to check attribute exists or not
    def codegen_expr(self) -> ast.expr:
        return with_location(
            ast.Attribute(self.value.codegen_expr(), attr=self.attr, ctx=EXPR_CONTEXT_MAP[self.ctx]), self.location
        )


@dataclass(frozen=True)
class UnaryOp(TermWithLocation):
    op: str
    operand: Term
    mode: Term

    def get_errors(self) -> list[ErrorTerm]:
        return self.operand.get_errors() + self.mode.get_errors()

    def separate(self) -> Term:
        ls = LayerSeparator()
        operand = ls.separate(self.operand)
        mode = ls.separate(self.mode)
        return ls.build(lambda layer: UnaryOp(self.location, self.op, layer(operand), layer(mode)))

    def codegen_expr(self) -> ast.expr:
        operand = self.operand.codegen_expr()
        if self.mode is MODE_TYPECHECK and self.op == 'not':
            # unary not operator always returns Bool type
            return ast_typelib_attribute('Bool_', self.location)
        return with_location(ast.UnaryOp(UNARY_OP_MAP[self.op], operand), self.location)


@dataclass(frozen=True)
class BoolOp(TermWithLocation):
    op: str
    values: list[Term]
    mode: Term

    def get_errors(self) -> list[ErrorTerm]:
        result = self.mode.get_errors()
        for v in self.values:
            result.extend(v.get_errors())
        return result

    def separate(self) -> Term:
        ls = LayerSeparator()
        values = [ls.separate(v) for v in self.values]
        mode = ls.separate(self.mode)
        return ls.build(lambda layer: BoolOp(self.location, self.op, [layer(v) for v in values], layer(mode)))

    def codegen_expr(self) -> ast.expr:
        if self.mode is MODE_EVALUATE:
            return with_location(
                ast.BoolOp(BOOL_OP_MAP[self.op], [v.codegen_expr() for v in self.values]), self.location
            )
        if self.mode is MODE_TYPECHECK:
            return ast_typelib_call('create_union', [v.codegen_expr() for v in self.values], self.location)
        raise TaplError(f'Run mode not found. {self.mode} term={self.__class__.__name__}')


@dataclass(frozen=True)
class BinOp(TermWithLocation):
    left: Term
    op: str
    right: Term

    def get_errors(self) -> list[ErrorTerm]:
        return self.left.get_errors() + self.right.get_errors()

    def separate(self):
        ls = LayerSeparator()
        left = ls.separate(self.left)
        right = ls.separate(self.right)
        return ls.build(lambda layer: BinOp(self.location, layer(left), self.op, layer(right)))

    def codegen_expr(self):
        return with_location(
            ast.BinOp(self.left.codegen_expr(), BIN_OP_MAP[self.op], self.right.codegen_expr()), self.location
        )


@dataclass(frozen=True)
class Compare(TermWithLocation):
    left: Term
    ops: list[str]
    comparators: list[Term]

    def get_errors(self) -> list[ErrorTerm]:
        result = self.left.get_errors()
        for v in self.comparators:
            result.extend(v.get_errors())
        return result

    def separate(self) -> Term:
        ls = LayerSeparator()
        left = ls.separate(self.left)
        comparators = [ls.separate(v) for v in self.comparators]
        return ls.build(lambda layer: Compare(self.location, layer(left), self.ops, [layer(v) for v in comparators]))

    def codegen_expr(self) -> ast.expr:
        return with_location(
            ast.Compare(
                self.left.codegen_expr(),
                [COMPARE_OP_MAP[op] for op in self.ops],
                [v.codegen_expr() for v in self.comparators],
            ),
            self.location,
        )


@dataclass(frozen=True)
class CallKeyword(TermWithLocation):
    arg: str | None
    value: Term

    def get_errors(self):
        return self.value.get_errors()

    def separate(self):
        ls = LayerSeparator()
        value = ls.separate(self.value)
        return ls.build(lambda layer: CallKeyword(self.location, self.arg, layer(value)))

    def codegen_expr(self):
        return super().codegen_expr()


@dataclass(frozen=True)
class Call(TermWithLocation):
    func: Term
    args: list[Term]
    keywords: list[CallKeyword]
