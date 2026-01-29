# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.lib import dynamic_attribute


class MySubject(dynamic_attribute.DynamicAttributeMixin):
    def __init__(self):
        self.vars__sa = {}

    def load__sa(self, key):
        try:
            return self.vars__sa[key]
        except KeyError:
            raise AttributeError(f'{self.__class__.__name__} has no attribute "{key}"') from None

    def store__sa(self, key, value):
        self.vars__sa[key] = value

    def delete__sa(self, key):
        del self.vars__sa[key]

    def __repr__(self):
        return f'MySubject{self.vars__sa}'


def test_define_variable():
    a = MySubject()
    a.x = 42
    assert a.x == 42


def test_undefined_variable():
    s = MySubject()
    s.store__sa('a', 100)
    del s.a
    with pytest.raises(AttributeError):
        _ = s.a


def test_repr():
    p = MySubject()
    assert repr(p) == 'MySubject{}'


def test_binop():
    s = MySubject()
    s.store__sa('__add__', lambda other: f'Added {other}')
    assert s + 3 == 'Added 3'


def test_binop_error():
    s = MySubject()
    with pytest.raises(TypeError):
        _ = s + 3
