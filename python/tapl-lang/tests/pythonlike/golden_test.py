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

from tapl_lang.core.compiler import compile_tapl


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


def run_golden_test(test_name: str) -> None:
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    base_path = os.path.join(base_directory, test_name)
    source = pathlib.Path(os.path.join(base_directory, f'{base_path}.tapl')).read_text()
    layers = compile_tapl(source)
    output = io.StringIO()
    success = True
    for i in reversed(range(len(layers))):
        suffix = i if i else ''
        filename = f'{base_path}{suffix}.py'
        verify(ast.unparse(layers[i]), namer=ApprovalNamer(filename))
        if success:
            return_code, stdout, stderr = run_command(['python', filename])
            output.write(f'====== layer={i} exit-status:{return_code} stdout:\n')
            output.write(stdout)
            output.write('\n------ stderr:\n')
            output.write(stderr)
            output.write('\n------ end.\n\n')
            success = return_code == 0
    verify(output.getvalue(), namer=ApprovalNamer(f'{base_path}.output'))


def test_simple_function():
    run_golden_test('simple_function')


def test_simple_class():
    run_golden_test('simple_class')
