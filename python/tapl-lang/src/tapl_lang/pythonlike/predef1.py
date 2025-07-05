# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.core import scope, typelib

NoneType = typelib.NoneType_
Bool = typelib.Bool_
Int = typelib.Int_
Str = typelib.Str_
Union = typelib.Union
create_union = typelib.create_union
FunctionType = typelib.FunctionType
function_type = typelib.function_type


Scope = scope.Scope
ScopeForker = scope.ScopeForker
add_return_type = scope.add_return_type
get_return_type = scope.get_return_type
predef_scope = scope.Scope(parent__tapl=None, label__tapl='predef_scope')
predef_scope.internal__tapl.variables.update(
    {
        'NoneType': typelib.NoneType_,
        'Bool': typelib.Bool_,
        'Int': typelib.Int_,
        'Float': typelib.Float_,
        'Str': typelib.Str_,
        'Union': typelib.Union,
        'create_union': typelib.create_union,
        'FunctionType': typelib.FunctionType,
        'function_type': typelib.function_type,
        'print__tapl': print,
    }
)


# TODO: remove once the class initialization is implemented
def init_class(self):
    return self
