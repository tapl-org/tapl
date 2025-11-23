# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

globals().update(__import__('tapl_lang.pythonlike.builtin_functions', globals(), locals(), ['export']).export)
