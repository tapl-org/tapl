# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.core import tapl_error
from tapl_lang.lib import builtin, typelib

_any = builtin.Types['Any']
_bool = builtin.Types['Bool']
_int = builtin.Types['Int']
_float = builtin.Types['Float']


def test_bool_subtype_of_itself():
    assert typelib.can_be_used_as(_bool, _bool)


def test_bool_subtype_of_any():
    assert typelib.can_be_used_as(_bool, _any)


def test_any_subtype_of_bool():
    assert not typelib.can_be_used_as(_any, _bool)


def test_create_union():
    # Multiple types
    union = typelib.create_union(_bool, _int).subject__tapl
    union_types = list(union)
    assert len(union_types) == 2
    assert union_types[0] is _bool
    assert union_types[1] is _int
    # Flatten union
    type_list = [_bool, typelib.Union(types=[_int, _float])]
    assert len(list(typelib.Union(types=type_list))) == 2
    assert len(list(typelib.create_union(*type_list).subject__tapl)) == 3
    # Trim union
    type_list = [_bool, _int, _bool]
    assert len(list(typelib.Union(types=type_list))) == 3
    assert len(list(typelib.create_union(*type_list).subject__tapl)) == 2


def test_function_parameters_invariants():
    with pytest.raises(tapl_error.TaplError, match='Function parameters must be a list.'):
        typelib.Function(parameters=_any, result=_bool)
    with pytest.raises(tapl_error.TaplError, match='Positional parameter follows labeled parameter.'):
        typelib.Function(
            parameters=[typelib.Labeled('x', _any), _bool],
            result=_bool,
        )


# Union(None | Any) should be only Any
