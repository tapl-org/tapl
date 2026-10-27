# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pathlib
import shutil
import stat

import pytest

from oymo import cli

GOLDENS = pathlib.Path(__file__).parent / 'goldens'
FACT = str(GOLDENS / 'fact.oymo')


# An ingot with one function `main`, whose entry block is `{}`.
INGOT = (
    "{{version = '0', symbols = {{main = {{type = {{'function', {{}}, 'i32'}}, body = λm. λp. m [] (λr. {{{}}})}}}}}}"
)


def write(tmp_path: pathlib.Path, text: str) -> str:
    path = tmp_path / 'a.oymo'
    path.write_text(text, encoding='utf-8')
    return str(path)


def _column(line: str, part: str) -> int:
    """The 1-based byte column of `part` in `line`."""
    return len(line[: line.index(part)].encode('utf-8')) + 1


def test_check_ok(capsys) -> None:
    assert cli.main(['check', FACT]) == 0
    assert capsys.readouterr() == ('', '')


def test_check_error_is_located(tmp_path, capsys) -> None:
    # Columns count UTF-8 bytes: `λ` is two columns.
    line = INGOT.format('nope')
    path = write(tmp_path, f'language oymomo\n// a comment\n{line}\n')
    assert cli.main(['check', path]) == 1
    column = len(line[: line.index('nope')].encode('utf-8')) + 1
    assert capsys.readouterr().err == f"{path}:3:{column}: error: Unknown name 'nope'.\n"


def test_check_reports_an_ingot_error(tmp_path, capsys) -> None:
    line = INGOT.format('p.z')
    path = write(tmp_path, f'language oymomo\n{line}\n')
    assert cli.main(['check', path]) == 1
    assert capsys.readouterr().err == (
        f"{path}:2:{_column(line, 'p.z')}: error: 'main' has no parameter 'z'; it has [].\n"
    )


def test_check_reports_an_llvm_error(tmp_path, capsys) -> None:
    line = INGOT.format('[01]')
    path = write(tmp_path, f'language oymomo\n{line}\n')
    assert cli.main(['check', path]) == 1
    assert capsys.readouterr().err == (
        f'{path}:2:{_column(line, "[01]")}: error: A constant of type i32 is a byte array of 4 bytes.\n'
    )


def test_syntax_error(tmp_path, capsys) -> None:
    path = write(tmp_path, 'language oymomo\n{x= \n')
    assert cli.main(['check', path]) == 1
    assert capsys.readouterr().err == f'{path}:2:1: error: Syntax error.\n'


def test_missing_header(tmp_path, capsys) -> None:
    path = write(tmp_path, '{}\n')
    assert cli.main(['fmt', path]) == 1
    assert capsys.readouterr().err == f"{path}:1:1: error: Expected the first line to be 'language oymomo'.\n"


def test_missing_file(tmp_path, capsys) -> None:
    path = str(tmp_path / 'missing.oymo')
    assert cli.main(['check', path]) == 1
    assert capsys.readouterr().err == f'{path}: error: Cannot read the file: No such file or directory.\n'


def test_fmt_prints_the_pretty_form(tmp_path, capsys) -> None:
    path = write(tmp_path, "language oymomo\n{version='0',symbols={main={type='i32',init=[00000000]}}}\n")
    assert cli.main(['fmt', path]) == 0
    assert capsys.readouterr().out == (
        "language oymomo\n{version= '0', symbols= {main= {type= 'i32', init= [00000000]}}}\n"
    )


def test_normal_prints_the_normal_form(capsys) -> None:
    assert cli.main(['normal', str(GOLDENS / 'helpers.oymo')]) == 0
    assert capsys.readouterr().out == (GOLDENS / 'helpers.normal.oymo').read_text(encoding='utf-8')


def test_fmt_keeps_a_pretty_file(capsys) -> None:
    assert cli.main(['fmt', FACT]) == 0
    assert capsys.readouterr().out == pathlib.Path(FACT).read_text(encoding='utf-8')


def test_emit_llvm_to_stdout_and_file(tmp_path, capsys) -> None:
    assert cli.main(['emit-llvm', FACT]) == 0
    ir_text = capsys.readouterr().out
    assert 'define i32 @"main"()' in ir_text
    output = tmp_path / 'fact.ll'
    assert cli.main(['emit-llvm', FACT, '-o', str(output)]) == 0
    assert output.read_text(encoding='utf-8') == ir_text


def test_run_without_clang(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli.shutil, 'which', lambda _name: None)
    assert cli.main(['run', FACT]) == 1
    assert 'needs clang' in capsys.readouterr().err


def test_run_prints_the_exit_status(tmp_path, monkeypatch, capfd) -> None:
    # A fake clang whose output program exits with 120, to test the plumbing without clang.
    fake = tmp_path / 'bin' / 'clang'
    fake.parent.mkdir()
    fake.write_text(
        '#!/bin/sh\nwhile [ "$1" != "-o" ]; do shift; done\nprintf "#!/bin/sh\\nexit 120\\n" > "$2"\nchmod +x "$2"\n'
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv('PATH', str(fake.parent), prepend=':')
    assert cli.main(['run', FACT]) == 0
    assert capfd.readouterr().out == '120\n'


@pytest.mark.skipif(shutil.which('clang') is None, reason='needs clang')
@pytest.mark.parametrize(
    ('golden', 'result'),
    [
        ('simplest', 0),
        ('structs', 7),
        ('fact', 120),
        ('gcd', 6),
        ('floyd', 7),
        ('globals', 83),
        ('puts', 0),
        ('helpers', 3),
    ],
)
def test_run_golden(capfd, golden: str, result: int) -> None:
    # The goldens that have a `main`; run with no arguments, so `argc` is 1.
    assert cli.main(['run', str(GOLDENS / f'{golden}.oymo')]) == 0
    assert capfd.readouterr().out == f'{result}\n'
