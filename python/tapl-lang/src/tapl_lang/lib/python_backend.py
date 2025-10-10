# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang.core import syntax
from tapl_lang.lib import untyped_terms


def locate(location: syntax.Location, *nodes: ast.expr | ast.stmt) -> None:
    for node in nodes:
        node.lineno = location.start.line
        node.col_offset = location.start.column
    if location.end:
        for node in nodes:
            node.end_lineno = location.end.line
            node.end_col_offset = location.end.column


def codegen_ast(term: syntax.Term, setting: syntax.AstSetting) -> ast.AST:
    if isinstance(term, untyped_terms.Module):
        stmts = []
        for t in term.body:
            stmts.extend(codegen_stmt(t, setting))
        return ast.Module(body=stmts, type_ignores=[])
    return term.codegen_ast(setting)


def codegen_stmt(term: syntax.Term, setting: syntax.AstSetting) -> list[ast.stmt]:
    if isinstance(term, syntax.TermList):
        stmts: list[ast.stmt] = []
        for t in term.flattened():
            stmts.extend(codegen_stmt(t, setting))
        return stmts
    if isinstance(term, untyped_terms.FunctionDef):
        func_def = ast.FunctionDef(
            name=term.name,
            args=ast.arguments(
                posonlyargs=[ast.arg(arg=name) for name in term.posonlyargs],
                args=[ast.arg(arg=name) for name in term.args],
                vararg=ast.arg(arg=term.vararg) if term.vararg else None,
                kwonlyargs=[ast.arg(arg=name) for name in term.kwonlyargs],
                kw_defaults=[codegen_expr(t, setting) for t in term.kw_defaults],
                kwarg=ast.arg(arg=term.kwarg) if term.kwarg else None,
                defaults=[codegen_expr(t, setting) for t in term.defaults],
            ),
            body=codegen_stmt(term.body, setting),
            decorator_list=[],
            returns=None,
            type_comment=None,
        )
        locate(term.location, func_def)
        return [func_def]
    return term.codegen_stmt(setting)


def codegen_expr(term: syntax.Term, setting: syntax.AstSetting) -> ast.expr:
    if isinstance(term, untyped_terms.Constant):
        const = ast.Constant(value=term.value)
        locate(term.location, const)
        return const
    if isinstance(term, untyped_terms.Name):
        name = ast.Name(id=term.id, ctx=ast.Load())
        locate(term.location, name)
        return name
    if isinstance(term, untyped_terms.Attribute):
        attr = ast.Attribute(
            value=codegen_expr(term.value, setting),
            attr=term.attr,
            ctx=ast.Load(),
        )
        locate(term.location, attr)
        return attr
    return term.codegen_expr(setting)
