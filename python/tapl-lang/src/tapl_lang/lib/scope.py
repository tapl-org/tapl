# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any, Self

from tapl_lang.lib import dynamic_attributes, typelib


class Slot:
    def __init__(self, value: Any):
        self.value = value


class Scope(dynamic_attributes.DynamicAttributeMixin):
    def __init__(self, parent: Scope | None = None, fields: dict[str, Any] | None = None, label: str | None = None):
        self.parent__tapl = parent
        self.fields__tapl: dict[str, Slot] = {}
        if fields:
            self.store_many__tapl(fields)
        # TODO: do we need label? #mvp
        self.label__tapl = label
        # TODO: move returns into fields. Find a better way to represent function return types
        self.return_type__tapl = None
        self.returns__tapl: list[Any] = []

    def find_slot__tapl(self, name: str) -> Slot | None:
        if name in self.fields__tapl:
            return self.fields__tapl[name]
        if self.parent__tapl is not None:
            return self.parent__tapl.find_slot__tapl(name)
        return None

    def load__tapl(self, name: str) -> Any:
        slot = self.find_slot__tapl(name)
        if slot is not None:
            return slot.value
        return super().load__tapl(name)

    def store__tapl(self, name: str, value: Any) -> None:
        slot = self.find_slot__tapl(name)
        if slot is None:
            self.fields__tapl[name] = Slot(value)
            return
        if not typelib.check_subtype(value, slot.value):
            raise TypeError(f'Type error in variable "{name}": Expected type "{slot.value}", but found "{value}".')

    def store_many__tapl(self, fields: dict[str, Any]) -> None:
        for name, value in fields.items():
            self.store__tapl(name, value)

    def __repr__(self) -> str:
        if '__repr__' in self.fields__tapl:
            return self.fields__tapl['__repr__'].value()
        if self.label__tapl:
            return self.label__tapl
        if self.parent__tapl is None:
            return f'Scope(parent={self.parent__tapl})'
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
        for var in self.branches[0].fields__tapl:
            values = []
            for record in self.branches:
                slot = record.fields__tapl.get(var)
                if slot is not None:
                    values.append(slot.value)
            if len(values) == len(self.branches):
                self.parent.store__tapl(var, typelib.create_union(*values))

    def new_scope(self) -> Scope:
        forked = Scope(parent=self.parent, label=f'{self.parent}.fork{len(self.branches)}')
        self.branches.append(forked)
        return forked
