# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import re

from tapl_lang.core import syntax
from tapl_lang.core.chunker import Chunk, chunk_text
from tapl_lang.core.tapl_error import TaplError
from tapl_lang.pythonlike import stmt
from tapl_lang.pythonlike.context import PythonlikeContext


def get_context_name(chunk: Chunk) -> str:
    if chunk.children:
        raise TaplError('Context clause chunk should not have children.')
    if len(chunk.line_records) != 1:
        raise TaplError('Context clause chunk should be one line.')
    pattern = r'^context ([a-zA-Z_][a-zA-Z0-9_]*)$'
    line = chunk.line_records[0].text
    match = re.findall(pattern, line)
    if not match:
        raise TaplError(f'Could not parse context clause[{line}]')
    return match[0]


def compile_tapl(text: str) -> list[ast.AST]:
    chunks = chunk_text(text)
    context_name = get_context_name(chunks[0])
    if context_name != 'pythonlike':
        raise TaplError('Only pythonlike context is supported now.')
    context = PythonlikeContext()
    predef_layers = context.get_predef_layers()
    body = syntax.Block([predef_layers], delayed=True)
    module = stmt.Module(body=body)
    context.parse_chunks(chunks[1:], [module])
    error_bucket: list[syntax.ErrorTerm] = syntax.gather_errors(module)
    if error_bucket:
        messages = [repr(e) for e in error_bucket]
        raise TaplError('\n\n'.join(messages))
    safe_module = syntax.make_safe_term(module)
    ls = syntax.LayerSeparator(len(predef_layers.layers))
    layers = ls.separate(safe_module)
    return [layer.codegen_ast(syntax.AstSetting()) for layer in layers]
