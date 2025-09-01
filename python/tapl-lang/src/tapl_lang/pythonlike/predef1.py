# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import api, builtin, proxy, scope, typelib


def create_function(parameters, result):
    func = typelib.Function(parameters=parameters, result=result)
    return proxy.Proxy(func)


predef_scope = scope.Scope(label='predef_scope')
predef_scope.store_many(builtin.Types)
predef_scope.store_many(
    {
        'Function': create_function,
        'print__tapl': print,
        'api__tapl': api,
        # 'print': typelib.FunctionType(lock: A)
    }
)

predef_proxy = proxy.Proxy(predef_scope)
