# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

from tapl_lang.lib import builtin_types as bt
from tapl_lang.lib import kinds

python_builtin_types = {
    '__name__': bt.Str,
    'print': kinds.create_function([bt.Any], bt.NoneType),
    'range': kinds.create_function([bt.Int], [bt.Int]),
    'str': kinds.create_function([bt.Any], bt.Str),
    'abs': kinds.create_function([bt.Float], bt.Float),
    'round': kinds.create_function([bt.Float], bt.Float),
}

export1: dict[str, Any] = {}
export1.update(python_builtin_types)
export1.update(bt.Types)
export1.update(bt.TYPE_CONSTRUCTORS)
