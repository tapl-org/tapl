# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any

from tapl_lang.syntax import Term, Layers, LayerSeparator, Location, TermWithLocation, MODE_EVALUATE, MODE_TYPECHECK
from tapl_lang.tapl_error import TaplError
from tapl_lang import types


def with_location(tree: ast.expr, loc: Location) -> ast.expr:
    if loc.start:
        tree.lineno = loc.start.line
        tree.col_offset = loc.start.column
    if loc.end:
        tree.end_lineno = loc.end.line
        tree.end_col_offset = loc.end.column
    return tree

@dataclass
class Constant(TermWithLocation):
    value: Any

    def has_error(self) -> bool:
        return False
    
    def separate(self) -> Term:
        return self
    
    def codegen(self) -> ast.AST:
        return with_location(ast.Constant(self.value), self.location)


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
        layers: list[Term] = []
        for i in range(separator.layer_count):
            operand = separator.extract_layer(i, self.operand)
            mode = separator.extract_layer(i, self.mode)
            layers.append(UnaryOp(self.location, op=self.op, operand=operand, mode=mode))
        return Layers(layers)
    
    def codegen(self) -> ast.AST:
        if self.mode is MODE_EVALUATE:
            return with_location(ast.UnaryOp(self.op, self.operand.codegen()), self.location)
        elif self.mode is MODE_TYPECHECK:
            return with_location(ast.Compare(left=self.operand.codegen(), ops=[ast.Eq()], comparators=ast.Constant(value=types.Bool)))
        raise TaplError(f'Run mode not found. {self.mode}')



@dataclass
class BoolOp(TermWithLocation):
    op: ast.boolop
    values: list[Term]
    mode: Term = MODE_EVALUATE

    def has_error(self) -> bool:
        return any(v.has_error() for v in self.values) or self.mode.has_error()
    
    def separate(self):
        separator = LayerSeparator()
        for i in range(len(self.values)):
            self.values[i] = separator.separate(self.values[i])
        self.mode = separator.separate(self.mode)
        if separator.layer_count == 1:
            return self
        layers: list[Term] = []
        for i in range(separator.layer_count):
            values = [separator.extract_layer(i, v) for v in self.values]
            mode = separator.extract_layer(i, self.mode)
            layers.append(BoolOp(self.location, op=self.op, values=values, mode=mode))
        return Layers(layers)
    
    def codegen(self) -> ast.AST:
        if self.mode is MODE_EVALUATE:
            return with_location(ast.BoolOp(self.op, [v.codegen() for v in self.vals]), self.location)
        elif self.mode is MODE_TYPECHECK:
            return 'all(v == Bool for v in values)'
        raise TaplError(f'Run mode not found. {self.mode}')


