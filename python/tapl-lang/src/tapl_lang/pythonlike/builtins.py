# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import builtin_types as bt
from tapl_lang.lib import tapl_dev, tapl_typing, typelib


def noop(*args, **kwargs):
    del args, kwargs


python_builtin_types = {
    '__name__': bt.Str,
    'print': typelib.create_function([bt.Any], bt.NoneType),
    'range': typelib.create_function([bt.Int], [bt.Int]),
    'str': typelib.create_function([bt.Any], bt.Str),
    'abs': typelib.create_function([bt.Float], bt.Float),
    'round': typelib.create_function([bt.Float], bt.Float),
}

pythonlike_builtins = {
    'tapl_dev': (
        tapl_dev.TaplDev(tapl_dev.EVALATE_LAYER_INDEX),
        tapl_dev.TaplDev(tapl_dev.TYPECHECK_LAYER_INDEX),
    ),
    'tapl_typing': (None, tapl_typing),
}

export = {k: v[0] for k, v in pythonlike_builtins.items()}
export1 = {k: v[1] for k, v in pythonlike_builtins.items()}
export1.update(python_builtin_types)

# Export all builtin types as well, set to None in value level
export.update({k: None for k in bt.Types})
export1.update(bt.Types)
