# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import api, builtin_types, proxy, scope, typelib
from tapl_lang.pythonlike import builtin_functions


def create_function(parameters, result):
    func = typelib.Function(parameters=parameters, result=result)
    return proxy.Proxy(func)


predef_scope = scope.Scope(label='predef_scope')
# TODO: rename 'api__tapl' to 'tapl_api', and change doc saying that all Tapl names are prefixed with 'tapl_', please don't use tapl_ prefix for other things. #mvp
# Maybe api__tapl is better then tapl_api. Decide which one to choose.
predef_scope.store('api__tapl', api)
predef_scope.store_many(builtin_types.Types)
predef_scope.store_many(builtin_functions.export1)

predef_proxy = proxy.Proxy(predef_scope)
