# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass

from tapl_lang.syntax import Term


@dataclass
class Constant(Term):
    value: int

    def separable(self) -> bool:
        return False


@dataclass
class BinOp(Term):
    left: Term
    op: ast.operator
    right: Term

    def separable(self) -> bool:
        return False
