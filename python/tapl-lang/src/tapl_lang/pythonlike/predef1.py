# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.core import scope, typelib

NoneType = scope.NoneType
Bool = typelib.Bool_
Int = typelib.Int_
Str = typelib.Str_
Union = typelib.Union
create_union = typelib.create_union
FunctionType = typelib.FunctionType


predef_scope = scope.Scope(label='predef_scope')
predef_scope.store_many(
    {
        'NoneType': NoneType,
        'Bool': typelib.Bool_,
        'Int': typelib.Int_,
        'Float': typelib.Float_,
        'Str': typelib.Str_,
        'Union': typelib.Union,
        'create_union': typelib.create_union,
        'FunctionType': typelib.FunctionType,
        'print__tapl': print,
        # 'print': typelib.FunctionType(lock: A)
    }
)


# TODO: remove once the class initialization is implemented
def init_class(self):
    return self
