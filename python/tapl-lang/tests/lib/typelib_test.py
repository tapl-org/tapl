# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.lib import proxy, typelib


class Atom(proxy.Subject):
    def __init__(self, title: str):
        self._title = title

    def is_supertype_of(self, subtype_):
        if self is subtype_:
            return True
        return None

    def is_subtype_of(self, supertype_):
        if self is supertype_:
            return True
        return None

    def __repr__(self):
        return self._title


NoneType_ = typelib.NoneType()
Any_ = typelib.Any()
Nothing_ = typelib.Nothing()

Alpha_ = Atom('Alpha')
Alpha = proxy.Proxy(Alpha_)
Beta_ = Atom('Beta')
Beta = proxy.Proxy(Beta_)


def test_none_type():
    assert typelib.check_subtype_(NoneType_, NoneType_)
    assert not typelib.check_subtype_(NoneType_, Any_)
    assert not typelib.check_subtype_(Any_, NoneType_)
    assert not typelib.check_subtype_(Nothing_, NoneType_)
    assert not typelib.check_subtype_(NoneType_, Nothing_)
    assert not typelib.check_subtype_(Alpha_, NoneType_)
    assert not typelib.check_subtype_(NoneType_, Alpha_)


def test_any():
    assert typelib.check_subtype_(Nothing_, Any_)
    assert not typelib.check_subtype_(Any_, Nothing_)
    assert typelib.check_subtype_(Alpha_, Any_)
    assert not typelib.check_subtype_(Any_, Alpha_)


def test_nothing():
    assert typelib.check_subtype_(Nothing_, Nothing_)
    assert Nothing_.is_subtype_of(Alpha_) is True
    assert Alpha_.is_supertype_of(Nothing_) is None
    assert typelib.check_subtype_(Nothing_, Alpha_)
    assert not typelib.check_subtype_(Alpha_, Nothing_)


def test_union():
    pass


# def test_record():
#     record_a = typelib.Record(fields={'x': Any, 'y': Any})
#     record_b = typelib.Record(fields={'x': Any})
#     record_c = typelib.Record(fields={'x': Any, 'y': typelib.Float})

#     assert typelib.check_subtype_(record_a, record_b)
#     assert not typelib.check_subtype_(record_b, record_a)
#     assert not typelib.check_subtype_(record_a, record_c)
