# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.core import spans


def test_make_packs_start_and_length() -> None:
    span = spans.make(0x26, 0x12)
    assert span == 0x260012
    assert (spans.start(span), spans.length(span)) == (0x26, 0x12)


def test_a_long_length_saturates() -> None:
    assert spans.length(spans.make(1, 0x12345)) == spans.MAX_LENGTH


def test_line_starts() -> None:
    assert spans.line_starts(b'ab\n\ncd') == (0, 3, 4)
    assert spans.line_starts(b'') == (0,)


def test_rows_start_at_one_and_never_touch() -> None:
    table = spans.SpanTable()
    a = table.add_file('a.oymo', 'oymomo', b'abc\n')
    b = table.add_file('b.oymo', 'alcor', b'x')
    assert (a.start, a.length) == (1, 4)
    # The end of `a.oymo` (position 5) is still in its row.
    assert b.start == 6
    assert table.row_of(spans.make(5, 0)) is a
    assert table.row_of(spans.make(6, 1)) is b


def test_no_span_and_a_span_outside_every_row_have_no_row() -> None:
    table = spans.SpanTable()
    table.add_file('a.oymo', 'oymomo', b'abc')
    assert table.row_of(spans.NO_SPAN) is None
    assert table.row_of(spans.make(100, 1)) is None
    assert table.resolve(spans.make(100, 1)) is None


def test_resolve_counts_lines_and_byte_columns_from_one() -> None:
    table = spans.SpanTable()
    row = table.add_file('a.oymo', 'oymomo', 'ab\nλx y\n'.encode())
    # `y` is after `λ` (two bytes), `x` and a space.
    assert table.resolve(spans.make(row.start + 7, 1)) == ('a.oymo', 2, 5)
    assert table.resolve(spans.make(row.start, 1)) == ('a.oymo', 1, 1)


def test_the_same_file_gets_one_row() -> None:
    table = spans.SpanTable()
    a = table.add_file('a.oymo', 'alcor', b'abc')
    assert table.add_file('a.oymo', 'alcor', b'abc') is a
    assert table.add_file('a.oymo', 'alcor', b'abd') is not a
