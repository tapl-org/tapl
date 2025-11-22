# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import typelib

Types = {
    'Any': typelib.Any(),
    'Nothing': typelib.Nothing(),
    'NoneType': typelib.NoneType(),
    'Bool': typelib.Record(fields={}, title='Bool'),
    'Int': typelib.Record(fields={}, title='Int'),
    'Float': typelib.Record(fields={}, title='Float'),
    'Str': typelib.Record(fields={}, title='Str'),
}

Any = Types['Any']
Nothing = Types['Nothing']
NoneType = Types['NoneType']
Bool = Types['Bool']
Int = Types['Int']
Float = Types['Float']
Str = Types['Str']


def _split_args(params):
    posonlyargs = []
    args = []
    tuple_found = False
    for p in params:
        if isinstance(p, tuple):
            tuple_found = True
            args.append((p[0], p[1]))
        elif not tuple_found:
            posonlyargs.append(p)
        else:
            raise ValueError('Positional-only arguments must come before regular arguments')
    return posonlyargs, args


def _init_methods(methods):
    """Create a dict of methods for the type with the given method template.
    methods: dict[str, tuple[list[str|list[str]], str]]: A list of methods for the type, where each method is represented as a tuple
    of (name, parameters, result). parameters are list of types which are represented as string or union of strings.
    """
    fields = {}
    for name, (params, result) in methods.items():
        posonlyargs, args = _split_args(params)
        fields[name] = typelib.Function(posonlyargs=posonlyargs, args=args, result=result)
    return fields


def _init_record(record, methods):
    object.__setattr__(record, '_fields__sa', _init_methods(methods))


_init_record(
    Bool, {'__hash__sa': ([], Int), '__eq__sa': ([Bool], Bool), '__lt__': ([Bool], Bool), '__gt__': ([Bool], Bool)}
)
_init_record(
    Int,
    {
        '__hash__sa': ([], Int),
        '__add__': ([Int], Int),
        '__sub__': ([Int], Int),
        '__mul__': ([Int], Int),
        '__truediv__': ([Int], Float),
        '__mod__': ([Int], Int),
        '__floordiv__': ([Int], Int),
        '__eq__sa': ([Int], Bool),
        '__ne__': ([Int], Bool),
        '__lt__': ([Int], Bool),
        '__gt__': ([Int], Bool),
        '__ge__': ([Int], Bool),
        '__le__': ([Int], Bool),
    },
)
_init_record(
    Float,
    {
        '__hash__sa': ([], Int),
        '__add__': ([Float], Float),
        '__sub__': ([Float], Float),
        '__mul__': ([Float], Float),
        '__eq__sa': ([Float], Bool),
        '__ne__': ([Float], Bool),
        '__lt__': ([Float], Bool),
        '__gt__': ([Float], Bool),
        '__ge__': ([Float], Bool),
        '__le__': ([Float], Bool),
    },
)
_init_record(Str, {'__hash__sa': ([], Int), '__eq__sa': ([Str], Bool), 'isalpha': ([], Bool), 'isdigit': ([], Bool)})


def create_list_type(element_type):
    methods = {
        'append': ([element_type], NoneType),
        '__len__': ([], Int),
        '__getitem__': ([Int], element_type),
        '__setitem__': ([Int, element_type], NoneType),
        '__delitem__': ([Int], NoneType),
    }
    return typelib.Record(
        fields=_init_methods(methods),
        title=f'List[{element_type}]',
    )


def create_dict_type(key_type, value_type):
    methods = {
        'get': ([key_type], value_type),
        'set': ([key_type, value_type], NoneType),
        'delete': ([key_type], NoneType),
        '__len__': ([], Int),
        '__getitem__': ([key_type], value_type),
        '__setitem__': ([key_type, value_type], NoneType),
        '__delitem__': ([key_type], NoneType),
    }
    return typelib.Record(
        fields=_init_methods(methods),
        title=f'Dict[{key_type}, {value_type}]',
    )


# TODO: Enable type constructors when needed.
# TypeConstructors = {}
# TypeConstructors['List'] = create_list_type
# TypeConstructors['Dict'] = create_dict_type
