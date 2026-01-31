# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.lib import dynamic_attribute, kinds
from tapl_lang.lib.kinds import check_subtype


class Atom(dynamic_attribute.DynamicAttributeMixin):
    def __init__(self, title: str):
        self._title__sa = title

    def is_supertype_of__sa(self, subtype):
        if self is subtype:
            return True
        if isinstance(subtype, kinds.Nothing):
            return True
        return None

    def is_subtype_of__sa(self, supertype):
        if self is supertype:
            return True
        if isinstance(supertype, kinds.Any):
            return True
        return None

    def __repr__(self):
        return self._title__sa


NoneType = kinds.NoneType()
Any = kinds.Any()
Nothing = kinds.Nothing()

Alpha = Atom('Alpha')
Beta = Atom('Beta')
Gamma = Atom('Gamma')


def test_union():
    alpha_or_beta = kinds.Union([Alpha, Beta])
    assert str(alpha_or_beta) == 'Alpha | Beta'
    assert check_subtype(Alpha, alpha_or_beta)
    assert check_subtype(Beta, alpha_or_beta)
    assert check_subtype(alpha_or_beta, Any)
    assert check_subtype(Nothing, alpha_or_beta)


def test_union_optional():
    alpha_or_none = kinds.Union([Alpha, NoneType])
    assert str(alpha_or_none) == 'Alpha | None'
    assert check_subtype(Alpha, alpha_or_none)
    assert check_subtype(NoneType, alpha_or_none)
    assert not check_subtype(alpha_or_none, Any)
    assert check_subtype(Nothing, alpha_or_none)


def test_union_to_union():
    alpha_or_beta = kinds.Union([Alpha, Beta])
    beta_or_gamma = kinds.Union([Beta, Gamma])
    alpha_beta_gamma = kinds.Union([Alpha, Beta, Gamma])
    assert check_subtype(alpha_or_beta, alpha_beta_gamma)
    assert not check_subtype(beta_or_gamma, alpha_or_beta)


def test_intersection():
    alpha_and_beta = kinds.Intersection([Alpha, Beta])
    assert str(alpha_and_beta) == 'Alpha & Beta'
    assert check_subtype(alpha_and_beta, Alpha)
    assert check_subtype(alpha_and_beta, Beta)
    assert check_subtype(alpha_and_beta, Any)
    assert check_subtype(Nothing, alpha_and_beta)
    assert not check_subtype(NoneType, alpha_and_beta)


def test_intersection_with_none():
    alpha_and_none = kinds.Intersection([Alpha, NoneType])
    assert str(alpha_and_none) == 'Alpha & None'
    assert check_subtype(alpha_and_none, Alpha)
    assert check_subtype(alpha_and_none, NoneType)
    assert check_subtype(alpha_and_none, Any)
    assert not check_subtype(Nothing, alpha_and_none)


def test_intersection_to_intersection():
    alpha_and_beta = kinds.Intersection([Alpha, Beta])
    beta_and_gamma = kinds.Intersection([Beta, Gamma])
    alpha_beta_gamma = kinds.Intersection([Alpha, Beta, Gamma])
    assert check_subtype(alpha_beta_gamma, alpha_and_beta)
    assert not check_subtype(alpha_and_beta, beta_and_gamma)


def test_any():
    assert check_subtype(Any, kinds.Any())
    assert check_subtype(kinds.Any(), Any)
    assert check_subtype(Nothing, Any)
    assert not check_subtype(Any, Nothing)
    assert check_subtype(Alpha, Any)
    assert not check_subtype(Any, Alpha)


def test_nothing():
    assert check_subtype(Nothing, kinds.Nothing())
    assert check_subtype(kinds.Nothing(), Nothing)
    assert check_subtype(Nothing, Alpha)
    assert not check_subtype(Alpha, Nothing)


def test_none_type():
    assert check_subtype(NoneType, kinds.NoneType())
    assert check_subtype(kinds.NoneType(), NoneType)
    assert not check_subtype(NoneType, Any)
    assert not check_subtype(Any, NoneType)
    assert not check_subtype(Nothing, NoneType)
    assert not check_subtype(NoneType, Nothing)
    assert not check_subtype(Alpha, NoneType)
    assert not check_subtype(NoneType, Alpha)


def test_record():
    ab = kinds.Record(fields={'a': Alpha, 'b': Beta})
    g = kinds.Record(fields={'g': Gamma})
    abg = kinds.Record(fields={'a': Alpha, 'b': Beta, 'g': Gamma})

    assert check_subtype(ab, Any)
    assert check_subtype(Nothing, ab)
    assert not check_subtype(ab, NoneType)
    assert not check_subtype(NoneType, ab)
    assert not check_subtype(ab, abg)
    assert check_subtype(abg, ab)
    assert not check_subtype(ab, g)
    assert not check_subtype(g, ab)
