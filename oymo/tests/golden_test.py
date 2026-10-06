# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


import io
import os
import pathlib
import subprocess

import llvmlite.binding as llvm
from approvaltests.approvals import verify
from approvaltests.core.namer import Namer

from oymo.oymomo import banf_terms, banf_translate, grammar, llvm_prims, llvm_translate, printer


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


TARGET = llvm_translate.Target(triple='x86_64-unknown-linux-gnu', data_layout='', prims=llvm_prims.DEFAULT_PRIMS)
LANGUAGE_HEADER = 'language oymomo\n'


def compile_oymo(source: str) -> tuple[str, str, str]:
    """Returns the shaped oymomo source, the BANF and the LLVM IR text of an oymomo program."""
    assert source.startswith(LANGUAGE_HEADER)
    shaped = banf_translate.shape(grammar.parse(source.removeprefix(LANGUAGE_HEADER)))
    module = banf_translate.convert(shaped)
    ir_text = str(llvm_translate.translate(module, TARGET))
    llvm.parse_assembly(ir_text).verify()
    shaped_text = LANGUAGE_HEADER + printer.show(shaped, pretty=True) + '\n'
    return shaped_text, banf_terms.show(module), ir_text


def run_golden_test(test_name: str) -> None:
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    source = pathlib.Path(os.path.join(base_directory, f'{test_name}.oymo')).read_text()
    shaped_text, banf_text, ir_text = compile_oymo(source)
    verify(shaped_text, namer=ApprovalNamer(os.path.join(base_directory, f'{test_name}.shaped.oymo')))
    # The shaped source is itself a program that gives the same BANF.
    assert compile_oymo(shaped_text)[1] == banf_text
    verify(banf_text, namer=ApprovalNamer(os.path.join(base_directory, f'{test_name}.banf')))
    verify(ir_text, namer=ApprovalNamer(os.path.join(base_directory, f'{test_name}.ll')))


def test_goldens():
    run_golden_test('simplest')
