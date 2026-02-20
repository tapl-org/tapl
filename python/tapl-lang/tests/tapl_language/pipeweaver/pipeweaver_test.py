# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast

from tapl_lang.lib import compiler


def test_simple_pipe():
    [ast1, ast2] = compiler.compile_tapl("""language pipeweaver
-7.3 |> print
""")
    assert ast.unparse(ast1) == """print(-7.3)"""
    assert (
        ast.unparse(ast2)
        == """from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
s0.print(-s0.Float)"""
    )


def test_complex_pipe():
    [ast1, ast2] = compiler.compile_tapl("""language pipeweaver
-7.3 |> round |> abs |> print
""")
    assert ast.unparse(ast1) == """print(abs(round(-7.3)))"""
    assert (
        ast.unparse(ast2)
        == """from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
s0.print(s0.abs(s0.round(-s0.Float)))"""
    )
