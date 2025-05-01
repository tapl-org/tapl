# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.core.scope import Scope


def test_define_variable():
    scope = Scope()
    scope.x = 42
    assert scope.x == 42


def test_undefined_variable():
    scope = Scope()
    with pytest.raises(AttributeError):
        _ = scope.undefined_variable


def test_variable_from_parent_scope():
    parent_scope = Scope()
    parent_scope.y = 'parent_value'
    child_scope = Scope(parent_scope)
    assert child_scope.y == 'parent_value'
