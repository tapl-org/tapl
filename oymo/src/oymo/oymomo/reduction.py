# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Reduction of oymomo terms: name resolution to De Bruijn indices, substitution, and the
rules of Section 4 at the root (`reduce`).

A `BruijnIndex(i)` refers to the binder `i` lambdas out: `λx. λy. x` is `λx. λy. $1`.
Binder names stay on `Lambda.param_name`; references don't carry them.
"""

from dataclasses import replace

from oymo.core import syntax
from oymo.oymomo import opcodes, terms


class ReductionError(Exception):
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
            raise ReductionError(f'Unknown name {name!r}.', location)
        case terms.Lambda(param_name=name, body=body):
            names.append(name)
            try:
                return replace(term, body=_resolve(body, names))
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
        case terms.Fix(body=body):
            return replace(term, body=f(body))
    return term


def free_bound(term: syntax.Term) -> int:
    """One more than the largest index free in `term`, seen from its root: 0 for a closed term.

    Cached on the term: terms are never changed after they are built.
    """
    cached = term.__dict__.get('_free_bound')
    if cached is not None:
        return cached
    match term:
        case terms.BruijnIndex(index=index):
            bound = index + 1
        case terms.Lambda(body=body):
            bound = max(free_bound(body) - 1, 0)
        case _:
            bound = max((free_bound(child) for child in term.children()), default=0)
    term.__dict__['_free_bound'] = bound
    return bound


def _map_indices(term, on_index, threshold, depth=0):
    """Rebuilds `term` with `on_index(index_term, depth)` applied to each BruijnIndex, where `depth`
    counts the lambdas entered inside `term`.

    `on_index` must leave an index below `threshold + depth` as it is. So a subterm with no
    such index is returned itself, not rebuilt: a closed value is shared, not copied.
    """
    if free_bound(term) <= threshold + depth:
        return term
    match term:
        case terms.BruijnIndex():
            return on_index(term, depth)
        case terms.Lambda(body=body):
            return replace(term, body=_map_indices(body, on_index, threshold, depth + 1))
    return _map_children(term, lambda child: _map_indices(child, on_index, threshold, depth))


def shift(term: syntax.Term, by: int, cutoff: int = 0) -> syntax.Term:
    """Adds `by` to every index that points at or beyond `cutoff` binders out of `term`."""
    if by == 0:
        return term

    def on_index(index_term, depth):
        if index_term.index >= cutoff + depth:
            return replace(index_term, index=index_term.index + by)
        return index_term

    return _map_indices(term, on_index, cutoff)


def substitute(term: syntax.Term, index: int, value: syntax.Term) -> syntax.Term:
    """Replaces the references to binder `index` (seen from `term`'s root) with `value`."""

    def on_index(index_term, depth):
        if index_term.index == index + depth:
            return shift(value, depth)
        return index_term

    return _map_indices(term, on_index, index)


def beta(lambda_: terms.Lambda, argument: syntax.Term) -> syntax.Term:
    """`(λx. body) argument` with `argument` put in for `x`. E-Beta (`reduce`) calls it
    only on a value; it substitutes any term."""
    return shift(substitute(lambda_.body, 0, shift(argument, 1)), -1)


def is_value(term: syntax.Term) -> bool:
    """A value (2.1h): a variable, a lambda, a byte array, a struct of values, or a fixed
    point `fix (λx. t)`. A projection is never one."""
    match term:
        case terms.Variable() | terms.BruijnIndex() | terms.Lambda() | terms.ByteArray():
            return True
        case terms.Struct(fields=fields):
            return all(is_value(f.value) for f in fields)
        case terms.Fix(body=terms.Lambda()):
            return True
    return False


def is_data(term: syntax.Term) -> bool:
    """Data (2.1i): a byte array, or a struct of data. It never steps."""
    match term:
        case terms.ByteArray():
            return True
        case terms.Struct(fields=fields):
            return all(is_data(f.value) for f in fields)
    return False


def field_position(struct: terms.Struct, label: str) -> int | None:
    """The position of the first field labeled `label`, or None."""
    return next((i for i, field in enumerate(struct.fields) if field.label == label), None)


def fold_opcode(call: terms.Apply) -> syntax.Term:
    """E-Opcode: `'name' {d}` with data operands gives the result, the bytes LLVM would
    compute (`opcode.evaluate`). Returns `call` itself where it doesn't fold: an unknown
    name, an impure opcode, an operand that is not data (4.4d), or operands the opcode
    can't evaluate (no defined result in LLVM).

    Root-only: it reduces nothing. Fields are positional and labels are ignored.
    """
    opcode = opcodes.lookup(call.function)
    argument = call.argument
    if opcode is None or not opcode.pure or not isinstance(argument, terms.Struct) or not is_data(argument):
        return call
    fields = [field.value for field in argument.fields]
    if (result := opcode.evaluate(fields)) is None:
        return call
    return terms.ByteArray(result.value, call.location)


def project(struct: syntax.Term, label: str) -> syntax.Term | None:
    """`{a = e, ...}.a` becomes `e`. None if the struct has no such label."""
    if isinstance(struct, terms.Struct):
        return next((field.value for field in struct.fields if field.label == label), None)
    return None


def unfold(fixed: terms.Fix) -> syntax.Term:
    """`fix (λx. t)` unfolded once: `t` with `fix (λx. t)` put in for `x` (E-FixProj,
    E-FixApp). `fixed.body` must be a lambda."""
    if not isinstance(fixed.body, terms.Lambda):
        raise TypeError('Only a fixed point of a lambda unfolds.')
    return beta(fixed.body, fixed)


def index_value(term: syntax.Term) -> int | None:
    """The index a byte array spells, unsigned little-endian; `''` is 0 (2.4a).
    None for anything that is not a byte array."""
    if isinstance(term, terms.ByteArray):
        return int.from_bytes(term.value, 'little')
    return None


def branch(term: syntax.Term) -> tuple[syntax.Term, syntax.Term, syntax.Term] | None:
    """`(condition, then, else)` if `term` is `{e, t} c` with both fields unlabeled, else None.

    That is what `if c then t else e` parses to: `[00]` picks field 0, the else arm.
    """
    match term:
        case terms.Apply(
            function=terms.Struct(fields=[terms.Field(label='', value=e), terms.Field(label='', value=t)]),
            argument=c,
        ):
            return c, t, e
    return None


def reduce(term: syntax.Term) -> syntax.Term:
    """Takes one step at the root of `term` if it is a redex, else returns `term` itself.

    Never looks inside `term` and never raises, so `reduce(t) is t` tells that the root is not a redex.
    """
    match term:
        case terms.Apply(function=terms.Lambda() as lambda_, argument=argument) if is_value(argument):
            # E-Beta is call-by-value (4.3): a term that still has to run is never copied or dropped.
            return beta(lambda_, argument)
        case terms.Apply(function=terms.ByteArray()):
            return fold_opcode(term)
        case terms.Project(struct=terms.Fix(body=terms.Lambda()) as fixed):
            # E-FixProj: the fixed point unfolds once where it is used (4.8).
            return replace(term, struct=unfold(fixed))
        case terms.Apply(function=terms.Fix(body=terms.Lambda()) as fixed):
            # E-FixApp.
            return replace(term, function=unfold(fixed))
        case terms.Project(struct=struct, label=label) if (projected := project(struct, label)) is not None:
            return projected
        case terms.Apply(function=terms.Struct(fields=fields), argument=argument) if (
            fields and (position := index_value(argument)) is not None
        ):
            # A struct applied to an index selects the field at that position, labeled or not;
            # an index past the last field selects the last one, so the last field is a default.
            # This is also `if`: `if c then t else e` is `{e, t} c`, true for any nonzero `c`.
            return fields[min(position, len(fields) - 1)].value
    return term


def stuck_part(term: syntax.Term) -> syntax.Term | None:
    """A part of the normal form `term` that no substitution can make reduce (5.5), or None.

    A stuck part is one of: the empty struct applied (no field to select); a struct
    applied to a lambda or a struct (never a byte array); a byte array applied to a lambda
    or a byte array (no rule); a projection of a lambda or a byte array, or of a struct
    without the label; `fix b` or `fix {…}` (never a lambda). Parts are searched outermost
    first, left to right.
    """
    match term:
        case terms.Apply(function=terms.Struct(fields=[])):
            return term
        case terms.Apply(function=terms.Struct(), argument=terms.Lambda() | terms.Struct()):
            return term
        case terms.Apply(function=terms.ByteArray(), argument=terms.Lambda() | terms.ByteArray()):
            return term
        case terms.Project(struct=terms.Lambda() | terms.ByteArray()):
            return term
        case terms.Project(struct=terms.Struct() as struct, label=label) if project(struct, label) is None:
            return term
        case terms.Fix(body=terms.ByteArray() | terms.Struct()):
            return term
    for child in term.children():
        if (found := stuck_part(child)) is not None:
            return found
    return None
