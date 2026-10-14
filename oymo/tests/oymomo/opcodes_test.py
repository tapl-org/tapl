# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.oymomo import terms
from oymo.oymomo.opcodes import FOLDED_TEMPLATES, OPCODES, OpcodeSignature, byte_count, evaluate, form_bits

I1, I8, I16, I32, I64 = (terms.ByteArray(name) for name in (b'i1', b'i8', b'i16', b'i32', b'i64'))


def test_same_form_ops():
    assert OPCODES['add_i32'] == OpcodeSignature('add_i32', 'add', (('a', I32), ('b', I32)), I32)
    assert OPCODES['sub_i8'].params == (('minuend', I8), ('subtrahend', I8))
    assert OPCODES['udiv_i64'].params == (('dividend', I64), ('divisor', I64))
    assert OPCODES['shl_i16'].params == (('value', I16), ('amount', I16))


def test_comparisons_return_i1():
    assert OPCODES['eq_i1'] == OpcodeSignature('eq_i1', 'eq', (('a', I1), ('b', I1)), I1)
    assert OPCODES['slt_i32'] == OpcodeSignature('slt_i32', 'slt', (('lhs', I32), ('rhs', I32)), I1)


def test_logic_includes_i1():
    assert 'and_i1' in OPCODES
    assert 'xor_i1' in OPCODES
    assert 'ne_i1' in OPCODES


def test_no_i1_arithmetic_shifts_or_ordered_comparisons():
    for template in ('add', 'mul', 'sub', 'sdiv', 'udiv', 'srem', 'urem', 'shl', 'lshr', 'ashr', 'slt', 'uge'):
        assert f'{template}_i1' not in OPCODES


def test_conversions():
    assert OPCODES['zext_i8_i32'] == OpcodeSignature('zext_i8_i32', 'zext', (('value', I8),), I32)
    assert OPCODES['sext_i1_i64'].result == I64
    assert OPCODES['trunc_i64_i32'] == OpcodeSignature('trunc_i64_i32', 'trunc', (('value', I64),), I32)
    assert 'zext_i32_i8' not in OPCODES
    assert 'trunc_i8_i32' not in OPCODES
    assert 'zext_i32_i32' not in OPCODES
    assert 'trunc_i32_i32' not in OPCODES


def test_byte_count():
    assert [byte_count(form_bits(form)) for form in (I1, I8, I16, I32, I64)] == [1, 1, 2, 4, 8]


def test_evaluate_wraps_to_the_result_width():
    assert evaluate(OPCODES['add_i8'], [0xFF, 0x01]) == 0x00
    assert evaluate(OPCODES['sub_i8'], [0x00, 0x01]) == 0xFF
    assert evaluate(OPCODES['mul_i16'], [0x100, 0x100]) == 0
    assert evaluate(OPCODES['add_i64'], [2**64 - 1, 2]) == 1


def test_evaluate_logic():
    assert evaluate(OPCODES['and_i1'], [1, 1]) == 1
    assert evaluate(OPCODES['xor_i1'], [1, 1]) == 0
    assert evaluate(OPCODES['or_i8'], [0x0F, 0xF0]) == 0xFF


def test_folded_templates_are_opcode_templates():
    assert {signature.template for signature in OPCODES.values()} >= FOLDED_TEMPLATES


def test_evaluate_division_rounds_toward_zero():
    assert evaluate(OPCODES['sdiv_i8'], [0xF9, 0x02]) == 0xFD  # -7 / 2 = -3
    assert evaluate(OPCODES['srem_i8'], [0xF9, 0x02]) == 0xFF  # -7 % 2 = -1
    assert evaluate(OPCODES['sdiv_i8'], [0x07, 0xFE]) == 0xFD  # 7 / -2 = -3
    assert evaluate(OPCODES['srem_i8'], [0x07, 0xFE]) == 0x01  # 7 % -2 = 1
    assert evaluate(OPCODES['udiv_i8'], [0xF9, 0x02]) == 0x7C  # 249 / 2
    assert evaluate(OPCODES['urem_i8'], [0xF9, 0x02]) == 0x01


def test_evaluate_shifts():
    assert evaluate(OPCODES['shl_i8'], [0x81, 0x01]) == 0x02
    assert evaluate(OPCODES['lshr_i8'], [0x80, 0x07]) == 0x01
    assert evaluate(OPCODES['ashr_i8'], [0x80, 0x07]) == 0xFF
    assert evaluate(OPCODES['ashr_i8'], [0x40, 0x07]) == 0x00


def test_evaluate_has_no_result_where_llvm_has_none():
    for template in ('sdiv', 'udiv', 'srem', 'urem'):
        assert evaluate(OPCODES[f'{template}_i32'], [5, 0]) is None
    assert evaluate(OPCODES['sdiv_i8'], [0x80, 0xFF]) is None  # -128 / -1
    assert evaluate(OPCODES['srem_i8'], [0x80, 0xFF]) is None
    assert evaluate(OPCODES['udiv_i8'], [0x80, 0xFF]) == 0  # unsigned: 128 / 255
    for template in ('shl', 'lshr', 'ashr'):
        assert evaluate(OPCODES[f'{template}_i8'], [1, 8]) is None
        assert evaluate(OPCODES[f'{template}_i8'], [1, 0xFF]) is None
        assert evaluate(OPCODES[f'{template}_i8'], [1, 7]) is not None


def test_evaluate_comparisons():
    assert evaluate(OPCODES['eq_i8'], [7, 7]) == 1
    assert evaluate(OPCODES['ne_i1'], [1, 1]) == 0
    # 0xff is -1 signed, 255 unsigned.
    assert evaluate(OPCODES['slt_i8'], [0xFF, 0x00]) == 1
    assert evaluate(OPCODES['ult_i8'], [0xFF, 0x00]) == 0
    assert evaluate(OPCODES['sge_i16'], [0x8000, 0x7FFF]) == 0
    assert evaluate(OPCODES['uge_i16'], [0x8000, 0x7FFF]) == 1
    assert evaluate(OPCODES['sle_i32'], [5, 5]) == 1
    assert evaluate(OPCODES['ugt_i64'], [2**64 - 1, 0]) == 1


def test_evaluate_conversions():
    assert evaluate(OPCODES['zext_i8_i32'], [0xFF]) == 0xFF
    assert evaluate(OPCODES['sext_i8_i32'], [0xFF]) == 0xFFFFFFFF
    assert evaluate(OPCODES['sext_i8_i32'], [0x7F]) == 0x7F
    assert evaluate(OPCODES['sext_i1_i8'], [1]) == 0xFF
    assert evaluate(OPCODES['zext_i1_i64'], [1]) == 1
    assert evaluate(OPCODES['trunc_i32_i8'], [0x12345678]) == 0x78
    assert evaluate(OPCODES['trunc_i8_i1'], [0xFE]) == 0


def test_every_opcode_folds():
    assert {signature.template for signature in OPCODES.values()} == FOLDED_TEMPLATES
