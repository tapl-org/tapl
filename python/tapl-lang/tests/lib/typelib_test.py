# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.lib import proxy, typelib
from tapl_lang.lib.typelib import check_subtype_


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
NoneType = proxy.Proxy(NoneType_)
Any_ = typelib.Any()
Nothing_ = typelib.Nothing()

Alpha_ = Atom('Alpha')
Alpha = proxy.Proxy(Alpha_)
Beta_ = Atom('Beta')
Beta = proxy.Proxy(Beta_)


def test_none_type():
    assert check_subtype_(NoneType_, NoneType_)
    assert not check_subtype_(NoneType_, Any_)
    assert not check_subtype_(Any_, NoneType_)
    assert not check_subtype_(Nothing_, NoneType_)
    assert not check_subtype_(NoneType_, Nothing_)
    assert not check_subtype_(Alpha_, NoneType_)
    assert not check_subtype_(NoneType_, Alpha_)


def test_any():
    assert check_subtype_(Nothing_, Any_)
    assert not check_subtype_(Any_, Nothing_)
    assert check_subtype_(Alpha_, Any_)
    assert not check_subtype_(Any_, Alpha_)


def test_nothing():
    assert check_subtype_(Nothing_, Nothing_)
    assert Nothing_.is_subtype_of(Alpha_) is True
    assert Alpha_.is_supertype_of(Nothing_) is None
    assert check_subtype_(Nothing_, Alpha_)
    assert not check_subtype_(Alpha_, Nothing_)


def test_union():
    alpha_or_beta_ = typelib.Union([Alpha, Beta])
    assert str(alpha_or_beta_) == 'Alpha | Beta'
    assert check_subtype_(Alpha_, alpha_or_beta_)
    assert check_subtype_(Beta_, alpha_or_beta_)
    assert check_subtype_(alpha_or_beta_, Any_)
    assert check_subtype_(Nothing_, alpha_or_beta_)


def test_union_optional():
    alpha_or_none_ = typelib.Union([Alpha, NoneType])
    assert str(alpha_or_none_) == 'Alpha | None'
    assert check_subtype_(Alpha_, alpha_or_none_)
    assert check_subtype_(NoneType_, alpha_or_none_)
    assert not check_subtype_(alpha_or_none_, Any_)
    assert check_subtype_(Nothing_, alpha_or_none_)


# def test_record():
#     record_a = typelib.Record(fields={'x': Any, 'y': Any})
#     record_b = typelib.Record(fields={'x': Any})
#     record_c = typelib.Record(fields={'x': Any, 'y': typelib.Float})

#     assert typelib.check_subtype_(record_a, record_b)
#     assert not typelib.check_subtype_(record_b, record_a)
#     assert not typelib.check_subtype_(record_a, record_c)
