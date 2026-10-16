# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import terms
from oymo.oymomo.opcodes import OPCODES, PTR, bit_width, byte_width, decode_uint, lookup

I1, I8, I16, I32, I64 = (terms.ByteArray(name) for name in (b'i1', b'i8', b'i16', b'i32', b'i64'))


def operand(form, value):
    """`value` as the bare bytes of an operand read at `form`."""
    return terms.ByteArray(value.to_bytes(byte_width(bit_width(form)), 'little'))


def ev(name, form, operands, to=None):
    """`evaluate` on `{form, operands...}`, or `{form, operand, to}` for a conversion, as an
    unsigned number (or None)."""
    form = terms.ByteArray.from_str(form)
    fields = [form, *(operand(form, value) for value in operands)]
    if to is not None:
        fields.append(terms.ByteArray.from_str(to))
    result = OPCODES[name].evaluate(fields)
    return None if result is None else int.from_bytes(result.value, 'little')


def test_one_opcode_per_llvm_instruction():
    assert set(OPCODES) == {
        *('add', 'sub', 'mul', 'sdiv', 'udiv', 'srem', 'urem', 'shl', 'lshr', 'ashr', 'and', 'or', 'xor'),
        *(f'icmp_{p}' for p in ('eq', 'ne', 'slt', 'sle', 'sgt', 'sge', 'ult', 'ule', 'ugt', 'uge')),
        *('zext', 'sext', 'trunc'),
        *('alloca', 'getelementptr', 'load', 'store', 'global'),
    }


def test_form_of():
    x = terms.Variable('x')
    assert OPCODES['add'].form_of([I32, x, x]) == I32
    assert OPCODES['icmp_eq'].form_of([I32, x, x]) == I1
    assert OPCODES['zext'].form_of([I8, x, I32]) == I32
    # The fields don't tell it: a wrong count, or a form that isn't a byte array.
    assert OPCODES['add'].form_of([I32, x]) is None
    assert OPCODES['add'].form_of([x, x, x]) is None
    assert OPCODES['zext'].form_of([I8, x, x]) is None


def test_evaluate_gives_the_result_bytes():
    assert OPCODES['add'].evaluate([I32, operand(I32, 1), operand(I32, 2)]) == operand(I32, 3)
    assert OPCODES['icmp_eq'].evaluate([I8, operand(I8, 7), operand(I8, 7)]) == operand(I1, 1)
    assert OPCODES['zext'].evaluate([I8, operand(I8, 0xFF), I32]) == operand(I32, 0xFF)


def test_evaluate_reads_bare_or_formed_operands():
    formed = terms.Formed(operand(I8, 1), I8)
    assert OPCODES['add'].evaluate([I8, formed, operand(I8, 2)]) == operand(I8, 3)
    assert decode_uint(formed, I8) == 1
    # A written form is not compared: the bytes are read at the opcode's form.
    assert decode_uint(terms.Formed(operand(I8, 1), I32), I8) == 1


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
    assert [byte_width(bit_width(form)) for form in (I1, I8, I16, I32, I64)] == [1, 1, 2, 4, 8]


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


def test_evaluate_comparisons():
    assert ev('icmp_eq', 'i8', [7, 7]) == 1
    assert ev('icmp_ne', 'i1', [1, 1]) == 0
    # 0xff is -1 signed, 255 unsigned.
    assert ev('icmp_slt', 'i8', [0xFF, 0x00]) == 1
    assert ev('icmp_ult', 'i8', [0xFF, 0x00]) == 0
    assert ev('icmp_sge', 'i16', [0x8000, 0x7FFF]) == 0
    assert ev('icmp_uge', 'i16', [0x8000, 0x7FFF]) == 1
    assert ev('icmp_sle', 'i32', [5, 5]) == 1
    assert ev('icmp_ugt', 'i64', [2**64 - 1, 0]) == 1


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
    assert impure == {'alloca', 'getelementptr', 'load', 'store', 'global'}


def test_memory_opcodes_give_a_pointer_and_never_evaluate():
    x = terms.Variable('x')
    point = terms.Struct([terms.Field('x', I32), terms.Field('y', I64)])
    assert OPCODES['alloca'].form_of([I32]) == PTR
    assert OPCODES['alloca'].form_of([point, x]) == PTR
    assert OPCODES['getelementptr'].form_of([point, x, x, x]) == PTR
    # A form that isn't a literal, or a wrong count.
    assert OPCODES['alloca'].form_of([x]) is None
    assert OPCODES['alloca'].form_of([]) is None
    assert OPCODES['alloca'].form_of([I32, x, x]) is None
    assert OPCODES['getelementptr'].form_of([I32, x]) is None
    assert OPCODES['alloca'].evaluate([I32]) is None


def test_load_gives_its_form_and_store_gives_the_empty_struct():
    x = terms.Variable('x')
    point = terms.Struct([terms.Field('x', I32), terms.Field('y', I64)])
    assert OPCODES['load'].form_of([I32, x]) == I32
    assert OPCODES['load'].form_of([point, x]) == point
    assert OPCODES['load'].form_of([PTR, x]) == PTR
    assert OPCODES['load'].form_of([x, x]) is None
    assert OPCODES['store'].form_of([x, x]) == terms.Struct([])
    # Neither runs in reduction: oymomo has no memory.
    assert OPCODES['load'].evaluate([I32, x]) is None
    assert OPCODES['store'].evaluate([terms.ByteArray(bytes(4)), x]) is None
