# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

_SUBJECT_FIELD_NAME = 'subject__tapl'


class Subject:
    def load(self, key: str) -> Any:
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def store(self, key: str, value: Any) -> None:
        del value  # unused
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')

    def delete(self, key: str) -> None:
        raise AttributeError(f'{self.__class__.__name__} class has no attribute "{key}"')


def extract_subject(p: 'Proxy') -> Any:
    """Retrieve the internal subject from a Proxy instance."""
    if isinstance(p, Proxy) is False:
        return p
    return object.__getattribute__(p, _SUBJECT_FIELD_NAME)


OP_LABEL = {
    '__add__': '+',
    '__sub__': '-',
    '__mul__': '*',
    '__truediv__': '/',
    '__floordiv__': '//',
    '__mod__': '%',
    '__lt__': '<',
    '__le__': '<=',
    '__eq__': '==',
    '__ne__': '!=',
    '__gt__': '>',
    '__ge__': '>=',
}


def call_binop(op: str, self__tapl: 'Proxy', other: Any) -> Any | None:
    left = object.__getattribute__(self__tapl, _SUBJECT_FIELD_NAME)
    right = extract_subject(other)
    try:
        return left.load(op)(right)
    except Exception as e:
        label = OP_LABEL.get(op, op)
        raise TypeError(f'unsupported operand type(s) for {label}: {left} and {right}') from e


# ruff: noqa: N805
class Proxy:
    """A proxy providing dynamic attribute access."""

    def __init__(self__tapl, subject__tapl: Any):
        if not isinstance(subject__tapl, Subject):
            raise TypeError(f'Proxy can only wrap Subject instances, but found {type(subject__tapl)}')
        object.__setattr__(self__tapl, _SUBJECT_FIELD_NAME, subject__tapl)

    def __getattribute__(self__tapl, name):
        return object.__getattribute__(self__tapl, _SUBJECT_FIELD_NAME).load(name)

    def __setattr__(self__tapl, name: str, value: Any):
        object.__getattribute__(self__tapl, _SUBJECT_FIELD_NAME).store(name, value)

    def __delattr__(self__tapl, name: str):
        object.__getattribute__(self__tapl, _SUBJECT_FIELD_NAME).delete(name)

    def __call__(self__tapl, *args, **kwargs):
        return object.__getattribute__(self__tapl, _SUBJECT_FIELD_NAME).load('__call__')(*args, **kwargs)

    def __repr__(self__tapl):
        return repr(object.__getattribute__(self__tapl, _SUBJECT_FIELD_NAME))

    def __add__(self__tapl, other):
        return call_binop('__add__', self__tapl, other)

    def __mul__(self__tapl, *args, **kwargs):
        return call_binop('__mul__', self__tapl, *args, **kwargs)

    def __lt__(self__tapl, *args, **kwargs):
        return call_binop('__lt__', self__tapl, *args, **kwargs)
