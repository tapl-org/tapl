# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.lib import builtin_types, kinds

_any = builtin_types.Any
_bool = builtin_types.Bool
_int = builtin_types.Int
_float = builtin_types.Float


def test_bool_subtype_of_itself():
    assert kinds.check_subtype(_bool, _bool)


def test_bool_subtype_of_any():
    assert kinds.check_subtype(_bool, _any)


def test_any_subtype_of_bool():
    assert not kinds.check_subtype(_any, _bool)


def union_len(union: kinds.Union) -> int:
    return len(list(union.iter_types__sa()))


def test_create_union():
    # Multiple types
    union = kinds.create_union(_bool, _int)
    union_types = list(union.iter_types__sa())
    assert len(union_types) == 2
    assert union_types[0] is _bool
    assert union_types[1] is _int
    # Flatten union
    type_list = [_bool, kinds.Union(types=[_int, _float])]
    assert union_len(kinds.Union(types=type_list)) == 2
    assert union_len(kinds.create_union(*type_list)) == 3
    # Trim union
    type_list = [_bool, _int, _bool]
    assert union_len(kinds.Union(types=type_list)) == 3
    assert union_len(kinds.create_union(*type_list)) == 2


def test_function_parameters_invariants():
    with pytest.raises(TypeError, match=r'Function posonlyargs must be a list\.'):
        kinds.Function(posonlyargs=_any, args=[], result=_bool)
    with pytest.raises(ValueError, match=r'Function args must be a list of \(name, type\) pairs\.'):
        kinds.Function(
            posonlyargs=[],
            args=[('x', _any), _bool],
            result=_bool,
        )


def test_lazy_function_result():
    func = kinds.Function(posonlyargs=[_int], args=[], lazy_result=lambda: _bool)
    assert func.result__sa is _bool
