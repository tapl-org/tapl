# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.lib import builtin_types, typelib

_any = builtin_types.Any
_bool = builtin_types.Bool
_int = builtin_types.Int
_float = builtin_types.Float


def test_bool_subtype_of_itself():
    assert typelib.check_subtype(_bool, _bool)


def test_bool_subtype_of_any():
    assert typelib.check_subtype(_bool, _any)


def test_any_subtype_of_bool():
    assert not typelib.check_subtype(_any, _bool)


def test_create_union():
    # Multiple types
    union = typelib.create_union(_bool, _int)
    union_types = list(union)
    assert len(union_types) == 2
    assert union_types[0] is _bool
    assert union_types[1] is _int
    # Flatten union
    type_list = [_bool, typelib.Union(types=[_int, _float])]
    assert len(list(typelib.Union(types=type_list))) == 2
    assert len(list(typelib.create_union(*type_list))) == 3
    # Trim union
    type_list = [_bool, _int, _bool]
    assert len(list(typelib.Union(types=type_list))) == 3
    assert len(list(typelib.create_union(*type_list))) == 2


def test_function_parameters_invariants():
    with pytest.raises(TypeError, match='Function posonlyargs must be a list.'):
        typelib.Function(posonlyargs=_any, args=[], result=_bool)
    with pytest.raises(ValueError, match='Function args must be a list of \\(name, type\\) pairs.'):
        typelib.Function(
            posonlyargs=[],
            args=[('x', _any), _bool],
            result=_bool,
        )


def test_lazy_function_result():
    func = typelib.Function(posonlyargs=[_int], args=[], lazy_result=lambda: _bool)
    assert func.result__sa is _bool
