# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

OP_LABEL = {
    '__add__': '+',
    '__sub__': '-',
    '__mul__': '*',
    '__truediv__': '/',
    '__floordiv__': '//',
    '__mod__': '%',
    '__pow__': '**',
    '__lshift__': '<<',
    '__rshift__': '>>',
    '__or__': '|',
    '__xor__': '^',
    '__and__': '&',
    '__matmul__': '@',
    # Comparison operators
    '__eq__': '==',
    '__ne__': '!=',
    '__lt__': '<',
    '__le__': '<=',
    '__gt__': '>',
    '__ge__': '>=',
}

# The __sa suffix (static attribute) indicates fields that are skipped by the DynamicAttributeMixin


# ruff: noqa: N805
class DynamicAttributeMixin:
    """Proxy mixin for dynamic attribute access."""

    def get_label__sa(self) -> str:
        return f'{self.__class__.__name__} class'

    def load__sa(self, key: str) -> Any:
        raise NotImplementedError(
            f'{self.__class__.__name__} class does not support loading attribute: {self.get_label__sa()}.{key}'
        )

    def store__sa(self, key: str, value: Any) -> None:
        del value  # unused
        raise NotImplementedError(
            f'{self.__class__.__name__} class does not support storing attribute: {self.get_label__sa()}.{key}'
        )

    def delete__sa(self, key: str) -> None:
        raise NotImplementedError(
            f'{self.__class__.__name__} class does not support deleting attribute: {self.get_label__sa()}.{key}'
        )

    def call_binop__sa(left, op: str, right: Any) -> Any | None:
        try:
            return left.load__sa(op)(right)
        except Exception as e:
            label = OP_LABEL.get(op, op)
            raise TypeError(f'unsupported operand type(s) for {label}: {left} and {right}. {e}') from e

    def __getattr__(self__sa, name):
        return self__sa.load__sa(name)

    def __setattr__(self__sa, name: str, value: Any):
        if name.endswith('__sa'):
            super().__setattr__(name, value)
        else:
            self__sa.store__sa(name, value)

    def __delattr__(self__sa, name: str):
        if name.endswith('__sa'):
            super().__delattr__(name)
        else:
            self__sa.delete__sa(name)

    def __call__(self__sa, *args, **kwargs):
        return self__sa.load__sa('__call__')(*args, **kwargs)

    # Numeric methods
    def __trunc__(self__sa):
        return self__sa.load__sa('__trunc__')()

    def __floor__(self__sa):
        return self__sa.load__sa('__floor__')()

    def __ceil__(self__sa):
        return self__sa.load__sa('__ceil__')()

    def __round__(self__sa, n: int = 0):
        return self__sa.load__sa('__round__')(n)

    def __invert__(self__sa):
        return self__sa.load__sa('__invert__')()

    def __neg__(self__sa):
        return self__sa.load__sa('__neg__')()

    def __pos__(self__sa):
        return self__sa.load__sa('__pos__')()

    def __abs__(self__sa):
        return self__sa.load__sa('__abs__')()

    def __int__(self__sa):
        return self__sa.load__sa('__int__')()

    def __float__(self__sa):
        return self__sa.load__sa('__float__')()

    def __complex__(self__sa):
        return self__sa.load__sa('__complex__')()

    def __index__(self__sa):
        return self__sa.load__sa('__index__')()

    # Arithmetic operators

    def __add__(self__sa, other):
        return self__sa.call_binop__sa('__add__', other)

    def __sub__(self__sa, other):
        return self__sa.call_binop__sa('__sub__', other)

    def __mul__(self__sa, other):
        return self__sa.call_binop__sa('__mul__', other)

    def __truediv__(self__sa, other):
        return self__sa.call_binop__sa('__truediv__', other)

    def __floordiv__(self__sa, other):
        return self__sa.call_binop__sa('__floordiv__', other)

    def __mod__(self__sa, other):
        return self__sa.call_binop__sa('__mod__', other)

    def __divmod__(self__sa, other):
        return self__sa.load__sa('__divmod__')(other)

    def __pow__(self__sa, other):
        return self__sa.call_binop__sa('__pow__', other)

    def __lshift__(self__sa, other):
        return self__sa.call_binop__sa('__lshift__', other)

    def __rshift__(self__sa, other):
        return self__sa.call_binop__sa('__rshift__', other)

    def __and__(self__sa, other):
        return self__sa.call_binop__sa('__and__', other)

    def __or__(self__sa, other):
        return self__sa.call_binop__sa('__or__', other)

    def __xor__(self__sa, other):
        return self__sa.call_binop__sa('__xor__', other)

    def __matmul__(self__sa, other):
        return self__sa.call_binop__sa('__matmul__', other)

    # String methods

    # TODO: Python __str__ method has special handling
    # def __str__(self__sa):
    #     return self__sa.load__sa('__str__')()

    def __repr__(self__sa):
        return self__sa.load__sa('__repr__')()

    def __unicode__(self__sa):
        return self__sa.load__sa('__unicode__')()

    # TODO: Python __format__ method has special handling
    # def __format__(self__sa, format_spec):
    #     return self__sa.load__sa('__format__')(format_spec)

    # Python __hash__ and __eq__ methods have special handling, so we manually dispatch them to __hash__sa and __eq__sa methods.
    # def __hash__(self__sa):
    #     return self__sa.load__sa('__hash__')()

    def __nonzero__(self__sa):
        return self__sa.load__sa('__nonzero__')()

    def __dir__(self__sa):
        return self__sa.load__sa('__dir__')()

    def __sizeof__(self__sa):
        return self__sa.load__sa('__sizeof__')()

    # Comparison operators

    # Python __hash__ and __eq__ methods have special handling, so we manually dispatch them to __hash__sa and __eq__sa methods.
    # def __eq__(self__sa, other):
    #     return self__sa.call_binop__sa('__eq__', other)  # operator: ==

    def __ne__(self__sa, other):
        return self__sa.call_binop__sa('__ne__', other)  # operator: !=

    def __lt__(self__sa, other):
        return self__sa.call_binop__sa('__lt__', other)  # operator: <

    def __le__(self__sa, other):
        return self__sa.call_binop__sa('__le__', other)  # operator: <=

    def __gt__(self__sa, other):
        return self__sa.call_binop__sa('__gt__', other)  # operator: >

    def __ge__(self__sa, other):
        return self__sa.call_binop__sa('__ge__', other)  # operator: >=

    # Subscript operators
    def __getitem__(self__sa, key):
        return self__sa.load__sa('__getitem__')(key)

    def __setitem__(self__sa, key, value):
        return self__sa.load__sa('__setitem__')(key, value)

    def __delitem__(self__sa, key):
        return self__sa.load__sa('__delitem__')(key)

    def __contains__(self__sa, item):
        return self__sa.load__sa('__contains__')(item)
