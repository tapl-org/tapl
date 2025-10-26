# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import itertools
from typing import Any

from tapl_lang.lib import builtin_types, proxy, scope, typelib


def get_scope_from_proxy(p: proxy.Proxy) -> scope.Scope:
    return p.subject__tapl


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
        return typelib.create_union(*returns)
    return builtin_types.Types['NoneType']


def scope_forker(proxy: proxy.Proxy) -> scope.ScopeForker:
    return scope.ScopeForker(get_scope_from_proxy(proxy))


def fork_scope(forker: scope.ScopeForker) -> proxy.Proxy:
    return proxy.Proxy(forker.new_scope())


def create_class(
    cls, init_args: list[proxy.Proxy], methods: list[tuple[str, list[proxy.Proxy]]]
) -> tuple[proxy.Proxy, proxy.Proxy]:
    class_type_proxy = proxy.Proxy(typelib.Interim())
    self_parent = scope.Scope()
    for method_name, param_types in methods:

        def create_lazy_result(name, types):
            return lambda: getattr(cls, name)(*(class_type_proxy, *types))

        method = typelib.Function(
            posonlyargs=[], args=param_types, lazy_result=create_lazy_result(method_name, param_types)
        )
        self_parent.store(method_name, proxy.Proxy(method))
    self_current = scope.Scope(parent=self_parent)
    cls.__init__(*[proxy.Proxy(self_current), *init_args])
    fields = {
        '__repr__': proxy.Proxy(typelib.Function(posonlyargs=[], args=[], result=builtin_types.Str)),
        '__str__': proxy.Proxy(typelib.Function(posonlyargs=[], args=[], result=builtin_types.Str)),
    }
    for label in itertools.chain(self_parent.fields.keys(), self_current.fields.keys()):
        member = self_current.load(label)
        fields[label] = member

    class_type = typelib.Record(
        fields=fields,
        title=cls.__name__[:-1],
    )
    object.__setattr__(class_type_proxy, proxy.SUBJECT_FIELD_NAME, class_type)
    for type_proxy in fields.values():
        member = type_proxy.subject__tapl
        if isinstance(member, typelib.Function):
            member.force()

    factory = typelib.Function(posonlyargs=init_args, args=[], result=class_type_proxy)
    return class_type_proxy, proxy.Proxy(factory)


def create_dynamic_variables(namespace, variables):
    for var_name, var_value in variables.items():
        namespace[var_name] = var_value
