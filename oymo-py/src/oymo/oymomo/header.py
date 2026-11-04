# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""A unit's header: what another unit reads to call this unit's linked symbols.

A header is an ordinary oymo file of declarations. `header_of(ingot)` keeps every linked
symbol the ingot provides, a definition, global variable or constant with a `link`, as a
declaration `{type, link}` at the same path, inside the same namespaces. It leaves out:

- internal symbols (no `link`): they are private to the unit;
- the unit's own declarations (its imports): a header lists what the unit provides;
- bodies, `init` and `value`: a header declares only.

A namespace left with no symbol is left out. Each declaration keeps the tag of the symbol
it comes from; `source.write` decides which places get written.

A unit with two layers has one header: the two layers' headers merged (`layers.merge`),
with a layering `low : high` only where they differ (`header_of_layers`).
"""

from oymo.core import syntax
from oymo.oymomo import ingot as ingots
from oymo.oymomo import layers, terms

# A namespace being built: each label's entry, or a namespace again, in order.
type _Namespace = dict[str, 'syntax.Term | _Namespace']


def header_of(ingot: ingots.Ingot) -> syntax.Term:
    """The header of `ingot`: its linked definitions, globals and constants as declarations."""
    top: _Namespace = {}
    for symbol in ingot.symbols:
        if isinstance(symbol, ingots.Declaration) or symbol.link is None:
            continue
        namespace = top
        for label in symbol.path[:-1]:
            inner = namespace.setdefault(label, {})
            # Paths come from one namespace tree, so a namespace's label never names an entry.
            assert isinstance(inner, dict)
            namespace = inner
        namespace[symbol.path[-1]] = _declaration(symbol)
    return _struct(top)


def header_of_layers(layer_ingots: list[ingots.Ingot], *, merged: bool = False) -> syntax.Term:
    """The header of a unit: of its one ingot, or of its two layers as one layering
    `low : high`. With `merged`, the two layers' headers are merged instead, a layering left
    only where they differ, for a developer who wants to read what differs."""
    headers = [header_of(each) for each in layer_ingots]
    if len(headers) == 1:
        return headers[0]
    if merged:
        return layers.merge(*headers)
    return syntax.Layers(layers=(headers[0], headers[1]))


def _declaration(symbol: ingots.Definition | ingots.Constant | ingots.Global) -> syntax.Term:
    """`{type, link}` for a linked symbol, with the symbol's tag."""
    assert symbol.link is not None
    return terms.Struct(
        [
            terms.Field('type', _type(symbol.type)),
            terms.Field('link', terms.ByteArray.from_str(symbol.link)),
        ],
        symbol.tag,
    )


def _type(type_: ingots.FunctionType | syntax.Term) -> syntax.Term:
    """A symbol's type as a term: a function type is written `{'function', {xᵢ = tᵢ}, t}`."""
    if not isinstance(type_, ingots.FunctionType):
        return type_
    params = terms.Struct([terms.Field(name, term) for name, term in type_.params])
    return terms.Struct(
        [terms.Field('', terms.ByteArray.from_str('function')), terms.Field('', params), terms.Field('', type_.result)]
    )


def _struct(namespace: _Namespace) -> syntax.Term:
    return terms.Struct(
        [
            terms.Field(label, value if not isinstance(value, dict) else _struct(value))
            for label, value in namespace.items()
        ]
    )
