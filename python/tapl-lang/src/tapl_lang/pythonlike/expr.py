# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any, override

from tapl_lang.syntax import MODE_EVALUATE, MODE_TYPECHECK, ErrorTerm, Layers, LayerSeparator, Term, TermWithLocation
from tapl_lang.tapl_error import TaplError

# Unary 'not' has dedicated 'BoolNot' term
UNARY_OP_MAP: dict[str, ast.unaryop] = {'+': ast.UAdd(), '-': ast.USub(), '~': ast.Invert()}
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


@dataclass
class Constant(TermWithLocation):
    value: Any

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []

    @override
    def codegen_expr(self) -> ast.expr:
        const = ast.Constant(self.value)
        self.locate(const)
        return const


@dataclass
class Name(TermWithLocation):
    id: str
    ctx: str

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []

    @override
    def codegen_expr(self) -> ast.expr:
        name = ast.Name(id=self.id, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.locate(name)
        return name


@dataclass
class Attribute(TermWithLocation):
    value: Term
    attr: str
    ctx: str

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.value.get_errors()

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Attribute(self.location, layer(self.value), self.attr, self.ctx))

    # TODO: Attribute must have a type layer to check attribute exists or not
    @override
    def codegen_expr(self) -> ast.expr:
        attr = ast.Attribute(self.value.codegen_expr(), attr=self.attr, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.locate(attr)
        return attr


@dataclass
class UnaryOp(TermWithLocation):
    op: str
    operand: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.operand.get_errors()

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: UnaryOp(self.location, self.op, layer(self.operand)))

    @override
    def codegen_expr(self) -> ast.expr:
        operand = self.operand.codegen_expr()
        unary = ast.UnaryOp(UNARY_OP_MAP[self.op], operand)
        self.locate(unary)
        return unary


@dataclass
class BoolNot(TermWithLocation):
    operand: Term
    mode: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.operand.get_errors() + self.mode.get_errors()

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: BoolNot(self.location, layer(self.operand), layer(self.mode)))

    @override
    def codegen_expr(self) -> ast.expr:
        if self.mode is MODE_EVALUATE:
            operand = self.operand.codegen_expr()
            unary = ast.UnaryOp(ast.Not(), operand)
            self.locate(unary)
            return unary
        if self.mode is MODE_TYPECHECK:
            # unary not operator always returns Bool type
            bool_type = ast.Name(id='Bool', ctx=ast.Load())
            self.locate(bool_type)
            return bool_type
        raise TaplError(f'Run mode not found. {self.mode} term={self.__class__.__name__}')


@dataclass
class BoolOp(TermWithLocation):
    op: str
    values: list[Term]
    mode: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = self.mode.get_errors()
        for v in self.values:
            result.extend(v.get_errors())
        return result

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: BoolOp(self.location, self.op, [layer(v) for v in self.values], layer(self.mode)))

    @override
    def codegen_expr(self) -> ast.expr:
        if self.mode is MODE_EVALUATE:
            op = ast.BoolOp(BOOL_OP_MAP[self.op], [v.codegen_expr() for v in self.values])
            self.locate(op)
            return op
        if self.mode is MODE_TYPECHECK:
            create_union = ast.Name(id='create_union', ctx=ast.Load())
            call = ast.Call(func=create_union, args=[v.codegen_expr() for v in self.values])
            self.locate(create_union, call)
            return call
        raise TaplError(f'Run mode not found. {self.mode} term={self.__class__.__name__}')


@dataclass
class BinOp(TermWithLocation):
    left: Term
    op: str
    right: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.left.get_errors() + self.right.get_errors()

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: BinOp(self.location, layer(self.left), self.op, layer(self.right)))

    @override
    def codegen_expr(self) -> ast.expr:
        op = ast.BinOp(self.left.codegen_expr(), BIN_OP_MAP[self.op], self.right.codegen_expr())
        self.locate(op)
        return op


@dataclass
class Compare(TermWithLocation):
    left: Term
    ops: list[str]
    comparators: list[Term]

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = self.left.get_errors()
        for v in self.comparators:
            result.extend(v.get_errors())
        return result

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: Compare(self.location, layer(self.left), self.ops, [layer(v) for v in self.comparators])
        )

    @override
    def codegen_expr(self) -> ast.expr:
        compare = ast.Compare(
            self.left.codegen_expr(),
            [COMPARE_OP_MAP[op] for op in self.ops],
            [v.codegen_expr() for v in self.comparators],
        )
        self.locate(compare)
        return compare


@dataclass
class Call(TermWithLocation):
    func: Term
    args: list[Term]

    @override
    def get_errors(self) -> list[ErrorTerm]:
        result = self.func.get_errors()
        for v in self.args:
            result.extend(v.get_errors())
        return result

    @override
    def separate(self, ls):
        return ls.build(lambda layer: Call(self.location, layer(self.func), [layer(v) for v in self.args]))

    @override
    def codegen_expr(self) -> ast.expr:
        call = ast.Call(self.func.codegen_expr(), [v.codegen_expr() for v in self.args])
        self.locate(call)
        return call
