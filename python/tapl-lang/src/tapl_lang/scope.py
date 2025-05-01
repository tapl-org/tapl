# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

from typing import Any, Self

from tapl_lang import typelib


class ScopeInternal:
    def __init__(self, parent: ScopeInternal | None = None, **kwargs: Any):
        self.parent = parent
        self.variables: dict[str, Any] = {}
        self.variables.update(kwargs)
        self.returns: list[Any] = []

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
        self.internal__tapl: ScopeInternal = ScopeInternal(parent.internal__tapl if parent else None, **kwargs)

    def __getattribute__(self, name):
        if name == 'internal__tapl':
            return super().__getattribute__(name)
        return self.internal__tapl.load(name)

    def __setattr__(self, name: str, value: Any):
        if name == 'internal__tapl':
            # Allow setting the variables in initialization
            super().__setattr__(name, value)
        else:
            self.internal__tapl.store(name, value)


class ScopeForker:
    def __init__(self, scope: Scope):
        self.parent_scope = scope
        self.forked_scopes: list[Scope] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self.forked_scopes:
            return
        for var in self.forked_scopes[0].internal__tapl.variables:
            values = []
            for scope in self.forked_scopes:
                value = scope.internal__tapl.variables.get(var)
                if value is not None:
                    values.append(value)
            if len(values) == len(self.forked_scopes):
                self.parent_scope.internal__tapl.store(var, typelib.create_union(*values))

    def new_scope(self) -> Scope:
        forked = Scope(self.parent_scope)
        self.forked_scopes.append(forked)
        return forked


def add_return_type(scope: Scope, return_type: Any) -> None:
    scope.internal__tapl.returns.append(return_type)


def get_return_type(scope: Scope) -> Any:
    if scope.internal__tapl.returns:
        return typelib.create_union(*scope.internal__tapl.returns)
    return typelib.NoneType_
