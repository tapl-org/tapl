# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Tags: the meta of one node, as terms hold it.

A `Tag` mirrors the `Tag` message of `meta.proto`. Its place is `(file, start, length)`:
the source `File` it comes from (an object, not a number), and a range of that file's
bytes, `start` counted from 0. A tag with no file has no place (`NO_TAG`). Line and column
are computed only when shown (`File.position`).

A tag is frozen, so terms share it freely: a part keeps its tag through reduction, a copy
shares its source's tag, and E-Opcode's result takes the redex's tag.

`source` converts tags to and from the message (`from_proto`, `to_proto`): an unset field
of the message is the parent's.
"""

import bisect
import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from oymo.oymomo import meta_pb2


def md5(data: bytes) -> str:
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def line_starts(data: bytes) -> tuple[int, ...]:
    """The byte offset of each line's start; the first is always 0."""
    starts = [0]
    position = data.find(b'\n')
    while position >= 0:
        starts.append(position + 1)
        position = data.find(b'\n', position + 1)
    return tuple(starts)


@dataclass(frozen=True)
class File:
    """A source file: its path as given on the command line, its language, its MD5, and the
    byte offset of each line's start."""

    path: str
    language: str
    md5: str
    lines: tuple[int, ...]

    @classmethod
    def of(cls, path: str, language: str, data: bytes) -> 'File':
        """The file `path`, from its bytes."""
        return cls(path, language, md5(data), line_starts(data))

    def position(self, offset: int) -> tuple[int, int]:
        """`(line, column)` of the byte at `offset`, both 1-based, the column in bytes."""
        line = bisect.bisect_right(self.lines, offset)
        return line, offset - self.lines[line - 1] + 1


@dataclass(frozen=True)
class Tag:
    file: File | None = None  # None: no place
    start: int = 0  # byte offset in `file`
    length: int = 0  # in bytes

    def place(self) -> tuple[File | None, int, int]:
        return self.file, self.start, self.length


# The tag of a term with no meta, shared.
NO_TAG = Tag()


def placed(*tags: Tag) -> Tag:
    """The first of `tags` that has a place, else `NO_TAG`."""
    return next((tag for tag in tags if tag.file is not None), NO_TAG)


def from_proto(entry: meta_pb2.Tag, parent: Tag, file: Callable[[int], File | None]) -> Tag:
    """The tag of a nonempty `entry`, whose parent has `parent`. `file` gives the `File` of a
    file number of the message (None for -1, no place)."""
    if not entry.HasField('file'):
        return parent
    return Tag(file(entry.file), entry.start, entry.length)


def to_proto(tag: Tag, parent: Tag, number: Callable[[File], int]) -> meta_pb2.Tag:
    """The entry of `tag`, whose parent has `parent`: the fields that differ from the
    parent's, so a tag equal to its parent's is an empty entry. `number` gives the file
    number of a `File` in the message."""
    entry = meta_pb2.Tag()
    if tag.place() != parent.place():
        if tag.file is None:
            entry.file = -1
        else:
            entry.file, entry.start, entry.length = number(tag.file), tag.start, tag.length
    return entry
