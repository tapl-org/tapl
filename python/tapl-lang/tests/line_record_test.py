# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.line_record import LineRecord


def test_empty_line1():
    line = LineRecord(1, '')
    assert line.empty
    assert line.indent is None


def test_empty_line2():
    line = LineRecord(1, '\n')
    assert line.empty
    assert line.indent is None


def test_line_ends_with_colon():
    line = LineRecord(1, ' abc : \n')
    assert not line.empty
    assert line.ends_with_colon
    assert line.indent == 1
