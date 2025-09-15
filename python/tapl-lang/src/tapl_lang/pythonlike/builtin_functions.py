# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import builtin_types, typelib

functions = {
    'print': (
        print,
        typelib.create_function(parameters=[builtin_types.Any], result=builtin_types.NoneType),
    )
}


export = {k: v[0] for k, v in functions.items()}
export1 = {k: v[1] for k, v in functions.items()}
