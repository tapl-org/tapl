# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from dataclasses import dataclass
from typing import Any

from tapl_lang.syntax import Term


@dataclass
class Constant(Term):
    value: Any

    def separable(self) -> bool:
        return False


@dataclass
class BoolOp(Term):
    op: ast.boolop
    values: list[Term]

    def separable(self) -> bool:
        return False
