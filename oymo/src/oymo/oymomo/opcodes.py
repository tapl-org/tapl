# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Abstract opcode signatures, generated from per-op templates.

Shared by the kernel (`bruijn`), BANF (`banf_terms`, `banf_translate`) and LLVM
(`llvm_opcodes`), so it holds no BANF and no LLVM and imports only `terms`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from oymo.oymomo import terms

INT_FORMS = ('i1', 'i8', 'i16', 'i32', 'i64')


@dataclass(frozen=True)
class OpcodeSignature:
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
            yield OpcodeSignature(f'{template}_{form}', template, params, terms.ByteArray.from_str(result or form))


def _conversions(templates, *, widening):
    for template in templates:
        for source in INT_FORMS:
            for target in INT_FORMS:
                wider = int_bits(target) > int_bits(source)
                if source != target and wider == widening:
                    params = (('value', terms.ByteArray.from_str(source)),)
                    yield OpcodeSignature(
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


OPCODES: dict[str, OpcodeSignature] = {signature.name: signature for signature in _generate()}


def form_bits(form: terms.Term) -> int:
    """The width of an integer form such as `'i32'` (a signature's param or result)."""
    name = form.as_str if isinstance(form, terms.ByteArray) else None
    if name is None or name not in INT_FORMS:
        raise ValueError(f'Not an integer form: {form!r}.')
    return int_bits(name)


def byte_count(bits: int) -> int:
    """How many bytes hold an `iN` value: `(N + 7) // 8`, so `i1` is one byte."""
    return (bits + 7) // 8


# How each template computes its result, on unsigned operands of `bits` bits (the first
# param's width). The result may be out of range (`evaluate` wraps it to the result's
# width); None means LLVM has no defined result.
type _Evaluator = Callable[..., int | None]


def _signed(bits: int, value: int) -> int:
    """`value` (unsigned, below `2^bits`) read as two's complement."""
    return value - (1 << bits) if value >> (bits - 1) else value


def _sdiv(bits: int, dividend: int, divisor: int) -> int | None:
    """Signed division, rounding toward zero, as LLVM's `sdiv`. None for a divisor of 0,
    and for the signed minimum by -1 (the quotient doesn't fit)."""
    a, b = _signed(bits, dividend), _signed(bits, divisor)
    if b == 0 or (a == -(1 << (bits - 1)) and b == -1):
        return None
    quotient = abs(a) // abs(b)
    return -quotient if (a < 0) != (b < 0) else quotient


def _srem(bits: int, dividend: int, divisor: int) -> int | None:
    """Signed remainder with the dividend's sign, as LLVM's `srem`. None where `sdiv` is."""
    quotient = _sdiv(bits, dividend, divisor)
    if quotient is None:
        return None
    return _signed(bits, dividend) - _signed(bits, divisor) * quotient


def _udiv(_bits: int, dividend: int, divisor: int) -> int | None:
    return None if divisor == 0 else dividend // divisor


def _urem(_bits: int, dividend: int, divisor: int) -> int | None:
    return None if divisor == 0 else dividend % divisor


def _shift(shift: Callable[[int, int, int], int]) -> _Evaluator:
    """A shift that is None (LLVM: poison) when the amount is the width or more."""
    return lambda bits, value, amount: None if amount >= bits else shift(bits, value, amount)


_BINARY: dict[str, _Evaluator] = {
    'add': lambda _bits, a, b: a + b,
    'sub': lambda _bits, minuend, subtrahend: minuend - subtrahend,
    'mul': lambda _bits, a, b: a * b,
    'and': lambda _bits, a, b: a & b,
    'or': lambda _bits, a, b: a | b,
    'xor': lambda _bits, a, b: a ^ b,
    'sdiv': _sdiv,
    'udiv': _udiv,
    'srem': _srem,
    'urem': _urem,
    'shl': _shift(lambda _bits, value, amount: value << amount),
    'lshr': _shift(lambda _bits, value, amount: value >> amount),
    'ashr': _shift(lambda bits, value, amount: _signed(bits, value) >> amount),
}


def _compare(compare: Callable[[int, int], bool], *, signed: bool) -> _Evaluator:
    """A comparison giving 1 or 0 (an `i1`), on operands read as unsigned or two's complement."""

    def evaluate(bits: int, lhs: int, rhs: int) -> int:
        if signed:
            lhs, rhs = _signed(bits, lhs), _signed(bits, rhs)
        return int(compare(lhs, rhs))

    return evaluate


_COMPARE: dict[str, _Evaluator] = {
    'eq': _compare(lambda a, b: a == b, signed=False),
    'ne': _compare(lambda a, b: a != b, signed=False),
    'slt': _compare(lambda a, b: a < b, signed=True),
    'sle': _compare(lambda a, b: a <= b, signed=True),
    'sgt': _compare(lambda a, b: a > b, signed=True),
    'sge': _compare(lambda a, b: a >= b, signed=True),
    'ult': _compare(lambda a, b: a < b, signed=False),
    'ule': _compare(lambda a, b: a <= b, signed=False),
    'ugt': _compare(lambda a, b: a > b, signed=False),
    'uge': _compare(lambda a, b: a >= b, signed=False),
}

# `bits` is the source width; `evaluate` wraps to the target width, so `trunc` keeps the
# low bits and a negative `sext` result becomes the target's two's complement.
_CONVERT: dict[str, _Evaluator] = {
    'zext': lambda _bits, value: value,
    'sext': lambda bits, value: _signed(bits, value),
    'trunc': lambda _bits, value: value,
}

_TEMPLATES: dict[str, _Evaluator] = _BINARY | _COMPARE | _CONVERT

# The templates `evaluate` knows. An opcode of another template is never folded.
FOLDED_TEMPLATES: frozenset[str] = frozenset(_TEMPLATES)


def evaluate(signature: OpcodeSignature, operands: list[int]) -> int | None:
    """The unsigned result of `signature` on unsigned operands, as LLVM computes it.

    Each operand must be below `2^N` for its param's `iN`. Arithmetic wraps modulo `2^N`
    of the result form. None where LLVM has no defined result.
    """
    bits = form_bits(signature.params[0][1])
    result = _TEMPLATES[signature.template](bits, *operands)
    if result is None:
        return None
    return result % (1 << form_bits(signature.result))
