# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import builtin_types as bt
from tapl_lang.lib import typelib


def noop(*args, **kwargs):
    del args, kwargs


functions = {
    'print': (
        print,
        typelib.create_function([bt.Any], bt.NoneType),
    ),
    'print_type': (
        noop,
        print,
    ),
    'range': (
        range,
        typelib.create_function([bt.Int], [bt.Int]),
    ),
    'str': (
        str,
        typelib.create_function([bt.Any], bt.Str),
    ),
}


export = {k: v[0] for k, v in functions.items()}
export1 = {k: v[1] for k, v in functions.items()}
