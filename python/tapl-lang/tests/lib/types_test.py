# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.core import tapl_error
from tapl_lang.lib import types


def test_bool_subtype_of_itself():
    assert types.is_subtype(types.BUILTIN['Bool'], types.BUILTIN['Bool'])


def test_bool_subtype_of_any():
    assert types.is_subtype(types.BUILTIN['Bool'], types.BUILTIN['Any'])


def test_any_subtype_of_bool():
    assert not types.is_subtype(types.BUILTIN['Any'], types.BUILTIN['Bool'])


def test_create_union():
    # Empty union
    assert str(types.create_union()) == 'Nothing'
    # Single type
    assert str(types.Union(types=[types.BUILTIN['Bool']])) == '[Bool]'
    assert str(types.create_union(types.BUILTIN['Bool'])) == 'Bool'
    # Multiple types
    assert str(types.create_union(types.BUILTIN['Bool'], types.BUILTIN['Int'])) == 'Bool | Int'
    # Flatten union
    type_list = [types.BUILTIN['Bool'], types.Union(types=[types.BUILTIN['Int']])]
    assert str(types.Union(types=type_list)) == 'Bool | [Int]'
    assert str(types.create_union(*type_list)) == 'Bool | Int'
    # Trim union
    type_list = [types.BUILTIN['Bool'], types.BUILTIN['Int'], types.BUILTIN['Bool']]
    assert str(types.Union(types=type_list)) == 'Bool | Int | Bool'
    assert str(types.create_union(*type_list)) == 'Bool | Int'


def test_function_parameters_invariants():
    with pytest.raises(tapl_error.TaplError, match='SyntaxError: Function parameters must be a list.'):
        types.Function(parameters=types.BUILTIN['Any'], result=types.BUILTIN['Bool'])
    with pytest.raises(tapl_error.TaplError, match='SyntaxError: positional parameter follows labeled parameter.'):
        types.Function(
            parameters=[types.Labeled('x', types.BUILTIN['Any']), types.BUILTIN['Any']], result=types.BUILTIN['Bool']
        )
