# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import io
import os
import pathlib
import subprocess

from approvaltests.approvals import verify
from approvaltests.core.namer import Namer

from tapl_lang.lib.compiler import compile_tapl


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


def run_golden_test(test_name: str, *, use_wrap: bool = False) -> None:
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    source = pathlib.Path(os.path.join(base_directory, f'{test_name}.tapl')).read_text()
    layers = compile_tapl(source)
    filenames = []

    for i in reversed(range(len(layers))):
        suffix = i if i else ''
        filename = f'{test_name}{suffix}.py'
        filenames.append(filename)
        filepath = os.path.join(base_directory, filename)
        verify(ast.unparse(layers[i]), namer=ApprovalNamer(filepath))
    if use_wrap:
        filenames = [f'{test_name}.wrap.py']
    run_python_files(base_directory, filenames, f'{test_name}.output')


def test_goldens():
    run_golden_test('grammar')
    run_golden_test('simple_function')
    run_golden_test('function_error', use_wrap=True)
    run_golden_test('simple_class')
    run_golden_test('importing')
    run_golden_test('sum')
    run_golden_test('collatz_conjecture')
    run_golden_test('type_constructions')
    run_golden_test('fibonacci')
