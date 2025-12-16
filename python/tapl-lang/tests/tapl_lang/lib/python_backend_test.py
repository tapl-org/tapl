# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast

from tapl_lang.core import syntax
from tapl_lang.lib import python_backend, terms


def test_generate_expr():
    backend = python_backend.AstGenerator()
    setting = syntax.BackendSetting(scope_level=0)
    term = terms.TypedName(
        location=syntax.Location(start=syntax.Position(line=1, column=0), end=syntax.Position(line=1, column=1)),
        id='x',
        ctx='load',
        mode=terms.MODE_EVALUATE,
    )
    expr = backend.try_generate_expr(term, setting)
    assert expr is None
    expr = backend.generate_expr(term, setting)
    assert isinstance(expr, ast.expr)
    assert isinstance(expr, ast.Name)
    assert expr.id == 'x'
    assert isinstance(expr.ctx, ast.Load)


def test_generate_stmt():
    backend = python_backend.AstGenerator()
    setting = syntax.BackendSetting(scope_level=0)
    term = terms.TypedReturn(
        location=syntax.Location(start=syntax.Position(line=1, column=0), end=syntax.Position(line=1, column=1)),
        value=terms.Constant(
            location=syntax.Location(start=syntax.Position(line=1, column=7), end=syntax.Position(line=1, column=9)),
            value=42,
        ),
        mode=terms.MODE_EVALUATE,
    )
    stmts = backend.try_generate_stmt(term, setting)
    assert stmts is None
    stmts = backend.generate_stmt(term, setting)
    assert isinstance(stmts, list)
    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ast.stmt)
    assert isinstance(stmt, ast.Return)
