# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The opcodes: one entry per LLVM instruction, polymorphic in `type`.

An opcode is called as a byte array applied to a struct, `'add' {'i32', a, b}`, which is
LLVM's `add i32 a, b`. Fields are positional, in LLVM's operand order; labels are
ignored. An opcode has no declared params: it reads its fields itself, by position, and
tells what it can from them. `result_type` gives the result's type, `evaluate` the result's
bytes when every field it needs is a literal.

Shared by `reduction`, ANF and LLVM, so it holds neither and imports only `terms`.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from oymo.oymomo import terms

INT_TYPES = ('i1', 'i8', 'i16', 'i32', 'i64')

type Fields = Sequence[terms.Term]

# Every integer opcode has three fields: `{type, a, b}`, or `{type, value, to}`. Memory
# opcodes count their own.
FIELD_COUNT = 3


@dataclass(frozen=True)
class Opcode:
    """One LLVM instruction.

    `result_type`: the result's type, or None if unknown.
    `evaluate`: the result's value as LLVM computes it, or None if the needed fields
    aren't literals or LLVM leaves the result undefined.
    `pure`: has no side effects, so reduction may fold it.
    """

    name: str
    result_type: Callable[[Fields], terms.Term | None]
    evaluate: Callable[[Fields], terms.ByteArray | None]
    pure: bool = True


def find_bit_width(typ: terms.Term) -> int | None:
    """The width of an integer type such as `'i32'` (32), or None for any other term."""
    name = typ.as_str if isinstance(typ, terms.ByteArray) else None
    return int(name[1:]) if name is not None and name in INT_TYPES else None


def bit_width(typ: terms.Term) -> int:
    """`find_bit_width`, for a type known to be an integer type: raises ValueError otherwise."""
    if (width := find_bit_width(typ)) is None:
        raise ValueError(f'Not an integer type: {typ!r}.')
    return width


def byte_width(bits: int) -> int:
    """How many bytes hold an `iN` value: `(N + 7) // 8`, so `i1` is one byte."""
    return (bits + 7) // 8


def decode_uint(term: terms.Term, typ: terms.Term) -> int | None:
    """The unsigned value of `term` read at the integer type `type`, or None.

    `term` must be a byte array of exactly `(N + 7) // 8` bytes, below `2^N`.
    """
    if not isinstance(term, terms.ByteArray):
        return None
    data = term.value
    bits = find_bit_width(typ)
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


_I1 = terms.ByteArray.from_str('i1')


def _binary(name: str, compute: _Compute, *, result: terms.Term | None = None) -> Opcode:
    """`{type, a, b}`: two operands read at `type`. The result is typed as `type`, or as
    `result` if given (`i1` for a comparison)."""

    def result_type(fields: Fields) -> terms.Term | None:
        if len(fields) != FIELD_COUNT or not isinstance(fields[0], terms.ByteArray):
            return None
        return fields[0] if result is None else result

    def evaluate(fields: Fields) -> terms.ByteArray | None:
        if (typ := result_type(fields)) is None or (bits := find_bit_width(fields[0])) is None:
            return None
        a, b = decode_uint(fields[1], fields[0]), decode_uint(fields[2], fields[0])
        if a is None or b is None or (value := compute(bits, a, b)) is None:
            return None
        return _encode(value, bit_width(typ))

    return Opcode(name, result_type, evaluate)


# `icmp`'s predicates (LLVM's names): how each compares, and whether it reads its operands
# as two's complement.
ICMP_PREDICATES: dict[str, tuple[Callable[[int, int], bool], bool]] = {
    'eq': (lambda a, b: a == b, False),
    'ne': (lambda a, b: a != b, False),
    'slt': (lambda a, b: a < b, True),
    'sle': (lambda a, b: a <= b, True),
    'sgt': (lambda a, b: a > b, True),
    'sge': (lambda a, b: a >= b, True),
    'ult': (lambda a, b: a < b, False),
    'ule': (lambda a, b: a <= b, False),
    'ugt': (lambda a, b: a > b, False),
    'uge': (lambda a, b: a >= b, False),
}

# `icmp` has four fields: `{predicate, type, a, b}`.
ICMP_FIELD_COUNT = 4


def icmp_predicate(fields: Fields) -> str | None:
    """The predicate an `icmp` call names in field 0, or None if it names none."""
    if not fields or not isinstance(fields[0], terms.ByteArray):
        return None
    name = fields[0].as_str
    return name if name in ICMP_PREDICATES else None


def _icmp() -> Opcode:
    """`'icmp' {'eq', 'i32', a, b}`: LLVM's `icmp eq i32 a, b`, an `i1`."""

    def result_type(fields: Fields) -> terms.Term | None:
        if len(fields) != ICMP_FIELD_COUNT or icmp_predicate(fields) is None:
            return None
        return _I1 if isinstance(fields[1], terms.ByteArray) else None

    def evaluate(fields: Fields) -> terms.ByteArray | None:
        predicate = icmp_predicate(fields)
        if predicate is None or result_type(fields) is None or (bits := find_bit_width(fields[1])) is None:
            return None
        a, b = decode_uint(fields[2], fields[1]), decode_uint(fields[3], fields[1])
        if a is None or b is None:
            return None
        compare, signed = ICMP_PREDICATES[predicate]
        if signed:
            a, b = _signed(bits, a), _signed(bits, b)
        return _encode(int(compare(a, b)), 1)

    return Opcode('icmp', result_type, evaluate)


def _convert(name: str, compute: _Compute, *, widening: bool) -> Opcode:
    """`{type, value, to}`: one operand read at `type`, the result typed as `to`.
    It evaluates only where LLVM converts: `to` wider than `type` (`zext`, `sext`), or
    narrower (`trunc`)."""

    def result_type(fields: Fields) -> terms.Term | None:
        if len(fields) != FIELD_COUNT or not isinstance(fields[2], terms.ByteArray):
            return None
        return fields[2]

    def evaluate(fields: Fields) -> terms.ByteArray | None:
        if result_type(fields) is None:
            return None
        source, target = find_bit_width(fields[0]), find_bit_width(fields[2])
        if source is None or target is None or (target > source) != widening or target == source:
            return None
        if (value := decode_uint(fields[1], fields[0])) is None or (result := compute(source, value)) is None:
            return None
        return _encode(result, target)

    return Opcode(name, result_type, evaluate)


PTR = terms.ByteArray.from_str('ptr')

# What a `store` gives: LLVM's `store` gives no value. A `let` binds it to a name that
# nothing reads; the `let` only orders the store (4.4c).
STORE_RESULT = terms.Struct([])

# `getelementptr` takes a type, a pointer and at least one index.
GEP_MIN_FIELDS = 3

# `load` takes `{type, ptr}`, `store` takes `{type, value, ptr}` (4.4c).
LOAD_FIELDS = 2
STORE_FIELDS = 3


# LLVM's aggregate types other than a plain struct are tagged structs: field 0 names the
# type, and the fields after it are its parts. Only LLVM
# translation reads the tag; to reduction they are structs like any other.
TYPE_TAGS = frozenset({'array', 'vector', 'packed'})

# The tags whose parts are `count, element`.
SEQUENCE_TAGS = frozenset({'array', 'vector'})
SEQUENCE_PARTS = 2


def tagged_type(typ: terms.Term) -> tuple[str, list[terms.Field]] | None:
    """`(tag, parts)` for a struct whose field 0 is one of `TYPE_TAGS`, else None. The tag's
    label is ignored. `{'i32', x = 'i8'}` is a plain struct: `'i32'` is not a tag."""
    if not isinstance(typ, terms.Struct) or not typ.fields:
        return None
    tag = typ.fields[0].value
    name = tag.as_str if isinstance(tag, terms.ByteArray) else None
    if name is None or name not in TYPE_TAGS:
        return None
    return name, typ.fields[1:]


def tag_count(term: terms.Term) -> int | None:
    """The `count` of an array or a vector: a byte array read as an unsigned,
    little-endian number (`[03]` is 3, 2.3a), or None."""
    if isinstance(term, terms.ByteArray):
        return int.from_bytes(term.value, 'little')
    return None


def is_literal_type(term: terms.Term) -> bool:
    """A named type (`'i32'`, `'ptr'`), a struct of literal types, or a tagged struct of
    them, with a literal `count`: what a type field must be."""
    if (tagged := tagged_type(term)) is not None:
        tag, parts = tagged
        if tag in SEQUENCE_TAGS:
            return (
                len(parts) == SEQUENCE_PARTS
                and tag_count(parts[0].value) is not None
                and is_literal_type(parts[1].value)
            )
        return all(is_literal_type(f.value) for f in parts)
    if isinstance(term, terms.ByteArray):
        return term.as_str is not None
    if isinstance(term, terms.Struct):
        return all(is_literal_type(f.value) for f in term.fields)
    return False


def _never(_fields: Fields) -> terms.ByteArray | None:
    return None


def _alloca_form_of(fields: Fields) -> terms.Term | None:
    """`{type}` or `{type, count}`: a pointer to a stack slot for one `type`, or `count` of them."""
    return PTR if len(fields) in (1, 2) and is_literal_type(fields[0]) else None


def _getelementptr_form_of(fields: Fields) -> terms.Term | None:
    """`{type, ptr, i0, ..., in}`: `ptr` moved by `i0` whole `type`s, then into `type`'s parts."""
    return PTR if len(fields) >= GEP_MIN_FIELDS and is_literal_type(fields[0]) else None


def _load_form_of(fields: Fields) -> terms.Term | None:
    """`{type, ptr}`: the `type` read at `ptr`. LLVM translation checks the field count."""
    return fields[0] if fields and is_literal_type(fields[0]) else None


def _store_form_of(fields: Fields) -> terms.Term | None:
    """`{type, value, ptr}`: writes `value`, a `type`, at `ptr` and gives `{}`."""
    return STORE_RESULT if fields and is_literal_type(fields[0]) else None


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
    yield _icmp()
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
