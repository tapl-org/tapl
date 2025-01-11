# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast
from typing import cast

from tapl_lang import typelib
from tapl_lang.parser import Grammar, parse_text
from tapl_lang.pythonlike import parser
from tapl_lang.syntax import Layers


def parse_stmt(text: str, *, log_cell_memo=False) -> list[ast.stmt]:
    parsed = parse_text(text, Grammar(parser.RULES, 'statement'), log_cell_memo=log_cell_memo)
    if parsed is None:
        raise RuntimeError('Parser returns None.')
    if errors := parsed.get_errors():
        messages = [e.message for e in errors]
        raise SyntaxError('\n\n'.join(messages))
    # print(parsed)
    separated = parsed.separate()
    layers = cast(Layers, separated).layers
    return [layer.codegen_stmt() for layer in layers]


def run_stmt(stmts: list[ast.stmt], /, globals_=None, locals_=None):
    compiled_code = compile(ast.Module(body=stmts), filename='', mode='exec')
    return eval(compiled_code, globals=globals_ or {'t': typelib}, locals=locals_ or {})


def test_assign1():
    [stmt1, stmt2] = parse_stmt('a=1')
    assert ast.unparse(stmt1) == 'a = 1'
    assert ast.unparse(stmt2) == 'a = t.Int_'
    assert run_stmt([stmt2]) is None
    assert run_stmt([stmt1]) is None
