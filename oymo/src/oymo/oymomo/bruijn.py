# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""De Bruijn indices for oymomo terms: name resolution, the kernel helpers, and `reduce`.

A `BruijnIndex(i)` refers to the binder `i` lambdas out: `x -> y -> x` is `x -> y -> $1`.
Binder names stay on `Lambda.param_name`; references don't carry them.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace

from oymo.core import syntax
from oymo.oymomo import opcodes, terms


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

    The lambda's form goes with the argument: `(x: F -> body) a` puts `a: F` in for `x`.
    It replaces `a`'s own form: `(x: F -> body) a: G` puts in `a: F`, too.
    A lambda without a form puts in `a` as it is, so `a` keeps its own form, if it has one.
    """
    if lambda_.param_form is not terms.Empty:
        if isinstance(argument, terms.Formed):
            argument = argument.term
        argument = terms.Formed(term=argument, form=lambda_.param_form, location=getattr(argument, 'location', None))
    return shift(substitute(lambda_.body, 0, shift(argument, 1)), -1)


ReducePart = Callable[[syntax.Term], syntax.Term]
"""Reduces a part of a built-in's argument until its top constructor can't change.
Returns the part itself if it doesn't change."""


def keep(part: syntax.Term) -> syntax.Term:
    """The `ReducePart` that reduces nothing. `reduce` passes it, so it stays root-only."""
    return part


@dataclass(frozen=True)
class BuiltinRule:
    """How `$name arg` steps.

    `reduce(call, reduce_part)` gets the whole call. It gives each part of the argument that
    it reads to `reduce_part` before reading it, and returns:
    - the result, if the call fires;
    - `call` with the changed parts put back, if a part changed but the call can't fire yet;
    - `call` itself, if nothing changed.
    """

    name: str
    reduce: Callable[[terms.Apply, ReducePart], syntax.Term]


def _fix(call: terms.Apply, _reduce_part: ReducePart) -> syntax.Term:
    """`$fix g` becomes `g ($fix g)`. `g` stays lazy: it is never given to `reduce_part`."""
    return terms.Apply(function=call.argument, argument=call, location=getattr(call, 'location', None))


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


def _struct_to_fields(call: terms.Apply, reduce_part: ReducePart) -> syntax.Term:
    """`$struct_to_fields s` gives `to_field_list(s)` once `s` reduces to a struct literal."""
    argument = reduce_part(call.argument)
    if isinstance(argument, terms.Struct):
        return to_field_list(argument)
    return call if argument is call.argument else replace(call, argument=argument)


def _field_position(struct: terms.Struct, label: str) -> int | None:
    """The position of the first field labeled `label`, or None."""
    return next((i for i, field in enumerate(struct.fields) if field.label == label), None)


def _bytes(term: syntax.Term) -> bytes | None:
    """The bytes of a byte array, with a form on it ignored. None for anything else."""
    match term:
        case terms.ByteArray(value=value) | terms.Formed(term=terms.ByteArray(value=value)):
            return value
    return None


def _with_value(struct: terms.Struct, position: int, value: syntax.Term) -> terms.Struct:
    """`struct` with the value at `position` replaced; `struct` itself if `value` is already there."""
    if value is struct.fields[position].value:
        return struct
    fields = list(struct.fields)
    fields[position] = replace(fields[position], value=value)
    return replace(struct, fields=fields)


def from_field_list(field_list: syntax.Term) -> terms.Struct | None:
    """The struct a literal list of fields spells (the reverse of `to_field_list`), or None.

    Each node must be a struct with `more = [00]` (the end), or `more = [01]` and a `label`
    of valid UTF-8, a `value` and a `rest`. A form on `more` or `label` is ignored; extra
    fields are ignored; the first of two equal labels in a node counts.
    """
    fields = []
    node = field_list
    while True:
        if not isinstance(node, terms.Struct) or (more := _field_position(node, 'more')) is None:
            return None
        match _bytes(node.fields[more].value):
            case b'\x00':
                return terms.Struct(fields, getattr(field_list, 'location', None))
            case b'\x01':
                pass
            case _:
                return None
        label, value, rest = (_field_position(node, name) for name in ('label', 'value', 'rest'))
        if label is None or value is None or rest is None:
            return None
        name = _bytes(node.fields[label].value)
        if name is None:
            return None
        try:
            fields.append(terms.Field(name.decode(), node.fields[value].value))
        except UnicodeDecodeError:
            return None
        node = node.fields[rest].value


def _reduce_field_list(field_list: syntax.Term, reduce_part: ReducePart) -> syntax.Term:
    """Reduces what `from_field_list` reads: each node, its `more`, and if `more` is [01],
    its `label` and its `rest`. Never a `value`. `field_list` itself if nothing changes.

    A loop, not recursion, so a long (or endless) list costs fuel, not Python stack.
    """
    parents = []  # (node, position of its rest), outermost first
    node = reduce_part(field_list)
    while isinstance(node, terms.Struct) and (more := _field_position(node, 'more')) is not None:
        node = _with_value(node, more, reduce_part(node.fields[more].value))
        if _bytes(node.fields[more].value) != b'\x01':
            break
        if (label := _field_position(node, 'label')) is not None:
            node = _with_value(node, label, reduce_part(node.fields[label].value))
        if (rest := _field_position(node, 'rest')) is None:
            break
        parents.append((node, rest))
        node = reduce_part(node.fields[rest].value)
    for parent, rest in reversed(parents):
        node = _with_value(parent, rest, node)
    return node


def _fields_to_struct(call: terms.Apply, reduce_part: ReducePart) -> syntax.Term:
    """`$fields_to_struct l` gives `from_field_list(l)` once `l` reduces to a literal list."""
    field_list = _reduce_field_list(call.argument, reduce_part)
    if (struct := from_field_list(field_list)) is not None:
        return struct
    return call if field_list is call.argument else replace(call, argument=field_list)


def _literal_operand(value: syntax.Term, form: syntax.Term) -> int | None:
    """The unsigned value of a literal operand for a param of form `form` (an `iN`), or None.

    It must be a byte array of exactly `(N + 7) // 8` bytes, below `2^N`, bare or under
    `form` itself. A wrong form or size is not folded, so `convert` still reports it.
    """
    match value:
        case terms.ByteArray(value=data):
            pass
        case terms.Formed(term=terms.ByteArray(value=data), form=written) if written == form:
            pass
        case _:
            return None
    bits = opcodes.form_bits(form)
    if len(data) != opcodes.byte_count(bits):
        return None
    number = int.from_bytes(data, 'little')
    return number if number < 1 << bits else None


def _literal_operands(signature: opcodes.OpcodeSignature, argument: syntax.Term) -> list[int] | None:
    """The operands of a call of `signature`, or None unless `argument` is a struct with the
    params' labels, in order, and every field is a literal operand."""
    if not isinstance(argument, terms.Struct) or len(argument.fields) != len(signature.params):
        return None
    operands = []
    for field, (label, form) in zip(argument.fields, signature.params, strict=True):
        if field.label != label or (operand := _literal_operand(field.value, form)) is None:
            return None
        operands.append(operand)
    return operands


def _fold(signature: opcodes.OpcodeSignature) -> BuiltinRule:
    """The rule of an opcode: on literal operands it gives the result, formed as the
    signature's result, the bytes LLVM would compute. Stuck where LLVM has no defined result.

    It reduces the argument, then, if it is a struct with the params' labels, each field in
    order. With other labels the call is stuck, so no field is reduced.
    """
    labels = [label for label, _ in signature.params]

    def reduce(call: terms.Apply, reduce_part: ReducePart) -> syntax.Term:
        argument = reduce_part(call.argument)
        if isinstance(argument, terms.Struct) and [field.label for field in argument.fields] == labels:
            for position, field in enumerate(argument.fields):
                argument = _with_value(argument, position, reduce_part(field.value))
        call = call if argument is call.argument else replace(call, argument=argument)
        operands = _literal_operands(signature, argument)
        if operands is None:
            return call
        result = opcodes.evaluate(signature, operands)
        if result is None:
            return call
        data = result.to_bytes(opcodes.byte_count(opcodes.form_bits(signature.result)), 'little')
        return terms.Formed(terms.ByteArray(data, call.location), signature.result, call.location)

    return BuiltinRule(signature.name, reduce)


# Reduction rules, by built-in name. A built-in with a rule and no opcode
# (`opcodes.OPCODES`) is kernel-only: it must reduce away before BANF. An opcode with a
# rule folds on literal operands and stays an opcode call otherwise.
BUILTIN_RULES: dict[str, BuiltinRule] = {
    rule.name: rule
    for rule in (
        BuiltinRule('fix', _fix),
        BuiltinRule('struct_to_fields', _struct_to_fields),
        BuiltinRule('fields_to_struct', _fields_to_struct),
        *(_fold(signature) for signature in opcodes.OPCODES.values() if signature.template in opcodes.FOLDED_TEMPLATES),
    )
}


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
        case terms.Apply(function=terms.Builtin(name=name)) if (builtin := BUILTIN_RULES.get(name)) is not None:
            # `keep` reduces no part, so the rule fires only if the parts it reads are already reduced.
            return builtin.reduce(term, keep)
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
