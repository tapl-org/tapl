# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""De Bruijn indices for oymomo terms: name resolution, the kernel helpers, and `reduce`.

A `BruijnIndex(i)` refers to the binder `i` lambdas out: `x -> y -> x` is `x -> y -> $1`.
Binder names stay on `Lambda.param_name`; references don't carry them.
"""

from dataclasses import replace

from oymo.core import syntax
from oymo.oymomo import terms


class BruijnError(Exception):
    def __init__(self, message: str, location: syntax.Location | None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


def resolve(term: syntax.Term) -> syntax.Term:
    """Replaces each `Variable` with the `BruijnIndex` of its binder. An unbound name is an error."""
    return _resolve(term, [])


def _resolve(term, names):
    match term:
        case terms.Variable(name=name, location=location):
            for distance, bound in enumerate(reversed(names)):
                if bound == name:
                    return terms.BruijnIndex(distance, location)
            raise BruijnError(f'Unknown name {name!r}.', location)
        case terms.Lambda(param_name=name, param_form=form, body=body):
            # The param's form is outside the param's scope.
            form = _resolve(form, names)
            names.append(name)
            try:
                return replace(term, param_form=form, body=_resolve(body, names))
            finally:
                names.pop()
    return _map_children(term, lambda child: _resolve(child, names))


def _map_children(term, f):
    """Rebuilds a term that binds nothing, with `f` applied to each child. Leaves are returned as they are."""
    match term:
        case terms.Apply(function=function, argument=argument):
            return replace(term, function=f(function), argument=f(argument))
        case terms.Struct(fields=fields):
            return replace(term, fields=[replace(field, value=f(field.value)) for field in fields])
        case terms.Project(struct=struct):
            return replace(term, struct=f(struct))
        case terms.If(condition=c, then_clause=t, else_clause=e):
            return replace(term, condition=f(c), then_clause=f(t), else_clause=f(e))
        case terms.Fix(function=function):
            return replace(term, function=f(function))
        case terms.Formed(term=inner, form=form):
            return replace(term, term=f(inner), form=f(form))
        case terms.FunctionForm(param=param, result=result):
            return replace(term, param=f(param), result=f(result))
    return term


def _map_indices(term, on_index, depth=0):
    """Rebuilds `term` with `on_index(index_term, depth)` applied to each BruijnIndex, where `depth`
    counts the lambdas entered inside `term`."""
    match term:
        case terms.BruijnIndex():
            return on_index(term, depth)
        case terms.Lambda(param_form=form, body=body):
            return replace(
                term,
                param_form=_map_indices(form, on_index, depth),
                body=_map_indices(body, on_index, depth + 1),
            )
    return _map_children(term, lambda child: _map_indices(child, on_index, depth))


def shift(term: syntax.Term, by: int, cutoff: int = 0) -> syntax.Term:
    """Adds `by` to every index that points at or beyond `cutoff` binders out of `term`."""

    def on_index(index_term, depth):
        if index_term.index >= cutoff + depth:
            return replace(index_term, index=index_term.index + by)
        return index_term

    return _map_indices(term, on_index)


def substitute(term: syntax.Term, index: int, value: syntax.Term) -> syntax.Term:
    """Replaces the references to binder `index` (seen from `term`'s root) with `value`."""

    def on_index(index_term, depth):
        if index_term.index == index + depth:
            return shift(value, depth)
        return index_term

    return _map_indices(term, on_index)


def beta(lambda_: terms.Lambda, argument: syntax.Term) -> syntax.Term:
    """`(x -> body) argument` with `argument` put in for `x`.

    The lambda's form goes with the argument: `(x : F -> body) a` puts `a : F` in for `x`.
    It replaces `a`'s own form: `(x : F -> body) a : G` puts in `a : F`, too.
    A lambda without a form puts in `a` as it is, so `a` keeps its own form, if it has one.
    """
    if lambda_.param_form is not terms.Void:
        if isinstance(argument, terms.Formed):
            argument = argument.term
        argument = terms.Formed(term=argument, form=lambda_.param_form, location=getattr(argument, 'location', None))
    return shift(substitute(lambda_.body, 0, shift(argument, 1)), -1)


def unfold(fix: terms.Fix) -> syntax.Term:
    """`fix g` becomes `g (fix g)`."""
    return terms.Apply(function=fix.function, argument=fix, location=fix.location)


def project(term: terms.Project) -> syntax.Term | None:
    """`{a = e, ...}.a` becomes `e`. None if the struct has no such label."""
    struct = term.struct
    if not isinstance(struct, terms.Struct):
        return None
    return next((field.value for field in struct.fields if field.label == term.label), None)


_TRUE, _FALSE = b'\x01', b'\x00'


def reduce(term: syntax.Term) -> syntax.Term:
    """Takes one step at the root of `term` if it is a redex, else returns `term` itself.

    Never looks inside `term` and never raises, so `reduce(t) is t` tells that the root is not a redex.
    """
    match term:
        case terms.Apply(function=terms.Lambda() as lambda_, argument=argument):
            return beta(lambda_, argument)
        case terms.Fix():
            return unfold(term)
        case terms.Project(struct=terms.Struct()):
            projected = project(term)
            return term if projected is None else projected
        case terms.If(
            condition=terms.ByteArray(value=value) | terms.Formed(term=terms.ByteArray(value=value)),
            then_clause=then_clause,
            else_clause=else_clause,
        ):
            # A form on the condition, as in `if [01]:'i1' then ...`, doesn't change which branch.
            if value == _TRUE:
                return then_clause
            if value == _FALSE:
                return else_clause
    return term
