# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import logging

from tapl_lang import typelib

# ruff: noqa: T201

logging.basicConfig(level=logging.INFO)

try:

    def _inc(a):
        return a + typelib.Int_

    inc = typelib.FunctionType(_inc, a=typelib.Int_)
finally:
    pass

print(inc)
print(inc(a=typelib.Int_))


parsed_code = ast.parse(
    """
func(a, b=c, *d, **e)
""",
    mode='exec',
)
logging.info(ast.dump(parsed_code, include_attributes=False, indent=4))
compiled_code = compile(parsed_code, filename='', mode='exec')
# ruff: noqa: S307
# result = eval(compiled_code)
# logging.info(result)
