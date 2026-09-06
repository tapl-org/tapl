# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from gap.printer import print_term
from gap.reader import read
from gap.term import Abs, App, Bound, Free

ROUND_TRIP = [
    '(bits 42)',
    '(bits "hello")',
    '(bits 0x3f800000)',
    '(var env)',
    '(get (var env) puts)',
    '(get (get (var x) a) b)',
    '(lambda x (var x))',
    '(lambda x (lambda y (var x)))',
    '(apply (var f) (bits 1))',
    '(fix (lambda x (var x)))',
    '(if (var c) (bits 1) (bits 0))',
    '(record a = (bits 1) b = (var x))',
    '(get (record a = (var x)) a)',
    '(lambda env (lambda module (record main = (get (var env) puts) helper = (get (var module) main))))',
]


@pytest.mark.parametrize('text', ROUND_TRIP)
def test_print_is_the_text_that_was_read(text: str):
    assert print_term(read(text)) == text


@pytest.mark.parametrize('text', ROUND_TRIP)
def test_read_after_print_is_the_same_term(text: str):
    term = read(text)
    assert read(print_term(term)) == term


def test_print_freshens_a_shadowing_binder():
    # the inner binder must not capture the occurrence that belongs to the outer one
    term = Abs('x', Abs('x', Bound(1, 'x')))
    printed = print_term(term)
    assert printed == '(lambda x (lambda x-1 (var x)))'
    assert read(printed) == term


def test_print_freshens_against_a_free_name():
    term = Abs('env', App(Bound(0, 'env'), Free('env')))
    printed = print_term(term)
    assert printed == '(lambda env-1 (apply (var env-1) (var env)))'
    assert read(printed) == term
