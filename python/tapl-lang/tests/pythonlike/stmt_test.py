# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang import syntax
from tapl_lang.chunker import chunk_text
from tapl_lang.parser import parse_text
from tapl_lang.pythonlike import parser, predef1, stmt
from tapl_lang.pythonlike.context import PythonlikeContext


def check_parsed_term(parsed: syntax.Term) -> None:
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    error_bucket: list[syntax.ErrorTerm] = syntax.gather_errors(parsed)
    if error_bucket:
        messages = [e.message for e in error_bucket]
        raise SyntaxError('\n\n'.join(messages))


def parse_stmt(text: str, *, debug=False) -> list[ast.stmt]:
    parsed = parse_text(text, parser.GRAMMAR, debug=debug)
    delayed_block = syntax.find_delayed_block(parsed)
    if delayed_block is not None:
        delayed_block.delayed = False
    check_parsed_term(parsed)
    safe_term = syntax.make_safe_term(parsed)
    layers = syntax.LayerSeparator(2).separate(safe_term)
    return [s for layer in layers for s in layer.codegen_stmt(syntax.AstSetting())]


def run_stmt(stmts: list[ast.stmt]):
    compiled_code = compile(ast.Module(body=stmts), filename='', mode='exec')
    globals_ = {'create_union': predef1.create_union, 's0': predef1.Scope(predef1.predef_scope)}
    return eval(compiled_code, globals=globals_)


def parse_module(text: str) -> list[ast.AST]:
    chunks = chunk_text(text.strip())
    context = PythonlikeContext()
    body = syntax.Block([], delayed=True)
    module = stmt.Module(body=body)
    context.parse_chunks(chunks, [module])
    check_parsed_term(module)
    ls = syntax.LayerSeparator(2)
    safe_module = syntax.make_safe_term(module)
    layers = ls.separate(safe_module)
    return [layer.codegen_ast(syntax.AstSetting()) for layer in layers]


def test_assign1():
    [stmt1, stmt2] = parse_stmt('a=1')
    assert ast.unparse(stmt1) == 'a = 1'
    assert ast.unparse(stmt2) == 's0.a = s0.Int'
    assert run_stmt([stmt2]) is None
    assert run_stmt([stmt1]) is None


def test_return1():
    [stmt1, stmt2] = parse_stmt('return')
    assert ast.unparse(stmt1) == 'return None'
    assert ast.unparse(stmt2) == 'return s0.NoneType'


def test_return2():
    [stmt1, stmt2] = parse_stmt('return True')
    assert ast.unparse(stmt1) == 'return True'
    assert ast.unparse(stmt2) == 'return s0.Bool'


def test_if():
    [stmt1, stmt2] = parse_stmt('if a == 2:')
    assert ast.unparse(stmt1) == 'if a == 2:'
    assert (
        ast.unparse(stmt2)
        == """
with predef.ScopeForker(s0) as f0:
    s1 = f0.new_scope()
    s1.a == s1.Int
    s1 = f0.new_scope()
""".strip()
    )


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
    s1 = predef.Scope(s0)
    return s1.Int
s0.hello = predef.FunctionType([], hello())
""".strip()
    )


def test_if_else_stmt():
    [stmt1, stmt2] = parse_module("""
if a == 2:
    b = 7
else:
    b = 'banana'
print(b)
""")
    assert (
        ast.unparse(stmt1)
        == """
if a == 2:
    b = 7
else:
    b = 'banana'
print(b)
""".strip()
    )
    assert (
        ast.unparse(stmt2)
        == """
with predef.ScopeForker(s0) as f0:
    s1 = f0.new_scope()
    s1.a == s1.Int
    s1.b = s1.Int
    s1 = f0.new_scope()
    s1.b = s1.Str
s0.print(s0.b)
""".strip()
    )
