# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from gap.error import ReadError
from gap.reader import read
from gap.term import Abs, App, Bits, BitsKind, Bound, Field, Fix, Free, If, Proj, Record


def test_read_bits():
    assert read('(bits 42)') == Bits(BitsKind.INTEGER, '42')
    assert read('(bits 0x3f800000)') == Bits(BitsKind.HEX, '0x3f800000')
    assert read('(bits "hello")') == Bits(BitsKind.STRING, '"hello"')


def test_read_free_variable():
    assert read('(var env)') == Free('env')


def test_read_binds_the_lambda_parameter():
    assert read('(lambda x (var x))') == Abs('x', Bound(0, 'x'))
    assert read('(lambda x (lambda y (var x)))') == Abs('x', Abs('y', Bound(1, 'x')))


def test_read_inner_lambda_shadows():
    assert read('(lambda x (lambda x (var x)))') == Abs('x', Abs('x', Bound(0, 'x')))


def test_read_record_keeps_written_order():
    assert read('(record b = (bits 1) a = (bits 2))') == Record(
        (Field('b', Bits(BitsKind.INTEGER, '1')), Field('a', Bits(BitsKind.INTEGER, '2')))
    )


def test_read_projection_chain():
    assert read('(get (get (var env) puts) x)') == Proj(Proj(Free('env'), 'puts'), 'x')


def test_read_projection_of_a_record():
    assert read('(get (record a = (var x)) a)') == Proj(Record((Field('a', Free('x')),)), 'a')


def test_read_the_other_forms():
    assert read('(apply (var f) (bits 1))') == App(Free('f'), Bits(BitsKind.INTEGER, '1'))
    assert read('(fix (var f))') == Fix(Free('f'))
    assert read('(if (var c) (bits 1) (bits 0))') == If(
        Free('c'), Bits(BitsKind.INTEGER, '1'), Bits(BitsKind.INTEGER, '0')
    )


def test_read_compilation_unit():
    unit = read("""
        (lambda env
          (lambda module
            (record
              main = (get (var env) puts)
              helper = (get (var module) main))))
    """)
    assert unit == Abs(
        'env',
        Abs(
            'module',
            Record((Field('main', Proj(Bound(1, 'env'), 'puts')), Field('helper', Proj(Bound(0, 'module'), 'main')))),
        ),
    )


@pytest.mark.parametrize(
    'text',
    [
        '()',  # the empty list is invalid
        '(f (var x))',  # not a head, never an implicit application
        'x',  # a bare name is not a term
        '42',  # a bare token is not a term
        '(get (var x) a).b',  # '.' is not part of the syntax
        '(var)',  # arity
        '(var x y)',  # arity
        '(var 42)',  # a variable name may not be bits
        '(bits)',  # arity
        '(bits x)',  # a name is not bits
        '(lambda x)',  # arity
        '(lambda x (var x) (var x))',  # arity
        '(lambda 42 (var x))',  # a parameter may not be bits
        '(get (var x))',  # arity
        '(get (var x) 42)',  # a label may not be bits
        '(fix)',  # arity
        '(apply (var f))',  # arity
        '(if (var c) (bits 1))',  # arity
        '(record)',  # a record needs a field
        '(record 1 = (var x))',  # a label may not be bits
        '(record a = (bits 1) a = (bits 2))',  # labels are pairwise distinct
        '(bits "unterminated)',
        '(bits 42abc)',  # starts like bits, matches no bits syntax
        '(var x) (var y)',  # one term per input
    ],
)
def test_read_rejects(text: str):
    with pytest.raises(ReadError):
        read(text)
