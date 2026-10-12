# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import terms
from oymo.oymomo.banf_prim import DYNAMIC_PRIMS, PRIMS, PrimFormError, PrimSignature

I1, I8, I16, I32, I64 = (terms.ByteArray(name) for name in (b'i1', b'i8', b'i16', b'i32', b'i64'))


def test_same_form_ops():
    assert PRIMS['add_i32'] == PrimSignature('add_i32', 'add', (('a', I32), ('b', I32)), I32)
    assert PRIMS['sub_i8'].params == (('minuend', I8), ('subtrahend', I8))
    assert PRIMS['udiv_i64'].params == (('dividend', I64), ('divisor', I64))
    assert PRIMS['shl_i16'].params == (('value', I16), ('amount', I16))


def test_comparisons_return_i1():
    assert PRIMS['eq_i1'] == PrimSignature('eq_i1', 'eq', (('a', I1), ('b', I1)), I1)
    assert PRIMS['slt_i32'] == PrimSignature('slt_i32', 'slt', (('lhs', I32), ('rhs', I32)), I1)


def test_logic_includes_i1():
    assert 'and_i1' in PRIMS
    assert 'xor_i1' in PRIMS
    assert 'ne_i1' in PRIMS


def test_no_i1_arithmetic_shifts_or_ordered_comparisons():
    for template in ('add', 'mul', 'sub', 'sdiv', 'udiv', 'srem', 'urem', 'shl', 'lshr', 'ashr', 'slt', 'uge'):
        assert f'{template}_i1' not in PRIMS


def test_conversions():
    assert PRIMS['zext_i8_i32'] == PrimSignature('zext_i8_i32', 'zext', (('value', I8),), I32)
    assert PRIMS['sext_i1_i64'].result == I64
    assert PRIMS['trunc_i64_i32'] == PrimSignature('trunc_i64_i32', 'trunc', (('value', I64),), I32)
    assert 'zext_i32_i8' not in PRIMS
    assert 'trunc_i8_i32' not in PRIMS
    assert 'zext_i32_i32' not in PRIMS
    assert 'trunc_i32_i32' not in PRIMS


def test_dynamic_prims_have_their_own_names():
    assert not PRIMS.keys() & DYNAMIC_PRIMS.keys()
    assert DYNAMIC_PRIMS['extractvalue'].labels == ('struct', 'index')


XY = terms.Struct([terms.Field('x', I32), terms.Field('y', I8)])


def extractvalue_form(forms, values):
    return DYNAMIC_PRIMS['extractvalue'].result_form(forms, values)


def test_extractvalue_form():
    assert extractvalue_form([XY, I8], [None, b'\x01']) == I8
    assert extractvalue_form([XY, I32], [None, b'\x00\x00\x00\x00']) == I32
    # Unlabeled fields are reached the same way.
    assert extractvalue_form([terms.Struct([terms.Field('', I8), terms.Field('', I64)]), I8], [None, b'\x01']) == I64


@pytest.mark.parametrize(
    ('forms', 'values', 'message'),
    [
        ([I32, I8], [None, b'\x00'], 'prim.extractvalue: struct must have a struct form.'),
        ([XY, I8], [None, None], "prim.extractvalue needs a literal index, such as [00]: 'i8'."),
        ([XY, I8], [None, b''], "prim.extractvalue needs a literal index, such as [00]: 'i8'."),
        ([XY, XY], [None, b'\x00'], 'prim.extractvalue: the index form must be one of i1, ..., i64.'),
        ([XY, I8], [None, b'\x02'], 'prim.extractvalue: the struct has no field at index 2.'),
    ],
)
def test_extractvalue_form_errors(forms, values, message):
    with pytest.raises(PrimFormError) as info:
        extractvalue_form(forms, values)
    assert str(info.value) == message
