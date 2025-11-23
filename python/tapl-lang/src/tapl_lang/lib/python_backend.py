# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import ast

from tapl_lang.core import syntax, tapl_error
from tapl_lang.lib import terms

# Unary 'not' has a dedicated 'BoolNot' term for logical negation
UNARY_OP_MAP: dict[str, ast.unaryop] = {'+': ast.UAdd(), '-': ast.USub(), 'not': ast.Not(), '~': ast.Invert()}
BIN_OP_MAP: dict[str, ast.operator] = {
    '+': ast.Add(),
    '-': ast.Sub(),
    '*': ast.Mult(),
    '/': ast.Div(),
    '//': ast.FloorDiv(),
    '%': ast.Mod(),
    '**': ast.Pow(),
    '<<': ast.LShift(),
    '>>': ast.RShift(),
    '|': ast.BitOr(),
    '^': ast.BitXor(),
    '&': ast.BitAnd(),
    '@': ast.MatMult(),
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
EXPR_CONTEXT_MAP: dict[str, ast.expr_context] = {'load': ast.Load(), 'store': ast.Store(), 'delete': ast.Del()}


def locate(location: syntax.Location, *nodes: ast.expr | ast.stmt) -> None:
    for node in nodes:
        node.lineno = location.start.line
        node.col_offset = location.start.column
    if location.end:
        for node in nodes:
            node.end_lineno = location.end.line
            node.end_col_offset = location.end.column


class AstGenerator:
    def generate_ast(self, term: syntax.Term, setting: syntax.BackendSetting) -> ast.AST:
        if (ast_node := self.try_generate_ast(term, setting)) is not None:
            return ast_node
        if (unfolded := term.unfold()) and unfolded is not term:
            return self.generate_ast(unfolded, setting)
        raise tapl_error.TaplError(
            f'The python_backend does not support AST generation for term: {term.__class__.__name__}'
        )

    def generate_stmt(self, term: syntax.Term, setting: syntax.BackendSetting) -> list[ast.stmt]:
        if (stmts := self.try_generate_stmt(term, setting)) is not None:
            return stmts
        if (unfolded := term.unfold()) and unfolded is not term:
            return self.generate_stmt(unfolded, setting)
        raise tapl_error.TaplError(
            f'The python_backend does not support statement generation for term: {term.__class__.__name__}'
        )

    def generate_expr(self, term: syntax.Term, setting: syntax.BackendSetting) -> ast.expr:
        if (expr := self.try_generate_expr(term, setting)) is not None:
            return expr
        if (unfolded := term.unfold()) and unfolded is not term:
            return self.generate_expr(unfolded, setting)
        raise tapl_error.TaplError(
            f'The python_backend does not support expression generation for term: {term.__class__.__name__}'
        )

    def try_generate_ast(self, term: syntax.Term, setting: syntax.BackendSetting) -> ast.AST | None:
        if isinstance(term, terms.Module):
            stmts = []
            for t in term.body:
                stmts.extend(self.generate_stmt(t, setting))
            return ast.Module(body=stmts, type_ignores=[])

        if isinstance(term, syntax.BackendSettingTerm):
            new_setting = term.new_setting(setting)
            return self.generate_ast(term.term, new_setting)

        return None

    def try_generate_stmt(self, term: syntax.Term, setting: syntax.BackendSetting) -> list[ast.stmt] | None:
        if isinstance(term, syntax.TermList):
            if term.is_placeholder:
                raise tapl_error.TaplError('The placeholder list must be initialized before code generation.')
            stmts: list[ast.stmt] = []
            for t in term.flattened():
                stmts.extend(self.generate_stmt(t, setting))
            return stmts

        if term is syntax.Empty:
            return []

        if isinstance(term, terms.FunctionDef):
            name = term.name(setting) if callable(term.name) else term.name
            func_def = ast.FunctionDef(
                name=name,
                args=ast.arguments(
                    posonlyargs=[ast.arg(arg=name) for name in term.posonlyargs],
                    args=[ast.arg(arg=name) for name in term.args],
                    vararg=ast.arg(arg=term.vararg) if term.vararg else None,
                    kwonlyargs=[ast.arg(arg=name) for name in term.kwonlyargs],
                    kw_defaults=[self.generate_expr(t, setting) for t in term.kw_defaults],
                    kwarg=ast.arg(arg=term.kwarg) if term.kwarg else None,
                    defaults=[self.generate_expr(t, setting) for t in term.defaults],
                ),
                body=self.generate_stmt(term.body, setting),
                decorator_list=[],
                returns=None,
                type_comment=None,
            )
            locate(term.location, func_def)
            return [func_def]

        if isinstance(term, terms.ClassDef):
            name = term.name(setting) if callable(term.name) else term.name
            class_def = ast.ClassDef(
                name=name,
                bases=[self.generate_expr(b, setting) for b in term.bases],
                keywords=[ast.keyword(arg=k, value=self.generate_expr(v, setting)) for k, v in term.keywords],
                body=[],
                decorator_list=[self.generate_expr(d, setting) for d in term.decorator_list],
            )
            locate(term.location, class_def)
            # FIXME: body should be a list of term??? for improving usability
            class_def.body = []
            for t in term.body:
                class_def.body.extend(self.generate_stmt(t, setting))
            return [class_def]

        if isinstance(term, terms.Return):
            return_stmt = ast.Return(self.generate_expr(term.value, setting)) if term.value else ast.Return()
            locate(term.location, return_stmt)
            return [return_stmt]

        if isinstance(term, terms.Delete):
            delete_stmt = ast.Delete(
                targets=[self.generate_expr(t, setting) for t in term.targets],
            )
            locate(term.location, delete_stmt)
            return [delete_stmt]

        if isinstance(term, terms.Assign):
            assign_stmt = ast.Assign(
                targets=[self.generate_expr(t, setting) for t in term.targets],
                value=self.generate_expr(term.value, setting),
            )
            locate(term.location, assign_stmt)
            return [assign_stmt]

        if isinstance(term, terms.For):
            for_stmt = ast.For(
                target=self.generate_expr(term.target, setting),
                iter=self.generate_expr(term.iter, setting),
                body=self.generate_stmt(term.body, setting),
                orelse=self.generate_stmt(term.orelse, setting) if term.orelse else [],
                type_comment=None,
            )
            locate(term.location, for_stmt)
            return [for_stmt]

        if isinstance(term, terms.While):
            while_stmt = ast.While(
                test=self.generate_expr(term.test, setting),
                body=self.generate_stmt(term.body, setting),
                orelse=self.generate_stmt(term.orelse, setting),
            )
            locate(term.location, while_stmt)
            return [while_stmt]

        if isinstance(term, terms.If):
            if_stmt = ast.If(
                test=self.generate_expr(term.test, setting),
                body=self.generate_stmt(term.body, setting),
                orelse=self.generate_stmt(term.orelse, setting),
            )
            locate(term.location, if_stmt)
            return [if_stmt]

        if isinstance(term, terms.With):
            items = []
            for item in term.items:
                if isinstance(item, terms.WithItem):
                    items.append(
                        ast.withitem(
                            context_expr=self.generate_expr(item.context_expr, setting),
                            optional_vars=self.generate_expr(item.optional_vars, setting),
                        )
                    )
                else:
                    raise tapl_error.TaplError(
                        f'Unsupported with item type: {item.__class__.__name__} in python backend.'
                    )
            with_stmt = ast.With(
                items=items,
                body=self.generate_stmt(term.body, setting),
                type_comment=None,
            )
            locate(term.location, with_stmt)
            return [with_stmt]

        if isinstance(term, terms.Try):
            handlers = []
            for h in term.handlers:
                if isinstance(h, terms.ExceptHandler):
                    optional_name = h.name(setting) if callable(h.name) else h.name
                    handlers.append(
                        ast.ExceptHandler(
                            type=self.generate_expr(h.exception_type, setting) if h.exception_type else None,
                            name=optional_name,
                            body=self.generate_stmt(h.body, setting),
                        )
                    )
                else:
                    raise tapl_error.TaplError(
                        f'Unsupported except handler type: {h.__class__.__name__} in python backend.'
                    )
            try_stmt = ast.Try(
                body=self.generate_stmt(term.body, setting),
                handlers=handlers,
                orelse=self.generate_stmt(term.orelse, setting),
                finalbody=self.generate_stmt(term.finalbody, setting),
            )
            locate(term.location, try_stmt)
            return [try_stmt]

        if isinstance(term, terms.Import):
            import_stmt = ast.Import(names=[ast.alias(name=n.name, asname=n.asname) for n in term.names])
            locate(term.location, import_stmt)
            return [import_stmt]

        if isinstance(term, terms.ImportFrom):
            import_from = ast.ImportFrom(
                module=term.module,
                names=[ast.alias(name=n.name, asname=n.asname) for n in term.names],
                level=term.level,
            )
            locate(term.location, import_from)
            return [import_from]

        if isinstance(term, terms.Expr):
            expr_stmt = ast.Expr(value=self.generate_expr(term.value, setting))
            locate(term.location, expr_stmt)
            return [expr_stmt]

        if isinstance(term, syntax.BackendSettingTerm):
            new_setting = term.new_setting(setting)
            return self.generate_stmt(term.term, new_setting)

        if isinstance(term, terms.Pass):
            pass_stmt = ast.Pass()
            locate(term.location, pass_stmt)
            return [pass_stmt]

        return None

    def try_generate_expr(self, term: syntax.Term, setting: syntax.BackendSetting) -> ast.expr | None:
        if isinstance(term, terms.BoolOp):
            bool_op = ast.BoolOp(
                op=BOOL_OP_MAP[term.operator], values=[self.generate_expr(v, setting) for v in term.values]
            )
            locate(term.location, bool_op)
            return bool_op

        if isinstance(term, terms.BinOp):
            bin_op = ast.BinOp(
                left=self.generate_expr(term.left, setting),
                op=BIN_OP_MAP[term.op],
                right=self.generate_expr(term.right, setting),
            )
            locate(term.location, bin_op)
            return bin_op

        if isinstance(term, terms.UnaryOp):
            op = ast.UnaryOp(op=UNARY_OP_MAP[term.op], operand=self.generate_expr(term.operand, setting))
            locate(term.location, op)
            return op

        if isinstance(term, terms.Dict):
            dict_expr = ast.Dict(
                keys=[self.generate_expr(k, setting) for k in term.keys],
                values=[self.generate_expr(v, setting) for v in term.values],
            )
            locate(term.location, dict_expr)
            return dict_expr

        if isinstance(term, terms.Compare):
            compare = ast.Compare(
                left=self.generate_expr(term.left, setting),
                ops=[COMPARE_OP_MAP[op] for op in term.operators],
                comparators=[self.generate_expr(v, setting) for v in term.comparators],
            )
            locate(term.location, compare)
            return compare

        if isinstance(term, terms.Call):
            call = ast.Call(
                func=self.generate_expr(term.func, setting),
                args=[self.generate_expr(arg, setting) for arg in term.args],
                keywords=[ast.keyword(arg=k, value=self.generate_expr(v, setting)) for k, v in term.keywords],
            )
            locate(term.location, call)
            return call

        if isinstance(term, terms.Constant):
            const = ast.Constant(value=term.value)
            locate(term.location, const)
            return const

        if isinstance(term, terms.Attribute):
            attr_name = term.attr(setting) if callable(term.attr) else term.attr
            attr = ast.Attribute(
                value=self.generate_expr(term.value, setting),
                attr=attr_name,
                ctx=EXPR_CONTEXT_MAP[term.ctx],
            )
            locate(term.location, attr)
            return attr

        if isinstance(term, terms.Subscript):
            subscript = ast.Subscript(
                value=self.generate_expr(term.value, setting),
                slice=self.generate_expr(term.slice, setting),
                ctx=EXPR_CONTEXT_MAP[term.ctx],
            )
            locate(term.location, subscript)
            return subscript

        if isinstance(term, terms.Name):
            name_id = term.id(setting) if callable(term.id) else term.id
            name = ast.Name(id=name_id, ctx=EXPR_CONTEXT_MAP[term.ctx])
            locate(term.location, name)
            return name

        if isinstance(term, terms.List):
            list_expr = ast.List(
                elts=[self.generate_expr(elt, setting) for elt in term.elements],
                ctx=EXPR_CONTEXT_MAP[term.ctx],
            )
            locate(term.location, list_expr)
            return list_expr

        if isinstance(term, terms.Tuple):
            tuple_expr = ast.Tuple(
                elts=[self.generate_expr(elt, setting) for elt in term.elements],
                ctx=EXPR_CONTEXT_MAP[term.ctx],
            )
            locate(term.location, tuple_expr)
            return tuple_expr

        if isinstance(term, syntax.BackendSettingTerm):
            new_setting = term.new_setting(setting)
            return self.generate_expr(term.term, new_setting)

        return None
