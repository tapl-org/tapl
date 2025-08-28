# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

from tapl_lang.core import attribute, scope, typelib


def get_scope_from_proxy(p: attribute.Proxy) -> scope.Scope:
    return attribute.extract_subject(p)


def create_scope(
    parent__tapl: attribute.Proxy | None = None,
    label__tapl: str | None = None,
    **kwargs: Any,
) -> attribute.Proxy:
    parent_scope = None
    if parent__tapl:
        parent_scope = get_scope_from_proxy(parent__tapl)
    current = scope.Scope(parent=parent_scope, label=label__tapl)
    current.store_many(kwargs)
    return attribute.Proxy(current)


def add_return_type(proxy: attribute.Proxy, return_type: Any) -> None:
    get_scope_from_proxy(proxy).returns.append(return_type)


def get_return_type(proxy: attribute.Proxy) -> Any:
    returns = get_scope_from_proxy(proxy).returns
    if returns:
        return typelib.create_union(*returns)
    return scope.NoneType


def scope_forker(proxy: attribute.Proxy) -> scope.ScopeForker:
    return scope.ScopeForker(get_scope_from_proxy(proxy))


def fork_scope(forker: scope.ScopeForker) -> attribute.Proxy:
    return attribute.Proxy(forker.new_scope())
