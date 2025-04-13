# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any, override

from tapl_lang.syntax import (
    ErrorTerm,
    Layers,
    LayerSeparator,
    Location,
    ModeBasedExpression,
    Term,
)

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
EXPR_CONTEXT_MAP: dict[str, ast.expr_context] = {'load': ast.Load(), 'store': ast.Store(), 'delete': ast.Del()}


# TODO: create a separate term for each kind of literal, and make it mode based expression
@dataclass
class Constant(Term):
    location: Location
    value: Any

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.replicate(self)

    @override
    def codegen_expr(self) -> ast.expr:
        const = ast.Constant(self.value)
        self.location.locate(const)
        return const


@dataclass
class Name(Term):
    location: Location
    id: str
    ctx: str

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.replicate(self)

    @override
    def codegen_expr(self) -> ast.expr:
        name = ast.Name(id=self.id, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.location.locate(name)
        return name


@dataclass
class Attribute(Term):
    location: Location
    value: Term
    attr: str
    ctx: str

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.value.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Attribute(self.location, layer(self.value), self.attr, self.ctx))

    # TODO: Attribute must have a type layer to check attribute exists or not
    @override
    def codegen_expr(self) -> ast.expr:
        attr = ast.Attribute(self.value.codegen_expr(), attr=self.attr, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.location.locate(attr)
        return attr


@dataclass
class UnaryOp(Term):
    location: Location
    op: str
    operand: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.operand.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: UnaryOp(self.location, self.op, layer(self.operand)))

    @override
    def codegen_expr(self) -> ast.expr:
        operand = self.operand.codegen_expr()
        unary = ast.UnaryOp(UNARY_OP_MAP[self.op], operand)
        self.location.locate(unary)
        return unary


@dataclass
class BoolNot(ModeBasedExpression):
    location: Location
    operand: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.operand.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: BoolNot(mode=layer(self.mode), location=self.location, operand=layer(self.operand))
        )

    @override
    def codegen_evaluate(self):
        operand = self.operand.codegen_expr()
        unary = ast.UnaryOp(ast.Not(), operand)
        self.location.locate(unary)
        return unary

    @override
    def codegen_typecheck(self):
        # unary not operator always returns Bool type
        bool_type = ast.Name(id='Bool', ctx=ast.Load())
        self.location.locate(bool_type)
        return bool_type


@dataclass
class BoolOp(ModeBasedExpression):
    location: Location
    op: str
    values: list[Term]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        for v in self.values:
            v.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: BoolOp(
                mode=layer(self.mode), location=self.location, op=self.op, values=[layer(v) for v in self.values]
            )
        )

    @override
    def codegen_evaluate(self) -> ast.expr:
        op = ast.BoolOp(BOOL_OP_MAP[self.op], [v.codegen_expr() for v in self.values])
        self.location.locate(op)
        return op

    @override
    def codegen_typecheck(self) -> ast.expr:
        create_union = ast.Name(id='create_union', ctx=ast.Load())
        call = ast.Call(func=create_union, args=[v.codegen_expr() for v in self.values])
        self.location.locate(create_union, call)
        return call


@dataclass
class BinOp(Term):
    location: Location
    left: Term
    op: str
    right: Term

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.left.gather_errors(error_bucket)
        self.right.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: BinOp(location=self.location, left=layer(self.left), op=self.op, right=layer(self.right))
        )

    @override
    def codegen_expr(self) -> ast.expr:
        op = ast.BinOp(self.left.codegen_expr(), BIN_OP_MAP[self.op], self.right.codegen_expr())
        self.location.locate(op)
        return op


@dataclass
class Compare(Term):
    location: Location
    left: Term
    ops: list[str]
    comparators: list[Term]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.left.gather_errors(error_bucket)
        for v in self.comparators:
            v.gather_errors(error_bucket)

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(
            lambda layer: Compare(
                location=self.location,
                left=layer(self.left),
                ops=self.ops,
                comparators=[layer(v) for v in self.comparators],
            )
        )

    @override
    def codegen_expr(self) -> ast.expr:
        compare = ast.Compare(
            self.left.codegen_expr(),
            [COMPARE_OP_MAP[op] for op in self.ops],
            [v.codegen_expr() for v in self.comparators],
        )
        self.location.locate(compare)
        return compare


@dataclass
class Call(Term):
    location: Location
    func: Term
    args: list[Term]

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        self.func.gather_errors(error_bucket)
        for v in self.args:
            v.gather_errors(error_bucket)

    @override
    def separate(self, ls):
        return ls.build(
            lambda layer: Call(location=self.location, func=layer(self.func), args=[layer(v) for v in self.args])
        )

    @override
    def codegen_expr(self) -> ast.expr:
        call = ast.Call(self.func.codegen_expr(), [v.codegen_expr() for v in self.args])
        self.location.locate(call)
        return call
