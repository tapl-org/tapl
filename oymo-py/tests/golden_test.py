# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import io
import os
import pathlib
import subprocess

import llvmlite.binding as llvm
import pytest
from approvaltests.approvals import verify
from approvaltests.core.namer import Namer

from oymo.oymomo import driver, ingot, layers, llvm_opcodes, llvm_translate, reduction, source, strategy


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


TARGET = llvm_translate.Target(triple='x86_64-unknown-linux-gnu', data_layout='', opcodes=llvm_opcodes.DEFAULT_OPCODES)


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
    normal = normals[0] if len(normals) == 1 else layers.merge(*normals)
    return source.write(normal), ir_texts


def run_golden_test(test_name: str) -> None:
    """Approves `name.ll` and, for two layers, `name.guard.ll` (the high layer), and
    `name.normal.oymo` unless the source is already normal."""
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
    approve(base_directory, test_name, text, normal_text, ir_texts)


def approve(base_directory: str, test_name: str, text: str, normal_text: str, ir_texts: list[str]) -> None:
    """Approves the outputs of the golden `test_name`, whose root source is `text`."""
    normal_path = pathlib.Path(base_directory, f'{test_name}.normal.oymo')
    if normal_text == text:
        # The source is already normal: no `.normal.oymo` is kept for it.
        normal_path.unlink(missing_ok=True)
    else:
        verify(normal_text, namer=ApprovalNamer(str(normal_path)))
    # The normal form is itself a program, already normal, that gives the same LLVM IR. It
    # reads no file, so it needs no driver session.
    assert compile_oymo(normal_text) == (normal_text, ir_texts)
    guard_path = pathlib.Path(base_directory, f'{test_name}.guard.ll')
    if len(ir_texts) == 1:
        guard_path.unlink(missing_ok=True)
    else:
        verify(ir_texts[1], namer=ApprovalNamer(str(guard_path)))
    verify(ir_texts[0], namer=ApprovalNamer(os.path.join(base_directory, f'{test_name}.ll')))


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
]


@pytest.mark.parametrize('name', GOLDENS)
def test_golden(name):
    run_golden_test(name)


def compile_unit(directory: pathlib.Path) -> tuple[str, list[str]]:
    """`compile_oymo` of `directory/root.oymo`, in a driver session whose top is `directory`."""
    with driver.session(str(directory)) as build:
        compiled = compile_oymo((directory / 'root.oymo').read_text())
        build.check()
    return compiled


def run_unit_golden(test_name: str) -> None:
    """A unit of several files: the directory `name/`, whose `root.oymo` reads the others.
    Every file is kept pretty-printed. Approves `name.ll` (and `name.guard.ll` for two
    layers) and `name.normal.oymo`, the unit's normal form: a program of one file."""
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    directory = pathlib.Path(base_directory, test_name)
    texts = {path: path.read_text() for path in sorted(directory.rglob('*.oymo'))}
    pretty_texts = {path: source.write(parse(text)) for path, text in texts.items()}
    if pretty_texts != texts:
        # Replace each file by its pretty form; the unit must give the same LLVM IR.
        ir_texts = compile_unit(directory)[1]
        for path, text in pretty_texts.items():
            path.write_text(text)
        assert compile_unit(directory)[1] == ir_texts
    normal_text, ir_texts = compile_unit(directory)
    approve(base_directory, test_name, pretty_texts[directory / 'root.oymo'], normal_text, ir_texts)


UNIT_GOLDENS = ['unit']


@pytest.mark.parametrize('name', UNIT_GOLDENS)
def test_unit_golden(name):
    run_unit_golden(name)
