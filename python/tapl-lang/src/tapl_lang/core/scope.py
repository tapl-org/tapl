# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any, Self

from tapl_lang.core import typelib
from tapl_lang.core.attribute import Proxy, get_proxy_subject
from tapl_lang.core.tapl_error import TaplError


class Slot:
    def __init__(self, value: Any):
        self.value = value


class Scope:
    def __init__(self, parent: Scope | None = None, fields: dict[str, Any] | None = None, label: str | None = None):
        self.parent = parent
        self.fields: dict[str, Slot] = {}
        if fields:
            self.store_many(fields)
        self.label = label
        # TODO: move returns into fields
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
        # TODO: convert this to strategy pattern
        if slot.value != value:
            raise TypeError(f'Variable {name} already exists with a different type.')

    def store_many(self, fields: dict[str, Any]) -> None:
        for name, value in fields.items():
            self.store(name, value)

    def __repr__(self) -> str:
        if '__repr__' in self.fields:
            return self.fields['__repr__'].value()
        if self.label:
            return self.label
        if self.parent is None:
            return f'Scope(parent={self.parent})'
        return object.__repr__(self)

    def __getitem__(self, key):
        return self.load(key)

    def __setitem__(self, key, value):
        self.store(key, value)

    def __delitem__(self, key):
        del self.fields[key]


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
        forked = Scope(parent=self.parent, label=f'{self.parent}.fork{len(self.branches)}')
        self.branches.append(forked)
        return forked


def get_scope_from_proxy(proxy: Proxy) -> Scope:
    return get_proxy_subject(proxy)


def create_scope(
    parent__tapl: Proxy | None = None,
    label__tapl: str | None = None,
    **kwargs: Any,
) -> Proxy:
    parent_scope = None
    if parent__tapl:
        parent_scope = get_scope_from_proxy(parent__tapl)
    current = Scope(parent=parent_scope, label=label__tapl)
    current.store_many(kwargs)
    return Proxy(current)


def add_return_type(proxy: Proxy, return_type: Any) -> None:
    get_scope_from_proxy(proxy).returns.append(return_type)


def get_return_type(proxy: Proxy) -> Any:
    returns = get_scope_from_proxy(proxy).returns
    if returns:
        return typelib.create_union(*returns)
    return NoneType


def scope_forker(proxy: Proxy) -> ScopeForker:
    return ScopeForker(get_scope_from_proxy(proxy))


def fork_scope(forker: ScopeForker) -> Proxy:
    return Proxy(forker.new_scope())


NoneType = Scope(label='NoneType')
