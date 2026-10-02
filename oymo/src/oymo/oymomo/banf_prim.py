# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Abstract prim op signatures, generated from per-op templates. Contains no LLVM."""

from dataclasses import dataclass

from oymo.oymomo import terms

INT_FORMS = ('i1', 'i8', 'i16', 'i32', 'i64')


@dataclass(frozen=True)
class PrimSignature:
    name: str
    template: str
    params: tuple[tuple[str, terms.Form], ...]
    result: terms.Form


def int_bits(form: str) -> int:
    return int(form[1:])


def _same_form(templates, labels, *, result=None, include_i1):
    for template in templates:
        for form in INT_FORMS:
            if form == 'i1' and not include_i1:
                continue
            params = tuple((label, form) for label in labels)
            yield PrimSignature(f'{template}_{form}', template, params, result or form)


def _conversions(templates, *, widening):
    for template in templates:
        for source in INT_FORMS:
            for target in INT_FORMS:
                wider = int_bits(target) > int_bits(source)
                if source != target and wider == widening:
                    yield PrimSignature(f'{template}_{source}_{target}', template, (('value', source),), target)


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
