# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.lib import typelib

NoneType = typelib.NoneType()
Any = typelib.Any()
Nothing = typelib.Nothing()


def test_none_type():
    assert typelib.check_subtype_(NoneType, NoneType)
    assert not typelib.check_subtype_(NoneType, Any)
    assert not typelib.check_subtype_(Any, NoneType)
    assert not typelib.check_subtype_(Nothing, NoneType)
    assert not typelib.check_subtype_(NoneType, Nothing)


def test_any_and_nothing():
    assert typelib.check_subtype_(Nothing, Any)
    assert not typelib.check_subtype_(Any, Nothing)


# def test_record():
#     record_a = typelib.Record(fields={'x': Any, 'y': Any})
#     record_b = typelib.Record(fields={'x': Any})
#     record_c = typelib.Record(fields={'x': Any, 'y': typelib.Float})

#     assert typelib.check_subtype_(record_a, record_b)
#     assert not typelib.check_subtype_(record_b, record_a)
#     assert not typelib.check_subtype_(record_a, record_c)
