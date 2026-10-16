# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The opcodes: one entry per LLVM instruction, polymorphic in `form`.

An opcode is called as a byte array applied to a struct, `'add' {'i32', a, b}`, which is
LLVM's `add i32 a, b`. Fields are positional, in LLVM's operand order; labels are
ignored. An opcode has no declared params: it reads its fields itself, by position, and
tells what it can from them. `form_of` gives the result's form, `evaluate` the result's
bytes when every field it needs is a literal.

Shared by `reduction`, BANF (`banf_translate`) and LLVM (`llvm_opcodes`), so it
holds no BANF and no LLVM and imports only `terms`.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from oymo.oymomo import terms

INT_FORMS = ('i1', 'i8', 'i16', 'i32', 'i64')

type Fields = Sequence[terms.Term]

# Every integer opcode has three fields: `{form, a, b}`, or `{form, value, to}`. Memory
# opcodes count their own.
FIELD_COUNT = 3


@dataclass(frozen=True)
class Opcode:
    """One LLVM instruction.

    `form_of`: the result's form, or None if unknown.
    `evaluate`: the result's value as LLVM computes it, or None if the needed fields
    aren't literals or LLVM leaves the result undefined.
    `pure`: has no side effects, so reduction may fold it.
    """

    name: str
    form_of: Callable[[Fields], terms.Term | None]
    evaluate: Callable[[Fields], terms.ByteArray | None]
    pure: bool = True


def find_bit_width(form: terms.Term) -> int | None:
    """The width of an integer form such as `'i32'` (32), or None for any other term."""
    name = form.as_str if isinstance(form, terms.ByteArray) else None
    return int(name[1:]) if name is not None and name in INT_FORMS else None


def bit_width(form: terms.Term) -> int:
    """`find_bit_width`, for a form known to be an integer form: raises ValueError otherwise."""
    if (width := find_bit_width(form)) is None:
        raise ValueError(f'Not an integer form: {form!r}.')
    return width


def byte_width(bits: int) -> int:
    """How many bytes hold an `iN` value: `(N + 7) // 8`, so `i1` is one byte."""
    return (bits + 7) // 8


def decode_uint(term: terms.Term, form: terms.Term) -> int | None:
    """The unsigned value of `term` read at the integer form `form`, or None.

    `term` must be a byte array of exactly `(N + 7) // 8` bytes, below `2^N`, bare or
    formed. A written form is not compared with `form`: the bytes are read at `form`.
    """
    match term:
        case terms.ByteArray(value=data) | terms.Formed(term=terms.ByteArray(value=data)):
            pass
        case _:
            return None
    bits = find_bit_width(form)
    if bits is None or len(data) != byte_width(bits):
        return None
    number = int.from_bytes(data, 'little')
    return number if number < 1 << bits else None


def _encode(value: int, bits: int) -> terms.ByteArray:
    """`value` wrapped modulo `2^bits`, as the little-endian bytes of an `iN`."""
    return terms.ByteArray((value % (1 << bits)).to_bytes(byte_width(bits), 'little'))


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


# How an opcode computes, on unsigned operands of `bits` bits (the operands' width). The
# result may be out of range (it is wrapped to the result's width); None means LLVM has
# no defined result.
type _Compute = Callable[..., int | None]


def _shift(shift: Callable[[int, int, int], int]) -> _Compute:
    """A shift that is None (LLVM: poison) when the amount is the width or more."""
    return lambda bits, value, amount: None if amount >= bits else shift(bits, value, amount)


def _compare(compare: Callable[[int, int], bool], *, signed: bool) -> _Compute:
    """A comparison giving 1 or 0 (an `i1`), on operands read as unsigned or two's complement."""

    def compute(bits: int, lhs: int, rhs: int) -> int:
        if signed:
            lhs, rhs = _signed(bits, lhs), _signed(bits, rhs)
        return int(compare(lhs, rhs))

    return compute


_I1 = terms.ByteArray.from_str('i1')


def _binary(name: str, compute: _Compute, *, result: terms.Term | None = None) -> Opcode:
    """`{form, a, b}`: two operands read at `form`. The result is formed as `form`, or as
    `result` if given (`i1` for a comparison)."""

    def form_of(fields: Fields) -> terms.Term | None:
        if len(fields) != FIELD_COUNT or not isinstance(fields[0], terms.ByteArray):
            return None
        return fields[0] if result is None else result

    def evaluate(fields: Fields) -> terms.ByteArray | None:
        if (form := form_of(fields)) is None or (bits := find_bit_width(fields[0])) is None:
            return None
        a, b = decode_uint(fields[1], fields[0]), decode_uint(fields[2], fields[0])
        if a is None or b is None or (value := compute(bits, a, b)) is None:
            return None
        return _encode(value, bit_width(form))

    return Opcode(name, form_of, evaluate)


def _convert(name: str, compute: _Compute, *, widening: bool) -> Opcode:
    """`{form, value, to}`: one operand read at `form`, the result formed as `to`.
    It evaluates only where LLVM converts: `to` wider than `form` (`zext`, `sext`), or
    narrower (`trunc`)."""

    def form_of(fields: Fields) -> terms.Term | None:
        if len(fields) != FIELD_COUNT or not isinstance(fields[2], terms.ByteArray):
            return None
        return fields[2]

    def evaluate(fields: Fields) -> terms.ByteArray | None:
        if form_of(fields) is None:
            return None
        source, target = find_bit_width(fields[0]), find_bit_width(fields[2])
        if source is None or target is None or (target > source) != widening or target == source:
            return None
        if (value := decode_uint(fields[1], fields[0])) is None or (result := compute(source, value)) is None:
            return None
        return _encode(result, target)

    return Opcode(name, form_of, evaluate)


PTR = terms.ByteArray.from_str('ptr')

# What a `store` gives: LLVM's `store` gives no value, and only `$seq` may use it
# (plan_memory.md decision 11).
STORE_RESULT = terms.Struct([])

# `getelementptr` takes a form, a pointer and at least one index.
GEP_MIN_FIELDS = 3

# `load` takes `{form, ptr}`, `store` takes `{value, ptr}`.
LOAD_STORE_FIELDS = 2


def is_literal_form(term: terms.Term) -> bool:
    """A named form (`'i32'`, `'ptr'`) or a struct of literal forms: what a form field must be."""
    if isinstance(term, terms.ByteArray):
        return term.as_str is not None
    if isinstance(term, terms.Struct):
        return all(is_literal_form(f.value) for f in term.fields)
    return False


def _never(_fields: Fields) -> terms.ByteArray | None:
    return None


def _alloca_form_of(fields: Fields) -> terms.Term | None:
    """`{form}` or `{form, count}`: a pointer to a stack slot for one `form`, or `count` of them."""
    return PTR if len(fields) in (1, 2) and is_literal_form(fields[0]) else None


def _getelementptr_form_of(fields: Fields) -> terms.Term | None:
    """`{form, ptr, i0, ..., in}`: `ptr` moved by `i0` whole `form`s, then into `form`'s parts."""
    return PTR if len(fields) >= GEP_MIN_FIELDS and is_literal_form(fields[0]) else None


def _load_form_of(fields: Fields) -> terms.Term | None:
    """`{form, ptr}`: the `form` read at `ptr`. The field count is the BANF verifier's
    check, so that `'load' {'i32'}` says how many fields it takes."""
    return fields[0] if fields and is_literal_form(fields[0]) else None


def _store_form_of(_fields: Fields) -> terms.Term | None:
    """`{value, ptr}`: writes `value` at `ptr` and gives `{}`. The field count is the BANF
    verifier's check, as for `load`."""
    return STORE_RESULT


def _generate():
    yield _binary('add', lambda _bits, a, b: a + b)
    yield _binary('sub', lambda _bits, minuend, subtrahend: minuend - subtrahend)
    yield _binary('mul', lambda _bits, a, b: a * b)
    yield _binary('sdiv', _sdiv)
    yield _binary('udiv', _udiv)
    yield _binary('srem', _srem)
    yield _binary('urem', _urem)
    yield _binary('shl', _shift(lambda _bits, value, amount: value << amount))
    yield _binary('lshr', _shift(lambda _bits, value, amount: value >> amount))
    yield _binary('ashr', _shift(lambda bits, value, amount: _signed(bits, value) >> amount))
    yield _binary('and', lambda _bits, a, b: a & b)
    yield _binary('or', lambda _bits, a, b: a | b)
    yield _binary('xor', lambda _bits, a, b: a ^ b)
    # One opcode per predicate, named `icmp_` and LLVM's predicate.
    for predicate, compare, signed in (
        ('eq', lambda a, b: a == b, False),
        ('ne', lambda a, b: a != b, False),
        ('slt', lambda a, b: a < b, True),
        ('sle', lambda a, b: a <= b, True),
        ('sgt', lambda a, b: a > b, True),
        ('sge', lambda a, b: a >= b, True),
        ('ult', lambda a, b: a < b, False),
        ('ule', lambda a, b: a <= b, False),
        ('ugt', lambda a, b: a > b, False),
        ('uge', lambda a, b: a >= b, False),
    ):
        yield _binary(f'icmp_{predicate}', _compare(compare, signed=signed), result=_I1)
    # `compute` gets the source width; the result wraps to the target width, so `trunc`
    # keeps the low bits and a negative `sext` result becomes the target's two's complement.
    yield _convert('zext', lambda _bits, value: value, widening=True)
    yield _convert('sext', lambda bits, value: _signed(bits, value), widening=True)
    yield _convert('trunc', lambda _bits, value: value, widening=False)
    # Memory: impure, so reduction never folds them; oymomo has no memory to run them on.
    yield Opcode('alloca', _alloca_form_of, _never, pure=False)
    yield Opcode('getelementptr', _getelementptr_form_of, _never, pure=False)
    yield Opcode('load', _load_form_of, _never, pure=False)
    yield Opcode('store', _store_form_of, _never, pure=False)


OPCODES: dict[str, Opcode] = {opcode.name: opcode for opcode in _generate()}


def lookup(term: terms.Term) -> Opcode | None:
    """The opcode a term in function position names: a byte array spelling its name."""
    if isinstance(term, terms.ByteArray) and (name := term.as_str) is not None:
        return OPCODES.get(name)
    return None
