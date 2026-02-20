# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import types

log = print


def describe(value):
    if isinstance(value, types.FunctionType):
        return f'<function {value.__name__}>'
    return str(value)
