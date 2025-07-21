# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any, Self, cast

from tapl_lang.core import context, typelib
from tapl_lang.core.tapl_error import TaplError


class Scope(context.Context):
    # TODO: parent should be a Context, not a Scope
    def __init__(self, fields: dict[str, Any] | None = None, label: str | None = None, parent: Scope | None = None):
        super().__init__(fields)
        self.label = label
        self.parent = parent
        self.returns: list[Any] = []

    def find_slot(self, name: str) -> context.Slot | None:
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
            self.fields[name] = context.Slot(value)
            return
        # TODO: convert this to strategy pattern
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


def get_scope_from_proxy(proxy: context.Proxy) -> Scope:
    return cast(Scope, context.get_proxy_internal(proxy))


def create_scope(
    parent__tapl: context.Proxy | None = None,
    label__tapl: str | None = None,
    **kwargs: Any,
) -> context.Proxy:
    parent_scope = None
    if parent__tapl:
        parent_scope = get_scope_from_proxy(parent__tapl)
    current = Scope(label=label__tapl, parent=parent_scope)
    current.store_many(kwargs)
    return context.Proxy(current)


def add_return_type(proxy: context.Proxy, return_type: Any) -> None:
    get_scope_from_proxy(proxy).returns.append(return_type)


def get_return_type(proxy: context.Proxy) -> Any:
    returns = get_scope_from_proxy(proxy).returns
    if returns:
        return typelib.create_union(*returns)
    return NoneType


def scope_forker(proxy: context.Proxy) -> ScopeForker:
    return ScopeForker(get_scope_from_proxy(proxy))


def fork_scope(forker: ScopeForker) -> context.Proxy:
    return context.Proxy(forker.new_scope())


NoneType = Scope(label='NoneType')
