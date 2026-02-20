# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

from tapl_lang.lib import builtin_types as bt
from tapl_lang.lib import kinds, tapl_typing


def noop(*args, **kwargs):
    del args, kwargs


python_builtin_types = {
    '__name__': bt.Str,
    'print': kinds.create_function([bt.Any], bt.NoneType),
    'range': kinds.create_function([bt.Int], [bt.Int]),
    'str': kinds.create_function([bt.Any], bt.Str),
    'abs': kinds.create_function([bt.Float], bt.Float),
    'round': kinds.create_function([bt.Float], bt.Float),
}

pythonlike_builtins = {
    'tapl_typing': (tapl_typing, tapl_typing),
}

export: dict[str, Any] = {k: v[0] for k, v in pythonlike_builtins.items()}
export1: dict[str, Any] = {k: v[1] for k, v in pythonlike_builtins.items()}
export1.update(python_builtin_types)

# Export all builtin types for both layers.
# `type` on the Type layer is used for type checking.
# `type` on the Value layer is used for operations on type instances.
export.update(bt.Types)
export1.update(bt.Types)

# Export type constructors for type level layer
# export.update(bt.TYPE_CONSTRUCTORS)
export1.update(bt.TYPE_CONSTRUCTORS)
