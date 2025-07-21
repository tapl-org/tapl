# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any, Self

from tapl_lang.core import typelib
from tapl_lang.core.tapl_error import TaplError


class Slot:
    def __init__(self, value: Any):
        self.value = value


class Context:
    def __init__(self, label: str | None = None, fields: dict[str, Any] | None = None):
        self.label = label
        self.fields: dict[str, Slot] = {}
        if fields:
            self.store_many(fields)

    def load(self, name: str) -> Any:
        return self.fields[name].value

    def store(self, name: str, value: Any) -> None:
        self.fields[name] = Slot(value)

    def store_many(self, fields: dict[str, Any]) -> None:
        for name, value in fields.items():
            self.store(name, value)

    def __repr__(self) -> str:
        if self.label:
            return self.label
        return object.__repr__(self)


class Scope(Context):
    def __init__(self, label: str | None = None, fields: dict[str, Any] | None = None, parent: Scope | None = None):
        super().__init__(label, fields)
        self.parent = parent
        self.returns: list[Any] = []

    def find_slot(self, name: str) -> Slot | None:
        if name in self.fields:
            return self.fields[name]
        if self.parent is not None:
            return self.parent.find_slot(name)
        return None

    def load(self, name: str) -> Any:
        slot = self.find_slot(name)
        if slot is not None:
            return slot.value
        raise TaplError(f'Variable {name} not found in the scope.')

    def store(self, name: str, value: Any) -> None:
        slot = self.find_slot(name)
        if slot is None:
            self.fields[name] = Slot(value)
            return
        if slot.value != value:
            raise TypeError(f'Variable {name} already exists with a different type.')

    def __repr__(self) -> str:
        if self.label:
            return self.label
        return f'Scope(parent={self.parent})'


class ScopeForker:
    def __init__(self, scope: Scope):
        self.parent = scope
        self.branches: list[Scope] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self.branches:
            return
        for var in self.branches[0].fields:
            values = []
            for record in self.branches:
                slot = record.fields.get(var)
                if slot is not None:
                    values.append(slot.value)
            if len(values) == len(self.branches):
                self.parent.store(var, typelib.create_union(*values))

    def new_scope(self) -> Scope:
        forked = Scope(label=f'{self.parent.label}.fork{len(self.branches)}', parent=self.parent)
        self.branches.append(forked)
        return forked


_SCOPE_FIELD_NAME = 'internal__tapl'


# ruff: noqa: N805
class ScopeProxy:
    """A scope proxy providing dynamic attribute access."""

    def __init__(self__tapl, scope__tapl: Scope):
        object.__setattr__(self__tapl, _SCOPE_FIELD_NAME, scope__tapl)

    def __getattribute__(self__tapl, name):
        return object.__getattribute__(self__tapl, _SCOPE_FIELD_NAME).load(name)

    def __setattr__(self__tapl, name: str, value: Any):
        object.__getattribute__(self__tapl, _SCOPE_FIELD_NAME).store(name, value)

    def __call__(self__tapl, *args, **kwargs):
        return object.__getattribute__(self__tapl, _SCOPE_FIELD_NAME).load('__call__')(self__tapl, *args, **kwargs)

    def __repr__(self__tapl):
        return object.__getattribute__(self__tapl, _SCOPE_FIELD_NAME).__repr__()


def create_scope(
    parent__tapl: ScopeProxy | None = None,
    label__tapl: str | None = None,
    **kwargs: Any,
) -> ScopeProxy:
    parent_scope = None
    if parent__tapl:
        parent_scope = object.__getattribute__(parent__tapl, _SCOPE_FIELD_NAME)
    current = Scope(label=label__tapl, parent=parent_scope)
    current.store_many(kwargs)
    return ScopeProxy(current)


def add_return_type(proxy: ScopeProxy, return_type: Any) -> None:
    object.__getattribute__(proxy, _SCOPE_FIELD_NAME).returns.append(return_type)


def get_return_type(proxy: ScopeProxy) -> Any:
    returns = object.__getattribute__(proxy, _SCOPE_FIELD_NAME).returns
    if returns:
        return typelib.create_union(*returns)
    return NoneType


def scope_forker(proxy: ScopeProxy) -> ScopeForker:
    return ScopeForker(object.__getattribute__(proxy, _SCOPE_FIELD_NAME))


def fork_scope(forker: ScopeForker) -> ScopeProxy:
    return ScopeProxy(forker.new_scope())


NoneType = Scope(label='NoneType')
