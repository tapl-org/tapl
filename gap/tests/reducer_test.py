# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from gap.printer import print_term
from gap.reader import read
from gap.reducer import is_neutral, is_value, reduce_term


@pytest.mark.parametrize(
    'text',
    [
        '(var x)',
        '(bits 42)',
        '(lambda x (apply (lambda y (var y)) (var x)))',  # a value even with a redex in the body
        '(record a = (bits 1) b = (lambda x (var x)))',
    ],
)
def test_value_shapes(text: str):
    assert is_value(read(text))


@pytest.mark.parametrize(
    'text',
    [
        '(apply (lambda x (var x)) (bits 1))',
        '(record a = (apply (var f) (bits 1)))',  # a field that is not a value
        '(if (var x) (bits 1) (bits 0))',
    ],
)
def test_non_value_shapes(text: str):
    assert not is_value(read(text))


@pytest.mark.parametrize(
    'text',
    [
        '(var x)',
        '(get (var x) a)',
        '(apply (var x) (bits 1))',
        '(apply (get (var x) a) (bits 1))',
        '(fix (var x))',
        '(if (var x) (bits 1) (bits 0))',
    ],
)
def test_neutral_shapes(text: str):
    assert is_neutral(read(text))


@pytest.mark.parametrize(
    'text',
    [
        '(bits 42)',
        '(lambda x (var x))',
        '(record a = (bits 1))',
        '(apply (lambda x (var x)) (bits 1))',  # a redex, not residual
        '(get (record a = (bits 1)) a)',
        '(if (bits 1) (bits 2) (bits 3))',
    ],
)
def test_non_neutral_shapes(text: str):
    assert not is_neutral(read(text))


@pytest.mark.skip(reason='reducer.step is the next piece to write')
@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('(apply (lambda x (var x)) (bits 42))', '(bits 42)'),
        ('(get (record a = (var x)) a)', '(var x)'),
        ('(get (record a = (var x)) b)', '(get (record a = (var x)) b)'),  # residual: label miss
        ('(get (var x) a)', '(get (var x) a)'),  # residual: unknown subject
        ('(if (bits 1) (bits 2) (bits 3))', '(bits 2)'),
        ('(if (bits 0) (bits 2) (bits 3))', '(bits 3)'),
        ('(if (bits "") (bits 2) (bits 3))', '(bits 3)'),  # "" has no bits, so it is zero
        ('(if (bits "0") (bits 2) (bits 3))', '(bits 2)'),  # "0" is the byte 0x30
        # residual: unknown condition
        ('(if (var x) (bits 1) (bits 0))', '(if (var x) (bits 1) (bits 0))'),
        # apply is not field lookup
        ('(apply (record a = (bits 1)) (bits 2))', '(apply (record a = (bits 1)) (bits 2))'),
        # reduction is strong
        ('(lambda y (apply (lambda x (var x)) (var y)))', '(lambda y (var y))'),
    ],
)
def test_reduce(text: str, expected: str):
    assert print_term(reduce_term(read(text))) == expected
