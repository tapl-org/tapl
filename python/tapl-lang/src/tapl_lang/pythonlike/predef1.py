# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang import scope, typelib

NoneType = typelib.NoneType_
Bool = typelib.Bool_
Int = typelib.Int_
Str = typelib.Str_
Union = typelib.Union
create_union = typelib.create_union
FunctionType = typelib.FunctionType
function_type = typelib.function_type


@function_type(Int)
def int_print(s):
    del s
    return NoneType


Scope = scope.Scope
predef_scope = scope.Scope()
predef_scope.internal__tapl.variables.update(
    {
        'NoneType': typelib.NoneType_,
        'Bool': typelib.Bool_,
        'Int': typelib.Int_,
        'Str': typelib.Str_,
        'Union': typelib.Union,
        'create_union': typelib.create_union,
        'FunctionType': typelib.FunctionType,
        'function_type': typelib.function_type,
        'int_print': int_print,
    }
)
