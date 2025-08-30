# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
Type system has mainly six types: Atom, Labeled, Union, Intersection, Function, and Recursive.

Atom type is the most basic type, most primitive type.

Labeled type unifies single labeled record and labeled variant.

Atom type looks like a nominal type. Because it has only name, nothing else.
Record type can be defined as a intersection of several labeled types.
Sum type can be defined as a union of several labeled types.

If we see from the Java class perspective then its type is intersection of record type and base type which has a name

Since Atom type contains a string, we can generalize it such that it can contain any value unless it has a equal property

Top or Any type is a empty Intersection type
Bottom or Nothing type is a empty Union type

Labels must be unique in Intersection and Union type.

The following does not use Python type hints intentionally.
"""

from tapl_lang.core import tapl_error
from tapl_lang.lib import proxy


class Atom:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return str(self.name)


class Labeled:
    def __init__(self, label, typ):
        self.label = label
        self.type = typ

    def __repr__(self):
        return f'{self.label}={self.type}'


def check_unique_labels(types):
    seen_labels = set()
    for t in types:
        if isinstance(t, Labeled):
            if t.label in seen_labels:
                raise ValueError(f'Duplicate label found: {t.label}')
            seen_labels.add(t.label)


class Union:
    def __init__(self, types, title=None):
        check_unique_labels(types)
        self.types = types
        self.title = title

    def __repr__(self):
        if self.title is not None:
            return self.title
        if len(self.types) == 0:
            return 'Nothing'
        if len(self.types) <= 1 or any(isinstance(t, Labeled) for t in self.types):
            return '[{}]'.format(', '.join([str(t) for t in self.types]))
        return ' | '.join([str(t) for t in self.types])

    def find_label(self, label):
        for t in self.types:
            if isinstance(t, Labeled) and t.label == label:
                return t
        return None


class Intersection:
    def __init__(self, types, title=None):
        check_unique_labels(types)
        self.types = types
        self.title = title

    def __repr__(self):
        if self.title is not None:
            return self.title
        if len(self.types) == 0:
            return 'Any'
        if len(self.types) <= 1 or any(isinstance(t, Labeled) for t in self.types):
            return '{{{}}}'.format(', '.join([str(t) for t in self.types]))
        return ' & '.join([str(t) for t in self.types])

    def find_label(self, label):
        for t in self.types:
            if isinstance(t, Labeled) and t.label == label:
                return t
        return None


def process_parameters(params):
    labeled_parameter_seen = False
    for i in range(len(params)):
        if isinstance(params[i], Labeled):
            labeled_parameter_seen = True
        elif labeled_parameter_seen:
            raise tapl_error.TaplError('SyntaxError: positional parameter follows labeled parameter.')
        else:
            params[i] = Labeled(str(i), params[i])

    return Intersection(types=params)


class Function:
    def __init__(self, parameters, result):
        if not isinstance(parameters, list):
            raise tapl_error.TaplError('SyntaxError: Function parameters must be a list.')
        self.parameters = process_parameters(parameters[:])
        self.result = result

    def __repr__(self):
        return f'{self.parameters}->{self.result}'

    def fix_labels(self, arguments):
        for i in range(len(arguments)):
            if isinstance(arguments[i], Labeled):
                break
            arguments[i] = Labeled(self.parameters.types[i].label, arguments[i])

    def __call__(self, *arguments):
        args = Intersection(types=self.fix_labels(list(arguments)))
        if is_subtype(subtype=args, supertype=self.parameters):
            raise TypeError(f'Not equal: parameters={self.parameters} arguments={args}')
        return self.result


def is_subtype(subtype, supertype):
    if subtype == supertype:
        return True
    if isinstance(subtype, Intersection) and isinstance(supertype, Intersection):
        for super_element in supertype.types:
            if isinstance(super_element, Labeled):
                sub_element = subtype.find_label(super_element.label)
                if sub_element is None or not is_subtype(sub_element.type, super_element.type):
                    return False
            else:
                raise tapl_error.TaplError(f'Unsupported-1 subtype check for subtype={subtype} supertype={supertype}.')
        return True
    if isinstance(subtype, Function) and isinstance(supertype, Function):
        return is_subtype(supertype.parameters, subtype.parameters) and is_subtype(subtype.result, supertype.result)
    raise tapl_error.TaplError(f'Unsupported-2 subtype check for subtype={subtype} supertype={supertype}.')


def is_equal(a, b):
    return is_subtype(a, b) and is_subtype(b, a)


def drop_same_types(types):
    result = []
    for t in types:
        for r in result:
            if is_equal(t, r):
                break
        else:
            result.append(t)
    return result


def create_union(*args):
    result = []
    for arg in args:
        # Union of unions are flattened
        if isinstance(arg, Union):
            result.extend(arg.types)
        else:
            result.append(arg)
    result = drop_same_types(result)
    # Unions of a single argument vanish
    if len(result) == 1:
        return next(iter(result))
    return Union(types=result)


class AtomSubject:
    def __init__(self, atom):
        self.atom = atom

    def __repr__(self):
        return repr(self.atom)

    def load(self, key):
        raise tapl_error.TaplError(f'AttributeError: Attribute not found: {key}')

    def store(self, key):
        raise tapl_error.TaplError(f'AttributeError: Attribute not found: {key}')


class IntersectionSubject:
    def __init__(self, intersection):
        self.intersection = intersection

    def __repr__(self):
        return repr(self.intersection)

    def load(self, key):
        t = self.intersection.find_label(key)
        if t is None:
            raise tapl_error.TaplError(f'AttributeError: Attribute not found: {key}')
        return t.type

    def store(self, key):
        raise tapl_error.TaplError(f'AttributeError: Attribute not found: {key}')


class UnionSubject:
    def __init__(self, union):
        self.union = union

    def __repr__(self):
        return repr(self.union)

    def load(self, key):
        raise tapl_error.TaplError(f'AttributeError: Attribute not found: {key}')

    def store(self, key):
        raise tapl_error.TaplError(f'AttributeError: Attribute not found: {key}')


def build_proxy(type_name: str):
    if type_name not in BUILTIN:
        raise tapl_error.TaplError(f'Type {type_name} not found in built-in types.')
    typ = BUILTIN[type_name]
    if isinstance(typ, Atom):
        return proxy.Proxy(AtomSubject(typ))
    if isinstance(typ, Intersection):
        return proxy.Proxy(IntersectionSubject(typ))
    if isinstance(typ, Union):
        return proxy.Proxy(UnionSubject(typ))
    raise tapl_error.TaplError(f'Cannot build proxy for type {type_name} of type {typ}.')


def add_methods(type_name, methods):
    types = BUILTIN[type_name].types
    for name, params, result in methods:
        for i in range(len(params)):
            if isinstance(params[i], str):
                params[i] = BUILTIN[params[i]]
        if isinstance(result, str):
            result = BUILTIN[result]  # noqa: PLW2901
        func = Function(parameters=params, result=result)
        types.append(Labeled(name, func))


BUILTIN = {
    'Any': Intersection(types=[]),
    'Nothing': Union(types=[]),
    'NoneType': Atom('NoneType'),
    'Bool': Intersection(types=[], title='Bool'),
    'Int': Intersection(types=[], title='Int'),
    'Float': Intersection(types=[], title='Float'),
    'Str': Intersection(types=[], title='Str'),
}


add_methods('Bool', [['__lt__', ['Bool'], 'Bool']])
add_methods('Int', [['__add__', ['Int'], 'Int'], ['__lt__', ['Int'], 'Bool']])
add_methods(
    'Float',
    [
        ['__add__', ['Float'], 'Float'],
        ['__mul__', ['Float'], 'Float'],
        ['__lt__', ['Float'], 'Bool'],
        ['__gt__', ['Float'], 'Bool'],
    ],
)
add_methods('Str', [['isalpha', [], 'Bool']])

BUILTIN_PROXY = {k: build_proxy(k) for k in BUILTIN}
