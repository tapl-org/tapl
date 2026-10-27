# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The `oymo` command: `emit-llvm`, `check`, `fmt`, `normal`, `run`."""

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

from oymo.core import spans, syntax
from oymo.oymomo import ingot as ingots
from oymo.oymomo import llvm_opcodes, llvm_translate, reduction, source, strategy

# The host is assumed to be x86-64 Linux until the `target` leaf reads the host's triple.
TARGET = llvm_translate.Target(triple='x86_64-unknown-linux-gnu', data_layout='', opcodes=llvm_opcodes.DEFAULT_OPCODES)


class CliError(Exception):
    """An error to print as `file:line:column: error: message`, from its span (`oymo.core.spans`)."""

    def __init__(self, message: str, span: int = spans.NO_SPAN) -> None:
        super().__init__(message)
        self.message = message
        self.span = span


class _Program:
    """The file named on the command line, and the run's span table."""

    def __init__(self, path: str, text: str, table: spans.SpanTable) -> None:
        self.path = path
        self.text = text
        self.table = table

    def term(self) -> syntax.Term:
        """The file's term: its header checked, its code parsed, its spans read."""
        try:
            loaded = source.read(self.text, self.path, self.table)
        except source.SourceError as error:
            raise CliError(error.message, error.span) from error
        for message, span in loaded.warnings:
            _print(self.table, self.path, 'warning', message, span)
        if errors := syntax.gather_errors(loaded.term):
            raise CliError(errors[0].message, errors[0].span)
        return loaded.term


def _ingot(program: _Program) -> ingots.Ingot:
    """The program's ingot: resolved, normalized, not stuck, read
    as an ingot."""
    try:
        return ingots.ingot_of(program.term())
    except (reduction.ReductionError, ingots.IngotError) as error:
        raise CliError(error.message, error.span) from error


def _check(program: _Program) -> None:
    _emit_llvm(program)


def _emit_llvm(program: _Program) -> str:
    ingot = _ingot(program)
    try:
        return str(llvm_translate.translate(ingot, TARGET))
    except llvm_translate.LlvmTranslationError as error:
        raise CliError(error.message, error.span) from error


def _normal(program: _Program) -> str:
    """The program's normal form, pretty-printed: a program that gives the same ingot."""
    try:
        normal = strategy.normalize(reduction.resolve(program.term()))
    except reduction.ReductionError as error:
        raise CliError(error.message, error.span) from error
    return source.write(normal, program.table)


def _fmt(program: _Program) -> str:
    return source.write(program.term(), program.table)


def _run(program: _Program) -> int:
    """Builds the program with `clang`, runs it, prints `main`'s result; returns the exit status."""
    clang = shutil.which('clang')
    if clang is None:
        raise CliError('oymo run needs clang, which is not on PATH; install clang.')
    ir_text = _emit_llvm(program)
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


def _print(table: spans.SpanTable, path: str, kind: str, message: str, span: int) -> None:
    """`file:line:column: kind: message`, the column in bytes; `path: kind: message` with no span."""
    if (where := table.resolve(span)) is None:
        print(f'{path}: {kind}: {message}', file=sys.stderr)
        return
    file, line, column = where
    print(f'{file}:{line}:{column}: {kind}: {message}', file=sys.stderr)


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
    table = spans.SpanTable()
    try:
        try:
            text = pathlib.Path(args.file).read_text(encoding='utf-8')
        except OSError as error:
            raise CliError(f'Cannot read the file: {error.strerror}.') from error
        program = _Program(args.file, text, table)
        if args.command == 'emit-llvm':
            ir_text = _emit_llvm(program)
            if args.output is None:
                sys.stdout.write(ir_text)
            else:
                pathlib.Path(args.output).write_text(ir_text, encoding='utf-8')
        elif args.command == 'check':
            _check(program)
        elif args.command == 'fmt':
            sys.stdout.write(_fmt(program))
        elif args.command == 'normal':
            sys.stdout.write(_normal(program))
        else:
            return _run(program)
    except CliError as error:
        _print(table, args.file, 'error', error.message, error.span)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
