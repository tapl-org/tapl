# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import logging

from tapl_lang.core import typelib

# ruff: noqa: T201

logging.basicConfig(level=logging.INFO)


@typelib.function_type(typelib.Int_)
def inc(a):
    return a + typelib.Int_


print(inc)
print(inc(typelib.Int_))


parsed_code = ast.parse(
    """
s0.SimplestClass = predef.Scope(label__tapl='SimplestClass')
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
