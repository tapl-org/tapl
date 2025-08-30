# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any, Self

from tapl_lang.core import tapl_error
from tapl_lang.lib import proxy, types


class Slot:
    def __init__(self, value: Any):
        self.value = value


class Scope(proxy.Subject):
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
        raise tapl_error.TaplError(f'Variable {name} not found in the scope.')

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
                self.parent.store(var, types.create_union(*values))

    def new_scope(self) -> Scope:
        forked = Scope(parent=self.parent, label=f'{self.parent}.fork{len(self.branches)}')
        self.branches.append(forked)
        return forked
