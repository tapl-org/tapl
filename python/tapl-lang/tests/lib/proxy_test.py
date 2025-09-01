# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.lib import proxy


class MySubject(proxy.Subject):
    def __init__(self):
        self.vars = {}

    def load(self, key):
        try:
            return self.vars[key]
        except KeyError:
            super().load(key)

    def store(self, key, value):
        self.vars[key] = value

    def delete(self, key):
        del self.vars[key]

    def __repr__(self):
        return f'MySubject{self.vars}'


def test_define_variable():
    a = proxy.Proxy(MySubject())
    a.x = 42
    assert a.x == 42


def test_undefined_variable():
    s = MySubject()
    s.store('a', 100)
    p = proxy.Proxy(s)
    del p.a
    with pytest.raises(AttributeError):
        _ = p.a


def test_repr():
    p = proxy.Proxy(MySubject())
    assert repr(p) == 'MySubject{}'


def test_binop():
    s = MySubject()
    s.store('__add__', lambda other: f'Added {other}')
    a = proxy.Proxy(s)
    assert a + 3 == 'Added 3'


def test_binop_error():
    s = MySubject()
    p = proxy.Proxy(s)
    with pytest.raises(TypeError):
        _ = p + 3


def test_replace_subject():
    x = MySubject()
    y = MySubject()
    p = proxy.Proxy(x)
    assert p.subject__tapl is x
    p.subject__tapl = y
    assert p.subject__tapl is not y
    assert repr(vars(p)) == "{'subject__tapl': MySubject{'subject__tapl': MySubject{}}}"
    object.__setattr__(p, proxy.SUBJECT_FIELD_NAME, y)
    assert p.subject__tapl is y
    assert repr(vars(p)) == "{'subject__tapl': MySubject{}}"
