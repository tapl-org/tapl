# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.core.line_record import LineRecord, split_text_to_lines


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


def test_ignore_comments_when_splitting():
    text = """
Hello
# comment
World
"""
    lines = split_text_to_lines(text.strip())
    assert len(lines) == 2
    assert lines[0].text == 'Hello\n'
    assert lines[1].text == 'World'
