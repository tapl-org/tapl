# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Renames binders of a term in BANF shape. See docs/notes.md, "Binders get fixed names".

The structural binders get fixed names, so every shaped program reads
`prim -> module -> {main = blocks -> {entry = args -> ...}}`. Any other binder keeps
its name unless that name is visible (an enclosing binder's name, or a param label of its
block); then it becomes `x_L`, `x__L`, ..., where `L` is its level. Labels are never renamed.
"""

from dataclasses import replace

from oymo.core import syntax
from oymo.oymomo import terms

PRIM = 'prim'
MODULE = 'module'
BLOCKS = 'blocks'
ARGS = 'args'


def fresh(name: str, level: int, visible: set[str]) -> str:
    """`name` if it isn't visible, else the first of `name_L`, `name__L`, ... that isn't."""
    if name not in visible:
        return name
    underscores = '_'
    while (candidate := f'{name}{underscores}{level}') in visible:
        underscores += '_'
    return candidate


def rename(term: syntax.Term) -> syntax.Term:
    return _Renamer().program(term)


class _Renamer:
    def __init__(self) -> None:
        self.visible: set[str] = set()
        self.level = 0

    def bind(self, lambda_, name, visit_body):
        """Renames `lambda_` to `name` and visits its body with `name` visible."""
        self.visible.add(name)
        self.level += 1
        try:
            return replace(lambda_, param_name=name, body=visit_body(lambda_.body))
        finally:
            self.level -= 1
            self.visible.discard(name)

    def fixed(self, term, name, visit_body):
        if isinstance(term, terms.Lambda):
            return self.bind(term, name, visit_body)
        return self.other(term)

    def program(self, term):
        return self.fixed(term, PRIM, lambda module: self.fixed(module, MODULE, self.module_body))

    def module_body(self, term):
        return self.struct_of(term, lambda func: self.fixed(func, BLOCKS, self.function_body))

    def function_body(self, term):
        return self.struct_of(term, lambda block: self.fixed(block, ARGS, self.block_body_of(block)))

    def struct_of(self, term, visit_value):
        if isinstance(term, terms.Struct):
            return replace(term, fields=[replace(f, value=visit_value(f.value)) for f in term.fields])
        return self.other(term)

    def block_body_of(self, block):
        """Visits a block body with the block's param labels visible."""
        form = block.param_form if isinstance(block, terms.Lambda) else None
        labels = [f.label for f in form.fields] if isinstance(form, terms.Struct) else []

        def visit(body):
            added = [label for label in labels if label not in self.visible]
            self.visible.update(added)
            try:
                return self.other(body)
            finally:
                self.visible.difference_update(added)

        return visit

    def other(self, term):
        """Any term outside the fixed positions: lets, and lambdas `banf_reduce` left."""
        match term:
            case terms.Lambda(param_name=name):
                return self.bind(term, fresh(name, self.level, self.visible), self.other)
            case terms.Apply(function=function, argument=argument):
                argument = self.other(argument)
                return replace(term, function=self.other(function), argument=argument)
            case terms.Struct(fields=fields):
                return replace(term, fields=[replace(f, value=self.other(f.value)) for f in fields])
            case terms.Project(struct=struct):
                return replace(term, struct=self.other(struct))
            case terms.If(condition=c, then_clause=t, else_clause=e):
                return replace(term, condition=self.other(c), then_clause=self.other(t), else_clause=self.other(e))
            case terms.Fix(function=function):
                return replace(term, function=self.other(function))
            case terms.FunctionForm(param=param, result=result):
                return replace(term, param=self.other(param), result=self.other(result))
            case terms.Formed(term=inner, form=form):
                return replace(term, term=self.other(inner), form=self.other(form))
        return term
