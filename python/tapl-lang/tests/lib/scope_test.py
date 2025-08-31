# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import api, scope


def test_variable_from_parent_scope():
    parent_scope = scope.Scope()
    parent_proxy = api.Proxy(parent_scope)
    parent_proxy.y = 'parent_value'
    child_proxy = api.Proxy(scope.Scope(parent=parent_scope))
    assert child_proxy.y == 'parent_value'
