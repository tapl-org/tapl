# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Reduction of oymomo terms: name resolution to De Bruijn indices, substitution, the built-in rules, and `reduce`.

A `BruijnIndex(i)` refers to the binder `i` lambdas out: `x -> y -> x` is `x -> y -> $1`.
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

    The lambda's form goes with the argument: `(x~F -> body) a` puts `a~F` in for `x`.
    It replaces `a`'s own form: `(x~F -> body) a~G` puts in `a~F`, too.
    A lambda without a form puts in `a` as it is, so `a` keeps its own form, if it has one.
    """
    if lambda_.param_form is not terms.Empty:
        if isinstance(argument, terms.Formed):
            argument = argument.term
        argument = terms.Formed(term=argument, form=lambda_.param_form, location=getattr(argument, 'location', None))
    return shift(substitute(lambda_.body, 0, shift(argument, 1)), -1)


BUILTINS = frozenset({'fix', 'struct_to_fields', 'fields_to_struct'})
"""The kernel-only built-ins: each must reduce away before BANF. Opcodes (`'add' {...}`) are
not built-ins: `fold_opcode` folds them.

Each fires in `reduce` only once its argument has the constructor it needs (a lambda, a
struct, a literal list of fields). Reducing the argument to it is the kernel's job
(`banf_shape`).
"""


def to_field_list(struct: terms.Struct) -> terms.Struct:
    """`{l1 = e1, ..., ln = en}` as a list of fields, in order:
    `{more = [01], label = 'l1', value = e1, rest = ... {more = [00]}}`.

    A label is its name's UTF-8 bytes, with no form (`''` for an unlabeled field). Values
    are kept as they are, unreduced.
    """
    location = struct.location
    field_list = terms.Struct([terms.Field('more', terms.ByteArray(b'\x00'))], location)
    for field in reversed(struct.fields):
        field_list = terms.Struct(
            [
                terms.Field('more', terms.ByteArray(b'\x01')),
                terms.Field('label', terms.ByteArray(field.label.encode())),
                terms.Field('value', field.value),
                terms.Field('rest', field_list),
            ],
            location,
        )
    return field_list


def field_position(struct: terms.Struct, label: str) -> int | None:
    """The position of the first field labeled `label`, or None."""
    return next((i for i, field in enumerate(struct.fields) if field.label == label), None)


def bytes_of(term: syntax.Term) -> bytes | None:
    """The bytes of a byte array, with a form on it ignored. None for anything else."""
    match term:
        case terms.ByteArray(value=value) | terms.Formed(term=terms.ByteArray(value=value)):
            return value
    return None


def from_field_list(field_list: syntax.Term) -> terms.Struct | None:
    """The struct a literal list of fields spells (the reverse of `to_field_list`), or None.

    Each node must be a struct with `more = [00]` (the end), or `more = [01]` and a `label`
    of valid UTF-8, a `value` and a `rest`. A form on `more` or `label` is ignored; extra
    fields are ignored; the first of two equal labels in a node counts.
    """
    fields = []
    node = field_list
    while True:
        if not isinstance(node, terms.Struct) or (more := field_position(node, 'more')) is None:
            return None
        match bytes_of(node.fields[more].value):
            case b'\x00':
                return terms.Struct(fields, getattr(field_list, 'location', None))
            case b'\x01':
                pass
            case _:
                return None
        label, value, rest = (field_position(node, name) for name in ('label', 'value', 'rest'))
        if label is None or value is None or rest is None:
            return None
        name = bytes_of(node.fields[label].value)
        if name is None:
            return None
        try:
            fields.append(terms.Field(name.decode(), node.fields[value].value))
        except UnicodeDecodeError:
            return None
        node = node.fields[rest].value


def fold_opcode(call: terms.Apply) -> syntax.Term:
    """`'name' {fields}` on literals gives the result: the bytes LLVM would compute
    (`opcode.evaluate`), formed as the opcode's result (`opcode.form_of`). Returns `call`
    itself where it doesn't fold: an unknown name, an impure opcode, or fields the opcode
    can't evaluate (a run-time operand, no defined result in LLVM).

    Root-only: it reduces nothing. The argument must already be a struct literal; reducing
    it to one, and its fields, is the kernel's job (`banf_shape`). Fields are positional and
    labels are ignored.
    """
    opcode = opcodes.lookup(call.function)
    argument = call.argument
    if opcode is None or not opcode.pure or not isinstance(argument, terms.Struct):
        return call
    fields = [field.value for field in argument.fields]
    if (result := opcode.evaluate(fields)) is None or (form := opcode.form_of(fields)) is None:
        return call
    return terms.Formed(terms.ByteArray(result.value, call.location), form, call.location)


def project(term: terms.Project) -> syntax.Term | None:
    """`{a = e, ...}.a` becomes `e`. None if the struct has no such label."""
    struct = term.struct
    if not isinstance(struct, terms.Struct):
        return None
    return next((field.value for field in struct.fields if field.label == term.label), None)


def index_value(term: syntax.Term) -> int | None:
    """The index a byte array spells, unsigned little-endian. A form on it is ignored.

    None for `''` and for anything that is not a (formed) byte array.
    """
    match term:
        case terms.ByteArray(value=value) | terms.Formed(term=terms.ByteArray(value=value)) if value:
            return int.from_bytes(value, 'little')
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
        case terms.Apply(function=terms.Lambda() as lambda_, argument=argument):
            return beta(lambda_, argument)
        case terms.Apply(function=terms.ByteArray()):
            return fold_opcode(term)
        case terms.Apply(function=terms.Builtin(name='fix'), argument=terms.Lambda() as g):
            # `$fix g` becomes `g ($fix g)`.
            return terms.Apply(g, term, term.location)
        case terms.Apply(function=terms.Builtin(name='struct_to_fields'), argument=terms.Struct() as struct):
            return to_field_list(struct)
        case terms.Apply(function=terms.Builtin(name='fields_to_struct'), argument=field_list) if (
            struct := from_field_list(field_list)
        ) is not None:
            return struct
        case terms.Project(struct=terms.Struct()):
            projected = project(term)
            return term if projected is None else projected
        case terms.Apply(function=terms.Struct(fields=fields), argument=argument) if (
            fields and (position := index_value(argument)) is not None
        ):
            # A struct applied to an index selects the field at that position, labeled or not;
            # an index past the last field selects the last one, so the last field is a default.
            # This is also `if`: `if c then t else e` is `{e, t} c`, true for any nonzero `c`.
            return fields[min(position, len(fields) - 1)].value
    return term
