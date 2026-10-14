# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.oymomo import terms
from oymo.oymomo.opcodes import OPCODES, OpcodeSignature

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
