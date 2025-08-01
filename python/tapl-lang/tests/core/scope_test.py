# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.core import api, scope, tapl_error


def test_define_variable():
    proxy = api.ScopeProxy(scope.Scope())
    proxy.x = 42
    assert proxy.x == 42


def test_undefined_variable():
    proxy = api.ScopeProxy(scope.Scope())
    with pytest.raises(tapl_error.TaplError):
        _ = proxy.undefined_variable


def test_variable_from_parent_scope():
    parent_scope = scope.Scope()
    parent_proxy = api.ScopeProxy(parent_scope)
    parent_proxy.y = 'parent_value'
    child_proxy = api.ScopeProxy(scope.Scope(parent=parent_scope))
    assert child_proxy.y == 'parent_value'
