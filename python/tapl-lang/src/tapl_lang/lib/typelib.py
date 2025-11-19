# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
Type system implementation for TAPL language.

Core Types:
- BaseType: Abstract base class for all types, and types does not have to inherit from it.
- Union: Represents a union of types (T1 | T2)
- Intersection: Represents an intersection of types (T1 & T2)
- Any: Top type - supertype of all types, except NoneType
- Nothing: Bottom type - subtype of all types
- NoneType: Singleton type for None value
- Record: Structural record type with labeled fields
- Function: Function type with positional and named arguments
- TypeVariable: Type variable for generic types

Type Checking:
- check_subtype(subtype, supertype): Checks if 'subtype' is a subtype of 'supertype'
- check_type_equality(a, b): Checks if two types are equivalent
- Uses caching and assumption stack to handle recursive type definitions

Design Notes:
- All types are immutable
- Naming convention: Variables with __sa suffix indicate internal type system attributes
- Methods is_subtype_of__sa and is_supertype_of__sa return None when inconclusive
- Inspired by Kotlin's type hierarchy
    - https://stackoverflow.com/a/54762815/22663977
    - NoneType is not subtype of Any, but it is a subtype of Union that includes NoneType
    - Any | NoneType is a top type, supertype of all types
    - Nothing is a bottom type, subtype of all types
"""

from tapl_lang.lib import dynamic_attributes


# TODO: extend from threading.local, and write a unit test for this - https://docs.python.org/3/library/threading.html#thread-local-data
class TypeCheckerState:
    """Holds transient state for subtype checks (cache + assumption stack)."""

    def __init__(self):
        self.cached_subtype_pairs = {}  # mapping of (subtype, supertype) pairs to bool
        self.assumed_subtype_pairs = []  # stack of (subtype, supertype) pairs


_TYPE_CHECKER_STATE = TypeCheckerState()


def compute_subtype(subtype, supertype):
    is_supertype = supertype.is_supertype_of__sa(subtype)
    is_subtype = subtype.is_subtype_of__sa(supertype)
    # Return Truee if both methods agree on True, or if one is True and the other is inconclusive.
    return is_supertype and is_subtype or (is_supertype is None and is_subtype) or (is_supertype and is_subtype is None)


def check_subtype(subtype, supertype):
    if subtype is supertype:
        return True
    pair = (subtype, supertype)
    result = _TYPE_CHECKER_STATE.cached_subtype_pairs.get(pair)
    if result is not None:
        return result
    if pair in _TYPE_CHECKER_STATE.assumed_subtype_pairs:
        return True
    try:
        _TYPE_CHECKER_STATE.assumed_subtype_pairs.append(pair)
        result = compute_subtype(subtype, supertype)
        _TYPE_CHECKER_STATE.cached_subtype_pairs[pair] = result
    finally:
        _TYPE_CHECKER_STATE.assumed_subtype_pairs.pop()
    return result


def check_type_equality(a, b):
    return check_subtype(a, b) and check_subtype(b, a)


# rename to keep_root_types or take_root_types or similar #mvp
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


class BaseType(dynamic_attributes.DynamicAttributeMixin):
    def is_supertype_of__sa(self, subtype):
        del subtype  # unused

    def is_subtype_of__sa(self, supertype):
        del supertype  # unused

    def __or__(self, other):
        return create_union(self, other)

    def __repr__(self):
        return 'BaseType'


# TODO: implement '|' operator for Union and '&' operator for Intersection
# TODO: what happens when these operators are used for binary operation instead of type construction?
# e.g., T1 | T2, T1 & T2
# Exception for binary-operator methods in Python; not intended for direct use.
# Example: alpha <: (alpha | beta) or beta <: (alpha | beta)
class Union(BaseType):
    def __init__(self, types, title=None):
        if len(types) <= 1:
            raise ValueError('Union requires at least two types.')
        self._types__sa = types
        self._title__sa = title

    def is_supertype_of__sa(self, subtype):
        # Example: alpha <: (alpha | beta)
        if any(check_subtype(subtype, typ) for typ in self._types__sa):
            return True
        # Inconclusive when subtype_ is itself a Union.
        # Example: (alpha | beta) <: (alpha | beta | gamma)
        return None

    def is_subtype_of__sa(self, supertype):
        # Example: (alpha | beta) <: (alpha | beta | gamma)
        return all(check_subtype(typ, supertype) for typ in self._types__sa)

    def __repr__(self):
        if self._title__sa is not None:
            return self._title__sa
        return ' | '.join([str(t) for t in self._types__sa])

    def iter_types__sa(self):
        yield from self._types__sa


# Example: alpha & beta <: alpha or alpha & beta <: beta
class Intersection(BaseType):
    def __init__(self, types, title=None):
        if len(types) <= 1:
            raise ValueError('At least two types are required to create Intersection.')
        self._types__sa = types
        self._title__sa = title

    def is_supertype_of__sa(self, subtype):
        # Example: (alpha & beta & gamma) <: (alpha & beta)
        return all(check_subtype(subtype, typ) for typ in self._types__sa)

    def is_subtype_of__sa(self, supertype):
        # Example: (alpha & beta) <: alpha
        if any(check_subtype(typ, supertype) for typ in self._types__sa):
            return True
        # Inconclusive when supertype_ is itself an Intersection.
        # Example: (alpha & beta & gamma) <: (alpha & beta)
        return None

    def __repr__(self):
        if self._title__sa is not None:
            return self._title__sa
        return ' & '.join([str(t) for t in self._types__sa])

    def iter_types__sa(self):
        yield from self._types__sa


# Top type
class Any(BaseType):
    def is_supertype_of__sa(self, subtype):
        if isinstance(subtype, Any):
            return True
        # Inconclusive, let subtype decide
        return None

    def is_subtype_of__sa(self, supertype):
        if isinstance(supertype, Any):
            return True
        # Inconclusive, example: Any <: (Any | NoneType)
        return None

    def __repr__(self):
        return 'Any'


# Bottom type
class Nothing(BaseType):
    def is_supertype_of__sa(self, subtype):
        if isinstance(subtype, Nothing):
            return True
        # Inconclusive, (Nothing & NoneType) <: Nothing
        return None

    def is_subtype_of__sa(self, supertype):
        if isinstance(supertype, Nothing):
            return True
        if isinstance(supertype, Any):
            return True
        # Inconclusive, let supertype decide
        return None

    def __repr__(self):
        return 'Nothing'


# Inspired by Kotlin type system - https://stackoverflow.com/a/54762815/22663977
class NoneType(BaseType):
    def is_supertype_of__sa(self, subtype):
        if isinstance(subtype, NoneType):
            return True
        # Inconclusive, example: (NoneType & T) <: NoneType
        return None

    def is_subtype_of__sa(self, supertype):
        if isinstance(supertype, NoneType):
            return True
        # Inconclusive, example: NoneType <: (T | NoneType)
        return None

    def __repr__(self):
        return 'None'


# TODO: A tuple type where labels are the characters 'a' through 'z'.
class Record(BaseType):
    def __init__(self, fields, title=None):
        self._fields__sa = fields
        self._title__sa = title

    def is_supertype_of__sa(self, subtype):
        if isinstance(subtype, Nothing):
            return True
        # Inconclusive, example: {a: Alpha, b: Beta} <: {a: Alpha}
        return None

    def is_subtype_of__sa(self, supertype):
        if isinstance(supertype, Any):
            return True
        if isinstance(supertype, Record):
            for label in supertype.labels__sa():
                if label not in self._fields__sa:
                    return False
                if not check_subtype(self._fields__sa[label], supertype.try_load(label)):
                    return False
            return True
        # Inconclusive, example: {a: Alpha, b: Beta} <: (Any | NoneType)
        return None

    def labels__sa(self):
        yield from self._fields__sa.keys()

    def __repr__(self):
        if self._title__sa is not None:
            return self._title__sa
        field_strs = [f'{label}: {typ}' for label, typ in self._fields__sa.items()]
        return '{' + ', '.join(field_strs) + '}'

    def try_load(self, label):
        return self._fields__sa.get(label)

    def load__sa(self, key):
        if key in self._fields__sa:
            return self._fields__sa[key]
        return super().load__sa(key)


_PAIR_ELEMENT_COUNT = 2


# TODO: Implement vararg, kwonlyargs, kw_defaults, kwarg, and defaults
class Function(BaseType):
    def __init__(self, posonlyargs, args, result=None, lazy_result=None):
        if not isinstance(posonlyargs, list):
            raise TypeError('Function posonlyargs must be a list.')
        if not isinstance(args, list):
            raise TypeError('Function args must be a list.')
        if any(not (isinstance(arg, tuple) and len(arg) == _PAIR_ELEMENT_COUNT) for arg in args):
            raise ValueError('Function args must be a list of (name, type) pairs.')
        if any(not (isinstance(name, str)) for name, _ in args):
            raise ValueError('Function args must be a list of (str, Any) tuples.')
        if lazy_result is not None and result is not None:
            raise ValueError('Pass either the result or lazy_result argument, but not both.')

        self._posonlyargs__sa = posonlyargs  # list of Type Proxy
        self._args__sa = args  # list of (name, Type Proxy)
        self._result__sa = result
        self._lazy_result__sa = lazy_result

    # TODO: implement supertype and subtype checking for function types
    def is_supertype_of__sa(self, subtype):
        del subtype  # unused
        return False

    def is_subtype_of__sa(self, supertype):
        del supertype  # unused
        return False

    def __repr__(self):
        args = [str(t) for t in self._posonlyargs__sa]
        args += [f'{name}: {typ}' for name, typ in self._args__sa]
        args_str = f'({", ".join(args)})'
        if self._lazy_result__sa:
            return f'{args_str}->[uncomputed]'
        return f'{args_str}->{self._result__sa}'

    def apply(self, *arguments):
        actual_all_args = list(arguments)
        expected_args_count = len(self._posonlyargs__sa) + len(self._args__sa)
        if len(actual_all_args) != expected_args_count:
            raise TypeError(f'Expected {expected_args_count} arguments, got {len(actual_all_args)}')
        actual_posonlyargs = actual_all_args[: len(self._posonlyargs__sa)]
        actual_args = actual_all_args[len(self._posonlyargs__sa) :]
        for p, a in zip(self._posonlyargs__sa, actual_posonlyargs, strict=False):
            if not check_subtype(a, p):
                raise TypeError(f'Not equal: posonlyargs={self._posonlyargs__sa} arguments={actual_posonlyargs}')
        for p, a in zip(self._args__sa, actual_args, strict=True):
            if not check_subtype(a, p):
                raise TypeError(f'Not equal: args={self._args__sa} arguments={actual_args}')
        return self.result__sa

    def load__sa(self, key):
        if key == '__call__':
            return self.apply
        return super().load__sa(key)

    @property
    def posonlyargs__sa(self):
        yield from self._posonlyargs__sa

    @property
    def args__sa(self):
        yield from self._args__sa

    @property
    def result__sa(self):
        self.force__sa()
        return self._result__sa

    def force__sa(self):
        if self._lazy_result__sa:
            self._result__sa = self._lazy_result__sa()
            self._lazy_result__sa = None


class TypeVariable(BaseType):
    def __init__(self, variable_name: str):
        self.variable_name = variable_name

    def is_supertype_of__sa(self, subtype):
        del subtype  # unused
        # Inconclusive: (T & Alpha) <: T

    def is_subtype_of__sa(self, supertype):
        del supertype  # unused
        # Inconclusive: T <: (T | Alpha)

    def __repr__(self):
        return self.variable_name


def create_union(*args):
    result = []
    for arg in args:
        # Union of unions are flattened
        subject = arg
        if isinstance(subject, Union):
            result.extend(subject.iter_types__sa())  # consume as iterable
        else:
            result.append(arg)
    result = drop_same_types(result)
    # Unions of a single argument vanish
    if len(result) == 1:
        return next(iter(result))
    return Union(types=result)


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
    return Function(posonlyargs=posonly, args=regular, result=result)
