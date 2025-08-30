# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import proxy, scope, types

predef_scope = scope.Scope(label='predef_scope')
predef_scope.store_many(types.BUILTIN_PROXY)
predef_scope.store_many(
    {
        'create_union': types.create_union,
        'FunctionType': types.Function,
        'print__tapl': print,
        # 'print': typelib.FunctionType(lock: A)
    }
)

predef_proxy = proxy.Proxy(predef_scope)
