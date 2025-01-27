# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import os
import pathlib

from approvaltests.approvals import verify
from approvaltests.core.namer import Namer

from tapl_lang.compiler import compile_tapl


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
    for i in range(len(layers)):
        verify(ast.unparse(layers[i]), namer=ApprovalNamer(f'{base_path}{i}.py'))
