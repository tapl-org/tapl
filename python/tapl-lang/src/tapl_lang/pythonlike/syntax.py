# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any

from tapl_lang import typelib
from tapl_lang.syntax import MODE_EVALUATE, MODE_TYPECHECK, Layers, LayerSeparator, Location, Term, TermWithLocation
from tapl_lang.tapl_error import TaplError


def with_location(tree: ast.expr, loc: Location) -> ast.expr:
    if loc.start:
        tree.lineno = loc.start.line
        tree.col_offset = loc.start.column
    if loc.end:
        tree.end_lineno = loc.end.line
        tree.end_col_offset = loc.end.column
    return tree


def create_ast_typelib_attribute(attr: str) -> ast.expr:
    return ast.Attribute(ast.Name(id='typelib', ctx=ast.Load()), attr=attr, ctx=ast.Load())


def create_ast_typelib_call(function_name: str, args: list[ast.expr]) -> ast.expr:
    return ast.Call(func=create_ast_typelib_attribute(function_name), args=args)


@dataclass
class Constant(TermWithLocation):
    value: Any

    def has_error(self) -> bool:
        return False

    def separate(self) -> Term:
        return self

    def codegen_expr(self) -> ast.expr:
        return with_location(ast.Constant(self.value), self.location)


@dataclass
class Name(TermWithLocation):
    id: str
    ctx: ast.expr_context

    def has_error(self):
        return False
    
    def separate(self):
        return self
    
    def codegen_expr(self):
        return with_location(ast.Name(id=self.id, ctx=self.ctx), self.location)


@dataclass
class Attribute(TermWithLocation):
    value: Term
    attr: str
    ctx: ast.expr_context

    def has_error(self):
        return self.value.has_error()

    def separate(self) -> Term:
        separator = LayerSeparator()
        self.value = separator.separate(self.value)
        if separator.layer_count == 1:
            return self
        layers: list[Term] = [
            Attribute(self.location, value=separator.extract_layer(i, self.value), attr=self.attr, ctx=self.ctx)
            for i in range(separator.layer_count)
        ]
        return Layers(layers)
    
    def codegen_expr(self) -> ast.expr:
        return with_location(ast.Attribute(self.value.codegen_expr(), attr=self.attr, ctx=self.ctx), self.location)


@dataclass
class UnaryOp(TermWithLocation):
    op: ast.unaryop
    operand: Term
    mode: Term

    def has_error(self):
        return self.operand.has_error() or self.mode.has_error()

    def separate(self) -> Term:
        separator = LayerSeparator()
        self.operand = separator.separate(self.operand)
        self.mode = separator.separate(self.mode)
        if separator.layer_count == 1:
            return self
        layers: list[Term] = [
            UnaryOp(
                self.location,
                op=self.op,
                operand=separator.extract_layer(i, self.operand),
                mode=separator.extract_layer(i, self.mode),
            )
            for i in range(separator.layer_count)
        ]
        return Layers(layers)

    def codegen_expr(self) -> ast.expr:
        if self.mode is MODE_EVALUATE:
            return with_location(ast.UnaryOp(self.op, self.operand.codegen_expr()), self.location)
        if self.mode is MODE_TYPECHECK:
            return with_location(create_ast_typelib_attribute('Bool'), self.location)
        raise TaplError(f'Layer mode not found. {self.mode}')


@dataclass
class BoolOp(TermWithLocation):
    op: ast.boolop
    values: list[Term]
    mode: Term

    def has_error(self) -> bool:
        return any(v.has_error() for v in self.values) or self.mode.has_error()

    def separate(self) -> Term:
        separator = LayerSeparator()
        for i in range(len(self.values)):
            self.values[i] = separator.separate(self.values[i])
        self.mode = separator.separate(self.mode)
        if separator.layer_count == 1:
            return self
        layers: list[Term] = [
            BoolOp(
                self.location,
                op=self.op,
                values=[separator.extract_layer(i, v) for v in self.values],
                mode=separator.extract_layer(i, self.mode),
            )
        ]
        return Layers(layers)

    def codegen(self) -> ast.AST:
        if self.mode is MODE_EVALUATE:
            return with_location(ast.BoolOp(self.op, [v.codegen_expr() for v in self.values]), self.location)
        if self.mode is MODE_TYPECHECK:
            return with_location(
                create_ast_typelib_call('create_union', [v.codegen_expr() for v in self.values]), self.location
            )
        raise TaplError(f'Run mode not found. {self.mode}')
