# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The `oymo` command: `emit-llvm`, `check`, `fmt`, `normal`, `run`."""

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

from oymo.core import syntax
from oymo.oymomo import grammar, llvm_opcodes, llvm_translate, printer, reduction, strategy
from oymo.oymomo import module as modules

LANGUAGE_HEADER = 'language oymomo\n'

# The host is assumed to be x86-64 Linux until the `target` leaf reads the host's triple.
TARGET = llvm_translate.Target(triple='x86_64-unknown-linux-gnu', data_layout='', opcodes=llvm_opcodes.DEFAULT_OPCODES)


class CliError(Exception):
    """An error to print as `file:line:column: error: message`. `offset` indexes the whole file."""

    def __init__(self, message: str, offset: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.offset = offset


def _parse(source: str) -> syntax.Term:
    """Checks and strips the `language oymomo` header, then parses."""
    if not source.startswith(LANGUAGE_HEADER):
        raise CliError(f'Expected the first line to be {LANGUAGE_HEADER.strip()!r}.', 0)
    term = grammar.parse(source.removeprefix(LANGUAGE_HEADER))
    errors = syntax.gather_errors(term)
    if errors:
        raise _located(errors[0].message, errors[0].location)
    return term


def _located(message: str, location: syntax.Location | None) -> CliError:
    """Locations index the source after the header; CLI errors index the whole file."""
    start = location.start if location is not None else None
    return CliError(message, None if start is None else start + len(LANGUAGE_HEADER))


def _module(source: str) -> modules.Module:
    """The program's module: resolved, normalized (semantics.tex, Section 6), not stuck, read
    as Section 8 says."""
    try:
        return modules.module_of(_parse(source))
    except (reduction.ReductionError, modules.ModuleError) as error:
        raise _located(error.message, error.location) from error


def _check(source: str) -> None:
    _emit_llvm(source)


def _emit_llvm(source: str) -> str:
    module = _module(source)
    try:
        return str(llvm_translate.translate(module, TARGET))
    except llvm_translate.LlvmTranslationError as error:
        raise _located(error.message, error.location) from error


def _normal(source: str) -> str:
    """The program's normal form, pretty-printed: a program that gives the same module."""
    try:
        normal = strategy.normalize(reduction.resolve(_parse(source)))
    except reduction.ReductionError as error:
        raise _located(error.message, error.location) from error
    return LANGUAGE_HEADER + printer.show(normal, pretty=True, name_indices=True) + '\n'


def _fmt(source: str) -> str:
    return LANGUAGE_HEADER + printer.show(_parse(source), pretty=True, name_indices=True) + '\n'


def _run(source: str) -> int:
    """Builds the program with `clang`, runs it, prints `main`'s result; returns the exit status."""
    clang = shutil.which('clang')
    if clang is None:
        raise CliError('oymo run needs clang, which is not on PATH; install clang.')
    ir_text = _emit_llvm(source)
    with tempfile.TemporaryDirectory(prefix='oymo-') as directory:
        ll_path = pathlib.Path(directory, 'program.ll')
        exe_path = pathlib.Path(directory, 'program')
        ll_path.write_text(ir_text)
        build = subprocess.run(
            [clang, '-Wno-override-module', '-x', 'ir', str(ll_path), '-o', str(exe_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if build.returncode != 0:
            raise CliError(f'clang failed:\n{build.stderr.rstrip()}')
        sys.stdout.flush()
        result = subprocess.run([str(exe_path)], check=False)
    if result.returncode < 0:
        print(f'oymo: the program was killed by signal {-result.returncode}.', file=sys.stderr)
        return 1
    # `main`'s result comes back as the exit status, so only its low 8 bits survive.
    print(result.returncode)
    return 0


def _line_column(text: str, offset: int) -> tuple[int, int]:
    line_start = text.rfind('\n', 0, offset) + 1
    return text.count('\n', 0, offset) + 1, offset - line_start + 1


def _report(path: str, source: str | None, error: CliError) -> None:
    if error.offset is None or source is None:
        print(f'{path}: error: {error.message}', file=sys.stderr)
        return
    line, column = _line_column(source, min(error.offset, len(source)))
    print(f'{path}:{line}:{column}: error: {error.message}', file=sys.stderr)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='oymo', description='The oymo compiler.')
    commands = parser.add_subparsers(dest='command', required=True)
    emit = commands.add_parser('emit-llvm', help='write the LLVM IR of a program')
    emit.add_argument('file')
    emit.add_argument('-o', dest='output', help='output .ll file (default: stdout)')
    check = commands.add_parser('check', help='parse, reduce and verify a program; print its errors')
    check.add_argument('file')
    fmt = commands.add_parser('fmt', help='print a program pretty-printed')
    fmt.add_argument('file')
    normal = commands.add_parser('normal', help='print the normal form of a program, pretty-printed')
    normal.add_argument('file')
    run = commands.add_parser('run', help="build a program with clang, run it, print main's result")
    run.add_argument('file')
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    source = None
    try:
        try:
            source = pathlib.Path(args.file).read_text(encoding='utf-8')
        except OSError as error:
            raise CliError(f'Cannot read the file: {error.strerror}.') from error
        if args.command == 'emit-llvm':
            ir_text = _emit_llvm(source)
            if args.output is None:
                sys.stdout.write(ir_text)
            else:
                pathlib.Path(args.output).write_text(ir_text, encoding='utf-8')
        elif args.command == 'check':
            _check(source)
        elif args.command == 'fmt':
            sys.stdout.write(_fmt(source))
        elif args.command == 'normal':
            sys.stdout.write(_normal(source))
        else:
            return _run(source)
    except CliError as error:
        _report(args.file, source, error)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
