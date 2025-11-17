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
    '__lt__': '<',
    '__le__': '<=',
    '__eq__': '==',
    '__ne__': '!=',
    '__gt__': '>',
    '__ge__': '>=',
}

# The __sa suffix (static attribute) indicates fields that are skipped by the DynamicAttributeMixin


# ruff: noqa: N805
class DynamicAttributeMixin:
    """Proxy mixin for dynamic attribute access."""

    def load__sa(self, key: str) -> Any:
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def store__sa(self, key: str, value: Any) -> None:
        del value  # unused
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def delete__sa(self, key: str) -> None:
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

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

    def __repr__(self__sa):
        return self__sa.load__sa('__repr__')()

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

    def __pow__(self__sa, other):
        return self__sa.call_binop__sa('__pow__', other)

    def __lshift__(self__sa, other):
        return self__sa.call_binop__sa('__lshift__', other)

    def __rshift__(self__sa, other):
        return self__sa.call_binop__sa('__rshift__', other)

    def __or__(self__sa, other):
        return self__sa.call_binop__sa('__or__', other)

    def __xor__(self__sa, other):
        return self__sa.call_binop__sa('__xor__', other)

    def __and__(self__sa, other):
        return self__sa.call_binop__sa('__and__', other)

    def __matmul__(self__sa, other):
        return self__sa.call_binop__sa('__matmul__', other)

    def __ne__(self__sa, other):
        return self__sa.call_binop__sa('__ne__', other)

    def __lt__(self__sa, other):
        return self__sa.call_binop__sa('__lt__', other)
