# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from tapl_lang.lib import api, proxy


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


def test_define_variable():
    a = proxy.Proxy(MySubject())
    a.x = 42
    assert a.x == 42


def test_undefined_variable():
    proxy = api.Proxy(MySubject())
    with pytest.raises(AttributeError):
        _ = proxy.undefined_variable
