# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any, override

from tapl_lang.syntax import (
    MODE_SAFE,
    MODE_TYPECHECK,
    ErrorTerm,
    Layers,
    LayerSeparator,
    Location,
    Term,
    TypedExpression,
    get_scope_name,
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
# TODO: add class with static fields for the context keys
EXPR_CONTEXT_MAP: dict[str, ast.expr_context] = {'load': ast.Load(), 'store': ast.Store(), 'delete': ast.Del()}


@dataclass
class Constant(Term):
    location: Location
    value: Any

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda _: Constant(location=self.location, value=self.value))

    @override
    def codegen_expr(self) -> ast.expr:
        const = ast.Constant(self.value)
        self.location.locate(const)
        return const


@dataclass
class Name(TypedExpression):
    location: Location
    id: str
    ctx: str

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return ls.build(lambda layer: Name(mode=layer(self.mode), location=self.location, id=self.id, ctx=self.ctx))

    @override
    def codegen_evaluate(self) -> ast.expr:
        name = ast.Name(id=self.id, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.location.locate(name)
        return name

    @override
    def codegen_typecheck(self) -> ast.expr:
        scope = ast.Name(id=get_scope_name(), ctx=ast.Load())
        attr = ast.Attribute(value=scope, attr=self.id, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.location.locate(scope, scope, attr)
        return attr


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
        return ls.build(
            lambda layer: Attribute(location=self.location, value=layer(self.value), attr=self.attr, ctx=self.ctx)
        )

    # TODO: Attribute must have a type layer to check attribute exists or not
    @override
    def codegen_expr(self) -> ast.expr:
        attr = ast.Attribute(self.value.codegen_expr(), attr=self.attr, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.location.locate(attr)
        return attr


@dataclass
class Literal(Term):
    location: Location

    @override
    def gather_errors(self, error_bucket: list[ErrorTerm]) -> None:
        pass

    def typeit(self, ls: LayerSeparator, value: Any, type_id: str) -> Layers:
        if ls.layer_count != len(MODE_SAFE.layers):
            raise ValueError('NoneLiteral must be separated in 2 layers')
        return Layers(
            [
                Constant(location=self.location, value=value),
                Name(mode=MODE_TYPECHECK, location=self.location, id=type_id, ctx='load'),
            ]
        )


@dataclass
class NoneLiteral(Literal):
    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return self.typeit(ls, value=None, type_id='NoneType')


@dataclass
class BooleanLiteral(Literal):
    value: bool

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return self.typeit(ls, value=self.value, type_id='Bool')


@dataclass
class IntegerLiteral(Literal):
    value: int

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return self.typeit(ls, value=self.value, type_id='Int')


@dataclass
class StringLiteral(Literal):
    value: str

    @override
    def separate(self, ls: LayerSeparator) -> Layers:
        return self.typeit(ls, value=self.value, type_id='Str')


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
        return ls.build(lambda layer: UnaryOp(location=self.location, op=self.op, operand=layer(self.operand)))

    @override
    def codegen_expr(self) -> ast.expr:
        operand = self.operand.codegen_expr()
        unary = ast.UnaryOp(UNARY_OP_MAP[self.op], operand)
        self.location.locate(unary)
        return unary


@dataclass
class BoolNot(TypedExpression):
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
        bool_type = Name(mode=MODE_TYPECHECK, location=self.location, id='Bool', ctx='load')
        return bool_type.codegen_expr()


@dataclass
class BoolOp(TypedExpression):
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
