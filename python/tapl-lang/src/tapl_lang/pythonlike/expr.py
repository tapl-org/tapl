# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, override

from tapl_lang.core import syntax, tapl_error

# Unary 'not' has a dedicated 'BoolNot' term for logical negation
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
class Constant(syntax.Term):
    location: syntax.Location
    value: Any

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Constant(location=self.location, value=self.value))

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        const = ast.Constant(self.value)
        self.location.locate(const)
        return const


@dataclass
class Name(syntax.Term):
    location: syntax.Location
    id: str
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda _: Name(location=self.location, id=self.id, ctx=self.ctx))

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        if setting.scope_native:
            name = ast.Name(id=self.id, ctx=EXPR_CONTEXT_MAP[self.ctx])
            self.location.locate(name)
            return name
        if setting.scope_manual:
            scope = ast.Name(id=setting.scope_name, ctx=ast.Load())
            attr = ast.Attribute(value=scope, attr=self.id, ctx=EXPR_CONTEXT_MAP[self.ctx])
            self.location.locate(scope, scope, attr)
            return attr
        raise tapl_error.UnhandledError


@dataclass
class Attribute(syntax.Term):
    location: syntax.Location
    value: syntax.Term
    attr: str
    ctx: str

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.value

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Attribute(location=self.location, value=layer(self.value), attr=self.attr, ctx=self.ctx)
        )

    # TODO: Attribute must have a type layer to check attribute exists or not. find a test case first
    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        attr = ast.Attribute(self.value.codegen_expr(setting), attr=self.attr, ctx=EXPR_CONTEXT_MAP[self.ctx])
        self.location.locate(attr)
        return attr


@dataclass
class Literal(syntax.Term):
    location: syntax.Location

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from ()

    def typeit(self, ls: syntax.LayerSeparator, value: Any, type_id: str) -> list[syntax.Term]:
        if ls.layer_count != syntax.SAFE_LAYER_COUNT:
            raise ValueError('NoneLiteral must be separated in 2 layers')
        return [
            Constant(location=self.location, value=value),
            Name(location=self.location, id=type_id, ctx='load'),
        ]


@dataclass
class NoneLiteral(Literal):
    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=None, type_id='NoneType')


@dataclass
class BooleanLiteral(Literal):
    value: bool

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Bool')


@dataclass
class IntegerLiteral(Literal):
    value: int

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Int')


@dataclass
class FloatLiteral(Literal):
    value: float

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Float')


@dataclass
class StringLiteral(Literal):
    value: str

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return self.typeit(ls, value=self.value, type_id='Str')


@dataclass
class UnaryOp(syntax.Term):
    location: syntax.Location
    op: str
    operand: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.operand

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: UnaryOp(location=self.location, op=self.op, operand=layer(self.operand)))

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        operand = self.operand.codegen_expr(setting)
        unary = ast.UnaryOp(UNARY_OP_MAP[self.op], operand)
        self.location.locate(unary)
        return unary


@dataclass
class BoolNot(syntax.Term):
    location: syntax.Location
    operand: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.operand

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(lambda layer: BoolNot(location=self.location, operand=layer(self.operand)))

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        if setting.code_evaluate:
            operand = self.operand.codegen_expr(setting)
            unary = ast.UnaryOp(ast.Not(), operand)
            self.location.locate(unary)
            return unary
        if setting.code_typecheck:
            # unary not operator always returns Bool type
            bool_type = Name(location=self.location, id='Bool', ctx='load')
            return bool_type.codegen_expr(setting)
        raise tapl_error.UnhandledError


@dataclass
class BoolOp(syntax.Term):
    location: syntax.Location
    op: str
    values: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield from self.values

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BoolOp(location=self.location, op=self.op, values=[layer(v) for v in self.values])
        )

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        if setting.code_evaluate:
            op = ast.BoolOp(BOOL_OP_MAP[self.op], [v.codegen_expr(setting) for v in self.values])
            self.location.locate(op)
            return op
        if setting.code_typecheck:
            create_union = ast.Name(id='create_union', ctx=ast.Load())
            call = ast.Call(func=create_union, args=[v.codegen_expr(setting) for v in self.values])
            self.location.locate(create_union, call)
            return call
        raise tapl_error.UnhandledError


@dataclass
class BinOp(syntax.Term):
    location: syntax.Location
    left: syntax.Term
    op: str
    right: syntax.Term

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.left
        yield self.right

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: BinOp(location=self.location, left=layer(self.left), op=self.op, right=layer(self.right))
        )

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        op = ast.BinOp(self.left.codegen_expr(setting), BIN_OP_MAP[self.op], self.right.codegen_expr(setting))
        self.location.locate(op)
        return op


@dataclass
class Compare(syntax.Term):
    location: syntax.Location
    left: syntax.Term
    ops: list[str]
    comparators: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.left
        yield from self.comparators

    @override
    def separate(self, ls: syntax.LayerSeparator) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Compare(
                location=self.location,
                left=layer(self.left),
                ops=self.ops,
                comparators=[layer(v) for v in self.comparators],
            )
        )

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        compare = ast.Compare(
            self.left.codegen_expr(setting),
            [COMPARE_OP_MAP[op] for op in self.ops],
            [v.codegen_expr(setting) for v in self.comparators],
        )
        self.location.locate(compare)
        return compare


@dataclass
class Call(syntax.Term):
    location: syntax.Location
    func: syntax.Term
    args: list[syntax.Term]

    @override
    def children(self) -> Generator[syntax.Term, None, None]:
        yield self.func
        yield from self.args

    @override
    def separate(self, ls) -> list[syntax.Term]:
        return ls.build(
            lambda layer: Call(location=self.location, func=layer(self.func), args=[layer(v) for v in self.args])
        )

    @override
    def codegen_expr(self, setting: syntax.AstSetting) -> ast.expr:
        call = ast.Call(self.func.codegen_expr(setting), [v.codegen_expr(setting) for v in self.args])
        self.location.locate(call)
        return call
