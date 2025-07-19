# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

from tapl_lang.core import scope, typelib

_SCOPE_FIELD_NAME = 'internal__tapl'


# ruff: noqa: N805
class ScopeProxy:
    """A scope proxy providing dynamic attribute access."""

    def __init__(self__tapl, scope__tapl: scope.Scope):
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
    current = scope.Scope(label=label__tapl, parent=parent_scope)
    current.store_many(kwargs)
    return ScopeProxy(current)


def add_return_type(proxy: ScopeProxy, return_type: Any) -> None:
    object.__getattribute__(proxy, _SCOPE_FIELD_NAME).returns.append(return_type)


def get_return_type(proxy: ScopeProxy) -> Any:
    returns = object.__getattribute__(proxy, _SCOPE_FIELD_NAME).returns
    if returns:
        return typelib.create_union(*returns)
    return scope.NoneType


def scope_forker(proxy: ScopeProxy) -> scope.ScopeForker:
    return scope.ScopeForker(object.__getattribute__(proxy, _SCOPE_FIELD_NAME))


def fork_scope(forker: scope.ScopeForker) -> ScopeProxy:
    return ScopeProxy(forker.new_scope())
