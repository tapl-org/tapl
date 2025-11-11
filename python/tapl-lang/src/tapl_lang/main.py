# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import logging

# ruff: noqa: T201

logging.basicConfig(level=logging.INFO)


parsed_code = ast.parse(
    """
if a:= first:
    return 1
elif b:
    return 2
elif c:
    return 4
else:
    return 3
""",
    mode='exec',
)
logging.info(ast.dump(parsed_code, include_attributes=False, indent=4))
compiled_code = compile(parsed_code, filename='', mode='exec')
# ruff: noqa: S307
# result = eval(compiled_code)
# logging.info(result)


class MyMeta(type):
    def __call__(cls, *args, **kwargs):
        print('Custom __call__ in metaclass')
        instance = super().__call__(*args, **kwargs)
        print('Instance created')
        return instance


class MyClass(metaclass=MyMeta):
    def __init__(self):
        print('Inside __init__')
