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

1. Types are considered immutable.
2. Inspired by Kotlin type hierarchy:
   - NoneType: The singleton, unit, or void type. 'None' is only instance of this type.
   - Any: the top type, excluding NoneType
   - Nothing: the bottom type
3. The methods is_subtype_of and is_supertype_of return None when the type relationship can't be determined.
4. Variables suffixed with an underscore denote a type instance not wrapped by a Proxy.
"""

from tapl_lang.lib import proxy


# TODO: extend from threading.local, and write a unit test for this - https://docs.python.org/3/library/threading.html#thread-local-data
class TypeCheckerState:
    """Holds transient state for subtype checks (cache + assumption stack)."""

    def __init__(self):
        self.cached_subtype_pairs = {}  # mapping of (subtype, supertype) pairs to bool
        self.assumed_subtype_pairs = []  # stack of (subtype, supertype) pairs


_TYPE_CHECKER_STATE = TypeCheckerState()


def compute_subtype_(subtype_, supertype_):
    is_supertype = supertype_.is_supertype_of(subtype_)
    is_subtype = subtype_.is_subtype_of(supertype_)
    # Return Truee if both methods agree on True, or if one is True and the other is inconclusive.
    return is_supertype and is_subtype or (is_supertype is None and is_subtype) or (is_supertype and is_subtype is None)


def check_subtype_(subtype_, supertype_):
    if subtype_ is supertype_:
        return True
    pair = (subtype_, supertype_)
    result = _TYPE_CHECKER_STATE.cached_subtype_pairs.get(pair)
    if result is not None:
        return result
    if pair in _TYPE_CHECKER_STATE.assumed_subtype_pairs:
        return True
    try:
        _TYPE_CHECKER_STATE.assumed_subtype_pairs.append(pair)
        result = compute_subtype_(subtype_, supertype_)
        _TYPE_CHECKER_STATE.cached_subtype_pairs[pair] = result
    finally:
        _TYPE_CHECKER_STATE.assumed_subtype_pairs.pop()
    return result


def check_subtype(subtype, supertype):
    return check_subtype_(subtype.subject__tapl, supertype.subject__tapl)


def check_type_equality(a, b):
    return check_subtype(a, b) and check_subtype(b, a)


def drop_same_types(types):
    # TODO: Build a directed graph, and keep only roots of the forests
    result = []
    for t in types:
        for r in result:
            if check_type_equality(t, r):
                break
        else:
            result.append(t)
    return result


# Used in Builtin Types to resolve circular dependency
class Interim(proxy.Subject):
    def is_supertype_of(self, subtype_):
        del subtype_  # unused
        raise NotImplementedError('Interim type does not implement is_supertype_of method.')

    def is_subtype_of(self, supertype_):
        del supertype_  # unused
        raise NotImplementedError('Interim type does not implement is_subtype_of method.')

    def __repr__(self):
        return 'InterimType'


# TODO: implement '|' operator for Union and '&' operator for Intersection
# e.g., T1 | T2, T1 & T2
# Exception for binary-operator methods in Python; not intended for direct use.
# Example: alpha <: (alpha | beta) or beta <: (alpha | beta)
class Union(proxy.Subject):
    def __init__(self, types, title=None):
        if len(types) <= 1:
            raise ValueError('Union requires at least two types.')
        self._types = types
        self._title = title

    def is_supertype_of(self, subtype_):
        # Example: alpha <: (alpha | beta)
        if any(check_subtype_(subtype_, typ.subject__tapl) for typ in self._types):
            return True
        # Inconclusive when subtype_ is itself a Union.
        # Example: (alpha | beta) <: (alpha | beta | gamma)
        return None

    def is_subtype_of(self, supertype_):
        # Example: (alpha | beta) <: (alpha | beta | gamma)
        return all(check_subtype_(typ.subject__tapl, supertype_) for typ in self._types)

    def __repr__(self):
        if self._title is not None:
            return self._title
        return ' | '.join([str(t) for t in self._types])

    def __iter__(self):
        yield from self._types


# Example: alpha & beta <: alpha or alpha & beta <: beta
class Intersection(proxy.Subject):
    def __init__(self, types, title=None):
        if len(types) <= 1:
            raise ValueError('At least two types are required to create Intersection.')
        self._types = types
        self._title = title

    def is_supertype_of(self, subtype_):
        # Example: (alpha & beta & gamma) <: (alpha & beta)
        return all(check_subtype_(subtype_, typ.subject__tapl) for typ in self._types)

    def is_subtype_of(self, supertype_):
        # Example: (alpha & beta) <: alpha
        if any(check_subtype_(typ.subject__tapl, supertype_) for typ in self._types):
            return True
        # Inconclusive when supertype_ is itself an Intersection.
        # Example: (alpha & beta & gamma) <: (alpha & beta)
        return None

    def __repr__(self):
        if self._title is not None:
            return self._title
        return ' & '.join([str(t) for t in self._types])

    def __iter__(self):
        yield from self._types


# Top type
class Any(proxy.Subject):
    def is_supertype_of(self, subtype_):
        if isinstance(subtype_, Any):
            return True
        # Inconclusive, let subtype decide
        return None

    def is_subtype_of(self, supertype_):
        if isinstance(supertype_, Any):
            return True
        # Inconclusive, example: Any <: (Any | NoneType)
        return None

    def __repr__(self):
        return 'Any'


# Bottom type
class Nothing(proxy.Subject):
    def is_supertype_of(self, subtype_):
        if isinstance(subtype_, Nothing):
            return True
        # Inconclusive, (Nothing & NoneType) <: Nothing
        return None

    def is_subtype_of(self, supertype_):
        if isinstance(supertype_, Nothing):
            return True
        if isinstance(supertype_, Any):
            return True
        # Inconclusive, let supertype decide
        return None

    def __repr__(self):
        return 'Nothing'


# Inspired by Kotlin type system - https://stackoverflow.com/a/54762815/22663977
class NoneType(proxy.Subject):
    def is_supertype_of(self, subtype_):
        if isinstance(subtype_, NoneType):
            return True
        # Inconclusive, example: (NoneType & T) <: NoneType
        return None

    def is_subtype_of(self, supertype_):
        if isinstance(supertype_, NoneType):
            return True
        # Inconclusive, example: NoneType <: (T | NoneType)
        return None

    def __repr__(self):
        return 'None'


# TODO: A tuple type where labels are the characters 'a' through 'z'.
class Record(proxy.Subject):
    def __init__(self, fields, title=None):
        self._fields = fields
        self._title = title

    def is_supertype_of(self, subtype_):
        if isinstance(subtype_, Nothing):
            return True
        # Inconclusive, example: {a: Alpha, b: Beta} <: {a: Alpha}
        return None

    def is_subtype_of(self, supertype_):
        if isinstance(supertype_, Any):
            return True
        if isinstance(supertype_, Record):
            for label, super_field_type in supertype_._fields.items():
                if label not in self._fields:
                    return False
                if not check_subtype(self._fields[label], super_field_type):
                    return False
            return True
        # Inconclusive, example: {a: Alpha, b: Beta} <: (Any | NoneType)
        return None

    def __repr__(self):
        if self._title is not None:
            return self._title
        field_strs = [f'{label}: {typ}' for label, typ in self._fields.items()]
        return '{' + ', '.join(field_strs) + '}'

    def __iter__(self):
        yield from self._fields.items()

    def try_load(self, label):
        return self._fields.get(label)

    def load(self, key):
        if key in self._fields:
            return self._fields[key]
        return super().load(key)


_PAIR_ELEMENT_COUNT = 2


# TODO: Implement vararg, kwonlyargs, kw_defaults, kwarg, and defaults
class Function(proxy.Subject):
    def __init__(self, posonlyargs, args, result=None, lazy_result=None):
        if not isinstance(posonlyargs, list):
            raise TypeError('Function posonlyargs must be a list.')
        if any(not isinstance(arg, proxy.Proxy) for arg in posonlyargs):
            raise ValueError('Function posonlyargs must be a list of Proxy.')
        if not isinstance(args, list):
            raise TypeError('Function args must be a list.')
        if any(not (isinstance(arg, tuple) and len(arg) == _PAIR_ELEMENT_COUNT) for arg in args):
            raise ValueError('Function args must be a list of (name, type) pairs.')
        if any(not (isinstance(name, str) and isinstance(arg_type, proxy.Proxy)) for name, arg_type in args):
            raise ValueError('Function args must be a list of (str, Proxy) tuples.')
        if lazy_result is not None and result is not None:
            raise ValueError('Pass either the result or lazy_result argument, but not both.')

        self._posonlyargs = posonlyargs  # list of Type Proxy
        self._args = args  # list of (name, Type Proxy)
        self._result = result
        self._lazy_result = lazy_result

    # TODO: implement subtype checking for function types
    def is_supertype_of(self, subtype_):
        del subtype_  # unused

    def is_subtype_of(self, supertype_):
        del supertype_  # unused

    def __repr__(self):
        args = [str(t) for t in self._posonlyargs]
        args += [f'{name}: {typ}' for name, typ in self._args]
        args_str = f'({", ".join(args)})'
        if self._lazy_result:
            return f'{args_str}->[uncomputed]'
        return f'{args_str}->{self._result}'

    def apply(self, *arguments):
        actual_all_args = list(arguments)
        expected_args_count = len(self._posonlyargs) + len(self._args)
        if len(actual_all_args) != expected_args_count:
            raise TypeError(f'Expected {expected_args_count} arguments, got {len(actual_all_args)}')
        actual_posonlyargs = actual_all_args[: len(self._posonlyargs)]
        actual_args = actual_all_args[len(self._posonlyargs) :]
        for p, a in zip(self._posonlyargs, actual_posonlyargs, strict=False):
            if not check_subtype(a, p):
                raise TypeError(f'Not equal: posonlyargs={self._posonlyargs} arguments={actual_posonlyargs}')
        for p, a in zip(self._args, actual_args, strict=True):
            if not check_subtype(a, p):
                raise TypeError(f'Not equal: args={self._args} arguments={actual_args}')
        return self.result

    def load(self, key):
        if key == '__call__':
            return self.apply
        return super().load(key)

    @property
    def posonlyargs(self):
        yield from self._posonlyargs

    @property
    def args(self):
        yield from self._args

    @property
    def result(self):
        self.force()
        return self._result

    def force(self):
        if self._lazy_result:
            self._result = self._lazy_result()
            self._lazy_result = None


def create_union(*args):
    result = []
    for arg in args:
        # Union of unions are flattened
        subject = arg.subject__tapl
        if isinstance(subject, Union):
            result.extend(subject)  # consume as iterable
        else:
            result.append(arg)
    result = drop_same_types(result)
    # Unions of a single argument vanish
    if len(result) == 1:
        return next(iter(result))
    return proxy.Proxy(Union(types=result))


def create_function(args, result):
    posonly = []
    regular = []
    tuple_found = False
    for arg in args:
        if isinstance(arg, tuple):
            tuple_found = True
            args.append((arg[0], arg[1]))
        elif not tuple_found:
            posonly.append(arg)
        else:
            raise ValueError('Positional-only arguments must come before regular arguments')
    func = Function(posonlyargs=posonly, args=regular, result=result)
    return proxy.Proxy(func)
