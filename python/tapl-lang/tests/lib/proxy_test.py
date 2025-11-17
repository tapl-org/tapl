# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.lib import proxy


class MySubject(proxy.ProxyMixin):
    def __init__(self):
        self.vars__tapl = {}

    def load__tapl(self, key):
        try:
            return self.vars__tapl[key]
        except KeyError:
            super().load__tapl(key)

    def store__tapl(self, key, value):
        self.vars__tapl[key] = value

    def delete__tapl(self, key):
        del self.vars__tapl[key]

    def __repr__(self):
        return f'MySubject{self.vars__tapl}'


def test_define_variable():
    a = MySubject()
    a.x = 42
    assert a.x == 42


def test_undefined_variable():
    s = MySubject()
    s.store__tapl('a', 100)
    del s.a
    with pytest.raises(AttributeError):
        _ = s.a


def test_repr():
    p = MySubject()
    assert repr(p) == 'MySubject{}'


def test_binop():
    s = MySubject()
    s.store__tapl('__add__', lambda other: f'Added {other}')
    assert s + 3 == 'Added 3'


def test_binop_error():
    s = MySubject()
    with pytest.raises(TypeError):
        _ = s + 3
