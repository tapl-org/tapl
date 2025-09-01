# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import proxy, scope, types


def create_function(parameters, result):
    func = types.Function(parameters=parameters, result=result)
    return proxy.Proxy(func)


predef_scope = scope.Scope(label='predef_scope')
predef_scope.store_many(types.BUILTIN)
predef_scope.store_many(
    {
        # TODO: move these to types module
        'create_union': types.create_union,
        'Function': create_function,
        'print__tapl': print,
        # 'print': typelib.FunctionType(lock: A)
    }
)

predef_proxy = proxy.Proxy(predef_scope)
