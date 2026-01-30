# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang.core import syntax
from tapl_lang.core.chunker import chunk_text
from tapl_lang.core.parser import parse_text
from tapl_lang.lib import compiler, python_backend, scope, terms
from tapl_lang.pythonlike import grammar, predef1
from tapl_lang.pythonlike.language import PythonlikeLanguage


def check_parsed_term(parsed: syntax.Term) -> None:
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    error_bucket: list[syntax.ErrorTerm] = compiler.gather_errors(parsed)
    if error_bucket:
        messages = [e.message for e in error_bucket]
        raise SyntaxError('\n\n'.join(messages))


def parse_stmt(text: str, *, debug=False) -> list[ast.stmt]:
    parsed = parse_text(text, grammar.get_grammar(), debug=debug)
    placeholder = syntax.find_placeholder(parsed)
    if placeholder is not None:
        placeholder.is_placeholder = False
    check_parsed_term(parsed)
    safe_term = compiler.make_safe_term(parsed)
    layers = syntax.LayerSeparator(2).build(lambda layer: layer(safe_term))
    ast_generator = python_backend.AstGenerator()
    return [s for layer in layers for s in ast_generator.generate_stmt(layer, syntax.BackendSetting(scope_level=0))]


def run_stmt(stmts: list[ast.stmt]):
    compiled_code = compile(ast.Module(body=stmts), filename='', mode='exec')
    globals_ = {'s0': scope.Scope(parent=predef1.predef_scope)}
    return eval(compiled_code, globals=globals_)


def parse_module(text: str) -> list[ast.AST]:
    chunks = chunk_text(text.strip())
    language = PythonlikeLanguage()
    module = terms.Module(body=[syntax.TermList(terms=[], is_placeholder=True)])
    language.parse_chunks(chunks, [module])
    check_parsed_term(module)
    ls = syntax.LayerSeparator(2)
    safe_module = compiler.make_safe_term(module)
    layers = ls.build(lambda layer: layer(safe_module))
    return [python_backend.AstGenerator().generate_ast(layer, syntax.BackendSetting(scope_level=0)) for layer in layers]


def test_assign_name():
    [stmt1, stmt2] = parse_stmt('a=1')
    assert ast.unparse(stmt1) == 'a = 1'
    assert ast.unparse(stmt2) == 's0.a = s0.Int'
    assert run_stmt([stmt2]) is None
    assert run_stmt([stmt1]) is None


def test_assign_empty_list():
    [stmt1, stmt2] = parse_stmt('a=[]')
    assert ast.unparse(stmt1) == 'a = []'
    assert ast.unparse(stmt2) == 's0.a = s0.tapl_typing.create_typed_list()'
    assert run_stmt([stmt2]) is None
    assert run_stmt([stmt1]) is None


def test_assign_attribute():
    [stmt1, stmt2] = parse_stmt('a.b=1')
    assert ast.unparse(stmt1) == 'a.b = 1'
    assert ast.unparse(stmt2) == 's0.a.b = s0.Int'


def test_return1():
    [stmt1, stmt2] = parse_stmt('return')
    assert ast.unparse(stmt1) == 'return None'
    assert ast.unparse(stmt2) == 's0.tapl_typing.add_return_type(s0, s0.NoneType)'


def test_return2():
    [stmt1, stmt2] = parse_stmt('return True')
    assert ast.unparse(stmt1) == 'return True'
    assert ast.unparse(stmt2) == 's0.tapl_typing.add_return_type(s0, s0.Bool)'


def test_if():
    [stmt1, stmt2] = parse_stmt('if a == 2:')
    assert ast.unparse(stmt1) == 'if a == 2:'
    assert (
        ast.unparse(stmt2)
        == """
with s0.tapl_typing.scope_forker(s0) as f0:
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.a == s1.Int
    s1 = s0.tapl_typing.fork_scope(f0)
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
    s1 = s0.tapl_typing.create_scope(parent__sa=s0)
    s1.tapl_typing.add_return_type(s1, s1.Int)
    return s1.tapl_typing.get_return_type(s1)
s0.hello = s0.tapl_typing.create_function([], hello())
""".strip()
    )


def test_function_with_return_type():
    [stmt1, stmt2] = parse_module("""
def hello() -> Int:
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
    s1 = s0.tapl_typing.create_scope(parent__sa=s0)
    s1.hello = s1.tapl_typing.create_function([], s1.Int)
    s1.tapl_typing.set_return_type(s1, s1.Int)
    s1.tapl_typing.add_return_type(s1, s1.Int)
    return s1.tapl_typing.get_return_type(s1)
s0.hello = s0.tapl_typing.create_function([], hello())
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
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, radius=radius)
    s1.tapl_typing.add_return_type(s1, s1.Float * s1.radius * s1.radius)
    return s1.tapl_typing.get_return_type(s1)
s0.area = s0.tapl_typing.create_function([s0.Int], area(s0.Int))
""".strip()
    )


def test_untyped_function():
    [stmt1, stmt2] = parse_module("""
def greet(name):
    print('Hello, ' + name)
""")
    assert (
        ast.unparse(stmt1)
        == """
def greet(name):
    print('Hello, ' + name)
""".strip()
    )
    assert (
        ast.unparse(stmt2)
        == """
def greet(name):
    s1 = s0.tapl_typing.create_scope(parent__sa=s0, name=name)
    s1.print(s1.Str + s1.name)
    return s1.tapl_typing.get_return_type(s1)
s0.greet = greet
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
with s0.tapl_typing.scope_forker(s0) as f0:
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.a == s1.Int
    s1.b = s1.Int
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.b = s1.Str
s0.print(s0.b)
""".strip()
    )


def test_with_stmt():
    [stmt1, stmt2] = parse_module("""
with context() as b:
    b.do_something()
""")
    assert (
        ast.unparse(stmt1)
        == """
with context() as b:
    b.do_something()
""".strip()
    )
    assert (
        ast.unparse(stmt2)
        == """
with s0.context() as s0.b:
    s0.b.do_something()
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
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self, radius=radius)
        s1.self.radius = s1.radius
        return s1.tapl_typing.get_return_type(s1)
s0.Circle = s0.tapl_typing.create_class(cls=Circle, init_args=[s0.Float], methods=[])
""".strip()
    )


def test_class2():
    [stmt1, stmt2] = parse_module("""
class Dog:
    def bark(self) -> Str:
        return 'Woof! Woof!'
""")
    assert (
        ast.unparse(stmt1)
        == """
class Dog:

    def bark(self):
        return 'Woof! Woof!'
""".strip()
    )
    assert (
        ast.unparse(stmt2)
        == """
class Dog:

    def bark(self):
        s1 = s0.tapl_typing.create_scope(parent__sa=s0, self=self)
        s1.bark = s1.tapl_typing.create_function([], s1.Str)
        s1.tapl_typing.set_return_type(s1, s1.Str)
        s1.tapl_typing.add_return_type(s1, s1.Str)
        return s1.tapl_typing.get_return_type(s1)
s0.Dog = s0.tapl_typing.create_class(cls=Dog, init_args=[], methods=[('bark', [])])
""".strip()
    )


def test_try_stmt():
    [stmt1, stmt2] = parse_module("""
try:
    do_something()
except SomeError:
    handle_error()
finally:
    cleanup()
""")
    assert (
        ast.unparse(stmt1)
        == """
try:
    do_something()
except SomeError:
    handle_error()
finally:
    cleanup()
""".strip()
    )
    assert (
        ast.unparse(stmt2)
        == """
with s0.tapl_typing.scope_forker(s0) as f0:
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.do_something()
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.handle_error()
    s1 = s0.tapl_typing.fork_scope(f0)
    s1.cleanup()
""".strip()
    )
