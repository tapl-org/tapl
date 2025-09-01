# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import proxy, typelib


def _init_record(type_name, methods):
    """Initialize a new type with the given name and methods.
    type_name: The name of the type.
    methods: list[tuple[str, list[str|list[str]], str]]: A list of methods for the type, where each method is represented as a tuple
    of (name, parameters, result). parameters are list of types which are represented as string or union of strings.
    """
    labels = []
    for name, params, result in methods:
        for i in range(len(params)):
            if isinstance(params[i], str):
                params[i] = Types[params[i]]
            else:
                params[i] = typelib.create_union(*(Types[p] for p in params[i]))
        func = typelib.Function(parameters=params, result=Types[result])
        labels.append(typelib.Labeled(name, proxy.Proxy(func)))
    record = typelib.Intersection(types=[proxy.Proxy(label) for label in labels], title=type_name)
    object.__setattr__(Types[type_name], proxy.SUBJECT_FIELD_NAME, record)


class FalseSubject(proxy.Subject):
    @property
    def kind(self):
        return typelib.Kind.Intersection


Types = {
    'Any': proxy.Proxy(typelib.Any()),
    'Nothing': proxy.Proxy(typelib.Nothing()),
    'NoneType': proxy.Proxy(typelib.NoneType()),
    'Bool': proxy.Proxy(FalseSubject()),
    'Int': proxy.Proxy(FalseSubject()),
    'Float': proxy.Proxy(FalseSubject()),
    'Str': proxy.Proxy(FalseSubject()),
}

_init_record('Bool', [['__lt__', ['Bool'], 'Bool'], ['__gt__', ['Bool'], 'Bool']])
_init_record('Int', [['__add__', ['Int'], 'Int'], ['__lt__', ['Int'], 'Bool']])
_init_record(
    'Float',
    [
        ['__add__', ['Float'], 'Float'],
        ['__mul__', ['Float'], 'Float'],
        ['__lt__', ['Float'], 'Bool'],
        ['__gt__', ['Float'], 'Bool'],
    ],
)
_init_record('Str', [['isalpha', [], 'Bool'], ['isdigit', [], 'Bool']])
