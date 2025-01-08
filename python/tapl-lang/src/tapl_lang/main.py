# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import logging

logging.basicConfig(level=logging.INFO)

parsed_code = ast.parse(
    """
import ast
print2('hello', line=False, **s)
""",
    mode='exec',
)
logging.info(ast.dump(parsed_code, include_attributes=True, indent=3))
compiled_code = compile(parsed_code, filename='', mode='exec')
# ruff: noqa: S307
# result = eval(compiled_code)
# logging.info(result)
