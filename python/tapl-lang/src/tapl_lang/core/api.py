# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.core import scope

ScopeProxy = scope.ScopeProxy
create_scope = scope.create_scope
add_return_type = scope.add_return_type
get_return_type = scope.get_return_type
scope_forker = scope.scope_forker
fork_scope = scope.fork_scope
