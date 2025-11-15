# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import proxy, typelib


def _validate_type(param):
    if isinstance(param, proxy.ProxyMixin):
        return param
    raise TypeError(f'Unexpected parameter type: {type(param)}')


def _split_args(params):
    posonlyargs = []
    args = []
    tuple_found = False
    for p in params:
        if isinstance(p, tuple):
            tuple_found = True
            args.append((p[0], _validate_type(p[1])))
        elif not tuple_found:
            posonlyargs.append(_validate_type(p))
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
        func = typelib.Function(posonlyargs=posonlyargs, args=args, result=_validate_type(result))
        fields[name] = proxy.ProxyMixin(func)
    return fields


def _init_record(type_name, methods):
    record = typelib.Record(fields=_init_methods(methods), title=type_name)
    object.__setattr__(Types[type_name], proxy.SUBJECT_FIELD_NAME, record)


Types = {
    'Any': proxy.ProxyMixin(typelib.Any()),
    'Nothing': proxy.ProxyMixin(typelib.Nothing()),
    'NoneType': proxy.ProxyMixin(typelib.NoneType()),
    'Bool': proxy.ProxyMixin(typelib.Interim()),
    'Int': proxy.ProxyMixin(typelib.Interim()),
    'Float': proxy.ProxyMixin(typelib.Interim()),
    'Str': proxy.ProxyMixin(typelib.Interim()),
}
TypeConstructors = {}


Any = Types['Any']
Nothing = Types['Nothing']
NoneType = Types['NoneType']
Bool = Types['Bool']
Int = Types['Int']
Float = Types['Float']
Str = Types['Str']


_init_record('Bool', {'__lt__': ([Bool], Bool), '__gt__': ([Bool], Bool)})
_init_record(
    'Int',
    {
        '__add__': ([Int], Int),
        '__sub__': ([Int], Int),
        '__mul__': ([Int], Int),
        '__truediv__': ([Int], Float),
        '__mod__': ([Int], Int),
        '__floordiv__': ([Int], Int),
        '__ne__': ([Int], Bool),
        '__lt__': ([Int], Bool),
    },
)
_init_record(
    'Float',
    {
        '__add__': ([Float], Float),
        '__sub__': ([Float], Float),
        '__mul__': ([Float], Float),
        '__lt__': ([Float], Bool),
        '__gt__': ([Float], Bool),
    },
)
_init_record('Str', {'isalpha': ([], Bool), 'isdigit': ([], Bool)})


def create_list_type(element_type: proxy.ProxyMixin) -> proxy.ProxyMixin:
    methods = {
        'append': ([element_type], NoneType),
        '__len__': ([], Int),
    }
    list_type = typelib.Record(
        fields=_init_methods(methods),
        title=f'List[{element_type}]',
    )
    return proxy.ProxyMixin(list_type)


TypeConstructors['List'] = create_list_type
