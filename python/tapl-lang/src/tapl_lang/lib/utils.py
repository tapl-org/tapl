# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Any

from tapl_lang.lib import proxy, scope, types


def get_scope_from_proxy(p: proxy.Proxy) -> scope.Scope:
    return proxy.extract_subject(p)


def create_scope(
    parent__tapl: proxy.Proxy | None = None,
    label__tapl: str | None = None,
    **kwargs: Any,
) -> proxy.Proxy:
    parent_scope = None
    if parent__tapl:
        parent_scope = get_scope_from_proxy(parent__tapl)
    current = scope.Scope(parent=parent_scope, label=label__tapl)
    current.store_many(kwargs)
    return proxy.Proxy(current)


def add_return_type(proxy: proxy.Proxy, return_type: Any) -> None:
    get_scope_from_proxy(proxy).returns.append(return_type)


def get_return_type(proxy: proxy.Proxy) -> Any:
    returns = get_scope_from_proxy(proxy).returns
    if returns:
        return types.create_union(*returns)
    return types.BUILTIN_PROXY['NoneType']


def scope_forker(proxy: proxy.Proxy) -> scope.ScopeForker:
    return scope.ScopeForker(get_scope_from_proxy(proxy))


def fork_scope(forker: scope.ScopeForker) -> proxy.Proxy:
    return proxy.Proxy(forker.new_scope())
