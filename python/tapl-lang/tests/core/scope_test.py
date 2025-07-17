# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.core import scope, tapl_error


def test_define_variable():
    daa = scope.ScopeProxy(scope.Scope())
    daa.x = 42
    assert daa.x == 42


def test_undefined_variable():
    daa = scope.ScopeProxy(scope.Scope())
    with pytest.raises(tapl_error.TaplError):
        _ = daa.undefined_variable


def test_variable_from_parent_scope():
    parent_scope = scope.Scope()
    parent_scope_daa = scope.ScopeProxy(parent_scope)
    parent_scope_daa.y = 'parent_value'
    child_scope_daa = scope.ScopeProxy(scope.Scope(parent=parent_scope))
    assert child_scope_daa.y == 'parent_value'
