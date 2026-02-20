# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.lib import scope, tapl_dev

s0 = scope.Scope(fields={'log': tapl_dev.log, 'describe': tapl_dev.describe}, label__sa=__name__)
