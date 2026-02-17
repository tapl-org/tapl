# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


parsed_code = ast.parse(
    """
def a(b=1, /, c=3, d=4, *e, f, **g):
    pass
""",
    mode='exec',
)
logger.info(ast.dump(parsed_code, include_attributes=False, indent=4))
compiled_code = compile(parsed_code, filename='', mode='exec')
logger.info(ast.unparse(parsed_code))
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
