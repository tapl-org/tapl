# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


def create_dynamic_variables(namespace, variables):
    for var_name, var_value in variables.items():
        namespace[var_name] = var_value
