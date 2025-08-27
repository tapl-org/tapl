# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import re

from tapl_lang.core import chunker, syntax, tapl_error
from tapl_lang.lib import aux_terms
from tapl_lang.pythonlike import language as python_language
from tapl_lang.pythonlike import stmt


def extract_language(chunk: chunker.Chunk) -> str:
    if chunk.children:
        raise tapl_error.TaplError('language clause chunk should not have children.')
    for i in range(1, len(chunk.line_records)):
        if not chunk.line_records[i].empty:
            raise tapl_error.TaplError('language clause chunk should be the first line.')
    pattern = r'^language ([a-zA-Z_][a-zA-Z0-9_]*)$'
    line = chunk.line_records[0].text
    match = re.findall(pattern, line)
    if not match:
        raise tapl_error.TaplError(f'Could not parse language clause[{line}]')
    return match[0]


def compile_tapl(text: str) -> list[ast.AST]:
    chunks = chunker.chunk_text(text)
    language_name = extract_language(chunks[0])
    # TODO: "language" must be linked dynamically
    if language_name != 'pythonlike':
        raise tapl_error.TaplError('Only pythonlike language is supported now.')
    language = python_language.PythonlikeLanguage()
    predef_headers = language.get_predef_headers()
    predef_layers = aux_terms.Layers(predef_headers)
    module = stmt.Module(body=[predef_layers])
    language.parse_chunks(chunks[1:], [module])
    error_bucket: list[syntax.ErrorTerm] = aux_terms.gather_errors(module)
    if error_bucket:
        messages = [repr(e) for e in error_bucket]
        raise tapl_error.TaplError(f'{len(error_bucket)} errors found:\n\n' + '\n\n'.join(messages))
    safe_module = aux_terms.make_safe_term(module)
    ls = syntax.LayerSeparator(len(predef_layers.layers))
    layers = ls.build(lambda layer: layer(safe_module))
    return [layer.codegen_ast(syntax.AstSetting()) for layer in layers]
