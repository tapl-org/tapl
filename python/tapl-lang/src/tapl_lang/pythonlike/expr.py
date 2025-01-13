# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any, override

from tapl_lang.syntax import MODE_EVALUATE, MODE_TYPECHECK, ErrorTerm, LayerSeparator, Term, TermWithLocation
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


@dataclass(frozen=True)
class Absence(Term):
    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []

    @override
    def layer_agnostic(self):
        return True

    def separate(self):
        return self


@dataclass(frozen=True)
class Constant(TermWithLocation):
    value: Any

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []

    @override
    def separate(self) -> Term:
        return self

    @override
    def codegen_expr(self) -> ast.expr:
        const = ast.Constant(self.value)
        self.locate(const)
        return const


@dataclass(frozen=True)
class Name(TermWithLocation):
    id: str
    ctx: str

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return []

    @override
    def layer_agnostic(self):
        return True

    @override
    def separate(self) -> Term:
        return self

    @override
    def codegen_expr(self) -> ast.expr:
        name = ast.Name(id=self.id, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.locate(name)
        return name


@dataclass(frozen=True)
class Attribute(TermWithLocation):
    value: Term
    attr: str
    ctx: str

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.value.get_errors()

    @override
    def separate(self) -> Term:
        ls = LayerSeparator()
        value = ls.separate(self.value)
        return ls.build(lambda layer: Attribute(self.location, layer(value), self.attr, self.ctx))

    # TODO: Attribute must have a type layer to check attribute exists or not
    @override
    def codegen_expr(self) -> ast.expr:
        attr = ast.Attribute(self.value.codegen_expr(), attr=self.attr, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.locate(attr)
        return attr


@dataclass(frozen=True)
class UnaryOp(TermWithLocation):
    op: str
    operand: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.operand.get_errors()

    @override
    def separate(self) -> Term:
        ls = LayerSeparator()
        operand = ls.separate(self.operand)
        return ls.build(lambda layer: UnaryOp(self.location, self.op, layer(operand)))

    @override
    def codegen_expr(self) -> ast.expr:
        operand = self.operand.codegen_expr()
        unary = ast.UnaryOp(UNARY_OP_MAP[self.op], operand)
        self.locate(unary)
        return unary


@dataclass(frozen=True)
class BoolNot(TermWithLocation):
    operand: Term
    mode: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.operand.get_errors() + self.mode.get_errors()

    @override
    def separate(self) -> Term:
        ls = LayerSeparator()
        operand = ls.separate(self.operand)
        mode = ls.separate(self.mode)
        return ls.build(lambda layer: BoolNot(self.location, layer(operand), layer(mode)))

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


@dataclass(frozen=True)
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
    def separate(self) -> Term:
        ls = LayerSeparator()
        values = [ls.separate(v) for v in self.values]
        mode = ls.separate(self.mode)
        return ls.build(lambda layer: BoolOp(self.location, self.op, [layer(v) for v in values], layer(mode)))

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


@dataclass(frozen=True)
class BinOp(TermWithLocation):
    left: Term
    op: str
    right: Term

    @override
    def get_errors(self) -> list[ErrorTerm]:
        return self.left.get_errors() + self.right.get_errors()

    @override
    def separate(self) -> Term:
        ls = LayerSeparator()
        left = ls.separate(self.left)
        right = ls.separate(self.right)
        return ls.build(lambda layer: BinOp(self.location, layer(left), self.op, layer(right)))

    @override
    def codegen_expr(self) -> ast.expr:
        op = ast.BinOp(self.left.codegen_expr(), BIN_OP_MAP[self.op], self.right.codegen_expr())
        self.locate(op)
        return op


@dataclass(frozen=True)
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
    def separate(self) -> Term:
        ls = LayerSeparator()
        left = ls.separate(self.left)
        comparators = [ls.separate(v) for v in self.comparators]
        return ls.build(lambda layer: Compare(self.location, layer(left), self.ops, [layer(v) for v in comparators]))

    @override
    def codegen_expr(self) -> ast.expr:
        compare = ast.Compare(
            self.left.codegen_expr(),
            [COMPARE_OP_MAP[op] for op in self.ops],
            [v.codegen_expr() for v in self.comparators],
        )
        self.locate(compare)
        return compare


@dataclass(frozen=True)
class Call(TermWithLocation):
    func: Term
    args: list[Term]
