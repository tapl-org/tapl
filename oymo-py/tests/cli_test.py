# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pathlib
import shutil
import stat
import subprocess

import pytest

from oymo import cli

GOLDENS = pathlib.Path(__file__).parent / 'goldens'
FACT = str(GOLDENS / 'fact.oymo')


@pytest.fixture(autouse=True)
def workspace(tmp_path, monkeypatch) -> None:
    """Every test runs with a temporary directory as the workspace (the current directory),
    so no `oymo-out/` is left in the repository."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def goldens_workspace(monkeypatch) -> None:
    """The goldens' folder as the workspace: a unit golden reads its files from there."""
    monkeypatch.chdir(GOLDENS)


# An ingot with one function `main`, whose entry block is `{}`.
INGOT = "{{main = {{type = {{'function', {{}}, 'i32'}}, link = 'main', body = λm. λp. m [] (λr. {{{}}})}}}}"


def write(tmp_path: pathlib.Path, text: str) -> str:
    path = tmp_path / 'a.oymo'
    path.write_text(text, encoding='utf-8')
    return str(path)


def _column(line: str, part: str) -> int:
    """The 1-based byte column of `part` in `line`."""
    return len(line[: line.index(part)].encode('utf-8')) + 1


@pytest.mark.usefixtures('goldens_workspace')
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


@pytest.mark.usefixtures('goldens_workspace')
def test_normal_prints_the_normal_form(capsys) -> None:
    assert cli.main(['normal', str(GOLDENS / 'helpers.oymo')]) == 0
    assert capsys.readouterr().out == (GOLDENS / 'helpers.normal.oymo').read_text(encoding='utf-8')


@pytest.mark.usefixtures('goldens_workspace')
def test_fmt_keeps_a_pretty_file(capsys) -> None:
    assert cli.main(['fmt', FACT]) == 0
    assert capsys.readouterr().out == pathlib.Path(FACT).read_text(encoding='utf-8')


@pytest.mark.usefixtures('goldens_workspace')
def test_emit_llvm_to_stdout_and_file(tmp_path, capsys) -> None:
    assert cli.main(['emit-llvm', FACT]) == 0
    ir_text = capsys.readouterr().out
    assert 'define i32 @"main"()' in ir_text
    output = tmp_path / 'fact.ll'
    assert cli.main(['emit-llvm', FACT, '-o', str(output)]) == 0
    assert output.read_text(encoding='utf-8') == ir_text


@pytest.mark.usefixtures('goldens_workspace')
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


@pytest.mark.usefixtures('goldens_workspace')
def test_run_prints_the_exit_status(tmp_path, monkeypatch, capfd) -> None:
    fake_clang(tmp_path, monkeypatch)
    assert cli.main(['run', FACT]) == 0
    assert capfd.readouterr().out == '120\n'


@pytest.mark.usefixtures('goldens_workspace')
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


@pytest.mark.usefixtures('goldens_workspace')
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


@pytest.mark.usefixtures('goldens_workspace')
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


def test_check_checks_both_layers(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(GOLDENS)
    assert cli.main(['check', LAYERS]) == 0
    monkeypatch.chdir(tmp_path)
    line = two_layers('[00000000]', '[01]')
    path = write(tmp_path, line)
    assert cli.main(['check', path]) == 1
    column = _column(line.splitlines()[1], '[01]')
    assert capsys.readouterr().err == f'{path}:2:{column}: error: A constant of type i32 is a byte array of 4 bytes.\n'


@pytest.mark.usefixtures('goldens_workspace')
def test_normal_prints_the_layers_low_then_high(capsys) -> None:
    assert cli.main(['normal', LAYERS]) == 0
    assert capsys.readouterr().out == (GOLDENS / 'layers.normal.oymo').read_text(encoding='utf-8')


@pytest.mark.usefixtures('goldens_workspace')
def test_normal_merge_merges_the_layers(capsys) -> None:
    assert cli.main(['normal', '--merge', LAYERS]) == 0
    out = capsys.readouterr().out
    assert "('add' : 'sub') {'i32', p.a, [05000000] : p.a}" in out


def test_fmt_keeps_the_layerings_as_written_and_merge_tidies_them(tmp_path, capsys, monkeypatch) -> None:
    path = write(tmp_path, 'language oymomo\nλa. λb. λc. {x = a b : a c, y = c : c}\n')
    assert cli.main(['fmt', path]) == 0
    assert capsys.readouterr().out == 'language oymomo\nλa. λb. λc. {x= a b : a c, y= c : c}\n'
    assert cli.main(['fmt', '--merge', path]) == 0
    assert capsys.readouterr().out == 'language oymomo\nλa. λb. λc. {x= a (b : c), y= c}\n'
    monkeypatch.chdir(GOLDENS)
    assert cli.main(['fmt', '--merge', FACT]) == 0
    assert capsys.readouterr().out == pathlib.Path(FACT).read_text(encoding='utf-8')


@pytest.mark.usefixtures('goldens_workspace')
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


# Driver sessions: a program reads files by their paths from the workspace.


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


# A unit `math`: `gcd` is linked, `helper` is internal and `puts` is an import.
MATH = """language oymomo
{
  math= {
    gcd= {
      type= {'function', {a= 'i32', b= 'i32'}, 'i32'},
      link= 'gcd',
      body= λm. λp. m [] (λr. {
        entry= r.loop p.a p.b,
        loop= λa. λb.
          let z = 'icmp' {'eq', 'i32', b, [00000000]} in
          m [] (λq. {
            if z then r.done a else q.step,
            step= let c = m.math.helper {a= a, b= b} in r.loop b c,
          }),
        done= λc. c,
      }),
    },
    helper= {
      type= {'function', {a= 'i32', b= 'i32'}, 'i32'},
      body= λm. λp. m [] (λr. {let c = 'urem' {'i32', p.a, p.b} in c}),
    },
  },
  puts= {type= {'function', {s= 'ptr'}, 'i32'}, link= 'puts'},
}
"""
MATH_HEADER = "language oymomo\n{math= {gcd= {type= {'function', {a= 'i32', b= 'i32'}, 'i32'}, link= 'gcd'}}}\n"

# A unit `app` that mounts math's header under `m2` and calls `gcd` through it. The header
# mirrors math's root, `math/root.oymo`, in the destination folder.
APP = """language oymomo
'unit.merge'
  {
    'unit.rebase' {{'m2'}, 'driver.read_low' 'out/math/root.h.oymo'},
    {
      main= {
        type= {'function', {}, 'i32'},
        link= 'main',
        body= λm. λp. m [] (λr. {let g = m.m2.math.gcd {a= [30000000], b= [12000000]} in g}),
      },
    },
  }
"""


def write_unit(tmp_path: pathlib.Path, name: str, text: str) -> str:
    """The unit `name`: its root `name/root.oymo` in the workspace, as a path from there."""
    path = tmp_path / name / 'root.oymo'
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return f'{name}/root.oymo'


def test_emit_header_mirrors_the_root_in_oymo_out(tmp_path, capsys) -> None:
    # One destination folder in the current directory for every unit built from here; the
    # header mirrors the root's path in the workspace.
    assert cli.main(['emit-header', write_unit(tmp_path, 'math', MATH)]) == 0
    assert capsys.readouterr() == ('', '')
    assert (tmp_path / 'oymo-out' / 'math' / 'root.h.oymo').read_text(encoding='utf-8') == MATH_HEADER
    assert not (tmp_path / 'math' / 'oymo-out').exists()


def test_emit_header_mirrors_a_nested_root(tmp_path, capsys) -> None:
    (tmp_path / 'lib').mkdir()
    write_unit(tmp_path / 'lib', 'math', MATH)
    assert cli.main(['emit-header', str(tmp_path / 'lib' / 'math' / 'root.oymo')]) == 0
    assert capsys.readouterr() == ('', '')
    assert (tmp_path / 'oymo-out' / 'lib' / 'math' / 'root.h.oymo').read_text(encoding='utf-8') == MATH_HEADER


def test_emit_header_writes_into_the_out_folder(tmp_path, capsys) -> None:
    out = tmp_path / 'build' / 'gen'
    assert cli.main(['emit-header', write_unit(tmp_path, 'math', MATH), '--out', str(out)]) == 0
    assert capsys.readouterr() == ('', '')
    assert (out / 'math' / 'root.h.oymo').read_text(encoding='utf-8') == MATH_HEADER
    assert not (tmp_path / 'oymo-out').exists()


def test_emit_header_to_a_path_and_to_stdout(tmp_path, capsys) -> None:
    output = tmp_path / 'm.h.oymo'
    math = write_unit(tmp_path, 'math', MATH)
    assert cli.main(['emit-header', math, '-o', str(output)]) == 0
    assert output.read_text(encoding='utf-8') == MATH_HEADER
    assert cli.main(['emit-header', math, '-o', '-']) == 0
    assert capsys.readouterr() == (MATH_HEADER, '')
    assert not (tmp_path / 'oymo-out').exists()


@pytest.mark.usefixtures('goldens_workspace')
def test_emit_header_of_two_layers_is_one_file(capsys) -> None:
    assert cli.main(['emit-header', LAYERS, '-o', '-']) == 0
    assert capsys.readouterr().out == (GOLDENS / 'layers.h.oymo').read_text(encoding='utf-8')


@pytest.mark.usefixtures('goldens_workspace')
def test_emit_header_merge(capsys) -> None:
    assert cli.main(['emit-header', LAYERS, '-o', '-', '--merge']) == 0
    assert capsys.readouterr().out == "language oymomo\n{main= {type= {'function', {a= 'i32'}, 'i32'}, link= 'main'}}\n"


def test_emit_header_cannot_write(tmp_path, capsys) -> None:
    output = tmp_path / 'missing' / 'm.h.oymo'
    path = write_unit(tmp_path, 'math', MATH)
    assert cli.main(['emit-header', path, '-o', str(output)]) == 1
    assert capsys.readouterr().err == (
        f'{path}: error: Cannot write the header to {str(output)!r}: No such file or directory.\n'
    )


def test_the_root_file_must_be_inside_the_workspace(tmp_path, capsys, monkeypatch) -> None:
    path = write_unit(tmp_path, 'math', MATH)
    (tmp_path / 'app').mkdir()
    monkeypatch.chdir(tmp_path / 'app')
    outside = f'../{path}'
    assert cli.main(['check', outside]) == 1
    assert capsys.readouterr().err == (
        f'{outside}: error: The root file must be inside the workspace, the current directory: {tmp_path / "app"}.\n'
    )


def test_reads_are_paths_from_the_workspace(tmp_path, capsys) -> None:
    # The root `calc/root.oymo` reads its lexer as `calc/lexer.oymo`, not `lexer.oymo`.
    (tmp_path / 'calc').mkdir()
    (tmp_path / 'calc' / 'lexer.oymo').write_text('language oymomo\n{x = [01]}\n', encoding='utf-8')
    root = tmp_path / 'calc' / 'root.oymo'
    root.write_text("language oymomo\n'driver.read_low' 'calc/lexer.oymo'\n", encoding='utf-8')
    assert cli.main(['normal', 'calc/root.oymo']) == 0
    assert capsys.readouterr().out == 'language oymomo\n{x= [01]}\n'
    root.write_text("language oymomo\n'driver.read_low' 'lexer.oymo'\n", encoding='utf-8')
    assert cli.main(['normal', 'calc/root.oymo']) == 1
    assert "Cannot read 'lexer.oymo': No such file or directory." in capsys.readouterr().err


def test_out_is_read_through_the_virtual_directory(tmp_path, capsys) -> None:
    out = tmp_path / 'build'
    assert cli.main(['emit-header', write_unit(tmp_path, 'math', MATH), '--out', str(out)]) == 0
    app = write_unit(tmp_path, 'app', APP)
    assert cli.main(['check', app, '--out', str(out)]) == 0
    # The default destination folder has no header.
    assert cli.main(['check', app]) == 1
    assert "Cannot read 'out/math/root.h.oymo': No such file or directory." in capsys.readouterr().err


@pytest.mark.skipif(shutil.which('clang') is None, reason='needs clang')
def test_a_unit_calls_another_through_its_header(tmp_path, capsys) -> None:
    """Compiled reuse, as Blaze builds: from the workspace, math builds to math.ll and its
    header `oymo-out/math/root.h.oymo`; app reads the header as `out/math/root.h.oymo` and
    builds to app.ll; the platform linker joins the two."""
    math = write_unit(tmp_path, 'math', MATH)
    assert cli.main(['emit-header', math]) == 0
    assert cli.main(['emit-llvm', math, '-o', 'math.ll']) == 0
    app = write_unit(tmp_path, 'app', APP)
    assert cli.main(['emit-llvm', app, '-o', 'app.ll']) == 0
    assert capsys.readouterr() == ('', '')
    clang = str(shutil.which('clang'))
    subprocess.run([clang, '-Wno-override-module', '-x', 'ir', 'math.ll', 'app.ll', '-o', 'app.exe'], check=True)
    assert subprocess.run([str(tmp_path / 'app.exe')], check=False).returncode == 6
