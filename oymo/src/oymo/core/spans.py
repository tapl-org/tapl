# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Spans: where a term comes from, as one integer into a table of source files.

A span is `start << 16 | length`. `start` is a position in a `SpanTable`: each file read
in a run gets its own range of positions, a `Row`, so one integer names both the file and
the place in it. Positions and lengths count UTF-8 bytes. `0` is no span (`NO_SPAN`):
rows start at 1. A length of `MAX_LENGTH` means that many bytes or more.

Line and column are computed only when shown (`SpanTable.resolve`): a row keeps the start
of every line, and a column counts bytes from 1.
"""

import bisect
import hashlib
from dataclasses import dataclass

NO_SPAN = 0
LENGTH_BITS = 16
MAX_LENGTH = (1 << LENGTH_BITS) - 1


def make(start: int, length: int) -> int:
    """The span of `length` bytes at `start`; a longer length saturates at `MAX_LENGTH`."""
    return start << LENGTH_BITS | min(length, MAX_LENGTH)


def start(span: int) -> int:
    return span >> LENGTH_BITS


def length(span: int) -> int:
    return span & MAX_LENGTH


def line_starts(data: bytes) -> tuple[int, ...]:
    """The byte offset of each line's start; the first is always 0."""
    starts = [0]
    position = data.find(b'\n')
    while position >= 0:
        starts.append(position + 1)
        position = data.find(b'\n', position + 1)
    return tuple(starts)


def md5(data: bytes) -> str:
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


@dataclass(frozen=True)
class Row:
    """A source file's range of positions: `start` up to `start + length`, both included,
    so a span at the end of the file still falls in its row."""

    start: int
    length: int
    file: str
    language: str
    hash: str
    lines: tuple[int, ...]

    def contains(self, position: int) -> bool:
        return self.start <= position <= self.start + self.length


class SpanTable:
    """One table per run. Rows never overlap and are kept in start order."""

    def __init__(self) -> None:
        self.rows: list[Row] = []
        self._starts: list[int] = []

    def add_file(self, file: str, language: str, data: bytes) -> Row:
        """The row of a file read in this run, from its bytes."""
        return self.add_row(len(data), file, language, md5(data), line_starts(data))

    def add_row(self, length: int, file: str, language: str, hash_: str, lines: tuple[int, ...]) -> Row:
        """A new row after the last one, or the row that already holds the same file."""
        for row in self.rows:
            if (row.length, row.file, row.language, row.hash, row.lines) == (length, file, language, hash_, lines):
                return row
        start_ = self.rows[-1].start + self.rows[-1].length + 1 if self.rows else 1
        row = Row(start_, length, file, language, hash_, lines)
        self.rows.append(row)
        self._starts.append(start_)
        return row

    def row_of(self, span: int) -> Row | None:
        """The row `span` points into; None for `NO_SPAN` or a span outside every row."""
        if span == NO_SPAN:
            return None
        position = start(span)
        index = bisect.bisect_right(self._starts, position) - 1
        if index >= 0 and self.rows[index].contains(position):
            return self.rows[index]
        return None

    def resolve(self, span: int) -> tuple[str, int, int] | None:
        """`(file, line, column)`, both 1-based, the column in bytes; None if no row holds `span`."""
        row = self.row_of(span)
        if row is None:
            return None
        offset = start(span) - row.start
        line = bisect.bisect_right(row.lines, offset)
        return row.file, line, offset - row.lines[line - 1] + 1
