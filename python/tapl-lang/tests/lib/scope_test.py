# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.lib import builtin_types, proxy, scope


def test_variable_from_parent_scope():
    parent_scope = scope.Scope()
    parent_proxy = proxy.Proxy(parent_scope)
    parent_proxy.y = 'parent_value'
    child_proxy = proxy.Proxy(scope.Scope(parent=parent_scope))
    assert child_proxy.y == 'parent_value'


def test_reassign_variable():
    s = scope.Scope()
    s.store('x', builtin_types.Int)
    assert s.load('x') == builtin_types.Int
    s.store('x', builtin_types.Int)
    assert s.load('x') == builtin_types.Int
    with pytest.raises(TypeError, match='Variable x already exists with a different type. Old: Int, new: Str'):
        s.store('x', builtin_types.Str)
