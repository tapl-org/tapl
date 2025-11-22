# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import itertools
from typing import Any

from tapl_lang.lib import builtin_types as bt
from tapl_lang.lib import dynamic_attributes, scope, typelib

# TODO: Copy definitions from typelib where appropriate.


def create_scope(
    parent__sa: scope.Scope | None = None,
    **kwargs: Any,
) -> dynamic_attributes.DynamicAttributeMixin:
    parent_scope = None
    if parent__sa:
        parent_scope = parent__sa
    current = scope.Scope(parent=parent_scope)
    current.store_many__sa(kwargs)
    return current


def set_return_type(s: scope.Scope, return_type: Any) -> None:
    if s.returns__sa or s.return_type__sa is not None:
        raise ValueError('Return type has already been set.')
    s.return_type__sa = return_type


def add_return_type(s: scope.Scope, return_type: Any) -> None:
    if s.return_type__sa is None:
        s.returns__sa.append(return_type)
    elif not typelib.check_subtype(return_type, s.return_type__sa):
        raise TypeError(f'Return type mismatch: expected {s.return_type__sa}, got {return_type}.')


def get_return_type(s: scope.Scope) -> Any:
    if s.return_type__sa is not None:
        return s.return_type__sa
    if s.returns__sa:
        return typelib.create_union(*s.returns__sa)
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
        self_parent.store__sa(method_name, method)
    self_current = scope.Scope(parent=self_parent)
    cls.__init__(*[self_current, *init_args])
    fields = {
        '__repr__': typelib.Function(posonlyargs=[], args=[], result=bt.Str),
        '__str__': typelib.Function(posonlyargs=[], args=[], result=bt.Str),
    }
    for label in itertools.chain(self_parent.fields__sa.keys(), self_current.fields__sa.keys()):
        member = self_current.load__sa(label)
        fields[label] = member

    class_type = typelib.Record(
        fields=fields,
        title=cls.__name__[:-1],
    )
    for member in fields.values():
        if isinstance(member, typelib.Function):
            member.force__sa()

    factory = typelib.Function(posonlyargs=init_args, args=[], result=class_type)
    return class_type, factory


def create_dynamic_variables(namespace, variables):
    for var_name, var_value in variables.items():
        namespace[var_name] = var_value


def create_typed_list(*element_types):
    if len(element_types) == 0:
        # TODO: implement dynamic Any element type which can be specified at runtime. For example, when appending Int to an empty list. element type becomes Int.
        element_type = bt.Any
    elif len(element_types) == 1:
        element_type = element_types[0]
    else:
        element_type = typelib.create_union(*element_types)
    return bt.create_list_type(element_type)


def create_typed_dict(keys, values):
    if len(keys) != len(values):
        raise ValueError('Keys and values must have the same length.')
    if len(keys) == 0:
        key_type = bt.Str
        value_type = bt.Any
    elif len(keys) == 1:
        key_type, value_type = keys[0], values[0]
    else:
        key_type = typelib.create_union(*keys)
        value_type = typelib.create_union(*values)
    return bt.create_dict_type(key_type, value_type)
