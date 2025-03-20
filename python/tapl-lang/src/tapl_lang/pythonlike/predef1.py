# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang import typelib

NoneType = typelib.NoneType_
Bool = typelib.Bool_
Int = typelib.Int_
Str = typelib.Str_
Union = typelib.Union
create_union = typelib.create_union
FunctionType = typelib.FunctionType
function_type = typelib.function_type

del typelib
