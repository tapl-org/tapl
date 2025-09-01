# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.core import tapl_error
from tapl_lang.lib import types


def test_bool_subtype_of_itself():
    assert types.can_be_used_as(types.BUILTIN['Bool'], types.BUILTIN['Bool'])


def test_bool_subtype_of_any():
    assert types.can_be_used_as(types.BUILTIN['Bool'], types.BUILTIN['Any'])


def test_any_subtype_of_bool():
    assert not types.can_be_used_as(types.BUILTIN['Any'], types.BUILTIN['Bool'])


def test_create_union():
    _bool = types.BUILTIN['Bool']
    _int = types.BUILTIN['Int']
    _float = types.BUILTIN['Float']
    # Multiple types
    union = types.create_union(_bool, _int).subject__tapl
    union_types = list(union)
    assert len(union_types) == 2
    assert union_types[0] is _bool
    assert union_types[1] is _int
    # Flatten union
    type_list = [_bool, types.Union(types=[_int, _float])]
    assert len(list(types.Union(types=type_list))) == 2
    assert len(list(types.create_union(*type_list).subject__tapl)) == 3
    # Trim union
    type_list = [_bool, _int, _bool]
    assert len(list(types.Union(types=type_list))) == 3
    assert len(list(types.create_union(*type_list).subject__tapl)) == 2


def test_function_parameters_invariants():
    with pytest.raises(tapl_error.TaplError, match='Function parameters must be a list.'):
        types.Function(parameters=types.BUILTIN['Any'], result=types.BUILTIN['Bool'])
    with pytest.raises(tapl_error.TaplError, match='Positional parameter follows labeled parameter.'):
        types.Function(
            parameters=[types.Labeled('x', types.BUILTIN['Any']), types.BUILTIN['Any']],
            result=types.BUILTIN['Bool'],
        )


# Union(None | Any) should be only Any
