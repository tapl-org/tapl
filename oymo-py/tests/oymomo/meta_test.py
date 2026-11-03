# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.oymomo import meta, meta_pb2


def test_line_starts() -> None:
    assert meta.line_starts(b'ab\n\ncd') == (0, 3, 4)
    assert meta.line_starts(b'') == (0,)


def test_position_counts_lines_and_byte_columns_from_one() -> None:
    file = meta.File.of('a.oymo', 'oymomo', 'ab\nλx y\n'.encode())
    # `y` is after `λ` (two bytes), `x` and a space.
    assert file.position(7) == (2, 5)
    assert file.position(0) == (1, 1)
    # The end of the file is still in its last line.
    assert file.position(len('ab\nλx y\n'.encode())) == (3, 1)


def test_the_same_file_read_twice_is_equal() -> None:
    assert meta.File.of('a.oymo', 'alcor', b'abc') == meta.File.of('a.oymo', 'alcor', b'abc')
    assert meta.File.of('a.oymo', 'alcor', b'abc') != meta.File.of('a.oymo', 'alcor', b'abd')


def test_a_long_length_does_not_saturate() -> None:
    file = meta.File.of('a.alcor', 'alcor', b'x' * 100_000)
    tag = meta.Tag(file, 3, 70_000)
    entry = meta.to_proto(tag, meta.NO_TAG, lambda _: 0)
    assert (entry.file, entry.start, entry.length) == (0, 3, 70_000)
    assert meta.from_proto(entry, meta.NO_TAG, lambda _: file) == tag


def test_placed_is_the_first_tag_with_a_place() -> None:
    tag = meta.Tag(meta.File.of('a', 'alcor', b''), 0, 0)
    assert meta.placed(meta.NO_TAG, tag) is tag
    assert meta.placed(meta.NO_TAG) is meta.NO_TAG


def test_an_entry_with_no_file_is_the_parent_tag() -> None:
    parent = meta.Tag(meta.File.of('a', 'alcor', b'abc'), 1, 2)
    assert meta.from_proto(meta_pb2.Tag(), parent, lambda _: None) is parent
    assert not meta.to_proto(meta.Tag(parent.file, 1, 2), parent, lambda _: 0).ListFields()


def test_no_place_is_file_minus_one() -> None:
    parent = meta.Tag(meta.File.of('a', 'alcor', b'abc'), 1, 2)
    entry = meta.to_proto(meta.NO_TAG, parent, lambda _: 0)
    assert entry.file == -1
    assert meta.from_proto(entry, parent, lambda number: None if number == -1 else parent.file) == meta.NO_TAG
