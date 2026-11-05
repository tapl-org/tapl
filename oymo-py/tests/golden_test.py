# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import io
import os
import pathlib
import subprocess

import llvmlite.binding as llvm
import pytest
from approvaltests.approvals import verify
from approvaltests.core.namer import Namer

from oymo.core import syntax
from oymo.oymomo import driver, header, ingot, layers, llvm_opcodes, llvm_translate, reduction, source, strategy


def run_command(command):
    """
    Runs a command and captures its stdout and stderr.

    Args:
      command: A string or list of strings representing the command to run.

    Returns:
      A tuple containing the return code, stdout, and stderr.
    """
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,  # Decode stdout and stderr as text
            check=False,  # do not raise exception on non-zero return code.
        )
    except FileNotFoundError:
        return -1, '', f'Command not found: {command}'
    else:
        return process.returncode, process.stdout, process.stderr


class ApprovalNamer(Namer):
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def get_received_filename(self, base: str | None = None) -> str:
        del base
        return self.filename + Namer.RECEIVED

    def get_approved_filename(self, base: str | None = None) -> str:
        del base
        return self.filename


def run_python_files(base_directory: str, filenames: list[str], output_file: str) -> None:
    output = io.StringIO()
    for filename in filenames:
        filepath = os.path.join(base_directory, filename)
        return_code, stdout, stderr = run_command(['python', filepath])
        output.write(f'====== {filename} exit-status:{return_code} stdout:\n')
        output.write(stdout)
        output.write('\n------ stderr:\n')
        output.write(stderr)
        output.write('\n------ end.\n\n')
        if return_code != 0:
            break
    filepath = os.path.join(base_directory, output_file)
    verify(output.getvalue(), namer=ApprovalNamer(filepath))


TARGET = llvm_translate.Target(opcodes=llvm_opcodes.DEFAULT_OPCODES)


def parse(text: str):
    loaded = source.read(text, 'golden.oymo')
    assert not loaded.warnings
    return loaded.term


def compile_oymo(text: str) -> tuple[str, list[str]]:
    """The normal form, pretty-printed with its tags, and the LLVM IR text of each layer (low,
    then high). With two layers, the normal form is the two layers' normal forms merged."""
    written = parse(text)
    separated = layers.separate(written)
    normals = [strategy.normalize(reduction.resolve(layer)) for layer in (separated or (written,))]
    ir_texts = [str(llvm_translate.translate(each, TARGET)) for each in ingot.ingots_of(parse(text))]
    for ir_text in ir_texts:
        llvm.parse_assembly(ir_text).verify()
    # Two layers are written as `low : high`, as `oymo normal` prints them.
    normal = normals[0] if len(normals) == 1 else syntax.Layers(layers=(normals[0], normals[1]))
    return source.write(normal), ir_texts


def run_golden_test(test_name: str) -> None:
    """Approves `name.ll` and, for two layers, `name.guard.ll` (the high layer), and
    `name.normal.oymo` unless the source is already normal; for a golden in `HEADERS`,
    its header `name.h.oymo` too."""
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    source_path = pathlib.Path(os.path.join(base_directory, f'{test_name}.oymo'))
    text = source_path.read_text()
    pretty_text = source.write(parse(text))
    if text != pretty_text:
        # The source is kept pretty-printed: replace it by its pretty form, which must give the same LLVM IR.
        assert compile_oymo(pretty_text)[1] == compile_oymo(text)[1]
        source_path.write_text(pretty_text)
        text = pretty_text
    normal_text, ir_texts = compile_oymo(text)
    header_text = header_oymo(text) if test_name in HEADERS else None
    approve(os.path.join(base_directory, test_name), text, normal_text, ir_texts, header_text)


def approve(prefix: str, text: str, normal_text: str, ir_texts: list[str], header_text: str | None) -> None:
    """Approves the outputs of a golden whose root source is `text`, at the paths `prefix`
    plus `.normal.oymo`, `.ll`, `.guard.ll`; and its header, `prefix.h.oymo`, if
    `header_text` is given."""
    normal_path = pathlib.Path(f'{prefix}.normal.oymo')
    if normal_text == text:
        # The source is already normal: no `.normal.oymo` is kept for it.
        normal_path.unlink(missing_ok=True)
    else:
        verify(normal_text, namer=ApprovalNamer(str(normal_path)))
    # The normal form is itself a program, already normal, that gives the same LLVM IR. It
    # reads no file, so it needs no driver session.
    assert compile_oymo(normal_text) == (normal_text, ir_texts)
    guard_path = pathlib.Path(f'{prefix}.guard.ll')
    if len(ir_texts) == 1:
        guard_path.unlink(missing_ok=True)
    else:
        verify(ir_texts[1], namer=ApprovalNamer(str(guard_path)))
    verify(ir_texts[0], namer=ApprovalNamer(f'{prefix}.ll'))
    if header_text is not None:
        # The normal form gives the same header.
        assert header_oymo(normal_text) == header_text
        verify(header_text, namer=ApprovalNamer(f'{prefix}.h.oymo'))


# The goldens whose header `name.h.oymo` is approved too.
HEADERS = {'layers', 'unit'}


def header_oymo(text: str) -> str:
    """The header of the program `text`, as a source file: one file for one layer or two."""
    return source.write(header.header_of_layers(ingot.ingots_of(parse(text))))


GOLDENS = [
    'simplest',
    'effects',
    'pointer',
    'memory',
    'aggregate',
    'structs',
    'globals',
    'fact',
    'gcd',
    'floyd',
    'field0',
    'puts',
    'helpers',
    'spans',
    'layers',
    'blocks',
    'table',
]


@pytest.mark.parametrize('name', GOLDENS)
def test_golden(name):
    run_golden_test(name)


def compile_unit(directory: pathlib.Path) -> tuple[str, list[str]]:
    """`compile_oymo` of `directory/root.oymo`, in a driver session whose top is the
    workspace, `directory`'s parent (`goldens/`): the unit's reads are paths from there."""
    with driver.session(str(directory.parent)) as build:
        compiled = compile_oymo((directory / 'root.oymo').read_text())
        build.check()
    return compiled


def unit_header(directory: pathlib.Path) -> str:
    """`header_oymo` of `directory/root.oymo`, in a driver session whose top is the
    workspace, `directory`'s parent (`goldens/`)."""
    with driver.session(str(directory.parent)) as build:
        header_text = header_oymo((directory / 'root.oymo').read_text())
        build.check()
    return header_text


def run_unit_golden(test_name: str) -> None:
    """A unit of several files: the directory `name/`, whose `root.oymo` reads the others
    by their paths from the workspace `goldens/` (`'name/lexer.oymo'`).
    Every file is kept pretty-printed. Approves, inside the directory and named after the
    root, `root.ll` (and `root.guard.ll` for two layers) and `root.normal.oymo`, the unit's
    normal form: a program of one file; for a golden in `HEADERS`, its header `root.h.oymo`
    too. These outputs are no source of the unit."""
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    directory = pathlib.Path(base_directory, test_name)
    outputs = {directory / 'root.normal.oymo', directory / 'root.h.oymo'}
    texts = {path: path.read_text() for path in sorted(directory.rglob('*.oymo')) if path not in outputs}
    pretty_texts = {path: source.write(parse(text)) for path, text in texts.items()}
    if pretty_texts != texts:
        # Replace each file by its pretty form; the unit must give the same LLVM IR.
        ir_texts = compile_unit(directory)[1]
        for path, text in pretty_texts.items():
            path.write_text(text)
        assert compile_unit(directory)[1] == ir_texts
    normal_text, ir_texts = compile_unit(directory)
    header_text = unit_header(directory) if test_name in HEADERS else None
    approve(str(directory / 'root'), pretty_texts[directory / 'root.oymo'], normal_text, ir_texts, header_text)


UNIT_GOLDENS = ['unit', 'diamond', 'template', 'say']


@pytest.mark.parametrize('name', UNIT_GOLDENS)
def test_unit_golden(name):
    run_unit_golden(name)
