# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import os
import pathlib
from typing import cast

from approvaltests.approvals import verify
from approvaltests.core.namer import Namer

from tapl_lang.chunker import chunk_text
from tapl_lang.pythonlike import stmt
from tapl_lang.pythonlike.context import PythonlikeContext
from tapl_lang.syntax import Layers, LayerSeparator


class ApprovalNamer(Namer):
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def get_received_filename(self, base: str | None = None) -> str:
        del base
        return self.filename + Namer.RECEIVED

    def get_approved_filename(self, base: str | None = None) -> str:
        del base
        return self.filename


def parse_module(text: str) -> list[ast.AST]:
    chunks = chunk_text(text.strip())
    context = PythonlikeContext()
    module = stmt.Module()
    context.parse_chunks(chunks, [module])
    ls = LayerSeparator(2)
    separated = ls.separate(module)
    separated = ls.build(lambda layer: layer(separated))
    layers = cast(Layers, separated).layers
    return [layer.codegen_ast() for layer in layers]


def test_simple():
    base_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'goldens')
    base_path = os.path.join(base_directory, 'simple_function')
    source = pathlib.Path(os.path.join(base_directory, f'{base_path}.tapl')).read_text()
    parsed = parse_module(source)
    for i in range(len(parsed)):
        verify(ast.unparse(parsed[i]), namer=ApprovalNamer(f'{base_path}{i}.py'))
