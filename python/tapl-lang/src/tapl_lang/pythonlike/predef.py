# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import tapl_lang.lib.api as api__tapl

api__tapl.create_dynamic_variables(
    globals(), __import__('tapl_lang.pythonlike.builtin_functions', globals(), locals(), ['export']).export
)
