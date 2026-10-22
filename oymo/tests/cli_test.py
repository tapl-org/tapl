# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pathlib
import shutil
import stat

import pytest

from oymo import cli

GOLDENS = pathlib.Path(__file__).parent / 'goldens'
FACT = str(GOLDENS / 'fact.oymo')


def write(tmp_path: pathlib.Path, text: str) -> str:
    path = tmp_path / 'a.oymo'
    path.write_text(text, encoding='utf-8')
    return str(path)


def test_check_ok(capsys) -> None:
    assert cli.main(['check', FACT]) == 0
    assert capsys.readouterr() == ('', '')


def test_check_error_is_located(tmp_path, capsys) -> None:
    # Columns count characters, not bytes: `λ` is one column.
    line = "λm. {main = {gives = 'i32', body = λf. {entry = {takes = {}, body = λp. nope}}}}"
    path = write(tmp_path, f'language oymomo\n// a comment\n{line}\n')
    assert cli.main(['check', path]) == 1
    assert capsys.readouterr().err == f"{path}:3:{line.index('nope') + 1}: error: Unknown name 'nope'.\n"


def test_check_reports_a_module_error(tmp_path, capsys) -> None:
    line = "λm. {main = {gives = 'i32', body = λf. {entry = {takes = {}, body = λp. p.z}}}}"
    path = write(tmp_path, f'language oymomo\n{line}\n')
    assert cli.main(['check', path]) == 1
    assert capsys.readouterr().err == (
        f"{path}:2:{line.index('p.z') + 1}: error: Block 'entry' reads its parameters as p.x, x one of [].\n"
    )


def test_check_reports_an_llvm_error(tmp_path, capsys) -> None:
    line = "λm. {main = {gives = 'i32', body = λf. {entry = {takes = {}, body = λp. [01]}}}}"
    path = write(tmp_path, f'language oymomo\n{line}\n')
    assert cli.main(['check', path]) == 1
    assert capsys.readouterr().err == (
        f'{path}:2:{line.index("[01]") + 1}: error: A constant of type i32 is a byte array of 4 bytes.\n'
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
    path = write(tmp_path, "language oymomo\nλm.{main={gives='i32',body=λf.{entry={takes={},body=λp.[00000000]}}}}\n")
    assert cli.main(['fmt', path]) == 0
    assert capsys.readouterr().out == (
        "language oymomo\nλm. {main= {gives= 'i32', body= λf. {entry= {takes= {}, body= λp. [00000000]}}}}\n"
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
def test_run_fact(capfd) -> None:
    assert cli.main(['run', FACT]) == 0
    assert capfd.readouterr().out == '120\n'
