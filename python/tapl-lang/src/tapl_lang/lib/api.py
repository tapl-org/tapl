# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import dynamic_attributes, typelib, utils

Proxy = dynamic_attributes.ProxyMixin
create_scope = utils.create_scope
set_return_type = utils.set_return_type
add_return_type = utils.add_return_type
get_return_type = utils.get_return_type
scope_forker = utils.scope_forker
fork_scope = utils.fork_scope
create_union = typelib.create_union
create_function = typelib.create_function
create_class = utils.create_class
print_log = print
create_dynamic_variables = utils.create_dynamic_variables
create_typed_list = utils.create_typed_list
