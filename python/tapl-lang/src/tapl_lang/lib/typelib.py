# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
TODO: This module doc is outdated, update it. Maybe write a separate explanation in doc folder.
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

All types should be immutable.

Source.can_be_used_as(Target) checks if Source can be used as Target. This returns True if Source is a subtype of Target.

Variable with underscore suffix means the type is wrapped with Proxy

The following does not use Python type hints intentionally.
"""

import enum

from tapl_lang.core import tapl_error
from tapl_lang.lib import proxy


class Kind(enum.Enum):
    Interim = 'Interim'
    Any = 'Any'  # Top type except NoneType (like Kotlin)
    Nothing = 'Nothing'  # Bottom type
    NoneType = 'NoneType'  # Singleton/Unit/Void type
    Labeled = 'Labeled'
    Union = 'Union'
    Intersection = 'Intersection'
    Function = 'Function'
    Scope = 'Scope'


class Interim(proxy.Subject):
    @property
    def kind(self):
        return Kind.Interim

    def __repr__(self):
        return 'Interim'


class NoneType(proxy.Subject):
    @property
    def kind(self):
        return Kind.NoneType

    def can_be_used_as(self, target):
        if self is target:
            return True
        if target.kind == Kind.NoneType:
            return True
        if target.kind == Kind.Union:
            return any(self.can_be_used_as(e.subject__tapl) for e in target)
        return False

    def __repr__(self):
        return 'NoneType'


class Any(proxy.Subject):
    @property
    def kind(self):
        return Kind.Any

    def can_be_used_as(self, target):
        if self is target:
            return True
        if target.kind == Kind.Any:
            return True
        if target.kind == Kind.Union:
            return any(self.can_be_used_as(e.subject__tapl) for e in target)
        return False

    def __repr__(self):
        return 'Any'


class Nothing(proxy.Subject):
    @property
    def kind(self):
        return Kind.Nothing

    def can_be_used_as(self, target):
        del target
        # Can be used as anything
        return True

    def __repr__(self):
        return 'Nothing'


class Labeled(proxy.Subject):
    def __init__(self, label, typ):
        if not isinstance(typ, proxy.Proxy):
            raise TypeError(f'Labeled type must be a Proxy, but found {type(typ)} in label={label}')
        self._label = label
        self._type = typ

    @property
    def kind(self):
        return Kind.Labeled

    def can_be_used_as(self, target):
        if self is target:
            return True
        if target.kind == Kind.Any:
            return True
        if target.kind == Kind.Labeled:
            return self.label == target.label and self.type.subject__tapl.can_be_used_as(target.type.subject__tapl)
        if target.kind in (Kind.Union, Kind.Intersection):
            return any(self.can_be_used_as(e.subject__tapl) for e in target)
        return False

    @property
    def label(self):
        return self._label

    @property
    def type(self):
        return self._type

    def __repr__(self):
        return f'{self._label}={self._type}'


class Union(proxy.Subject):
    def __init__(self, types, title=None):
        _validate_types(types)
        self._types = types
        self._title = title

    @property
    def kind(self):
        return Kind.Union

    def __iter__(self):
        yield from self._types

    def can_be_used_as(self, target):
        if self is target:
            return True
        if target.kind == Kind.Union:
            return all(any(can_be_used_as(se, te) for te in target) for se in self)
        return False

    def __repr__(self):
        if self._title is not None:
            return self._title
        return ' | '.join([str(t) for t in self._types])


class Intersection(proxy.Subject):
    def __init__(self, types, title=None):
        _validate_types(types)
        self._types = types
        self._title = title

    @property
    def kind(self):
        return Kind.Intersection

    def __iter__(self):
        yield from self._types

    def can_be_used_as(self, target):
        if self is target:
            return True
        if target.kind == Kind.Any:
            return True
        if target.kind == Kind.Union:
            return any(self.can_be_used_as(e.subject__tapl) for e in target)
        if target.kind == Kind.Intersection:
            for te_ in target:
                te = te_.subject__tapl
                if te.kind == Kind.Labeled:
                    se = self._find_labeled(te.label)
                    if se is None or not se.can_be_used_as(te.type.subject__tapl):
                        return False
                else:
                    raise tapl_error.TaplError(
                        f'Unsupported: Intersection type contains non-Labeled type self={self} target={target}.'
                    )
        return False

    def _find_labeled(self, label):
        for t_ in self:
            t = t_.subject__tapl
            if t.kind == Kind.Labeled and t.label == label:
                return t
        return None

    def load(self, key):
        t = self._find_labeled(key)
        if t:
            return t.type
        return super().load(key)

    def __repr__(self):
        if self._title is not None:
            return self._title
        return ' & '.join([str(t) for t in self._types])


class Function(proxy.Subject):
    def __init__(self, parameters, result=None, lazy_result=None):
        if lazy_result is not None and result is not None:
            raise ValueError('Pass either the result or lazy_result argument, but not both.')
        # TODO: Parameters must be Intersection type of Labeled types. In addition,
        # Labeled type's name may be omitted for positional parameters.
        self._parameters = _process_parameters(parameters)
        self._result = result
        self._lazy_result = lazy_result

    @property
    def kind(self):
        return Kind.Function

    @property
    def parameters(self):
        yield from self._parameters

    @property
    def result(self):
        self.force()
        return self._result

    def force(self):
        if self._lazy_result:
            self._result = self._lazy_result()
            self._lazy_result = None

    def can_be_used_as(self, target):
        if self is target:
            return True
        if target.kind != Kind.Function:
            return False
        for self_param, target_param in zip(self.parameters, target.parameters, strict=True):
            if not can_be_used_as(self_param, target_param):
                return False
        return can_be_used_as(self.result, target.result)

    def fix_labels(self, arguments):
        for i in range(len(arguments)):
            if arguments[i].subject__tapl.kind == Kind.Labeled:
                break
            arguments[i] = proxy.Proxy(Labeled(self._parameters[i].subject__tapl.label, arguments[i]))
        return arguments

    def apply(self, *arguments):
        args = list(arguments)
        if len(args) != len(self._parameters):
            raise TypeError(f'Expected {len(self._parameters)} arguments, got {len(args)}')
        args = self.fix_labels(args)
        for p, a in zip(self.parameters, args, strict=True):
            if not can_be_used_as(a, p):
                raise TypeError(f'Not equal: parameters={self.parameters} arguments={args}')
        return self.result

    def load(self, key):
        if key == '__call__':
            return self.apply
        return super().load(key)

    def __repr__(self):
        if self._lazy_result:
            return f'{self._parameters}->[uncomputed]'
        return f'{self._parameters}->{self._result}'


def _process_parameters(parameters):
    if not isinstance(parameters, list):
        raise tapl_error.TaplError('Function parameters must be a list.')
    params = parameters[:]
    labeled_parameter_seen = False
    for i in range(len(params)):
        p = params[i].subject__tapl
        if p.kind == Kind.Labeled:
            labeled_parameter_seen = True
        elif labeled_parameter_seen:
            raise tapl_error.TaplError('Positional parameter follows labeled parameter.')
        else:
            params[i] = proxy.Proxy(Labeled(str(i), params[i]))
    return params


def _validate_types(types):
    if len(types) <= 1:
        raise ValueError('At least two types are required.')
    # check for duplicate labels
    seen_labels = set()
    for t_ in types:
        if not isinstance(t_, proxy.Proxy):
            raise TypeError(f'Type must be a Proxy, but found {type(t_)}')
        t = t_.subject__tapl
        if t.kind == Kind.Labeled:
            if t.label in seen_labels:
                raise ValueError(f'Duplicate label found: {t.label}')
            seen_labels.add(t.label)


def can_be_used_as(source, target):
    if source is target:
        return True
    return source.subject__tapl.can_be_used_as(target.subject__tapl)


def is_equal(a, b):
    return can_be_used_as(a, b) and can_be_used_as(b, a)


def drop_same_types(types):
    # TODO: Build a directed graph, and keep only roots of the forests
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
        subject = arg.subject__tapl
        if subject.kind == Kind.Union:
            result.extend(subject)  # consume as iterable
        else:
            result.append(arg)
    result = drop_same_types(result)
    # Unions of a single argument vanish
    if len(result) == 1:
        return next(iter(result))
    return proxy.Proxy(Union(types=result))


def create_function(parameters, result):
    func = Function(parameters=parameters, result=result)
    return proxy.Proxy(func)
