# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import terms
from oymo.oymomo.opcodes import OPCODES, PTR, bit_width, byte_width, decode_uint, lookup

I1, I8, I16, I32, I64 = (terms.ByteArray(name) for name in (b'i1', b'i8', b'i16', b'i32', b'i64'))
EQ = terms.ByteArray(b'eq')


def operand(typ, value):
    """`value` as the bare bytes of an operand read at `type`."""
    return terms.ByteArray(value.to_bytes(byte_width(bit_width(typ)), 'little'))


def ev(name, typ, operands, to=None):
    """`evaluate` on `{type, operands...}`, or `{type, operand, to}` for a conversion, as an
    unsigned number (or None)."""
    typ = terms.ByteArray.from_str(typ)
    fields = [typ, *(operand(typ, value) for value in operands)]
    if to is not None:
        fields.append(terms.ByteArray.from_str(to))
    result = OPCODES[name].evaluate(fields)
    return None if result is None else int.from_bytes(result.value, 'little')


def test_one_opcode_per_llvm_instruction():
    assert set(OPCODES) == {
        *('add', 'sub', 'mul', 'sdiv', 'udiv', 'srem', 'urem', 'shl', 'lshr', 'ashr', 'and', 'or', 'xor'),
        'icmp',
        *('zext', 'sext', 'trunc'),
        *('alloca', 'getelementptr', 'load', 'store'),
    }


def test_form_of():
    x = terms.Variable('x')
    assert OPCODES['add'].result_type([I32, x, x]) == I32
    assert OPCODES['icmp'].result_type([EQ, I32, x, x]) == I1
    assert OPCODES['zext'].result_type([I8, x, I32]) == I32
    # The fields don't tell it: a wrong count, or a type that isn't a byte array.
    assert OPCODES['add'].result_type([I32, x]) is None
    assert OPCODES['add'].result_type([x, x, x]) is None
    assert OPCODES['zext'].result_type([I8, x, x]) is None
    # `icmp` needs a predicate it knows in field 0.
    assert OPCODES['icmp'].result_type([I32, x, x]) is None
    assert OPCODES['icmp'].result_type([terms.ByteArray(b'lt'), I32, x, x]) is None
    assert OPCODES['icmp'].result_type([x, I32, x, x]) is None


def test_evaluate_gives_the_result_bytes():
    assert OPCODES['add'].evaluate([I32, operand(I32, 1), operand(I32, 2)]) == operand(I32, 3)
    assert OPCODES['icmp'].evaluate([EQ, I8, operand(I8, 7), operand(I8, 7)]) == operand(I1, 1)
    assert OPCODES['zext'].evaluate([I8, operand(I8, 0xFF), I32]) == operand(I32, 0xFF)


def test_evaluate_reads_bare_operands():
    assert OPCODES['add'].evaluate([I8, operand(I8, 1), operand(I8, 2)]) == operand(I8, 3)
    assert decode_uint(operand(I8, 1), I8) == 1
    # The bytes are read at the opcode's type: a wrong size does not decode.
    assert decode_uint(operand(I8, 1), I32) is None


def test_evaluate_needs_what_it_can_read():
    x = terms.Variable('x')
    assert OPCODES['add'].evaluate([I32, x, operand(I32, 1)]) is None  # a run-time operand
    assert OPCODES['add'].evaluate([I32, operand(I8, 1), operand(I32, 1)]) is None  # wrong size
    assert OPCODES['add'].evaluate([terms.ByteArray.from_str('ptr'), operand(I8, 1), operand(I8, 1)]) is None
    assert OPCODES['add'].evaluate([I32, operand(I32, 1)]) is None  # wrong count


def test_conversions_evaluate_only_where_llvm_converts():
    assert ev('zext', 'i32', [1], to='i8') is None
    assert ev('zext', 'i32', [1], to='i32') is None
    assert ev('trunc', 'i8', [1], to='i32') is None
    assert ev('trunc', 'i32', [1], to='i32') is None


def test_lookup():
    assert lookup(terms.ByteArray.from_str('add')) is OPCODES['add']
    assert lookup(terms.ByteArray.from_str('add_i32')) is None
    assert lookup(terms.ByteArray(b'\xff')) is None
    assert lookup(terms.Variable('add')) is None


def test_byte_width():
    assert [byte_width(bit_width(typ)) for typ in (I1, I8, I16, I32, I64)] == [1, 1, 2, 4, 8]


def test_evaluate_wraps_to_the_result_width():
    assert ev('add', 'i8', [0xFF, 0x01]) == 0x00
    assert ev('sub', 'i8', [0x00, 0x01]) == 0xFF
    assert ev('mul', 'i16', [0x100, 0x100]) == 0
    assert ev('add', 'i64', [2**64 - 1, 2]) == 1


def test_evaluate_logic():
    assert ev('and', 'i1', [1, 1]) == 1
    assert ev('xor', 'i1', [1, 1]) == 0
    assert ev('or', 'i8', [0x0F, 0xF0]) == 0xFF


def test_evaluate_division_rounds_toward_zero():
    assert ev('sdiv', 'i8', [0xF9, 0x02]) == 0xFD  # -7 / 2 = -3
    assert ev('srem', 'i8', [0xF9, 0x02]) == 0xFF  # -7 % 2 = -1
    assert ev('sdiv', 'i8', [0x07, 0xFE]) == 0xFD  # 7 / -2 = -3
    assert ev('srem', 'i8', [0x07, 0xFE]) == 0x01  # 7 % -2 = 1
    assert ev('udiv', 'i8', [0xF9, 0x02]) == 0x7C  # 249 / 2
    assert ev('urem', 'i8', [0xF9, 0x02]) == 0x01


def test_evaluate_shifts():
    assert ev('shl', 'i8', [0x81, 0x01]) == 0x02
    assert ev('lshr', 'i8', [0x80, 0x07]) == 0x01
    assert ev('ashr', 'i8', [0x80, 0x07]) == 0xFF
    assert ev('ashr', 'i8', [0x40, 0x07]) == 0x00


@pytest.mark.parametrize('name', ['sdiv', 'udiv', 'srem', 'urem'])
def test_evaluate_division_by_zero_has_no_result(name):
    assert ev(name, 'i32', [5, 0]) is None


def test_evaluate_has_no_result_where_llvm_has_none():
    assert ev('sdiv', 'i8', [0x80, 0xFF]) is None  # -128 / -1
    assert ev('srem', 'i8', [0x80, 0xFF]) is None
    assert ev('udiv', 'i8', [0x80, 0xFF]) == 0  # unsigned: 128 / 255
    for name in ('shl', 'lshr', 'ashr'):
        assert ev(name, 'i8', [1, 8]) is None
        assert ev(name, 'i8', [1, 0xFF]) is None
        assert ev(name, 'i8', [1, 7]) is not None


def icmp(predicate, typ, a, b):
    """`evaluate` on `{predicate, type, a, b}`, as a number (or None)."""
    typ = terms.ByteArray.from_str(typ)
    fields = [terms.ByteArray.from_str(predicate), typ, operand(typ, a), operand(typ, b)]
    result = OPCODES['icmp'].evaluate(fields)
    return None if result is None else int.from_bytes(result.value, 'little')


def test_evaluate_comparisons():
    assert icmp('eq', 'i8', 7, 7) == 1
    assert icmp('ne', 'i1', 1, 1) == 0
    # 0xff is -1 signed, 255 unsigned.
    assert icmp('slt', 'i8', 0xFF, 0x00) == 1
    assert icmp('ult', 'i8', 0xFF, 0x00) == 0
    assert icmp('sge', 'i16', 0x8000, 0x7FFF) == 0
    assert icmp('uge', 'i16', 0x8000, 0x7FFF) == 1
    assert icmp('sle', 'i32', 5, 5) == 1
    assert icmp('ugt', 'i64', 2**64 - 1, 0) == 1
    assert icmp('sgt', 'i8', 0x01, 0xFF) == 1
    assert icmp('ule', 'i8', 0x01, 0xFF) == 1


def test_evaluate_conversions():
    assert ev('zext', 'i8', [0xFF], to='i32') == 0xFF
    assert ev('sext', 'i8', [0xFF], to='i32') == 0xFFFFFFFF
    assert ev('sext', 'i8', [0x7F], to='i32') == 0x7F
    assert ev('sext', 'i1', [1], to='i8') == 0xFF
    assert ev('zext', 'i1', [1], to='i64') == 1
    assert ev('trunc', 'i32', [0x12345678], to='i8') == 0x78
    assert ev('trunc', 'i8', [0xFE], to='i1') == 0


def test_only_memory_opcodes_are_impure():
    impure = {name for name, opcode in OPCODES.items() if not opcode.pure}
    assert impure == {'alloca', 'getelementptr', 'load', 'store'}


def test_memory_opcodes_give_a_pointer_and_never_evaluate():
    x = terms.Variable('x')
    point = terms.Struct([terms.Field('x', I32), terms.Field('y', I64)])
    assert OPCODES['alloca'].result_type([I32]) == PTR
    assert OPCODES['alloca'].result_type([point, x]) == PTR
    assert OPCODES['getelementptr'].result_type([point, x, x, x]) == PTR
    # A type that isn't a literal, or a wrong count.
    assert OPCODES['alloca'].result_type([x]) is None
    assert OPCODES['alloca'].result_type([]) is None
    assert OPCODES['alloca'].result_type([I32, x, x]) is None
    assert OPCODES['getelementptr'].result_type([I32, x]) is None
    assert OPCODES['alloca'].evaluate([I32]) is None


def test_load_gives_its_form_and_store_gives_the_empty_struct():
    x = terms.Variable('x')
    point = terms.Struct([terms.Field('x', I32), terms.Field('y', I64)])
    assert OPCODES['load'].result_type([I32, x]) == I32
    assert OPCODES['load'].result_type([point, x]) == point
    assert OPCODES['load'].result_type([PTR, x]) == PTR
    assert OPCODES['load'].result_type([x, x]) is None
    assert OPCODES['store'].result_type([I32, x, x]) == terms.Struct([])
    assert OPCODES['store'].result_type([x, x, x]) is None
    # Neither runs in reduction: oymomo has no memory.
    assert OPCODES['load'].evaluate([I32, x]) is None
    assert OPCODES['store'].evaluate([I32, terms.ByteArray(bytes(4)), x]) is None
