# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Abstract prim op signatures, generated from per-op templates. Contains no LLVM."""

from collections.abc import Callable
from dataclasses import dataclass

from oymo.oymomo import terms

INT_FORMS = ('i1', 'i8', 'i16', 'i32', 'i64')


@dataclass(frozen=True)
class PrimSignature:
    name: str
    template: str
    params: tuple[tuple[str, terms.Term], ...]
    result: terms.Term


def int_bits(form: str) -> int:
    return int(form[1:])


def _same_form(templates, labels, *, result=None, include_i1):
    for template in templates:
        for form in INT_FORMS:
            if form == 'i1' and not include_i1:
                continue
            params = tuple((label, terms.ByteArray.from_str(form)) for label in labels)
            yield PrimSignature(f'{template}_{form}', template, params, terms.ByteArray.from_str(result or form))


def _conversions(templates, *, widening):
    for template in templates:
        for source in INT_FORMS:
            for target in INT_FORMS:
                wider = int_bits(target) > int_bits(source)
                if source != target and wider == widening:
                    params = (('value', terms.ByteArray.from_str(source)),)
                    yield PrimSignature(
                        f'{template}_{source}_{target}', template, params, terms.ByteArray.from_str(target)
                    )


def _generate():
    yield from _same_form(('add', 'mul'), ('a', 'b'), include_i1=False)
    yield from _same_form(('and', 'or', 'xor'), ('a', 'b'), include_i1=True)
    yield from _same_form(('sub',), ('minuend', 'subtrahend'), include_i1=False)
    yield from _same_form(('sdiv', 'udiv', 'srem', 'urem'), ('dividend', 'divisor'), include_i1=False)
    yield from _same_form(('shl', 'lshr', 'ashr'), ('value', 'amount'), include_i1=False)
    yield from _same_form(('eq', 'ne'), ('a', 'b'), result='i1', include_i1=True)
    yield from _same_form(
        ('slt', 'sle', 'sgt', 'sge', 'ult', 'ule', 'ugt', 'uge'), ('lhs', 'rhs'), result='i1', include_i1=False
    )
    yield from _conversions(('zext', 'sext'), widening=True)
    yield from _conversions(('trunc',), widening=False)


PRIMS: dict[str, PrimSignature] = {signature.name: signature for signature in _generate()}


# Dynamic prims


class PrimFormError(Exception):
    """A dynamic prim's arguments don't fit it. `banf_terms` turns it into a FormError."""


@dataclass(frozen=True)
class DynamicPrim:
    """A prim with no fixed signature: its result form depends on its arguments.

    `result_form` gets each argument's form and, for a constant, its bytes (None for a
    name). It returns the result form, or raises PrimFormError.
    """

    name: str
    labels: tuple[str, ...]
    result_form: Callable[[list[terms.Term], list[bytes | None]], terms.Term]


def _extractvalue_form(forms, values):
    struct_form, index_form = forms
    _, index = values
    if not isinstance(struct_form, terms.Struct):
        raise PrimFormError('prim.extractvalue: struct must have a struct form.')
    if not index:
        raise PrimFormError("prim.extractvalue needs a literal index, such as [00]: 'i8'.")
    if not (isinstance(index_form, terms.ByteArray) and index_form.as_str in INT_FORMS):
        raise PrimFormError('prim.extractvalue: the index form must be one of i1, ..., i64.')
    # Unsigned little-endian, as `bruijn.index_value` reads a struct apply's index.
    position = int.from_bytes(index, 'little')
    if position >= len(struct_form.fields):
        raise PrimFormError(f'prim.extractvalue: the struct has no field at index {position}.')
    return struct_form.fields[position].value


DYNAMIC_PRIMS: dict[str, DynamicPrim] = {
    prim.name: prim for prim in (DynamicPrim('extractvalue', ('struct', 'index'), _extractvalue_form),)
}
