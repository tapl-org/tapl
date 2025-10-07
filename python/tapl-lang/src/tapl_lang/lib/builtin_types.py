# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import proxy, typelib


def _fix_type(param):
    if isinstance(param, proxy.Proxy):
        return param
    if isinstance(param, str):
        return Types[param]
    if isinstance(param, list):
        return typelib.create_union(*(Types[p] for p in param))
    raise TypeError(f'Unexpected parameter type: {type(param)}')


def _init_record(type_name, methods):
    """Initialize a new type with the given name and methods.
    type_name: The name of the type.
    methods: list[tuple[str, list[str|list[str]], str]]: A list of methods for the type, where each method is represented as a tuple
    of (name, parameters, result). parameters are list of types which are represented as string or union of strings.
    """
    labels = []
    for name, params, result in methods:
        for i in range(len(params)):
            params[i] = _fix_type(params[i])
        func = typelib.Function(parameters=params, result=_fix_type(result))
        labels.append(typelib.Labeled(name, proxy.Proxy(func)))
    record = typelib.Intersection(types=[proxy.Proxy(label) for label in labels], title=type_name)
    object.__setattr__(Types[type_name], proxy.SUBJECT_FIELD_NAME, record)


Types = {
    'Any': proxy.Proxy(typelib.Any()),
    'Nothing': proxy.Proxy(typelib.Nothing()),
    'NoneType': proxy.Proxy(typelib.NoneType()),
    'Bool': proxy.Proxy(typelib.Interim()),
    'Int': proxy.Proxy(typelib.Interim()),
    'Float': proxy.Proxy(typelib.Interim()),
    'Str': proxy.Proxy(typelib.Interim()),
    'ListInt': proxy.Proxy(typelib.Interim()),
}


Any = Types['Any']
Nothing = Types['Nothing']
NoneType = Types['NoneType']
Bool = Types['Bool']
Int = Types['Int']
Float = Types['Float']
Str = Types['Str']
ListInt = Types['ListInt']

_init_record('Bool', [['__lt__', [Bool], Bool], ['__gt__', [Bool], Bool]])
_init_record(
    'Int',
    [
        ['__add__', [Int], Int],
        ['__sub__', [Int], Int],
        ['__mul__', [Int], Int],
        ['__truediv__', [Int], Float],
        ['__mod__', [Int], Int],
        ['__floordiv__', [Int], Int],
        ['__ne__', [Int], Bool],
        ['__lt__', [Int], Bool],
    ],
)
_init_record(
    'Float',
    [
        ['__add__', [Float], Float],
        ['__sub__', [Float], Float],
        ['__mul__', [Float], Float],
        ['__lt__', [Float], Bool],
        ['__gt__', [Float], Bool],
    ],
)
_init_record('Str', [['isalpha', [], Bool], ['isdigit', [], Bool]])
_init_record('ListInt', [['append', [Int], NoneType], ['__len__', [], Int]])
