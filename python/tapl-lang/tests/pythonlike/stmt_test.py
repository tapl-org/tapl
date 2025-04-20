# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang import syntax
from tapl_lang.chunker import chunk_text
from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike import parser, predef1, stmt
from tapl_lang.pythonlike.context import PythonlikeContext


def check_parsed_term(parsed: syntax.Term) -> None:
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    error_bucket: list[syntax.ErrorTerm] = []
    parsed.gather_errors(error_bucket)
    if error_bucket:
        messages = [e.message for e in error_bucket]
        raise SyntaxError('\n\n'.join(messages))


def parse_stmt(text: str, *, debug=False) -> list[ast.stmt]:
    parsed = parse_text(text, Grammar(parser.RULES, 'statement'), debug=debug)
    check_parsed_term(parsed)
    safe_term = syntax.make_safe_term(parsed)
    layers = syntax.LayerSeparator(2).separate(safe_term)
    return [s for layer in layers for s in layer.codegen_stmt(syntax.AstSetting())]


def run_stmt(stmts: list[ast.stmt]):
    compiled_code = compile(ast.Module(body=stmts), filename='', mode='exec')
    globals_ = {'create_union': predef1.create_union, 'scope0': predef1.Scope(predef1.predef_scope)}
    return eval(compiled_code, globals=globals_)


def parse_module(text: str) -> list[ast.AST]:
    chunks = chunk_text(text.strip())
    context = PythonlikeContext()
    module = stmt.Module()
    context.parse_chunks(chunks, [module])
    ls = syntax.LayerSeparator(2)
    safe_module = syntax.make_safe_term(module)
    layers = ls.separate(safe_module)
    return [layer.codegen_ast(syntax.AstSetting()) for layer in layers]


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
def hello():
    scope1 = predef.Scope(scope0)
    return scope1.Int
scope0.hello = predef.FunctionType([], hello())
""".strip()
    )
