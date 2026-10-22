# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import io
import os
import pathlib
import subprocess

import llvmlite.binding as llvm
import pytest
from approvaltests.approvals import verify
from approvaltests.core.namer import Namer

from oymo.oymomo import grammar, llvm_opcodes, llvm_translate, module, printer, reduction, strategy


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
LANGUAGE_HEADER = 'language oymomo\n'


def parse(source: str):
    assert source.startswith(LANGUAGE_HEADER)
    return grammar.parse(source.removeprefix(LANGUAGE_HEADER))


def show(term) -> str:
    return LANGUAGE_HEADER + printer.show(term, pretty=True, name_indices=True) + '\n'


def compile_oymo(source: str) -> tuple[str, str]:
    """The normal form (semantics.tex, Section 6), pretty-printed, and the LLVM IR text."""
    normal = strategy.normalize(reduction.resolve(parse(source)))
    ir_text = str(llvm_translate.translate(module.module_of(parse(source)), TARGET))
    llvm.parse_assembly(ir_text).verify()
    return show(normal), ir_text


def run_golden_test(test_name: str) -> None:
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    source_path = pathlib.Path(os.path.join(base_directory, f'{test_name}.oymo'))
    source = source_path.read_text()
    pretty_text = show(parse(source))
    if source != pretty_text:
        # The source is kept pretty-printed: replace it by its pretty form, which must give the same LLVM IR.
        assert compile_oymo(pretty_text)[1] == compile_oymo(source)[1]
        source_path.write_text(pretty_text)
        source = pretty_text
    normal_text, ir_text = compile_oymo(source)
    verify(normal_text, namer=ApprovalNamer(os.path.join(base_directory, f'{test_name}.normal.oymo')))
    # The normal form is itself a program, already normal, that gives the same LLVM IR.
    assert compile_oymo(normal_text) == (normal_text, ir_text)
    verify(ir_text, namer=ApprovalNamer(os.path.join(base_directory, f'{test_name}.ll')))


GOLDENS = ['simplest', 'effects', 'pointer', 'memory', 'aggregate', 'globals', 'fact', 'gcd', 'helpers']


@pytest.mark.parametrize('name', GOLDENS)
def test_golden(name):
    run_golden_test(name)
