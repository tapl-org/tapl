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

    def load__tapl(self, key: str) -> Any:
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def store__tapl(self, key: str, value: Any) -> None:
        del value  # unused
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def delete__tapl(self, key: str) -> None:
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def call_binop__tapl(left, op: str, right: Any) -> Any | None:
        try:
            return left.load__tapl(op)(right)
        except Exception as e:
            label = OP_LABEL.get(op, op)
            raise TypeError(f'unsupported operand type(s) for {label}: {left} and {right}. {e}') from e

    def __getattr__(self__tapl, name):
        return self__tapl.load__tapl(name)

    def __setattr__(self__tapl, name: str, value: Any):
        if name.endswith('__tapl'):
            super().__setattr__(name, value)
        else:
            self__tapl.store__tapl(name, value)

    def __delattr__(self__tapl, name: str):
        if name.endswith('__tapl'):
            super().__delattr__(name)
        else:
            self__tapl.delete__tapl(name)

    def __call__(self__tapl, *args, **kwargs):
        return self__tapl.load__tapl('__call__')(*args, **kwargs)

    def __repr__(self__tapl):
        return self__tapl.load__tapl('__repr__')()

    def __add__(self__tapl, other):
        return self__tapl.call_binop__tapl('__add__', other)

    def __sub__(self__tapl, other):
        return self__tapl.call_binop__tapl('__sub__', other)

    def __mul__(self__tapl, other):
        return self__tapl.call_binop__tapl('__mul__', other)

    def __truediv__(self__tapl, other):
        return self__tapl.call_binop__tapl('__truediv__', other)

    def __floordiv__(self__tapl, other):
        return self__tapl.call_binop__tapl('__floordiv__', other)

    def __mod__(self__tapl, other):
        return self__tapl.call_binop__tapl('__mod__', other)

    def __pow__(self__tapl, other):
        return self__tapl.call_binop__tapl('__pow__', other)

    def __lshift__(self__tapl, other):
        return self__tapl.call_binop__tapl('__lshift__', other)

    def __rshift__(self__tapl, other):
        return self__tapl.call_binop__tapl('__rshift__', other)

    def __or__(self__tapl, other):
        return self__tapl.call_binop__tapl('__or__', other)

    def __xor__(self__tapl, other):
        return self__tapl.call_binop__tapl('__xor__', other)

    def __and__(self__tapl, other):
        return self__tapl.call_binop__tapl('__and__', other)

    def __matmul__(self__tapl, other):
        return self__tapl.call_binop__tapl('__matmul__', other)

    def __ne__(self__tapl, other):
        return self__tapl.call_binop__tapl('__ne__', other)

    def __lt__(self__tapl, other):
        return self__tapl.call_binop__tapl('__lt__', other)
