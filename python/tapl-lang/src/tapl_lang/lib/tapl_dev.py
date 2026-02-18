# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import types

from tapl_lang.lib import tapl_typing


class TaplDev:
    def __init__(self) -> None:
        self.print = print
        self.typing = tapl_typing

    def to_string(self, value) -> str:
        if isinstance(value, types.FunctionType):
            return f'<function {value.__name__}>'
        return str(value)
