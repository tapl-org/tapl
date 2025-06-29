# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import re

from tapl_lang.core import syntax
from tapl_lang.core.chunker import Chunk, chunk_text
from tapl_lang.core.tapl_error import TaplError
from tapl_lang.pythonlike import stmt
from tapl_lang.pythonlike.language import PythonlikeLanguage


def extract_language(chunk: Chunk) -> str:
    if chunk.children:
        raise TaplError('language clause chunk should not have children.')
    for i in range(1, len(chunk.line_records)):
        if not chunk.line_records[i].empty:
            raise TaplError('language clause chunk should be the first line.')
    pattern = r'^language ([a-zA-Z_][a-zA-Z0-9_]*)$'
    line = chunk.line_records[0].text
    match = re.findall(pattern, line)
    if not match:
        raise TaplError(f'Could not parse language clause[{line}]')
    return match[0]


def compile_tapl(text: str) -> list[ast.AST]:
    chunks = chunk_text(text)
    language_name = extract_language(chunks[0])
    # TODO: "language" must be linked dynamically
    if language_name != 'pythonlike':
        raise TaplError('Only pythonlike language is supported now.')
    language = PythonlikeLanguage()
    predef_layers = language.get_predef_layers()
    body = syntax.Block([predef_layers], delayed=True)
    module = stmt.Module(body=body)
    language.parse_chunks(chunks[1:], [module])
    error_bucket: list[syntax.ErrorTerm] = syntax.gather_errors(module)
    if error_bucket:
        messages = [repr(e) for e in error_bucket]
        raise TaplError(f'{len(error_bucket)} errors found:\n\n' + '\n\n'.join(messages))
    safe_module = syntax.make_safe_term(module)
    ls = syntax.LayerSeparator(len(predef_layers.layers))
    layers = ls.separate(safe_module)
    return [layer.codegen_ast(syntax.AstSetting()) for layer in layers]
