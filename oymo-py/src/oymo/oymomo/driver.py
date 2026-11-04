# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The driver's side of a build: a session that gives the driver opcodes their results.

    with driver.session(top, config) as build:
        ...reduce...
        build.check()

Inside a session, the driver opcodes give:

- `'driver.read_low' path`: the low layer of the oymo file at `path` (the whole term for a
  file with one layer), its names resolved to de Bruijn indices;
- `'driver.read_high' path`: its high layer, or the whole term for a file with one layer;
- `'driver.read_bytes' path`: the file's bytes, as a byte array;
- `'driver.config' {}`: the build's config, a struct of text byte arrays `{key = 'value', …}`.

Outside a session they give no result, and the call stays as written.

Paths name files in the virtual directory, whose top is a directory of the host: for the
`oymo` command, the workspace, which is the current directory, as Blaze's workspace root.
So every read path is from the workspace, whichever file reads it: the root `calc/root.oymo`
reads its lexer as `'driver.read_low' 'calc/lexer.oymo'`. A path is relative to the top,
its parts separated by `/`; it is never absolute and has no `..`, `.` or empty part, and it
may not leave the top through a link. Each path is read once per session, so the same path
always gives the same term: the opcodes are deterministic.

The virtual directory also shows the destination folder, where generated files such as
headers are written, under the fixed prefix `out/`. Generated files mirror their sources:
the header of the unit whose root is `calc/root.oymo` is `calc/root.h.oymo` in the
destination folder, read as `out/calc/root.h.oymo`. The destination folder is by default
`oymo-out/` in the current directory, one for every unit built from there, as Blaze's
`bazel-out/`. A source file never sits under `out/`, so a path says by itself whether it
names a source or a generated file. A path under `out/` may not leave the destination
folder through a link.

A read file keeps its own tags, which point into it, so errors inside it name it; its meta
section is read as usual. A name it doesn't bind is an error in that file, at its place.

An opcode gives no result where it fails, so the call stays; the error is recorded in the
session, at the place of the call's operand (the path), naming the path. `check` raises the
first one: after reduction, it explains a leftover call better than the ingot's error does.
"""

import contextlib
import os
import pathlib
from collections.abc import Iterator, Mapping

from oymo.core import syntax
from oymo.oymomo import layers, opcodes, reduction, source, terms
from oymo.oymomo.meta import Tag


class DriverError(Exception):
    def __init__(self, message: str, tag: Tag) -> None:
        super().__init__(message)
        self.message = message
        self.tag = tag


# The prefix under which the virtual directory shows the destination folder.
OUT = 'out'
# The destination folder's name in the current directory, by default.
DEFAULT_OUT = 'oymo-out'


class Session:
    """One build: the virtual directory's top, the destination folder, the config, what was
    read, and the errors and warnings recorded so far."""

    def __init__(self, top: str, config: Mapping[str, str], out: str | None = None) -> None:
        self.top = top
        self.out = os.path.join(os.getcwd(), DEFAULT_OUT) if out is None else out
        self.config = dict(config)
        # In order, each once: the opcodes are retried at every step while they fail.
        self._errors: dict[tuple[str, Tag], None] = {}
        self._warnings: list[tuple[str, Tag]] = []
        # The paths read, in the order of first reading.
        self.paths: list[str] = []
        self._bytes: dict[str, bytes | None] = {}
        self._layers: dict[str, tuple[syntax.Term, syntax.Term] | None] = {}
        self._resolved: dict[tuple[str, int], syntax.Term | None] = {}

    @property
    def errors(self) -> list[tuple[str, Tag]]:
        """The errors recorded, as `(message, tag)`, in order."""
        return list(self._errors)

    def check(self) -> None:
        """Raises `DriverError` for the first error recorded, if any."""
        for message, tag in self._errors:
            raise DriverError(message, tag)

    def take_warnings(self) -> list[tuple[str, Tag]]:
        """The warnings recorded since the last call, as `(message, tag)`."""
        warnings, self._warnings = self._warnings, []
        return warnings

    def apply(self, name: str, operand: terms.Term) -> terms.Term | None:
        """The result of the driver opcode `name` on `operand`, or None."""
        if name == 'driver.config':
            if operand != terms.Struct([]):
                return self._error("'driver.config' takes {}.", operand.tag)
            return terms.Struct(
                [terms.Field(key, terms.ByteArray.from_str(value)) for key, value in self.config.items()]
            )
        path = operand.as_str if isinstance(operand, terms.ByteArray) else None
        if path is None:
            return self._error(f'{name!r} takes a path: a text byte array.', operand.tag)
        if name == 'driver.read_bytes':
            data = self._read(path, operand.tag)
            return None if data is None else terms.ByteArray(data)
        return self._layer(path, 0 if name == 'driver.read_low' else 1, operand.tag)

    def _error(self, message: str, tag: Tag) -> None:
        self._errors.setdefault((message, tag), None)

    def _read(self, path: str, tag: Tag) -> bytes | None:
        """The bytes of the file at `path`, read once; None if it can't be read."""
        if path not in self._bytes:
            self._bytes[path] = self._read_file(path, tag)
        return self._bytes[path]

    def _read_file(self, path: str, tag: Tag) -> bytes | None:
        if (problem := path_error(path)) is not None:
            return self._error(problem, tag)
        full = self.host_path(path)
        generated = _is_generated(path)
        folder = self.out if generated else self.top
        if not pathlib.Path(os.path.realpath(full)).is_relative_to(os.path.realpath(folder or os.curdir)):
            where = 'the destination folder' if generated else 'the top of the virtual directory'
            return self._error(f'{path!r} leaves {where}.', tag)
        try:
            data = pathlib.Path(full).read_bytes()
        except OSError as error:
            return self._error(f'Cannot read {path!r}: {error.strerror}.', tag)
        self.paths.append(path)
        return data

    def host_path(self, path: str) -> str:
        """Where the file at `path` is on the host, as errors in it name it: in the
        destination folder for a path under `out/`, else in the top."""
        parts = path.split('/')
        if _is_generated(path):
            return os.path.join(self.out, *parts[1:])
        return os.path.join(self.top, *parts)

    def _layer(self, path: str, which: int, tag: Tag) -> syntax.Term | None:
        """Layer `which` (0 low, 1 high) of the oymo file at `path`, resolved; None on an error.
        A file with one layer is resolved once, for both."""
        written = self._written_layers(path, tag)
        if written is None:
            return None
        key = (path, 0 if written[0] is written[1] else which)
        if key not in self._resolved:
            try:
                self._resolved[key] = reduction.resolve(written[which])
            except reduction.ReductionError as error:
                self._resolved[key] = self._error(error.message, error.tag)
        return self._resolved[key]

    def _written_layers(self, path: str, tag: Tag) -> tuple[syntax.Term, syntax.Term] | None:
        """The low and high layers of the oymo file at `path`, as written; the same term twice
        for a file with one layer. None if it can't be read."""
        if path not in self._layers:
            self._layers[path] = self._parse(path, tag)
        return self._layers[path]

    def _parse(self, path: str, tag: Tag) -> tuple[syntax.Term, syntax.Term] | None:
        data = self._read(path, tag)
        if data is None:
            return None
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            return self._error(f'Cannot read {path!r}: it is not UTF-8 text.', tag)
        try:
            loaded = source.read(text, self.host_path(path))
        except source.SourceError as error:
            return self._error(_located(path, error.message, error.tag), tag)
        if errors := syntax.gather_errors(loaded.term):
            return self._error(_located(path, errors[0].message, errors[0].tag), tag)
        self._warnings.extend(loaded.warnings)
        separated = layers.separate(loaded.term)
        return separated if separated is not None else (loaded.term, loaded.term)


def _located(path: str, message: str, tag: Tag) -> str:
    """`message`, an error at `tag` in the file at `path`, for the place of the read."""
    if tag.file is None:
        return f'Cannot read {path!r}: {message}'
    line, column = tag.file.position(tag.start)
    return f'Cannot read {path!r}: at {line}:{column}: {message}'


def path_error(path: str) -> str | None:
    """Why `path` is not a path of the virtual directory, or None if it is one."""
    if path.startswith('/'):
        return f'{path!r} is absolute; a read path is relative to the top of the virtual directory.'
    if '\0' in path or any(part in ('', '.', '..') for part in path.split('/')):
        return f"{path!r} is not a read path: its parts are separated by '/', and none is empty, '.' or '..'."
    return None


def _is_generated(path: str) -> bool:
    """Whether `path` names a file of the destination folder: it starts with `out/`."""
    return path.split('/')[0] == OUT


@contextlib.contextmanager
def session(top: str, config: Mapping[str, str] | None = None, out: str | None = None) -> Iterator[Session]:
    """A build whose virtual directory's top is the host directory `top` ('' for the current
    one), with the config `config`, and whose destination folder is the host directory
    `out` (by default `oymo-out` in the current directory). The driver opcodes give results only inside it."""
    build = Session(top, config or {}, out)
    token = opcodes.DRIVER.set(build.apply)
    try:
        yield build
    finally:
        opcodes.DRIVER.reset(token)
