# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang import syntax
import ast


parsed_code = ast.parse('2+3', mode='eval')
print(ast.dump(parsed_code))
compiled_code = compile(parsed_code, filename='', mode='eval')
result = eval(compiled_code)
print(result)