# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast
from typing import cast

from tapl_lang.chunker import chunk_text
from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike import parser, predef1, stmt
from tapl_lang.pythonlike.context import PythonlikeContext
from tapl_lang.syntax import ErrorTerm, Layers, LayerSeparator


def parse_stmt(text: str, *, debug=False) -> list[ast.stmt]:
    parsed = parse_text(text, Grammar(parser.RULES, 'statement'), debug=debug)
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    error_bucket: list[ErrorTerm] = []
    parsed.gather_errors(error_bucket)
    if error_bucket:
        messages = [e.message for e in error_bucket]
        raise SyntaxError('\n\n'.join(messages))
    ls = LayerSeparator(2)
    separated = ls.separate(parsed)
    separated = ls.build(lambda layer: layer(separated))
    layers = cast(Layers, separated).layers
    return [s for layer in layers for s in layer.codegen_stmt()]


def run_stmt(stmts: list[ast.stmt]):
    compiled_code = compile(ast.Module(body=stmts), filename='', mode='exec')
    globals_ = {'create_union': predef1.create_union, 'scope0': predef1.Scope(predef1.predef_scope)}
    return eval(compiled_code, globals=globals_)


def parse_module(text: str) -> list[ast.AST]:
    chunks = chunk_text(text.strip())
    context = PythonlikeContext()
    module = stmt.Module()
    context.parse_chunks(chunks, [module])
    ls = LayerSeparator(2)
    separated = ls.separate(module)
    separated = ls.build(lambda layer: layer(separated))
    layers = cast(Layers, separated).layers
    return [layer.codegen_ast() for layer in layers]


def test_assign1():
    [stmt1, stmt2] = parse_stmt('a=1')
    assert ast.unparse(stmt1) == 'a = 1'
    assert ast.unparse(stmt2) == 'scope0.a = scope0.Int'
    assert run_stmt([stmt2]) is None
    assert run_stmt([stmt1]) is None


def test_return1():
    [stmt1, stmt2] = parse_stmt('return')
    assert ast.unparse(stmt1) == 'return None'
    assert ast.unparse(stmt2) == 'return scope0.NoneType'


def test_return2():
    [stmt1, stmt2] = parse_stmt('return True')
    assert ast.unparse(stmt1) == 'return True'
    assert ast.unparse(stmt2) == 'return scope0.Bool'


def test_function1():
    [stmt1, stmt2] = parse_module("""
def hello():
    return 0
""")
    assert (
        ast.unparse(stmt1)
        == """
def hello():
    return 0
""".strip()
    )
    assert (
        ast.unparse(stmt2)
        == """
@predef.function_type()
def hello():
    return scope0.Int
""".strip()
    )
