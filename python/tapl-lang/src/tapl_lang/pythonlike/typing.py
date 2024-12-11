# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass

from tapl_lang.syntax import Term


@dataclass
class Type(Term):
    name: str


Any = Type('Any')
Nothing = Type('Nothing')
NoneType = Type('None')


Bool = Type('Bool')
Int = Type('Int')
Float = Type('Float')
Complex = Type('Complex')
Str = Type('Str')
Tuple = Type('Tuple')
Bytes = Type('Bytes')
List = Type('List')
ByteArray = Type('ByteArray')
Set = Type('Set')
FrozenSet = Type('FrozenSet')
Dict = Type('Dictionary')
