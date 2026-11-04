# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The driver's side of a build: a session that gives the driver opcodes their results.

    with driver.session(top, config, mounts) as build:
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

A mount shows a host folder at a path of the virtual directory: with the mount
`vendor/math` of `../math/oymo-out`, `'driver.read_low' 'vendor/math/unit.h.oymo'` reads
`../math/oymo-out/unit.h.oymo`. This is how a unit reads a header that lives outside the
project; reading it is a plain file read. A mount's path is a path of the virtual directory
that names no file or folder of the top, and overlaps no other mount (`check_mounts`); a
path under it may not leave the mounted folder through a link. The destination folder,
where outputs are written, is never read.

A read file keeps its own tags, which point into it, so errors inside it name it; its meta
section is read as usual. A name it doesn't bind is an error in that file, at its place.

An opcode gives no result where it fails, so the call stays; the error is recorded in the
session, at the place of the call's operand (the path), naming the path. `check` raises the
first one: after reduction, it explains a leftover call better than the ingot's error does.
An oymo file read with `'driver.read_low'` or `'driver.read_high'` that isn't there gives
"could not find oymo file 'path'".
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


class MountError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Session:
    """One build: the virtual directory's top, its mounts, the config, what was read, and
    the errors and warnings recorded so far."""

    def __init__(self, top: str, config: Mapping[str, str], mounts: Mapping[str, str] | None = None) -> None:
        self.top = top
        # Each mount's path in the virtual directory, and the host folder it shows.
        self.mounts = dict(mounts or {})
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

    def _read(self, path: str, tag: Tag, *, oymo: bool = False) -> bytes | None:
        """The bytes of the file at `path`, read once; None if it can't be read. `oymo` says
        the file is read as an oymo file, for the error if it is missing."""
        if path not in self._bytes:
            self._bytes[path] = self._read_file(path, tag, oymo=oymo)
        return self._bytes[path]

    def _read_file(self, path: str, tag: Tag, *, oymo: bool) -> bytes | None:
        if (problem := path_error(path)) is not None:
            return self._error(problem, tag)
        full = self.host_path(path)
        mount = self._mount(path)
        folder = self.top if mount is None else self.mounts[mount]
        if not pathlib.Path(os.path.realpath(full)).is_relative_to(os.path.realpath(folder or os.curdir)):
            where = 'the top of the virtual directory' if mount is None else f'the folder mounted at {mount!r}'
            return self._error(f'{path!r} leaves {where}.', tag)
        try:
            data = pathlib.Path(full).read_bytes()
        except FileNotFoundError as error:
            if oymo:
                return self._error(not_found(path), tag)
            return self._error(f'Cannot read {path!r}: {error.strerror}.', tag)
        except OSError as error:
            return self._error(f'Cannot read {path!r}: {error.strerror}.', tag)
        self.paths.append(path)
        return data

    def _mount(self, path: str) -> str | None:
        """The path of the mount that `path` is under, or None if it is under none."""
        parts = path.split('/')
        for mount in self.mounts:
            if parts[: mount.count('/') + 1] == mount.split('/'):
                return mount
        return None

    def host_path(self, path: str) -> str:
        """Where the file at `path` is on the host, as errors in it name it: in the mounted
        folder for a path under a mount, else in the top."""
        parts = path.split('/')
        if (mount := self._mount(path)) is not None:
            return os.path.join(self.mounts[mount], *parts[mount.count('/') + 1 :])
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
        data = self._read(path, tag, oymo=True)
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


def not_found(path: str) -> str:
    """The error for an oymo file missing at `path`, a path of the virtual directory."""
    return f"could not find oymo file '{path}'"


def check_mounts(top: str, mounts: Mapping[str, str]) -> None:
    """Raises `MountError` if a mount of `mounts` (path in the virtual directory: host
    folder) can't be shown in the virtual directory whose top is the host directory `top`:
    its path is not a path of the virtual directory, names a file or folder of the top (or
    goes through a file of it), or overlaps another mount's path; or its folder is not one."""
    for mount, folder in mounts.items():
        if mount.startswith('/'):
            raise MountError(
                f'The mount path {mount!r} is absolute; it is relative to the top of the virtual directory.'
            )
        if path_error(mount) is not None:
            raise MountError(
                f"The mount path {mount!r} is not a path of the virtual directory: its parts are separated by '/', "
                "and none is empty, '.' or '..'."
            )
        parts = mount.split('/')
        for end in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:end])
            host = os.path.join(top, *parts[:end])
            if os.path.lexists(host) and (end == len(parts) or not os.path.isdir(host)):
                raise MountError(f'The mount path {mount!r} clashes with the file or folder {prefix!r} of the top.')
        if not os.path.isdir(folder):
            raise MountError(f'The mount {mount!r} shows {folder!r}, which is not a folder.')
    paths = sorted(mounts)
    for index, mount in enumerate(paths):
        for other in paths[index + 1 :]:
            if other.startswith(mount + '/'):
                raise MountError(f'The mount paths {mount!r} and {other!r} overlap.')


@contextlib.contextmanager
def session(
    top: str, config: Mapping[str, str] | None = None, mounts: Mapping[str, str] | None = None
) -> Iterator[Session]:
    """A build whose virtual directory's top is the host directory `top` ('' for the current
    one), with the config `config`, and the mounts `mounts` (path in the virtual directory:
    host folder; checked with `check_mounts`, which raises `MountError`). The driver opcodes
    give results only inside it."""
    check_mounts(top, mounts or {})
    build = Session(top, config or {}, mounts)
    token = opcodes.DRIVER.set(build.apply)
    try:
        yield build
    finally:
        opcodes.DRIVER.reset(token)
