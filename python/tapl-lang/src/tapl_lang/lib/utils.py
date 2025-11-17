# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import itertools
from typing import Any

from tapl_lang.lib import builtin_types as bt
from tapl_lang.lib import proxy, scope, typelib


def create_scope(
    parent__tapl: scope.Scope | None = None,
    label__tapl: str | None = None,
    **kwargs: Any,
) -> proxy.ProxyMixin:
    parent_scope = None
    if parent__tapl:
        parent_scope = parent__tapl
    current = scope.Scope(parent=parent_scope, label=label__tapl)
    current.store_many__tapl(kwargs)
    return current


def set_return_type(s: scope.Scope, return_type: Any) -> None:
    if s.returns__tapl or s.return_type__tapl is not None:
        raise ValueError('Return type has already been set.')
    s.return_type__tapl = return_type


def add_return_type(s: scope.Scope, return_type: Any) -> None:
    if s.return_type__tapl is None:
        s.returns__tapl.append(return_type)
    elif not typelib.check_subtype(return_type, s.return_type__tapl):
        raise TypeError(f'Return type mismatch: expected {s.return_type__tapl}, got {return_type}.')


def get_return_type(s: scope.Scope) -> Any:
    if s.return_type__tapl is not None:
        return s.return_type__tapl
    if s.returns__tapl:
        return typelib.create_union(*s.returns__tapl)
    return bt.NoneType


def scope_forker(s: scope.Scope) -> scope.ScopeForker:
    return scope.ScopeForker(s)


def fork_scope(forker: scope.ScopeForker) -> scope.Scope:
    return forker.new_scope()


def create_class(
    cls, init_args: list[Any], methods: list[tuple[str, list[Any]]]
) -> tuple[typelib.Record, typelib.Function]:
    class_type = typelib.Record(fields={}, title=cls.__name__[:-1])
    self_parent = scope.Scope()
    for method_name, param_types in methods:

        def create_lazy_result(name, types):
            return lambda: getattr(cls, name)(*(class_type, *types))

        method = typelib.Function(
            posonlyargs=[], args=param_types, lazy_result=create_lazy_result(method_name, param_types)
        )
        self_parent.store__tapl(method_name, method)
    self_current = scope.Scope(parent=self_parent)
    cls.__init__(*[self_current, *init_args])
    fields = {
        '__repr__': typelib.Function(posonlyargs=[], args=[], result=bt.Str),
        '__str__': typelib.Function(posonlyargs=[], args=[], result=bt.Str),
    }
    for label in itertools.chain(self_parent.fields__tapl.keys(), self_current.fields__tapl.keys()):
        member = self_current.load__tapl(label)
        fields[label] = member

    class_type = typelib.Record(
        fields=fields,
        title=cls.__name__[:-1],
    )
    for member in fields.values():
        if isinstance(member, typelib.Function):
            member.force__tapl()

    factory = typelib.Function(posonlyargs=init_args, args=[], result=class_type)
    return class_type, factory


def create_dynamic_variables(namespace, variables):
    for var_name, var_value in variables.items():
        namespace[var_name] = var_value


def create_typed_list(*element_types) -> proxy.ProxyMixin:
    if len(element_types) == 0:
        # TODO: implement dynamic Any element type which can be specified at runtime. For example, when appending Int to an empty list. element type becomes Int.
        element_type = bt.Any
    elif len(element_types) == 1:
        element_type = element_types[0]
    else:
        element_type = typelib.create_union(*element_types)
    return bt.create_list_type(element_type)
