# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang.core import syntax
from tapl_lang.lib import untyped_terms

# Unary 'not' has a dedicated 'BoolNot' term for logical negation
UNARY_OP_MAP: dict[str, ast.unaryop] = {'+': ast.UAdd(), '-': ast.USub(), 'not': ast.Not(), '~': ast.Invert()}
BIN_OP_MAP: dict[str, ast.operator] = {
    '+': ast.Add(),
    '-': ast.Sub(),
    '*': ast.Mult(),
    '/': ast.Div(),
    '//': ast.FloorDiv(),
    '%': ast.Mod(),
}
BOOL_OP_MAP: dict[str, ast.boolop] = {'and': ast.And(), 'or': ast.Or()}
COMPARE_OP_MAP: dict[str, ast.cmpop] = {
    '==': ast.Eq(),
    '!=': ast.NotEq(),
    '<': ast.Lt(),
    '<=': ast.LtE(),
    '>': ast.Gt(),
    '>=': ast.GtE(),
    'is': ast.Is(),
    'is not': ast.IsNot(),
    'in': ast.In(),
    'not in': ast.NotIn(),
}
# TODO: add class with static fields for the context keys
EXPR_CONTEXT_MAP: dict[str, ast.expr_context] = {'load': ast.Load(), 'store': ast.Store(), 'delete': ast.Del()}


def locate(location: syntax.Location, *nodes: ast.expr | ast.stmt) -> None:
    for node in nodes:
        node.lineno = location.start.line
        node.col_offset = location.start.column
    if location.end:
        for node in nodes:
            node.end_lineno = location.end.line
            node.end_col_offset = location.end.column


def generate_ast(term: syntax.Term, setting: syntax.AstSetting) -> ast.AST:
    if isinstance(term, untyped_terms.Module):
        stmts = []
        for t in term.body:
            stmts.extend(generate_stmt(t, setting))
        return ast.Module(body=stmts, type_ignores=[])
    if (unfolded := term.unfold()) and unfolded is not term:
        return generate_ast(unfolded, setting)
    # TODO: raise error once refactor complete #refactor
    return term.codegen_ast(setting)


def generate_stmt(term: syntax.Term, setting: syntax.AstSetting) -> list[ast.stmt]:
    if isinstance(term, syntax.TermList):
        stmts: list[ast.stmt] = []
        for t in term.flattened():
            stmts.extend(generate_stmt(t, setting))
        return stmts

    if isinstance(term, untyped_terms.FunctionDef):
        name = term.name(setting) if callable(term.name) else term.name
        func_def = ast.FunctionDef(
            name=name,
            args=ast.arguments(
                posonlyargs=[ast.arg(arg=name) for name in term.posonlyargs],
                args=[ast.arg(arg=name) for name in term.args],
                vararg=ast.arg(arg=term.vararg) if term.vararg else None,
                kwonlyargs=[ast.arg(arg=name) for name in term.kwonlyargs],
                kw_defaults=[generate_expr(t, setting) for t in term.kw_defaults],
                kwarg=ast.arg(arg=term.kwarg) if term.kwarg else None,
                defaults=[generate_expr(t, setting) for t in term.defaults],
            ),
            body=generate_stmt(term.body, setting),
            decorator_list=[],
            returns=None,
            type_comment=None,
        )
        locate(term.location, func_def)
        return [func_def]

    if isinstance(term, untyped_terms.Return):
        return_stmt = ast.Return(generate_expr(term.value, setting)) if term.value else ast.Return()
        locate(term.location, return_stmt)
        return [return_stmt]

    if isinstance(term, untyped_terms.Assign):
        assign_stmt = ast.Assign(
            targets=[generate_expr(t, setting) for t in term.targets],
            value=generate_expr(term.value, setting),
        )
        locate(term.location, assign_stmt)
        return [assign_stmt]

    if isinstance(term, untyped_terms.Expr):
        expr_stmt = ast.Expr(value=generate_expr(term.value, setting))
        locate(term.location, expr_stmt)
        return [expr_stmt]

    if isinstance(term, syntax.AstSettingChanger):
        new_setting = term.changer(setting)
        return generate_stmt(term.inner, new_setting)

    if (unfolded := term.unfold()) and unfolded is not term:
        return generate_stmt(unfolded, setting)
    return term.codegen_stmt(setting)


def generate_expr(term: syntax.Term, setting: syntax.AstSetting) -> ast.expr:
    if isinstance(term, untyped_terms.BoolOp):
        bool_op = ast.BoolOp(op=BOOL_OP_MAP[term.op], values=[generate_expr(v, setting) for v in term.values])
        locate(term.location, bool_op)
        return bool_op

    if isinstance(term, untyped_terms.BinOp):
        bin_op = ast.BinOp(
            left=generate_expr(term.left, setting), op=BIN_OP_MAP[term.op], right=generate_expr(term.right, setting)
        )
        locate(term.location, bin_op)
        return bin_op

    if isinstance(term, untyped_terms.UnaryOp):
        op = ast.UnaryOp(op=UNARY_OP_MAP[term.op], operand=generate_expr(term.operand, setting))
        locate(term.location, op)
        return op

    if isinstance(term, untyped_terms.Compare):
        compare = ast.Compare(
            left=generate_expr(term.left, setting),
            ops=[COMPARE_OP_MAP[op] for op in term.ops],
            comparators=[generate_expr(v, setting) for v in term.comparators],
        )
        locate(term.location, compare)
        return compare

    if isinstance(term, untyped_terms.Call):
        call = ast.Call(
            func=generate_expr(term.func, setting),
            args=[generate_expr(arg, setting) for arg in term.args],
            keywords=[ast.keyword(arg=k, value=generate_expr(v, setting)) for k, v in term.keywords],
        )
        locate(term.location, call)
        return call

    if isinstance(term, untyped_terms.Constant):
        const = ast.Constant(value=term.value)
        locate(term.location, const)
        return const

    if isinstance(term, untyped_terms.Attribute):
        attr_name = term.attr(setting) if callable(term.attr) else term.attr
        attr = ast.Attribute(
            value=generate_expr(term.value, setting),
            attr=attr_name,
            ctx=EXPR_CONTEXT_MAP[term.ctx],
        )
        locate(term.location, attr)
        return attr

    if isinstance(term, untyped_terms.Name):
        name_id = term.id(setting) if callable(term.id) else term.id
        name = ast.Name(id=name_id, ctx=EXPR_CONTEXT_MAP[term.ctx])
        locate(term.location, name)
        return name

    if isinstance(term, untyped_terms.List):
        list_expr = ast.List(
            elts=[generate_expr(elt, setting) for elt in term.elts],
            ctx=EXPR_CONTEXT_MAP[term.ctx],
        )
        locate(term.location, list_expr)
        return list_expr

    if isinstance(term, untyped_terms.Tuple):
        tuple_expr = ast.Tuple(
            elts=[generate_expr(elt, setting) for elt in term.elts],
            ctx=EXPR_CONTEXT_MAP[term.ctx],
        )
        locate(term.location, tuple_expr)
        return tuple_expr

    if isinstance(term, syntax.AstSettingChanger):
        new_setting = term.changer(setting)
        return generate_expr(term.inner, new_setting)

    if (unfolded := term.unfold()) and unfolded is not term:
        return generate_expr(unfolded, setting)
    return term.codegen_expr(setting)
