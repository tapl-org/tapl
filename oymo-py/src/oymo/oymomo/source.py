# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""An oymomo source file: the code, then an optional meta section with the code's tags.

    language oymomo
    <the code: one term>
    ---
    <the meta: a `Tags` message of `meta.proto`, as textproto>

The meta is not a term and is never reduced: the file's term is the code alone. Tags are
not for humans; they pass a frontend's source places on to the backend.

    code_md5: "<MD5 of everything before the `---` line>"
    files {
      path: "alcor/helpers.oymo"
      language: "alcor"
      md5: "<the file's MD5>"
      lines: [0, 15, 16]
    }
    tags { skip: 3 }
    tags { file: 0 start: 57 length: 73 }

- `files` are the source files the tags point into, numbered from 0: the path as given on
  the command line, the language of that file, the file's MD5, and the byte offset of each
  of its lines.
- `tags` has one entry per node of the code's kernel term: the node's `meta.Tag`. Its place
  is `file: k` (`files[k]`) with `start` and `length` in bytes of that file, or `file: -1`
  (no place). An entry with no `file` is the parent's place; an empty entry is the parent's
  tag, shared. `skip: N` stands for N empty entries. Nodes are visited as `terms.nodes`
  does: a node, then its children; a struct's `Field` before its value.
- Fields a reader doesn't know are skipped, so meta has no version.
- A term with no entry gets its place in the file being read. If the code's MD5 doesn't
  match `code_md5`, the tags are dropped with a warning.
- `write` writes an empty entry for a tag equal to its parent's. It never writes a place in
  a `language oymomo` file: oymomo code is generated, so only places in a frontend's
  sources (Alcor, Mizar, ...) are kept; such a tag is written with its parent's place. It
  numbers the files in the order of their first use. With no file to point into, there is
  no meta section.
- `write` prints the meta in field order: one line per field, a list of numbers on one
  line, a `files` entry over several lines, and a `tags` entry on one line.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace

from google.protobuf import text_format

from oymo.core import syntax
from oymo.oymomo import grammar, meta, meta_pb2, printer, terms

LANGUAGE = grammar.LANGUAGE
LANGUAGE_HEADER = f'language {LANGUAGE}\n'
SEPARATOR = '---'

_SEPARATOR_LINE = re.compile(rf'^{re.escape(SEPARATOR)}$', re.MULTILINE)
# The `line:column : ` that the textproto parser puts before its message.
_PARSE_ERROR_PLACE = re.compile(r'^\d+(:\d+)? : ')


class SourceError(Exception):
    def __init__(self, message: str, tag: meta.Tag) -> None:
        super().__init__(message)
        self.message = message
        self.tag = tag


@dataclass
class Loaded:
    """A file's term, and warnings as `(message, tag)`."""

    term: syntax.Term
    warnings: list[tuple[str, meta.Tag]] = field(default_factory=list)


def read(text: str, path: str) -> Loaded:
    """The term of the source file `text`, read from `path`, with its tags. A syntax error is
    an `ErrorTerm`; a bad header or meta section raises `SourceError`."""
    file = meta.File.of(path, LANGUAGE, text.encode('utf-8'))

    def here(offset: int) -> meta.Tag:
        return meta.Tag(file, len(text[:offset].encode('utf-8')), 0)

    if not text.startswith(LANGUAGE_HEADER):
        raise SourceError(f'Expected the first line to be {LANGUAGE_HEADER.strip()!r}.', here(0))
    separator = _SEPARATOR_LINE.search(text, len(LANGUAGE_HEADER))
    code_end = len(text) if separator is None else separator.start()
    # The header is ASCII, so its length in characters is its length in bytes.
    term = grammar.parse(text[len(LANGUAGE_HEADER) : code_end], file, len(LANGUAGE_HEADER))
    loaded = Loaded(term)
    if separator is None or isinstance(term, syntax.ErrorTerm):
        return loaded
    meta_start = separator.end() + 1 if text.startswith('\n', separator.end()) else separator.end()
    message = _parse_meta(text, meta_start, here)
    read_ = _read_meta(message, text[:code_end].encode('utf-8'), here(separator.start()), loaded)
    if read_ is not None:
        _assign(term, *read_, here(separator.start()))
    return loaded


def _parse_meta(text: str, meta_start: int, here: Callable[[int], meta.Tag]) -> meta_pb2.Tags:
    """The meta section, `text` from `meta_start` on; unknown fields are skipped."""
    message = meta_pb2.Tags()
    try:
        text_format.Parse(text[meta_start:], message, allow_unknown_field=True)
    except text_format.ParseError as error:
        offset = meta_start
        if (line := error.GetLine()) is not None:
            for _ in range(line - 1):
                offset = text.find('\n', offset) + 1 or len(text)
            offset = min(offset + max((error.GetColumn() or 1) - 1, 0), len(text))
        reason = _PARSE_ERROR_PLACE.sub('', str(error))
        raise SourceError(f'The meta section is not valid textproto: {reason}', here(offset)) from None
    return message


def _read_meta(
    message: meta_pb2.Tags, code: bytes, here: meta.Tag, loaded: Loaded
) -> tuple[list[meta_pb2.Tag | None], list[meta.File]] | None:
    """The `tags` entries, one per node (None for an empty entry), and the files they number;
    None if the code changed."""
    if message.code_md5 != meta.md5(code):
        loaded.warnings.append(('The code changed since its tags were written; the tags are dropped.', here))
        return None
    files = [_read_file(file, here) for file in message.files]
    entries: list[meta_pb2.Tag | None] = []
    for entry in message.tags:
        if entry.skip and entry.HasField('file'):
            raise SourceError('A tag of the meta has both a file and a skip.', here)
        if not entry.HasField('file') and (entry.start or entry.length):
            raise SourceError('A tag of the meta has a start or a length but no file.', here)
        if entry.HasField('file') and not -1 <= entry.file < len(files):
            raise SourceError(f'A tag of the meta names file {entry.file}; there are {len(files)} files.', here)
        if entry.skip or not entry.ListFields():
            entries.extend([None] * max(entry.skip, 1))
        else:
            entries.append(entry)
    return entries, files


def _read_file(file: meta_pb2.File, here: meta.Tag) -> meta.File:
    if not file.lines:
        raise SourceError(f'The file {file.path!r} in the meta has no line starts.', here)
    return meta.File(file.path, file.language, file.md5, tuple(file.lines))


def _assign(term: syntax.Term, entries: list[meta_pb2.Tag | None], files: list[meta.File], here: meta.Tag) -> None:
    """Gives each node its entry's `meta.Tag`; an empty entry (None) gives the parent's."""

    def file(number: int) -> meta.File | None:
        return None if number == -1 else files[number]

    stack: list[tuple[terms.Node, meta.Tag]] = [(term, meta.NO_TAG)]
    count = 0
    while stack:
        node, parent = stack.pop()
        if count == len(entries):
            raise SourceError(f'The meta has {len(entries)} tags; the code has more nodes.', here)
        entry = entries[count]
        count += 1
        node.tag = parent if entry is None else meta.from_proto(entry, parent, file)
        stack.extend((child, node.tag) for child in reversed(terms.node_children(node)))
    if count != len(entries):
        raise SourceError(f'The meta has {len(entries)} tags; the code has {count} nodes.', here)


def write(term: syntax.Term) -> str:
    """The source file of `term`: the code pretty-printed, then the meta section if a place
    in a frontend's source is left to write."""
    code = LANGUAGE_HEADER + printer.show(term, pretty=True, name_indices=True) + '\n'
    files: list[meta.File] = []
    numbers: dict[meta.File, int] = {}
    by_id: dict[int, int] = {}  # numbers by object, so a file's lines are hashed once

    def number(file: meta.File) -> int:
        if id(file) not in by_id:
            if file not in numbers:
                numbers[file] = len(files)
                files.append(file)
            by_id[id(file)] = numbers[file]
        return by_id[id(file)]

    entries = [meta.to_proto(tag, parent, number) for tag, parent in _written(term)]
    if not files:
        return code
    message = meta_pb2.Tags(code_md5=meta.md5(code.encode('utf-8')))
    for file in files:
        message.files.add(path=file.path, language=file.language, md5=file.md5, lines=file.lines)
    message.tags.extend(_runs(entries))
    return code + SEPARATOR + '\n' + _show(message)


def _show(message: meta_pb2.Tags) -> str:
    """`message` as textproto, in field order: a list of numbers on one line, a `tags` entry
    on one line. `tags` is the last field, so it is printed last."""
    head = meta_pb2.Tags()
    head.CopyFrom(message)
    del head.tags[:]
    lines = [text_format.MessageToString(head, as_utf8=True, use_short_repeated_primitives=True)]
    for entry in message.tags:
        shown = text_format.MessageToString(entry, as_one_line=True)
        lines.append(f'tags {{ {shown} }}\n' if shown else 'tags {}\n')
    return ''.join(lines)


def _written(term: syntax.Term) -> list[tuple[meta.Tag, meta.Tag]]:
    """`(tag, parent)` per node: the `meta.Tag` written for it, and the one written for its
    parent. A place in a `language oymomo` file is never written: such a tag is written with
    its parent's place."""
    written: list[tuple[meta.Tag, meta.Tag]] = []
    stack: list[tuple[terms.Node, meta.Tag]] = [(term, meta.NO_TAG)]
    while stack:
        node, parent = stack.pop()
        tag = node.tag
        if tag.file is not None and tag.file.language == LANGUAGE:
            tag = replace(tag, file=parent.file, start=parent.start, length=parent.length)
        written.append((tag, parent))
        stack.extend((child, tag) for child in reversed(terms.node_children(node)))
    return written


def _runs(entries: list[meta_pb2.Tag]) -> list[meta_pb2.Tag]:
    """`entries` with each run of empty entries as one `skip`, or one empty entry."""
    result: list[meta_pb2.Tag] = []
    empty = 0
    for entry in entries:
        if not entry.ListFields():
            empty += 1
            continue
        if empty:
            result.append(_empty(empty))
            empty = 0
        result.append(entry)
    if empty:
        result.append(_empty(empty))
    return result


def _empty(count: int) -> meta_pb2.Tag:
    return meta_pb2.Tag() if count == 1 else meta_pb2.Tag(skip=count)
