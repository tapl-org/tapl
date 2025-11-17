# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import builtin_types, dynamic_attributes, scope, tapl_typing, typelib
from tapl_lang.pythonlike import builtin_functions


def create_function(parameters, result):
    func = typelib.Function(parameters=parameters, result=result)
    return dynamic_attributes.DynamicAttributeMixin(func)


predef_scope = scope.Scope(label='predef_scope')
predef_scope.store__sa('tapl_typing', tapl_typing)
predef_scope.store_many__sa(builtin_types.Types)
predef_scope.store_many__sa(builtin_functions.export1)
