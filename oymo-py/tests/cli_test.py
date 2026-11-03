# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pathlib
import shutil
import stat

import pytest

from oymo import cli

GOLDENS = pathlib.Path(__file__).parent / 'goldens'
FACT = str(GOLDENS / 'fact.oymo')


# An ingot with one function `main`, whose entry block is `{}`.
INGOT = "{{main = {{type = {{'function', {{}}, 'i32'}}, link = 'main', body = λm. λp. m [] (λr. {{{}}})}}}}"


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
    path = write(tmp_path, "language oymomo\n{main={type='i32',init=[00000000]}}\n")
    assert cli.main(['fmt', path]) == 0
    assert capsys.readouterr().out == "language oymomo\n{main= {type= 'i32', init= [00000000]}}\n"


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


def fake_clang(tmp_path, monkeypatch) -> None:
    """A fake clang whose output program exits with 120, to test the plumbing without clang."""
    fake = tmp_path / 'bin' / 'clang'
    fake.parent.mkdir()
    fake.write_text(
        '#!/bin/sh\nwhile [ "$1" != "-o" ]; do shift; done\nprintf "#!/bin/sh\\nexit 120\\n" > "$2"\nchmod +x "$2"\n'
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv('PATH', str(fake.parent), prepend=':')


def test_run_prints_the_exit_status(tmp_path, monkeypatch, capfd) -> None:
    fake_clang(tmp_path, monkeypatch)
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
        ('layers', 6),
        # A unit of several files; its root reads the others.
        ('unit/root', 24),
    ],
)
def test_run_golden(capfd, golden: str, result: int) -> None:
    # The goldens that have a `main`; run with no arguments, so `argc` is 1.
    assert cli.main(['run', str(GOLDENS / f'{golden}.oymo')]) == 0
    assert capfd.readouterr().out == f'{result}\n'


LAYERS = str(GOLDENS / 'layers.oymo')


# A `main` returning `low` in the low layer and `high` in the high layer.
def two_layers(low: str, high: str, link: str = "'main'") -> str:
    return (
        "language oymomo\n{main = {type = {'function', {}, 'i32'}, link = "
        f'{link}, body = λm. λp. m [] (λr. {{entry = {low} : {high}}})}}}}\n'
    )


def test_emit_llvm_writes_both_layers(tmp_path, capsys) -> None:
    low, high = tmp_path / 'low.ll', tmp_path / 'high.ll'
    assert cli.main(['emit-llvm', LAYERS, '--low', str(low), '--high', str(high)]) == 0
    assert capsys.readouterr() == ('', '')
    assert low.read_text(encoding='utf-8') == (GOLDENS / 'layers.ll').read_text(encoding='utf-8')
    assert high.read_text(encoding='utf-8') == (GOLDENS / 'layers.guard.ll').read_text(encoding='utf-8')
    assert cli.main(['emit-llvm', LAYERS, '--low', '-', '--high', str(high)]) == 0
    assert capsys.readouterr().out == (GOLDENS / 'layers.ll').read_text(encoding='utf-8')
    assert cli.main(['emit-llvm', LAYERS, '--low', str(low), '--high', '-']) == 0
    assert capsys.readouterr().out == (GOLDENS / 'layers.guard.ll').read_text(encoding='utf-8')


@pytest.mark.parametrize(
    ('arguments', 'message'),
    [
        ([LAYERS], 'The program has two layers: give both --low and --high, each a path or - for stdout.'),
        (
            [LAYERS, '--low', '-'],
            'The program has two layers: give both --low and --high, each a path or - for stdout.',
        ),
        ([LAYERS, '-o', 'x.ll'], 'The program has two layers: write them with --low and --high, not -o.'),
        ([LAYERS, '--low', '-', '--high', '-'], 'At most one of --low and --high may be - (stdout).'),
        (
            [FACT, '--low', 'a.ll', '--high', 'b.ll'],
            '--low and --high are for a program with two layers; this one has one: use -o.',
        ),
    ],
)
def test_emit_llvm_layer_errors(capsys, arguments: list[str], message: str) -> None:
    assert cli.main(['emit-llvm', *arguments]) == 1
    assert capsys.readouterr() == ('', f'{arguments[0]}: error: {message}\n')


def test_check_checks_both_layers(tmp_path, capsys) -> None:
    assert cli.main(['check', LAYERS]) == 0
    line = two_layers('[00000000]', '[01]')
    path = write(tmp_path, line)
    assert cli.main(['check', path]) == 1
    column = _column(line.splitlines()[1], '[01]')
    assert capsys.readouterr().err == f'{path}:2:{column}: error: A constant of type i32 is a byte array of 4 bytes.\n'


def test_normal_merges_the_layers(capsys) -> None:
    assert cli.main(['normal', LAYERS]) == 0
    assert capsys.readouterr().out == (GOLDENS / 'layers.normal.oymo').read_text(encoding='utf-8')


def test_fmt_keeps_the_layerings_as_written_and_merge_tidies_them(tmp_path, capsys) -> None:
    path = write(tmp_path, 'language oymomo\nλa. λb. λc. {x = a b : a c, y = c : c}\n')
    assert cli.main(['fmt', path]) == 0
    assert capsys.readouterr().out == 'language oymomo\nλa. λb. λc. {x= a b : a c, y= c : c}\n'
    assert cli.main(['fmt', '--merge', path]) == 0
    assert capsys.readouterr().out == 'language oymomo\nλa. λb. λc. {x= a (b : c), y= c}\n'
    assert cli.main(['fmt', '--merge', FACT]) == 0
    assert capsys.readouterr().out == pathlib.Path(FACT).read_text(encoding='utf-8')


def test_run_a_failing_guard_stops_the_program(tmp_path, monkeypatch, capfd) -> None:
    fake_clang(tmp_path, monkeypatch)  # every program exits with 120, the guard too
    assert cli.main(['run', LAYERS]) == 1
    assert capfd.readouterr() == ('', f'{LAYERS}: error: The guard failed with status 120.\n')


@pytest.mark.parametrize(
    ('link', 'layer'),
    [("'main' : 'guard'", 'high layer (the guard)'), ("'start' : 'main'", 'low layer')],
)
def test_run_needs_main_in_both_layers(tmp_path, monkeypatch, capfd, link: str, layer: str) -> None:
    fake_clang(tmp_path, monkeypatch)
    path = write(tmp_path, two_layers('[00000000]', '[00000000]', link))
    assert cli.main(['run', path]) == 1
    message = f"The {layer} has no function linked as 'main'; both layers need one to run."
    assert capfd.readouterr() == ('', f'{path}: error: {message}\n')


@pytest.mark.skipif(shutil.which('clang') is None, reason='needs clang')
@pytest.mark.parametrize(('high', 'out', 'err'), [('[00000000]', '7\n', ''), ('[03000000]', '', 'status 3.')])
def test_run_the_guard_first(tmp_path, capfd, high: str, out: str, err: str) -> None:
    path = write(tmp_path, two_layers('[07000000]', high))
    assert cli.main(['run', path]) == (1 if err else 0)
    captured = capfd.readouterr()
    assert captured.out == out
    assert captured.err == (f'{path}: error: The guard failed with {err}\n' if err else '')


# Driver sessions: a program reads files under its own directory.


def test_config_fills_driver_config(tmp_path, capsys) -> None:
    path = write(tmp_path, "language oymomo\n{c = {type = {'array', [02], 'i8'}, value = ('driver.config' {}).v}}\n")
    assert cli.main(['normal', path, '--config', 'v=hi', '--config', 'w=']) == 0
    assert capsys.readouterr().out == "language oymomo\n{c= {type= {'array', [02], 'i8'}, value= 'hi'}}\n"


@pytest.mark.parametrize(
    ('arguments', 'message'),
    [
        (['--config', 'v'], "--config takes key=value, with a nonempty key; got 'v'."),
        (['--config', '=v'], "--config takes key=value, with a nonempty key; got '=v'."),
        (['--config', 'v=1', '--config', 'v=2'], "--config gives 'v' twice."),
    ],
)
def test_bad_config(tmp_path, capsys, arguments: list[str], message: str) -> None:
    path = write(tmp_path, 'language oymomo\n{}\n')
    assert cli.main(['check', path, *arguments]) == 1
    assert capsys.readouterr().err == f'{path}: error: {message}\n'


def test_an_error_inside_a_read_file_names_that_file(tmp_path, capsys) -> None:
    line = INGOT.format('nope')
    (tmp_path / 'lib').mkdir()
    (tmp_path / 'lib' / 'b.oymo').write_text(f'language oymomo\n{line}\n', encoding='utf-8')
    path = write(tmp_path, "language oymomo\n'driver.read_low' 'lib/b.oymo'\n")
    assert cli.main(['check', path]) == 1
    assert (
        capsys.readouterr().err
        == f"{tmp_path / 'lib' / 'b.oymo'}:2:{_column(line, 'nope')}: error: Unknown name 'nope'.\n"
    )


def test_a_failed_read_is_reported_at_the_read(tmp_path, capsys) -> None:
    line = "{a = 'driver.read_low' 'missing.oymo'}"
    path = write(tmp_path, f'language oymomo\n{line}\n')
    assert cli.main(['normal', path]) == 1
    assert capsys.readouterr().err == (
        f"{path}:2:{_column(line, chr(39) + 'missing')}: error: Cannot read 'missing.oymo': No such file or directory.\n"
    )
