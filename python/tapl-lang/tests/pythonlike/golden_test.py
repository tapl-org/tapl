# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import io
import os
import pathlib

from approvaltests.approvals import verify
from approvaltests.core.namer import Namer

from tapl_lang.compiler import compile_tapl


import subprocess

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
        check=False, # do not raise exception on non-zero return code.
    )
    return process.returncode, process.stdout, process.stderr
  except FileNotFoundError:
    return -1, "", f"Command not found: {command}"
  except Exception as e:
    return -1, "", f"An error occurred: {e}"


class ApprovalNamer(Namer):
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def get_received_filename(self, base: str | None = None) -> str:
        del base
        return self.filename + Namer.RECEIVED

    def get_approved_filename(self, base: str | None = None) -> str:
        del base
        return self.filename


def test_simple():
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    base_path = os.path.join(base_directory, 'simple_function')
    source = pathlib.Path(os.path.join(base_directory, f'{base_path}.tapl')).read_text()
    layers = compile_tapl(source)
    output = io.StringIO()
    success = True
    for i in reversed(range(len(layers))):
        filename = f'{base_path}{i}.py'
        verify(ast.unparse(layers[i]), namer=ApprovalNamer(filename))
        if success:
          returnCode, stdout, stderr = run_command(['python', filename])
          output.write(f'====== level={i} exit-status:{returnCode} stdout:\n')
          output.write(stdout)
          output.write(f'\n------ stderr:\n')
          output.write(stderr)
          output.write(f'\n------ end.\n\n')
          success = returnCode == 0
    verify(output.getvalue(), namer=ApprovalNamer(f'{base_path}.output'))
