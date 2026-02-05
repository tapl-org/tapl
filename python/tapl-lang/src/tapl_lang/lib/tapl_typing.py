# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import importlib
import itertools
from typing import Any

from tapl_lang.lib import builtin_types as bt
from tapl_lang.lib import kinds, scope

create_union = kinds.create_union
create_function = kinds.create_function


def import_module(scope_: scope.Scope, module_names: list[str]) -> None:
    for module_name in module_names:
        path = module_name.split('.')
        current_scope = scope_
        for name in path[:-1]:
            if not hasattr(current_scope, name):
                setattr(current_scope, name, scope.Scope(label__sa=f'{name} module'))
            current_scope = getattr(current_scope, name)
        # adding '1' suffix to module name to import the type level module
        module = importlib.import_module(f'{module_name}1')
        setattr(current_scope, path[-1], module.s0)


def create_scope(
    parent__sa: scope.Scope | None = None,
    **kwargs: Any,
) -> scope.Scope:
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
    elif not kinds.check_subtype(return_type, s.return_type__sa):
        raise TypeError(f'Return type mismatch: expected {s.return_type__sa}, got {return_type}.')


def get_return_type(s: scope.Scope) -> Any:
    if s.return_type__sa is not None:
        return s.return_type__sa
    if s.returns__sa:
        return kinds.create_union(*s.returns__sa)
    return bt.NoneType


def scope_forker(s: scope.Scope) -> scope.ScopeForker:
    return scope.ScopeForker(s)


def fork_scope(forker: scope.ScopeForker) -> scope.Scope:
    return forker.new_scope()


TO_STRING_FUNCTION = kinds.Function(posonlyargs=[], args=[], result=bt.Str)


def create_class(cls, init_args: list[Any], methods: list[tuple[str, list[Any]]]) -> kinds.Function:
    fields: dict[str, Any] = {}
    class_name = getattr(cls, 'class_name', cls.__name__)
    obj_type = kinds.Record(fields=fields, label=f'{class_name}!')
    self_methods_scope = scope.Scope()
    for method_name, param_types in methods:

        def create_lazy_result(name, types):
            return lambda: getattr(cls, name)(*(obj_type, *types))

        method = kinds.create_function(args=param_types, lazy_result=create_lazy_result(method_name, param_types))
        self_methods_scope.store__sa(method_name, method)
    self_scope = scope.Scope(parent=self_methods_scope)
    cls.__init__(*[self_scope, *init_args])
    fields.update(
        {
            '__repr__': TO_STRING_FUNCTION,
            '__str__': TO_STRING_FUNCTION,
        }
    )
    for label in itertools.chain(self_methods_scope.fields__sa.keys(), self_scope.fields__sa.keys()):
        member = self_scope.load__sa(label)
        fields[label] = member

    for member in fields.values():
        if isinstance(member, kinds.Function):
            member.evaluate_lazy_result__sa()

    return kinds.Function(posonlyargs=init_args, args=[], result=obj_type)


def create_typed_list(*element_types):
    if len(element_types) == 0:
        # TODO: Implement dynamic Any element type that can be specified at runtime (e.g., when appending Int to an empty list, element type becomes Int).
        # Maybe consider introducing an Unknown type for such cases.
        element_type = bt.Any
    elif len(element_types) == 1:
        element_type = element_types[0]
    else:
        element_type = kinds.create_union(*element_types)
    return bt.List(element_type)


def create_typed_set(*element_types):
    if len(element_types) == 0:
        element_type = bt.Any
    elif len(element_types) == 1:
        element_type = element_types[0]
    else:
        element_type = kinds.create_union(*element_types)
    return bt.Set(element_type)


def create_typed_dict(keys, values):
    if len(keys) != len(values):
        raise ValueError('Keys and values must have the same length.')
    if len(keys) == 0:
        key_type = bt.Str
        value_type = bt.Any
    elif len(keys) == 1:
        key_type, value_type = keys[0], values[0]
    else:
        key_type = kinds.create_union(*keys)
        value_type = kinds.create_union(*values)
    return bt.Dict(key_type, value_type)
