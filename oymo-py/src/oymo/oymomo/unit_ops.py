# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The unit tools: opcodes that build a unit's namespace out of parts.

- `'unit.merge' {X₁, X₂, …}` merges the structs `Xᵢ` deeply, in order.
- `'unit.rebase' {P, X}` puts `X` under the prefix `P` and rewrites the paths in its
  entries' bodies to match.
- `'unit.make_reducible' I` turns an ingot into `t = λg. {…}`, whose fixed point `fix t`
  runs the unit by reduction.

All read their whole operand (`Opcode.apply`): a closed normal value. Where the result is
not defined they give none, and the call stays; the ingot rejects it later as a
reduce-time value left in the ingot.

Imports only `terms` and `meta`, so `opcodes` can list them.
"""

from dataclasses import replace

from oymo.oymomo import terms
from oymo.oymomo.meta import Tag

# What an entry may bring besides its `type`: a hole is filled by an entry that brings one.
_FILLERS = ('body', 'init', 'value', 'link')


def merge(operand: terms.Term) -> terms.Term | None:
    """`'unit.merge' {X₁, X₂, …}`: the structs `Xᵢ` merged into one, or None.

    A label in one of them is kept as it is. A label in two is merged: two namespaces
    (structs without `type`) recursively; a hole `{type}` and an entry of the same type that
    brings a `body`, `init`, `value` or `link` give that entry; a declaration `{type, link}`
    and a definition, global variable or constant of the same type and `link` give the
    latter (what the system linker would join); two equal λ-free values give one. Anything else gives no result: a symbol defined twice is an error even if both
    bodies are equal. Unlabeled fields are appended, never merged. Labels keep the order of
    their first appearance. The operand's labels are ignored.
    """
    if not isinstance(operand, terms.Struct):
        return None
    fields: list[terms.Field] | None = []
    for part in operand.fields:
        if fields is None or not isinstance(part.value, terms.Struct):
            return None
        fields = _merge_fields(fields, part.value.fields)
    return None if fields is None else terms.Struct(fields)


def _merge_fields(fields: list[terms.Field], more: list[terms.Field]) -> list[terms.Field] | None:
    """`fields` with `more` merged in, or None where two fields can't merge."""
    merged = list(fields)
    positions = {f.label: i for i, f in enumerate(merged) if f.label}
    for f in more:
        if not f.label or f.label not in positions:
            if f.label:
                positions[f.label] = len(merged)
            merged.append(f)
            continue
        position = positions[f.label]
        value = _merge_values(merged[position].value, f.value)
        if value is None:
            return None
        merged[position] = replace(merged[position], value=value)
    return merged


def _merge_values(a: terms.Term, b: terms.Term) -> terms.Term | None:
    """Two values with the same label merged, or None."""
    if isinstance(a, terms.Struct) and isinstance(b, terms.Struct):
        a_type, b_type = _entry_type(a), _entry_type(b)
        if a_type is None and b_type is None:
            # Two namespaces.
            fields = _merge_fields(a.fields, b.fields)
            return None if fields is None else replace(a, fields=fields)
        if a_type is not None and a_type == b_type:
            if _is_hole(a) and (_is_hole(b) or _fills(b)):
                return b
            if _is_hole(b) and _fills(a):
                return a
            if _is_declaration(a) and _defines(b, a):
                return b
            if _is_declaration(b) and _defines(a, b):
                return a
    if a == b and _is_lambda_free(a):
        return a
    return None


def _labels(struct: terms.Struct) -> list[str]:
    return [f.label for f in struct.fields]


def _entry_type(struct: terms.Struct) -> terms.Term | None:
    """The `type` of an entry; None for a namespace (a struct without `type`)."""
    return next((f.value for f in struct.fields if f.label == 'type'), None)


def _is_hole(entry: terms.Struct) -> bool:
    """An entry with only a `type`."""
    return _labels(entry) == ['type']


def _fills(entry: terms.Struct) -> bool:
    """An entry that may fill a hole: it brings a `body`, `init`, `value` or `link`."""
    return any(label in _FILLERS for label in _labels(entry))


def _is_declaration(entry: terms.Struct) -> bool:
    """An entry with only a `type` and a `link`: a symbol another unit defines."""
    return sorted(_labels(entry)) == ['link', 'type']


def _defines(entry: terms.Struct, declaration: terms.Struct) -> bool:
    """Whether `entry` defines what `declaration` declares: it brings a `body`, `init` or
    `value`, and has the same `link`."""
    link = next(f.value for f in declaration.fields if f.label == 'link')
    return any(label in ('body', 'init', 'value') for label in _labels(entry)) and any(
        f.label == 'link' and f.value == link for f in entry.fields
    )


def _is_lambda_free(term: terms.Term) -> bool:
    return not any(isinstance(node, terms.Lambda | terms.Fix) for node in terms.nodes(term))


def rebase(operand: terms.Term) -> terms.Term | None:
    """`'unit.rebase' {P, X}`: `X` under the prefix `P`, `{p₁ = {p₂ = … X'}}`, or None.

    `P` is a struct of labels, each a nonempty text byte array (`{'dbl'}`); the operand's
    labels are ignored. `X'` is the struct `X` with every path from `g` in every entry's body
    `λg. …` prefixed: `g.lib.step` becomes `g.dbl.lib.step`. Any other use of `g`, a body
    that is not a lambda, or a lambda outside an entry's body gives no result. λ-free data is copied as it is, so mounting a header is a
    rebase too.
    """
    if not isinstance(operand, terms.Struct) or len(operand.fields) != 2:  # noqa: PLR2004
        return None
    prefix, struct = (f.value for f in operand.fields)
    if not isinstance(prefix, terms.Struct) or not isinstance(struct, terms.Struct):
        return None
    labels = [_label(f.value) for f in prefix.fields]
    if any(label is None for label in labels):
        return None
    path = [(label, f.value.tag) for label, f in zip(labels, prefix.fields, strict=True) if label is not None]
    rebased = _rebase_namespace(struct, path)
    if rebased is None:
        return None
    for label, tag in reversed(path):
        rebased = terms.Struct([terms.Field(label, rebased, tag)], tag)
    return rebased


def _label(term: terms.Term) -> str | None:
    """The label a byte array spells: nonempty UTF-8 text, else None."""
    return (term.as_str or None) if isinstance(term, terms.ByteArray) else None


# A prefix: each label, with the tag of the byte array that spells it.
type _Path = list[tuple[str, Tag]]


def _rebase_namespace(struct: terms.Struct, path: _Path) -> terms.Struct | None:
    """A struct of `X` with its entries' bodies rebased, or None."""
    is_entry = 'type' in _labels(struct)
    fields = []
    for f in struct.fields:
        if is_entry and f.label == 'body':
            value = _rebase_body(f.value, path)
        elif isinstance(f.value, terms.Struct):
            value = _rebase_namespace(f.value, path)
        else:
            value = f.value if _is_lambda_free(f.value) else None
        if value is None:
            return None
        fields.append(f if value is f.value else replace(f, value=value))
    return replace(struct, fields=fields)


def _rebase_body(body: terms.Term, path: _Path) -> terms.Term | None:
    """An entry's body `λg. B` with every path from `g` in `B` prefixed, or None."""
    if not isinstance(body, terms.Lambda):
        return None
    rebased = _rebase_term(body.body, 0, path)
    return None if rebased is None else replace(body, body=rebased)


def _rebase_term(term: terms.Term, depth: int, path: _Path) -> terms.Term | None:
    """`term`, `depth` binders inside `λg`, with every path from `g` prefixed, or None where
    `g` is used another way. `g` is the index `depth`."""
    match term:
        case terms.Project():
            labels: list[terms.Project] = []
            root: terms.Term = term
            while isinstance(root, terms.Project):
                labels.append(root)
                root = root.struct
            if isinstance(root, terms.BruijnIndex) and root.index == depth:
                rebuilt: terms.Term = root
                for label, tag in path:
                    rebuilt = terms.Project(rebuilt, label, tag)
                for project in reversed(labels):
                    rebuilt = replace(project, struct=rebuilt)
                return rebuilt
            struct = _rebase_term(term.struct, depth, path)
            return None if struct is None else replace(term, struct=struct)
        case terms.BruijnIndex(index=index):
            return None if index == depth else term
        case terms.Lambda(body=body):
            rebased = _rebase_term(body, depth + 1, path)
            return None if rebased is None else replace(term, body=rebased)
        case terms.Apply(function=function, argument=argument):
            new_function = _rebase_term(function, depth, path)
            new_argument = _rebase_term(argument, depth, path)
            if new_function is None or new_argument is None:
                return None
            return replace(term, function=new_function, argument=new_argument)
        case terms.Struct(fields=fields):
            new_fields = []
            for f in fields:
                value = _rebase_term(f.value, depth, path)
                if value is None:
                    return None
                new_fields.append(replace(f, value=value))
            return replace(term, fields=new_fields)
        case terms.Fix(body=body):
            rebased = _rebase_term(body, depth, path)
            return None if rebased is None else replace(term, body=rebased)
    return term


# The region marker (`anf.REGION`, kept here so `opcodes` can import this module).
_REGION = b'R'


def make_reducible(operand: terms.Term) -> terms.Term | None:
    """`'unit.make_reducible' I`: the ingot `I` as `t = λg. N`, or None.

    `N` has `I`'s namespaces. A definition, an entry whose `body` is `λg. λp. R`, becomes
    `λp. R'`: its own `λg` moves out to `t`'s (structs bind nothing, so `g` keeps its index),
    and `R'` is `R` with every region `'R' (λr. u)` turned into `(fix (λr. u)) [00]`. Every
    other entry (a global variable, a constant, a declaration, a hole) stays as it is. So
    `fix t` is the unit's instance: projecting a definition unfolds it, and a call runs the
    body. A struct with a λ outside an entry's body, or a body not shaped `λg. λp. …`, gives
    no result.
    """
    if not isinstance(operand, terms.Struct):
        return None
    namespace = _reducible_namespace(operand)
    if namespace is None:
        return None
    return terms.Lambda('g', namespace, operand.tag)


def _reducible_namespace(struct: terms.Struct) -> terms.Struct | None:
    fields = []
    for f in struct.fields:
        value = f.value
        if isinstance(value, terms.Struct) and 'type' in _labels(value):
            body = next((e.value for e in value.fields if e.label == 'body'), None)
            if body is None:
                if not _is_lambda_free(value):
                    return None
            elif isinstance(body, terms.Lambda) and isinstance(body.body, terms.Lambda):
                value = _run_regions(body.body)
            else:
                return None
        elif isinstance(value, terms.Struct):
            value = _reducible_namespace(value)
            if value is None:
                return None
        elif not _is_lambda_free(value):
            return None
        fields.append(f if value is f.value else replace(f, value=value))
    return replace(struct, fields=fields)


def _run_regions(term: terms.Term) -> terms.Term:
    """`term` with every region `'R' (λr. u)` turned into `(fix (λr. u)) [00]`."""
    match term:
        case terms.Apply(function=terms.ByteArray(value=value), argument=terms.Lambda() as blocks) if value == _REGION:
            fixed = terms.Fix(_run_regions(blocks), term.tag)
            return terms.Apply(fixed, terms.ByteArray(b'\x00', term.function.tag), term.tag)
        case terms.Lambda(body=body):
            return replace(term, body=_run_regions(body))
        case terms.Apply(function=function, argument=argument):
            return replace(term, function=_run_regions(function), argument=_run_regions(argument))
        case terms.Struct(fields=fields):
            return replace(term, fields=[replace(f, value=_run_regions(f.value)) for f in fields])
        case terms.Project(struct=struct):
            return replace(term, struct=_run_regions(struct))
        case terms.Fix(body=body):
            return replace(term, body=_run_regions(body))
    return term
