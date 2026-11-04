# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The `oymo` command: `emit-llvm`, `emit-header`, `check`, `fmt`, `normal`, `run`.

A program has one layer or two (a layering `low : high` somewhere in it). With two, each
layer is built on its own: `emit-llvm` writes them with `--low` and `--high`, `normal`
prints the normal form as `low : high` (`--merge` merges the two), and `run` runs the high layer (the guard) first and the low
layer only if the guard exits with status 0.

`emit-header` writes the program's header (`header.header_of_layers`), one file for one
layer or two (`low : high`; `--merge` merges the two). Outputs mirror sources: the header of
`calc/root.oymo` is `<out>/calc/root.h.oymo`, the root's path in the workspace with `.oymo`
changed to `.h.oymo`, so headers of many units meet in one folder without clashing; another
unit reads it as `'driver.read_low' 'out/calc/root.h.oymo'`.

Every command runs inside a driver session (`driver.session`) whose virtual directory's
top is the workspace, the current directory, as Blaze's workspace root: every read path is
from there, and the root file must be inside it. So a program may read files (`fmt` reduces
nothing, so it reads none); `--config key=value` fills `'driver.config' {}`. The destination
folder is `oymo-out/` in the current directory (one for every unit built from there, as
Blaze's `bazel-out/`), or `--out DIR`; the virtual directory shows it under `out/`.
"""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

from oymo.core import syntax
from oymo.oymomo import ingot as ingots
from oymo.oymomo import driver, header, layers, llvm_opcodes, llvm_translate, reduction, source, strategy
from oymo.oymomo.meta import NO_TAG, Tag

# The host is assumed to be x86-64 Linux until the `target` leaf reads the host's triple.
TARGET = llvm_translate.Target(triple='x86_64-unknown-linux-gnu', data_layout='', opcodes=llvm_opcodes.DEFAULT_OPCODES)


class CliError(Exception):
    """An error to print as `file:line:column: error: message`, from its tag's place."""

    def __init__(self, message: str, tag: Tag = NO_TAG) -> None:
        super().__init__(message)
        self.message = message
        self.tag = tag


class _Program:
    """The file named on the command line, and the build it is the root of. `workspace_path`
    is the file's path from the workspace, its parts separated by `/`."""

    def __init__(self, path: str, text: str, build: driver.Session, workspace_path: str) -> None:
        self.path = path
        self.text = text
        self.build = build
        self.workspace_path = workspace_path
        self._term: syntax.Term | None = None

    def term(self) -> syntax.Term:
        """The file's term: its header checked, its code parsed, its tags read. Read once."""
        if self._term is None:
            self._term = self._read()
        return self._term

    def layers(self) -> list[syntax.Term]:
        """The file's layers: `[low, high]`, or `[term]` for a program with no layering."""
        term = self.term()
        separated = layers.separate(term)
        return [term] if separated is None else list(separated)

    def _read(self) -> syntax.Term:
        try:
            loaded = source.read(self.text, self.path)
        except source.SourceError as error:
            raise CliError(error.message, error.tag) from error
        for message, tag in loaded.warnings:
            _print(self.path, 'warning', message, tag)
        if errors := syntax.gather_errors(loaded.term):
            raise CliError(errors[0].message, errors[0].tag)
        return loaded.term


def _check_reads(program: _Program) -> None:
    """Prints the warnings of the files read, and raises the first error of the driver
    opcodes: a read that failed explains a leftover call better than the ingot's error."""
    for message, tag in program.build.take_warnings():
        _print(program.path, 'warning', message, tag)
    try:
        program.build.check()
    except driver.DriverError as error:
        raise CliError(error.message, error.tag) from error


def _ingot(program: _Program, layer: syntax.Term) -> ingots.Ingot:
    """A layer's ingot: resolved, normalized, not stuck, read
    as an ingot."""
    try:
        ingot = ingots.ingot_of(layer)
    except (reduction.ReductionError, ingots.IngotError) as error:
        _check_reads(program)
        raise CliError(error.message, error.tag) from error
    _check_reads(program)
    return ingot


def _check(program: _Program) -> None:
    _emit_llvm(program)


def _compile(program: _Program) -> list[tuple[ingots.Ingot, str]]:
    """Each layer's ingot and LLVM IR: low, then high."""
    compiled = []
    for layer in program.layers():
        ingot = _ingot(program, layer)
        try:
            compiled.append((ingot, str(llvm_translate.translate(ingot, TARGET))))
        except llvm_translate.LlvmTranslationError as error:
            raise CliError(error.message, error.tag) from error
    return compiled


def _emit_llvm(program: _Program) -> list[str]:
    """Each layer's LLVM IR: low, then high."""
    return [ir_text for _, ir_text in _compile(program)]


def _normal(program: _Program, *, merge: bool = False) -> str:
    """The program's normal form, pretty-printed: a program that gives the same ingots. With
    two layers, each is normalized on its own and printed as `low : high`; with `merge`, the
    two are merged, a layering left only where they differ."""
    try:
        normals = [strategy.normalize(reduction.resolve(layer)) for layer in program.layers()]
    except reduction.ReductionError as error:
        _check_reads(program)
        raise CliError(error.message, error.tag) from error
    _check_reads(program)
    if len(normals) == 1:
        return source.write(normals[0])
    if merge:
        return source.write(layers.merge(*normals))
    return source.write(syntax.Layers(layers=(normals[0], normals[1])))


def _fmt(program: _Program, *, merge: bool = False) -> str:
    """The program as written, pretty-printed. With `merge`, a program with two layers is
    written with its layerings only where its layers differ."""
    term = program.term()
    if merge and (separated := layers.separate(term)) is not None:
        term = layers.merge(*separated)
    return source.write(term)


def _emit_llvm_to(program: _Program, output: str | None, low: str | None, high: str | None) -> None:
    """Writes the LLVM IR: one layer to `output` (stdout if None), two layers to `low` and
    `high`, each a path or `-` for stdout."""
    two = len(program.layers()) == 2
    if not two and (low is not None or high is not None):
        raise CliError('--low and --high are for a program with two layers; this one has one: use -o.')
    if two and output is not None:
        raise CliError('The program has two layers: write them with --low and --high, not -o.')
    if two and (low is None or high is None):
        raise CliError('The program has two layers: give both --low and --high, each a path or - for stdout.')
    if two and low == '-' and high == '-':
        raise CliError('At most one of --low and --high may be - (stdout).')
    destinations = [low, high] if two else [output or '-']
    for destination, ir_text in zip(destinations, _emit_llvm(program), strict=True):
        if destination == '-':
            sys.stdout.write(ir_text)
        else:
            pathlib.Path(str(destination)).write_text(ir_text, encoding='utf-8')


def _header(program: _Program, *, merged: bool = False) -> str:
    """The program's header as a source file: one file for one layer or two."""
    ingots = [_ingot(program, layer) for layer in program.layers()]
    return source.write(header.header_of_layers(ingots, merged=merged))


def _emit_header_to(program: _Program, output: str | None, *, merged: bool = False) -> None:
    """Writes the header to `output` (`-` for stdout), by default `<out>/<root>.h.oymo` in
    the destination folder, `<root>` the root's path in the workspace without `.oymo`; the
    folders on the way are made if missing."""
    text = _header(program, merged=merged)
    if output == '-':
        sys.stdout.write(text)
        return
    if output is None:
        output = os.path.join(program.build.out, *_header_path(program.workspace_path).split('/'))
        folder = os.path.dirname(output)
        try:
            pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise CliError(f'Cannot make the folder {folder!r} for the header: {error.strerror}.') from error
    try:
        pathlib.Path(output).write_text(text, encoding='utf-8')
    except OSError as error:
        raise CliError(f'Cannot write the header to {output!r}: {error.strerror}.') from error


def _header_path(workspace_path: str) -> str:
    """The header's path in the destination folder, mirroring the root's path in the
    workspace: `calc/root.oymo` gives `calc/root.h.oymo`."""
    return workspace_path.removesuffix('.oymo') + '.h.oymo'


def _workspace_path(path: str, workspace: str) -> str:
    """The path of the root file `path` from `workspace`, its parts separated by `/`. Folders
    are compared with their links resolved; the file's own name is kept as written."""
    full = os.path.join(os.path.realpath(os.path.dirname(os.path.abspath(path))), os.path.basename(path))
    relative = os.path.relpath(full, os.path.realpath(workspace))
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        raise CliError(f'The root file must be inside the workspace, the current directory: {workspace}.')
    return relative.replace(os.sep, '/')


def _has_main(ingot: ingots.Ingot) -> bool:
    return any(isinstance(symbol, ingots.Definition) and symbol.link == 'main' for symbol in ingot.symbols)


def _build(clang: str, directory: str, name: str, ir_text: str) -> pathlib.Path:
    """The executable of `ir_text`, built with `clang` in `directory`."""
    ll_path = pathlib.Path(directory, f'{name}.ll')
    exe_path = pathlib.Path(directory, name)
    ll_path.write_text(ir_text)
    build = subprocess.run(
        [clang, '-Wno-override-module', '-x', 'ir', str(ll_path), '-o', str(exe_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if build.returncode != 0:
        raise CliError(f'clang failed:\n{build.stderr.rstrip()}')
    return exe_path


def _run(program: _Program) -> int:
    """Builds the program with `clang`, runs it, prints `main`'s result; returns the exit status.
    With two layers, both are built, and the high layer (the guard) runs first: the low layer
    runs only if the guard exits with status 0."""
    clang = shutil.which('clang')
    if clang is None:
        raise CliError('oymo run needs clang, which is not on PATH; install clang.')
    compiled = _compile(program)
    if len(compiled) == 2:
        for (ingot, _), name in zip(compiled, ('low layer', 'high layer (the guard)'), strict=True):
            if not _has_main(ingot):
                raise CliError(f"The {name} has no function linked as 'main'; both layers need one to run.")
    with tempfile.TemporaryDirectory(prefix='oymo-') as directory:
        names = ('program', 'guard')[: len(compiled)]
        executables = [
            _build(clang, directory, name, ir_text) for (_, ir_text), name in zip(compiled, names, strict=True)
        ]
        sys.stdout.flush()
        if len(executables) == 2:
            guard = subprocess.run([str(executables[1])], check=False)
            sys.stdout.flush()
            if guard.returncode < 0:
                raise CliError(f'The guard was killed by signal {-guard.returncode}.')
            if guard.returncode != 0:
                raise CliError(f'The guard failed with status {guard.returncode}.')
        result = subprocess.run([str(executables[0])], check=False)
    if result.returncode < 0:
        print(f'oymo: the program was killed by signal {-result.returncode}.', file=sys.stderr)
        return 1
    # `main`'s result comes back as the exit status, so only its low 8 bits survive.
    print(result.returncode)
    return 0


def _print(path: str, kind: str, message: str, tag: Tag) -> None:
    """`file:line:column: kind: message`, the column in bytes; `path: kind: message` with no place."""
    if tag.file is None:
        print(f'{path}: {kind}: {message}', file=sys.stderr)
        return
    line, column = tag.file.position(tag.start)
    print(f'{tag.file.path}:{line}:{column}: {kind}: {message}', file=sys.stderr)


def _config(pairs: list[str]) -> dict[str, str]:
    """The build's config from `--config key=value` flags."""
    config: dict[str, str] = {}
    for pair in pairs:
        key, equals, value = pair.partition('=')
        if not key or not equals:
            raise CliError(f'--config takes key=value, with a nonempty key; got {pair!r}.')
        if key in config:
            raise CliError(f'--config gives {key!r} twice.')
        config[key] = value
    return config


def _add_config(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        '--config',
        action='append',
        default=[],
        metavar='KEY=VALUE',
        help="a config entry for 'driver.config' {}; may be repeated",
    )
    command.add_argument(
        '--out',
        metavar='DIR',
        help=f'the destination folder, shown as {driver.OUT}/ in the virtual directory '
        f'(default: {driver.DEFAULT_OUT}/ in the current directory)',
    )


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='oymo', description='The oymo compiler.')
    commands = parser.add_subparsers(dest='command', required=True)
    emit = commands.add_parser('emit-llvm', help='write the LLVM IR of a program')
    emit.add_argument('file')
    emit.add_argument('-o', dest='output', help='output .ll file (default: stdout); for a program with one layer')
    emit.add_argument('--low', help="the low layer's .ll file, or - for stdout; for a program with two layers")
    emit.add_argument('--high', help="the high layer's .ll file, or - for stdout; for a program with two layers")
    _add_config(emit)
    emit_header = commands.add_parser(
        'emit-header', help="write a program's header: its linked symbols, declared, for other units to read"
    )
    emit_header.add_argument('file')
    emit_header.add_argument(
        '-o',
        dest='output',
        help='output file, or - for stdout (default: <out>/<root path>.h.oymo, mirroring the root in the workspace)',
    )
    emit_header.add_argument(
        '--merge',
        action='store_true',
        help='with two layers, merge their headers: a layering only where they differ',
    )
    _add_config(emit_header)
    check = commands.add_parser('check', help='parse, reduce and verify a program; print its errors')
    check.add_argument('file')
    _add_config(check)
    fmt = commands.add_parser('fmt', help='print a program pretty-printed')
    fmt.add_argument('file')
    fmt.add_argument(
        '--merge', action='store_true', help='write a program with two layers with layerings only where they differ'
    )
    normal = commands.add_parser('normal', help='print the normal form of a program, pretty-printed')
    normal.add_argument('file')
    normal.add_argument(
        '--merge', action='store_true', help='with two layers, merge them: a layering only where they differ'
    )
    _add_config(normal)
    run = commands.add_parser(
        'run', help="build a program with clang, run it, print main's result; with two layers, the high one guards"
    )
    run.add_argument('file')
    _add_config(run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    try:
        workspace = os.getcwd()
        workspace_path = _workspace_path(args.file, workspace)
        try:
            text = pathlib.Path(args.file).read_text(encoding='utf-8')
        except OSError as error:
            raise CliError(f'Cannot read the file: {error.strerror}.') from error
        config = _config(getattr(args, 'config', []))
        with driver.session(workspace, config, getattr(args, 'out', None)) as build:
            program = _Program(args.file, text, build, workspace_path)
            if args.command == 'emit-llvm':
                _emit_llvm_to(program, args.output, args.low, args.high)
            elif args.command == 'emit-header':
                _emit_header_to(program, args.output, merged=args.merge)
            elif args.command == 'check':
                _check(program)
            elif args.command == 'fmt':
                sys.stdout.write(_fmt(program, merge=args.merge))
            elif args.command == 'normal':
                sys.stdout.write(_normal(program, merge=args.merge))
            else:
                return _run(program)
    except CliError as error:
        _print(args.file, 'error', error.message, error.tag)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
