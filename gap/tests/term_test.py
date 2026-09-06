# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from gap.term import Abs, App, Bits, BitsKind, Bound, Field, Free, Record, shift, substitute_top


def integer(text: str) -> Bits:
    return Bits(BitsKind.INTEGER, text)


def test_zero_bits():
    assert integer('0').is_zero
    assert Bits(BitsKind.HEX, '0x00000000').is_zero
    assert Bits(BitsKind.STRING, '""').is_zero


def test_nonzero_bits():
    assert not integer('1').is_zero
    assert not Bits(BitsKind.HEX, '0x1').is_zero
    assert not Bits(BitsKind.STRING, '"0"').is_zero
    assert not Bits(BitsKind.STRING, '"hello"').is_zero


def test_shift_skips_inner_binders():
    # (lambda x (apply x y)) where y is index 0 outside
    term = Abs('x', App(Bound(0, 'x'), Bound(1, 'y')))
    assert shift(term, 2) == Abs('x', App(Bound(0, 'x'), Bound(3, 'y')))


def test_substitute_top_replaces_the_parameter():
    # [x ↦ 42] (apply x x)
    assert substitute_top(App(Bound(0, 'x'), Bound(0, 'x')), integer('42')) == App(integer('42'), integer('42'))


def test_substitute_top_shifts_the_argument_under_a_binder():
    # [x ↦ free] (lambda y x) keeps the argument pointing at the same binder
    body = Abs('y', Bound(1, 'x'))
    assert substitute_top(body, Free('env')) == Abs('y', Free('env'))


def test_substitute_top_leaves_a_shadowed_name_alone():
    # [x ↦ 42] (lambda x x) substitutes nothing: the inner lambda shadows x
    assert substitute_top(Abs('x', Bound(0, 'x')), integer('42')) == Abs('x', Bound(0, 'x'))


def test_substitute_reaches_record_fields_but_not_labels():
    record = Record((Field('a', Bound(0, 'x')), Field('b', Free('y'))))
    assert substitute_top(record, integer('7')) == Record((Field('a', integer('7')), Field('b', Free('y'))))
