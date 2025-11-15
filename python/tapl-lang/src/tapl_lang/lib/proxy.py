# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

SUBJECT_FIELD_NAME = 'subject__tapl'


class Subject:
    def load__tapl(self, key: str) -> Any:
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def store__tapl(self, key: str, value: Any) -> None:
        del value  # unused
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def delete__tapl(self, key: str) -> None:
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def subject__tapl(self):
        raise AttributeError(
            f'{self.__class__.__name__} class has no attribute "{SUBJECT_FIELD_NAME}". It is used where Proxy is expected.'
        )


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


def call_binop(op: str, left: 'Proxy', right: Any) -> Any | None:
    try:
        return left.subject__tapl.load__tapl(op)(right)
    except Exception as e:
        label = OP_LABEL.get(op, op)
        # TODO: Show the underlying exception message? #mvp
        raise TypeError(f'unsupported operand type(s) for {label}: {left} and {right}') from e


# TODO: should Proxy be renamed to TypeProxy since it mainly deals with types? or it is a python specific concept? #mvp
# ruff: noqa: N805
class Proxy:
    """A proxy providing dynamic attribute access."""

    def __init__(self__tapl, subject__tapl: Any):
        if not isinstance(subject__tapl, Subject):
            raise TypeError(f'Proxy can only wrap Subject instances, but found {type(subject__tapl)}')
        object.__setattr__(self__tapl, SUBJECT_FIELD_NAME, subject__tapl)

    def __getattr__(self__tapl, name):
        return self__tapl.subject__tapl.load__tapl(name)

    def __setattr__(self__tapl, name: str, value: Any):
        self__tapl.subject__tapl.store__tapl(name, value)

    def __delattr__(self__tapl, name: str):
        self__tapl.subject__tapl.delete__tapl(name)

    def __call__(self__tapl, *args, **kwargs):
        return self__tapl.subject__tapl.load__tapl('__call__')(*args, **kwargs)

    def __repr__(self__tapl):
        return self__tapl.subject__tapl.__repr__()

    def __add__(self__tapl, other):
        return call_binop('__add__', self__tapl, other)

    def __sub__(self__tapl, other):
        return call_binop('__sub__', self__tapl, other)

    def __mul__(self__tapl, other):
        return call_binop('__mul__', self__tapl, other)

    def __truediv__(self__tapl, other):
        return call_binop('__truediv__', self__tapl, other)

    def __floordiv__(self__tapl, other):
        return call_binop('__floordiv__', self__tapl, other)

    def __mod__(self__tapl, other):
        return call_binop('__mod__', self__tapl, other)

    def __pow__(self__tapl, other):
        return call_binop('__pow__', self__tapl, other)

    def __lshift__(self__tapl, other):
        return call_binop('__lshift__', self__tapl, other)

    def __rshift__(self__tapl, other):
        return call_binop('__rshift__', self__tapl, other)

    def __or__(self__tapl, other):
        return call_binop('__or__', self__tapl, other)

    def __xor__(self__tapl, other):
        return call_binop('__xor__', self__tapl, other)

    def __and__(self__tapl, other):
        return call_binop('__and__', self__tapl, other)

    def __matmul__(self__tapl, other):
        return call_binop('__matmul__', self__tapl, other)

    def __ne__(self__tapl, other):
        return call_binop('__ne__', self__tapl, other)

    def __lt__(self__tapl, other):
        return call_binop('__lt__', self__tapl, other)
