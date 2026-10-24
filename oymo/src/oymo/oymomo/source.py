# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""An oymomo source file: the code, then an optional `info` section with the code's spans.

    language oymomo
    <the code: one term>
    ---
    info 1
    code <MD5 of everything before the `---` line>
    start length file language hash lines
    <one row per source file the spans point into>
    spans
    <one entry per node of the code's kernel term, in pre-order>

The `info` section is not a term and is never reduced: the file's term is the code alone.
Spans are not for humans; they pass a frontend's source positions on to the backend.

- Every number is hex without `0x`. A row is `start length 'file' language hash {lines}`:
  its range of positions in this file's numbering, the path as given on the command line,
  the language of that file, the file's MD5, and the start of each of its lines.
- The column names line names the columns; a reader finds them by name and skips the
  ones it doesn't know.
- An entry of `spans` is a span (`start << 16 | length`, `start` in a row of this file),
  `0` (no span), `.` (the parent's span) or `.N` (N dots, N in hex). Nodes are visited
  as `nodes` does: a node, then its children; a struct's `Field` before its value.
- A file read in a run gets a row in the run's `SpanTable`; a term with no entry in the
  list gets its own position in that row. The rows of the `info` section are added to the
  table and the spans moved to them, so spans from many files never clash.
- `write` never writes a span into a `language oymomo` file: oymomo code is generated, so
  only spans into a frontend's sources (Alcor, Mizar, ...) are kept; it writes `.` for
  them. With no span left to write, there is no `info` section.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from oymo.core import spans, syntax
from oymo.oymomo import grammar, printer, terms

LANGUAGE = 'oymomo'
LANGUAGE_HEADER = f'language {LANGUAGE}\n'
SEPARATOR = '---'
INFO_VERSION = 1
COLUMNS = ('start', 'length', 'file', 'language', 'hash', 'lines')

# A row's cells: a quoted file name, a `{...}` list of line starts, or a word.
_CELL = re.compile(r"'[^'\n]*'|\{[^}\n]*\}|\S+")
_SEPARATOR_LINE = re.compile(rf'^{re.escape(SEPARATOR)}$', re.MULTILINE)
_LINE_WIDTH = 80

type Node = syntax.Term | terms.Field


class SourceError(Exception):
    def __init__(self, message: str, span: int) -> None:
        super().__init__(message)
        self.message = message
        self.span = span


@dataclass
class Loaded:
    """A file's term, and warnings as `(message, span)`."""

    term: syntax.Term
    warnings: list[tuple[str, int]] = field(default_factory=list)


def nodes(term: syntax.Term) -> Iterator[Node]:
    """Every node of `term` in pre-order: a node, then its children; a struct's fields, each
    before its value. A node shared by two parents is visited twice."""
    stack: list[Node] = [term]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(_children(node)))


def _children(node: Node) -> list[Node]:
    if isinstance(node, terms.Field):
        return [node.value]
    if isinstance(node, terms.Struct):
        return list(node.fields)
    return list(node.children())


class _Bytes:
    """UTF-8 byte offsets of the character offsets of a text."""

    def __init__(self, text: str) -> None:
        self._prefix = None
        if len(text.encode('utf-8')) != len(text):
            prefix = [0]
            for char in text:
                prefix.append(prefix[-1] + len(char.encode('utf-8')))
            self._prefix = prefix

    def __call__(self, offset: int) -> int:
        return offset if self._prefix is None else self._prefix[offset]


def read(text: str, file: str, table: spans.SpanTable) -> Loaded:
    """The term of the source file `text`, read from `file`, with its spans in `table`.
    A syntax error is an `ErrorTerm`; a bad header or `info` section raises `SourceError`."""
    row = table.add_file(file, LANGUAGE, text.encode('utf-8'))
    to_bytes = _Bytes(text)

    def here(offset: int) -> int:
        return spans.make(row.start + to_bytes(offset), 0)

    if not text.startswith(LANGUAGE_HEADER):
        raise SourceError(f'Expected the first line to be {LANGUAGE_HEADER.strip()!r}.', here(0))
    separator = _SEPARATOR_LINE.search(text, len(LANGUAGE_HEADER))
    code_end = len(text) if separator is None else separator.start()
    term = grammar.parse(text[len(LANGUAGE_HEADER) : code_end])
    _move_to_row(term, len(LANGUAGE_HEADER), row, to_bytes)
    loaded = Loaded(term)
    if separator is None or isinstance(term, syntax.ErrorTerm):
        return loaded
    info = text[separator.end() :].removeprefix('\n')
    entries = _read_info(info, text[:code_end].encode('utf-8'), table, here(separator.start()), loaded)
    if entries is not None:
        _assign(term, entries, here(separator.start()))
    return loaded


def _move_to_row(term: syntax.Term, offset: int, row: spans.Row, to_bytes: _Bytes) -> None:
    """Turns the spans `grammar.parse` gives, characters from `offset` in the file, into
    spans of `row`."""
    seen = set()
    for node in nodes(term):
        if id(node) in seen:
            continue
        seen.add(id(node))
        start = spans.start(node.span) + offset
        length = spans.length(node.span)
        if length < spans.MAX_LENGTH:
            length = to_bytes(start + length) - to_bytes(start)
        node.span = spans.make(row.start + to_bytes(start), length)


def _read_info(info: str, code: bytes, table: spans.SpanTable, here: int, loaded: Loaded) -> list[int | None] | None:
    """The `spans` entries, moved into `table` (None for `.`); None if the code changed."""
    # A missing header line reads as empty, so it fails its own check below.
    header, code_line, columns_line, *rest = [*info.split('\n'), '', '']
    if header.split() != ['info', format(INFO_VERSION, 'x')]:
        raise SourceError(f"The info section must start with 'info {INFO_VERSION:x}'.", here)
    match code_line.split():
        case ['code', md5]:
            pass
        case _:
            raise SourceError("The info section needs a line 'code <MD5>' after its header.", here)
    if md5 != spans.md5(code):
        loaded.warnings.append(('The code changed since its spans were written; the spans are dropped.', here))
        return None
    columns = columns_line.split()
    if missing := [c for c in COLUMNS if c not in columns]:
        raise SourceError(f'The info section has no column {missing[0]!r}.', here)
    try:
        end = rest.index('spans')
    except ValueError:
        raise SourceError("The info section needs a line 'spans' after its rows.", here) from None
    moved = [_read_row(line, columns, table, here) for line in rest[:end] if line.strip()]
    entries: list[int | None] = []
    for token in ' '.join(rest[end + 1 :]).split():
        if token.startswith('.'):
            entries.extend([None] * (_hex(token[1:], here) if len(token) > 1 else 1))
        elif (span := _hex(token, here)) == spans.NO_SPAN:
            entries.append(spans.NO_SPAN)
        else:
            entries.append(_move(span, moved, here))
    return entries


def _read_row(line: str, columns: list[str], table: spans.SpanTable, here: int) -> tuple[int, int, spans.Row]:
    """`(start, length, row)`: a row's range in the file, and the row it now has in `table`."""
    cells = _CELL.findall(line)
    if len(cells) != len(columns):
        raise SourceError(f'A row of the info section has {len(cells)} cells, not {len(columns)}.', here)
    row = dict(zip(columns, cells, strict=True))
    if not (row['file'].startswith("'") and row['file'].endswith("'") and len(row['file']) > 1):
        raise SourceError(f"A file name is written in quotes, 'name', not {row['file']}.", here)
    if not (row['lines'].startswith('{') and row['lines'].endswith('}')):
        raise SourceError(f'Line starts are written {{0, ...}}, not {row["lines"]}.', here)
    line_starts = tuple(_hex(n.strip(), here) for n in row['lines'][1:-1].split(','))
    start, length = _hex(row['start'], here), _hex(row['length'], here)
    added = table.add_row(length, row['file'][1:-1], row['language'], row['hash'], line_starts)
    return start, length, added


def _hex(token: str, here: int) -> int:
    try:
        return int(token, 16)
    except ValueError:
        raise SourceError(f'{token!r} is not a hex number.', here) from None


def _move(span: int, moved: list[tuple[int, int, spans.Row]], here: int) -> int:
    position = spans.start(span)
    for start, length, row in moved:
        if start <= position <= start + length:
            return spans.make(row.start + position - start, spans.length(span))
    raise SourceError(f'The span {span:x} is in no row of the info section.', here)


def _assign(term: syntax.Term, entries: list[int | None], here: int) -> None:
    """Gives each node its entry; `.` (None) gives the parent's span."""
    stack: list[tuple[Node, int]] = [(term, spans.NO_SPAN)]
    count = 0
    while stack:
        node, parent = stack.pop()
        if count == len(entries):
            raise SourceError(f'The spans list has {len(entries)} entries; the code has more nodes.', here)
        entry = entries[count]
        count += 1
        node.span = parent if entry is None else entry
        stack.extend((child, node.span) for child in reversed(_children(node)))
    if count != len(entries):
        raise SourceError(f'The spans list has {len(entries)} entries; the code has {count} nodes.', here)


def write(term: syntax.Term, table: spans.SpanTable) -> str:
    """The source file of `term`: the code pretty-printed, then the `info` section if a span
    into a frontend's source is left to write."""
    code = LANGUAGE_HEADER + printer.show(term, pretty=True, name_indices=True) + '\n'
    entries = _entries(term, table)
    rows = [row for row in table.rows if any(e and table.row_of(e) is row for e in entries)]
    if not rows:
        return code
    starts, start = {}, 1
    for row in rows:
        starts[row.start] = start
        start += row.length + 1
    lines = [SEPARATOR, f'info {INFO_VERSION:x}', f'code {spans.md5(code.encode("utf-8"))}', ' '.join(COLUMNS)]
    for row in rows:
        if "'" in row.file:
            raise SourceError(f"A file name in the info section can't hold a quote: {row.file}.", spans.NO_SPAN)
        line_starts = ', '.join(format(n, 'x') for n in row.lines)
        lines.append(f"{starts[row.start]:x} {row.length:x} '{row.file}' {row.language} {row.hash} {{{line_starts}}}")
    lines.append('spans')
    lines.extend(_wrap(_tokens(entries, table, starts)))
    return code + '\n'.join(lines) + '\n'


def _entries(term: syntax.Term, table: spans.SpanTable) -> list[int | None]:
    """One entry per node: its span, `NO_SPAN`, or None for `.` (the parent's span). A span
    into a `language oymomo` file, or into no row, is never written: it becomes `.`."""
    entries: list[int | None] = []
    stack: list[tuple[Node, int]] = [(term, spans.NO_SPAN)]
    while stack:
        node, parent = stack.pop()
        span = node.span
        row = table.row_of(span)
        if span != spans.NO_SPAN and (row is None or row.language == LANGUAGE):
            entries.append(None)
            span = parent
        elif span == parent:
            entries.append(None)
        else:
            entries.append(span)
        stack.extend((child, span) for child in reversed(_children(node)))
    return entries


def _tokens(entries: list[int | None], table: spans.SpanTable, starts: dict[int, int]) -> list[str]:
    """The entries as text: a run of dots as one `.` or `.N`."""
    tokens: list[str] = []
    dots = 0
    for entry in entries:
        if entry is None:
            dots += 1
            continue
        if dots:
            tokens.append('.' if dots == 1 else f'.{dots:x}')
            dots = 0
        tokens.append(_written(entry, table, starts))
    if dots:
        tokens.append('.' if dots == 1 else f'.{dots:x}')
    return tokens


def _written(span: int, table: spans.SpanTable, starts: dict[int, int]) -> str:
    row = table.row_of(span)
    if row is None:
        return '0'
    return format(spans.make(starts[row.start] + spans.start(span) - row.start, spans.length(span)), 'x')


def _wrap(tokens: list[str]) -> list[str]:
    lines, line = [], ''
    for token in tokens:
        if line and len(line) + 1 + len(token) > _LINE_WIDTH:
            lines.append(line)
            line = token
        else:
            line = f'{line} {token}' if line else token
    if line:
        lines.append(line)
    return lines
