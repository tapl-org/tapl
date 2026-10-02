# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.oymomo.banf_prim import PRIMS, PrimSignature


def test_same_form_ops():
    assert PRIMS['add_i32'] == PrimSignature('add_i32', 'add', (('a', 'i32'), ('b', 'i32')), 'i32')
    assert PRIMS['sub_i8'].params == (('minuend', 'i8'), ('subtrahend', 'i8'))
    assert PRIMS['udiv_i64'].params == (('dividend', 'i64'), ('divisor', 'i64'))
    assert PRIMS['shl_i16'].params == (('value', 'i16'), ('amount', 'i16'))


def test_comparisons_return_i1():
    assert PRIMS['eq_i1'] == PrimSignature('eq_i1', 'eq', (('a', 'i1'), ('b', 'i1')), 'i1')
    assert PRIMS['slt_i32'] == PrimSignature('slt_i32', 'slt', (('lhs', 'i32'), ('rhs', 'i32')), 'i1')


def test_logic_includes_i1():
    assert 'and_i1' in PRIMS
    assert 'xor_i1' in PRIMS
    assert 'ne_i1' in PRIMS


def test_no_i1_arithmetic_shifts_or_ordered_comparisons():
    for template in ('add', 'mul', 'sub', 'sdiv', 'udiv', 'srem', 'urem', 'shl', 'lshr', 'ashr', 'slt', 'uge'):
        assert f'{template}_i1' not in PRIMS


def test_conversions():
    assert PRIMS['zext_i8_i32'] == PrimSignature('zext_i8_i32', 'zext', (('value', 'i8'),), 'i32')
    assert PRIMS['sext_i1_i64'].result == 'i64'
    assert PRIMS['trunc_i64_i32'] == PrimSignature('trunc_i64_i32', 'trunc', (('value', 'i64'),), 'i32')
    assert 'zext_i32_i8' not in PRIMS
    assert 'trunc_i8_i32' not in PRIMS
    assert 'zext_i32_i32' not in PRIMS
    assert 'trunc_i32_i32' not in PRIMS
