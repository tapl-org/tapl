# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
Type system implementation for TAPL language.

Core Kinds:
- BaseKind: Abstract base class for all types, and types does not have to inherit from it.
- Union: Represents a union of types (T1 | T2)
- Intersection: Represents an intersection of types (T1 & T2)
- Any: Top type - supertype of all types, except NoneType
- Nothing: Bottom type - subtype of all types
- NoneType: Singleton type for None value
- Record: Structural record type with labeled fields
- Function: Function type with positional and named arguments

Type Checking:
- check_subtype(subtype, supertype): Checks if 'subtype' is a subtype of 'supertype'
- check_type_equality(a, b): Checks if two types are equivalent
- Uses caching and assumption stack to handle recursive type definitions

Design Notes:
- All types are considered as immutable
- Naming convention: Variables with __sa suffix indicate internal type system attributes
- Methods is_subtype_of__sa and is_supertype_of__sa return None when inconclusive
- Inspired by Kotlin's type hierarchy
    - https://stackoverflow.com/a/54762815/22663977
    - NoneType is not subtype of Any, but it is a subtype of Union that includes NoneType
    - Any | NoneType is a top type, supertype of all types
    - Nothing is a bottom type, subtype of all types
"""

from tapl_lang.lib import dynamic_attribute


# FIXME: extend from threading.local, and write a unit test for this - https://docs.python.org/3/library/threading.html#thread-local-data
class TypeCheckerState:
    """Holds transient state for subtype checks (cache + assumption stack)."""

    def __init__(self):
        self.cached_subtype_pairs = {}  # mapping of (subtype, supertype) pairs to bool
        self.assumed_subtype_pairs = []  # stack of (subtype, supertype) pairs


_TYPE_CHECKER_STATE = TypeCheckerState()


def compute_subtype(subtype, supertype):
    if hasattr(supertype, 'is_supertype_of__sa') and hasattr(subtype, 'is_subtype_of__sa'):
        is_supertype = supertype.is_supertype_of__sa(subtype)
        is_subtype = subtype.is_subtype_of__sa(supertype)
        # Return Truee if both methods agree on True, or if one is True and the other is inconclusive.
        return (
            is_supertype
            and is_subtype
            or (is_supertype is None and is_subtype)
            or (is_supertype and is_subtype is None)
        )
    # Fallback: treat them as literals and check for equality.
    return subtype == supertype


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
    # FIXME: Build a directed graph, and keep only roots of the forests
    result = []
    for t in types:
        for r in result:
            if check_type_equality(t, r):
                break
        else:
            result.append(t)
    return result


class BaseKind(dynamic_attribute.DynamicAttributeMixin):
    def is_supertype_of__sa(self, subtype):
        del subtype  # unused

    def is_subtype_of__sa(self, supertype):
        del supertype  # unused

    def __or__(self, other):
        return create_union(self, other)

    def __repr__(self):
        return 'BaseKind!'


# FIXME: what happens when '|' and '&' operators are used for binary operation instead of type construction?


# Example: alpha <: (alpha | beta) or beta <: (alpha | beta)
class Union(BaseKind):
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


# TODO: implement '&' operator for Intersection
# Example: alpha & beta <: alpha or alpha & beta <: beta
class Intersection(BaseKind):
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
class Any(BaseKind):
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
class Nothing(BaseKind):
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
class NoneType(BaseKind):
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


class Record(BaseKind):
    def __init__(self, fields, label=None):
        self._fields__sa = fields
        self._label__sa = label

    def is_supertype_of__sa(self, subtype):
        if isinstance(subtype, Nothing):
            return True
        # Inconclusive, example: {a: Alpha, b: Beta} <: {a: Alpha}
        return None

    def is_subtype_of__sa(self, supertype):
        if isinstance(supertype, Any):
            return True
        if isinstance(supertype, Record):
            for label in supertype.keys__sa():
                if label not in self._fields__sa:
                    return False
                if not check_subtype(self._fields__sa[label], supertype.try_load(label)):
                    return False
            return True
        # Inconclusive, example: {a: Alpha, b: Beta} <: (Any | NoneType)
        return None

    def keys__sa(self):
        yield from self._fields__sa.keys()

    def fields_repr__sa(self):
        field_strs = [f'{key}: {typ}' for key, typ in self._fields__sa.items()]
        return '{' + ', '.join(field_strs) + '}'

    def __repr__(self):
        if self._label__sa is not None:
            return self._label__sa
        return self.fields_repr__sa()

    def try_load(self, key):
        return self._fields__sa.get(key)

    def load__sa(self, key):
        if key in self._fields__sa:
            return self._fields__sa[key]
        raise AttributeError(f'{self.get_label__sa()} record has no attribute "{key}"')

    def store__sa(self, name: str, value: Any) -> None:
        stored_value = self.load__sa(name)
        if not check_subtype(value, stored_value):
            raise TypeError(f'Type error in variable "{name}": Expected type "{stored_value}", but found "{value}".')

    def get_label__sa(self):
        if self._label__sa is not None:
            return self._label__sa
        return 'Unlabeled record class'


_PAIR_ELEMENT_COUNT = 2


# XXX: Implement vararg, kwonlyargs, kw_defaults, kwarg, and defaults. For example string.format function.
class Function(BaseKind):
    def __init__(self, posonlyargs, args, result=None, lazy_result=None):
        if not isinstance(posonlyargs, list):
            raise TypeError('Function posonlyargs must be a list.')
        if not isinstance(args, list):
            raise TypeError('Function args must be a list.')
        if any(not (isinstance(arg, tuple) and len(arg) == _PAIR_ELEMENT_COUNT) for arg in args):
            raise ValueError(f'Function args must be a list of (name, type) pairs. args={args}')
        if any(not (isinstance(name, str)) for name, _ in args):
            raise ValueError('Function args must be a list of (str, Any) tuples.')
        if lazy_result is not None and result is not None:
            raise ValueError('Pass either the result or lazy_result argument, but not both.')

        self.posonlyargs__sa = posonlyargs  # list of Type Proxy
        self.args__sa = args  # list of (name, Type Proxy)
        self._result__sa = result
        self._lazy_result__sa = lazy_result

    # TODO: implement supertype and subtype checking for function types
    def is_supertype_of__sa(self, subtype):
        if isinstance(subtype, Nothing):
            return True
        # Inconclusive, example: ???
        return None

    def is_subtype_of__sa(self, supertype):
        if isinstance(supertype, Any):
            return True
        if isinstance(supertype, Function):
            if len(self.posonlyargs__sa) != len(supertype.posonlyargs__sa):
                return False
            for p_self, p_super in zip(self.posonlyargs__sa, supertype.posonlyargs__sa, strict=False):
                if not check_subtype(p_super, p_self):
                    return False
            if len(self.args__sa) != len(supertype.args__sa):
                return False
            for (n_self, a_self), (n_super, a_super) in zip(self.args__sa, supertype.args__sa, strict=True):
                if n_self != n_super:
                    return False
                if not check_subtype(a_super, a_self):
                    return False
            if not check_subtype(self.result__sa, supertype.result__sa):
                return False
            return True
        # Inconclusive, example: ???
        return None

    def __repr__(self):
        args = [str(t) for t in self.posonlyargs__sa]
        args += [f'{name}: {typ}' for name, typ in self.args__sa]
        args_str = f'({", ".join(args)})'
        if self._lazy_result__sa:
            return f'{args_str}->[uncomputed]'
        return f'{args_str}->{self._result__sa}'

    def apply(self, *arguments):
        actual_all_args = list(arguments)
        expected_args_count = len(self.posonlyargs__sa) + len(self.args__sa)
        if len(actual_all_args) != expected_args_count:
            raise TypeError(f'Expected {expected_args_count} arguments, got {len(actual_all_args)}')
        actual_posonlyargs = actual_all_args[: len(self.posonlyargs__sa)]
        actual_args = actual_all_args[len(self.posonlyargs__sa) :]
        for p, a in zip(self.posonlyargs__sa, actual_posonlyargs, strict=False):
            if not check_subtype(a, p):
                raise TypeError(
                    f'Function positional arguments are not equal: expected={self.posonlyargs__sa} actual={actual_posonlyargs}'
                )
        for p, a in zip(self.args__sa, actual_args, strict=True):
            if not check_subtype(a, p):
                raise TypeError(f'Function arguments are not equal: expected={self.args__sa} actual={actual_args}')
        return self.result__sa

    def load__sa(self, key):
        if key == '__call__':
            return self.apply
        raise AttributeError(f'{self} function has no attribute "{key}"')

    @property
    def result__sa(self):
        self.evaluate_lazy_result__sa()
        return self._result__sa

    def evaluate_lazy_result__sa(self):
        if self._lazy_result__sa:
            self._result__sa = self._lazy_result__sa()
            self._lazy_result__sa = None


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


def create_function(args, result=None, lazy_result=None):
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
    return Function(posonlyargs=posonly, args=regular, result=result, lazy_result=lazy_result)
