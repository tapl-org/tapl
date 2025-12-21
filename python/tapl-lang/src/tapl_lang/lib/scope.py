# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any, Self

from tapl_lang.lib import dynamic_attribute, typelib


class Slot:
    def __init__(self, value: Any):
        self.value = value


class Scope(dynamic_attribute.DynamicAttributeMixin):
    def __init__(self, parent: Scope | None = None, fields: dict[str, Any] | None = None, label__sa: str | None = None):
        self.parent__sa = parent
        self.fields__sa: dict[str, Slot] = {}
        if fields:
            self.store_many__sa(fields)
        # TODO: move returns into fields. Find a better way to represent function return types
        self.return_type__sa = None
        self.returns__sa: list[Any] = []
        self.label__sa = label__sa

    def find_slot__sa(self, name: str) -> Slot | None:
        if name in self.fields__sa:
            return self.fields__sa[name]
        if self.parent__sa is not None:
            return self.parent__sa.find_slot__sa(name)
        return None

    def load__sa(self, name: str) -> Any:
        slot = self.find_slot__sa(name)
        if slot is not None:
            return slot.value
        return super().load__sa(name)

    def store__sa(self, name: str, value: Any) -> None:
        slot = self.find_slot__sa(name)
        if slot is None:
            self.fields__sa[name] = Slot(value)
            return
        if not typelib.check_subtype(value, slot.value):
            raise TypeError(f'Type error in variable "{name}": Expected type "{slot.value}", but found "{value}".')

    def store_many__sa(self, fields: dict[str, Any]) -> None:
        for name, value in fields.items():
            self.store__sa(name, value)

    def get_label__sa(self) -> str:
        if self.label__sa:
            return self.label__sa
        if self.parent__sa is None:
            return 'Global Scope'
        return f'Scope({self.parent__sa.get_label__sa()})'

    def __repr__(self) -> str:
        if '__repr__' in self.fields__sa:
            return self.fields__sa['__repr__'].value()
        if self.label__sa:
            return self.label__sa
        if self.parent__sa is None:
            return f'Scope(parent={self.parent__sa})'
        return object.__repr__(self)


class ScopeForker:
    def __init__(self, scope: Scope):
        self.parent = scope
        self.branches: list[Scope] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self.branches:
            raise RuntimeError('No branches were created in the scope forker.')
        for var in self.branches[0].fields__sa:
            values = []
            for record in self.branches:
                slot = record.fields__sa.get(var)
                if slot is not None:
                    values.append(slot.value)
            if len(values) == len(self.branches):
                self.parent.store__sa(var, typelib.create_union(*values))

    def new_scope(self) -> Scope:
        forked = Scope(parent=self.parent)
        self.branches.append(forked)
        return forked
