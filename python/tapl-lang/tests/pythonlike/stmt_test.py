# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang.core import syntax
from tapl_lang.core.chunker import chunk_text
from tapl_lang.core.parser import parse_text
from tapl_lang.lib import proxy, scope, terms
from tapl_lang.pythonlike import grammar, predef1, stmt
from tapl_lang.pythonlike.language import PythonlikeLanguage


def check_parsed_term(parsed: syntax.Term) -> None:
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    error_bucket: list[syntax.ErrorTerm] = terms.gather_errors(parsed)
    if error_bucket:
        messages = [e.message for e in error_bucket]
        raise SyntaxError('\n\n'.join(messages))


def parse_stmt(text: str, *, debug=False) -> list[ast.stmt]:
    parsed = parse_text(text, grammar.get_grammar(), debug=debug)
    delayed_statements = syntax.find_delayed_statements(parsed)
    if delayed_statements is not None:
        delayed_statements.delayed = False
    check_parsed_term(parsed)
    safe_term = terms.make_safe_term(parsed)
    layers = syntax.LayerSeparator(2).build(lambda layer: layer(safe_term))
    return [s for layer in layers for s in layer.codegen_stmt(syntax.AstSetting())]


def run_stmt(stmts: list[ast.stmt]):
    compiled_code = compile(ast.Module(body=stmts), filename='', mode='exec')
    daa = proxy.Proxy(scope.Scope(parent=predef1.predef_scope))
    globals_ = {'s0': daa}
    return eval(compiled_code, globals=globals_)


def parse_module(text: str) -> list[ast.AST]:
    chunks = chunk_text(text.strip())
    language = PythonlikeLanguage()
    module = stmt.Module(header=syntax.Statements(terms=[]), body=syntax.Statements(terms=[], delayed=True))
    language.parse_chunks(chunks, [module])
    check_parsed_term(module)
    ls = syntax.LayerSeparator(2)
    safe_module = terms.make_safe_term(module)
    layers = ls.build(lambda layer: layer(safe_module))
    return [layer.codegen_ast(syntax.AstSetting()) for layer in layers]


def test_assign_name():
    [stmt1, stmt2] = parse_stmt('a=1')
    assert ast.unparse(stmt1) == 'a = 1'
    assert ast.unparse(stmt2) == 's0.a = s0.Int'
    assert run_stmt([stmt2]) is None
    assert run_stmt([stmt1]) is None


def test_assign_attribute():
    [stmt1, stmt2] = parse_stmt('a.b=1')
    assert ast.unparse(stmt1) == 'a.b = 1'
    assert ast.unparse(stmt2) == 's0.a.b = s0.Int'


def test_return1():
    [stmt1, stmt2] = parse_stmt('return')
    assert ast.unparse(stmt1) == 'return None'
    assert ast.unparse(stmt2) == 'api__tapl.add_return_type(s0, s0.NoneType)'


def test_return2():
    [stmt1, stmt2] = parse_stmt('return True')
    assert ast.unparse(stmt1) == 'return True'
    assert ast.unparse(stmt2) == 'api__tapl.add_return_type(s0, s0.Bool)'


def test_if():
    [stmt1, stmt2] = parse_stmt('if a == 2:')
    assert ast.unparse(stmt1) == 'if a == 2:'
    assert (
        ast.unparse(stmt2)
        == """
with api__tapl.scope_forker(s0) as f0:
    s1 = api__tapl.fork_scope(f0)
    s1.a == s1.Int
    s1 = api__tapl.fork_scope(f0)
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
    s1 = api__tapl.create_scope(parent__tapl=s0)
    api__tapl.add_return_type(s1, s1.Int)
    return api__tapl.get_return_type(s1)
s0.hello = s0.Function([], hello())
""".strip()
    )


def test_area_function_codegen():
    [stmt1, stmt2] = parse_module("""
def area(radius: Int):
    return 3.14 * radius * radius
""")
    assert (
        ast.unparse(stmt1)
        == """
def area(radius):
    return 3.14 * radius * radius
""".strip()
    )
    assert (
        ast.unparse(stmt2)
        == """
def area(radius):
    s1 = api__tapl.create_scope(parent__tapl=s0, radius=radius)
    api__tapl.add_return_type(s1, s1.Float * s1.radius * s1.radius)
    return api__tapl.get_return_type(s1)
s0.area = s0.Function([s0.Int], area(s0.Int))
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
with api__tapl.scope_forker(s0) as f0:
    s1 = api__tapl.fork_scope(f0)
    s1.a == s1.Int
    s1.b = s1.Int
    s1 = api__tapl.fork_scope(f0)
    s1.b = s1.Str
s0.print(s0.b)
""".strip()
    )


def test_class1():
    [stmt1, stmt2] = parse_module("""
class Circle:
    def __init__(self, radius: Float):
        self.radius = radius
""")
    assert (
        ast.unparse(stmt1)
        == """
class Circle:

    def __init__(self, radius):
        self.radius = radius
""".strip()
    )
    assert (
        ast.unparse(stmt2)
        == """
class Circle:

    def __init__(self, radius):
        s1 = api__tapl.create_scope(parent__tapl=s0, self=self, radius=radius)
        s1.self.radius = s1.radius
        return api__tapl.get_return_type(s1)
s0.Circle = api__tapl.create_scope(label__tapl='Circle')
s0.Circle_ = api__tapl.create_scope(label__tapl='Circle_')
Circle.__init__(s0.Circle_, s0.Float)
s0.Circle.__call__ = s0.Function([s0.Float], s0.Circle_)
""".strip()
    )
