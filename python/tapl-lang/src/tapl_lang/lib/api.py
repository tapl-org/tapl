# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import utils

# TODO: rename this to just 'Proxy'
ScopeProxy = utils.attribute.Proxy
create_scope = utils.create_scope
add_return_type = utils.add_return_type
get_return_type = utils.get_return_type
scope_forker = utils.scope_forker
fork_scope = utils.fork_scope
