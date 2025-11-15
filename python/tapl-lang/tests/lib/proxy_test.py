# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.lib import proxy


class MySubject(proxy.Subject):
    def __init__(self):
        self.vars = {}

    def load__tapl(self, key):
        try:
            return self.vars[key]
        except KeyError:
            super().load__tapl(key)

    def store__tapl(self, key, value):
        self.vars[key] = value

    def delete__tapl(self, key):
        del self.vars[key]

    def __repr__(self):
        return f'MySubject{self.vars}'


def test_define_variable():
    a = proxy.ProxyMixin(MySubject())
    a.x = 42
    assert a.x == 42


def test_undefined_variable():
    s = MySubject()
    s.store__tapl('a', 100)
    p = proxy.ProxyMixin(s)
    del p.a
    with pytest.raises(AttributeError):
        _ = p.a


def test_repr():
    p = proxy.ProxyMixin(MySubject())
    assert repr(p) == 'MySubject{}'


def test_binop():
    s = MySubject()
    s.store__tapl('__add__', lambda other: f'Added {other}')
    a = proxy.ProxyMixin(s)
    assert a + 3 == 'Added 3'


def test_binop_error():
    s = MySubject()
    p = proxy.ProxyMixin(s)
    with pytest.raises(TypeError):
        _ = p + 3


def test_replace_subject():
    x = MySubject()
    y = MySubject()
    p = proxy.ProxyMixin(x)
    assert p.subject__tapl is x
    p.subject__tapl = y
    assert p.subject__tapl is not y
    assert repr(vars(p)) == "{'subject__tapl': MySubject{'subject__tapl': MySubject{}}}"
    object.__setattr__(p, proxy.SUBJECT_FIELD_NAME, y)
    assert p.subject__tapl is y
    assert repr(vars(p)) == "{'subject__tapl': MySubject{}}"
