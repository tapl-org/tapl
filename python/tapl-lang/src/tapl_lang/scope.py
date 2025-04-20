# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any


class ScopeInternal:
    def __init__(self, parent: ScopeInternal | None = None, **kwargs: Any):
        self.parent = parent
        self.variables: dict[str, Any] = {}
        self.variables.update(kwargs)

    def try_load(self, name: str) -> Any | None:
        if name in self.variables:
            return self.variables[name]
        if self.parent is not None:
            return self.parent.try_load(name)
        return None

    def load(self, name: str) -> Any:
        value = self.try_load(name)
        if value is not None:
            return value
        raise AttributeError(f'Variable {name} not found in the scope.')

    def store(self, name: str, value: Any) -> None:
        stored_value = self.try_load(name)
        if stored_value is None:
            self.variables[name] = value
            return
        if stored_value != value:
            raise TypeError(f'Variable {name} already exists with a different type.')


class Scope:
    def __init__(self, parent: Scope | None = None, **kwargs: Any):
        self.internal__: ScopeInternal = ScopeInternal(parent.internal__ if parent else None, **kwargs)

    def __getattribute__(self, name):
        if name == 'internal__':
            return super().__getattribute__(name)
        return self.internal__.load(name)

    def __setattr__(self, name: str, value: Any):
        if name == 'internal__':
            # Allow setting the variables in initialization
            super().__setattr__(name, value)
        else:
            self.internal__.store(name, value)
