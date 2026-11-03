# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""A program's layers: separation of a written term, and merging two layers back into one.

A written term with no layering `low : high` has one layer, itself. Otherwise it has two,
its low and its high layer (`separate`); each reduces on its own. Separation runs on the
written term, before any reduction, so reduction never meets a layering.

`merge` is the inverse: the most compact written term that separates back to two given
layers. It pushes a layering down to exactly where the two layers differ.
"""

from dataclasses import replace

from oymo.core import syntax
from oymo.oymomo import terms


def has_layering(term: syntax.Term) -> bool:
    """Whether a layering is anywhere in `term`."""
    return any(isinstance(node, syntax.Layers) for node in terms.nodes(term))


def separate(term: syntax.Term) -> tuple[syntax.Term, syntax.Term] | None:
    """The low and high layers of a written term; None if it has no layering (one layer).
    A part with no layering is the same object in both layers; a layering's tag is dropped."""
    if not has_layering(term):
        return None
    return term.separate(syntax.LayerSeparator())


def merge(low: syntax.Term, high: syntax.Term) -> syntax.Term:
    """The most compact layered term that separates back to `(low, high)`, two terms with no
    layering. Equal parts (tags aside) are written once, with low's tags; a layering is put
    only where the two differ, so it never holds a layering.

    A lambda merges into one only if both binders have the same name: a body may name its
    binder, so under one name it would read another binder in one of the layers."""
    if low is high or low == high:
        return low
    match low, high:
        case terms.Apply(), terms.Apply():
            return replace(
                low, function=merge(low.function, high.function), argument=merge(low.argument, high.argument)
            )
        case terms.Lambda(), terms.Lambda() if low.param_name == high.param_name:
            return replace(low, body=merge(low.body, high.body))
        case terms.Struct(), terms.Struct() if [f.label for f in low.fields] == [f.label for f in high.fields]:
            fields = [
                replace(lf, value=merge(lf.value, hf.value)) for lf, hf in zip(low.fields, high.fields, strict=True)
            ]
            return replace(low, fields=fields)
        case terms.Project(), terms.Project() if low.label == high.label:
            return replace(low, struct=merge(low.struct, high.struct))
        case terms.Fix(), terms.Fix():
            return replace(low, body=merge(low.body, high.body))
    return syntax.Layers(layers=(low, high))
