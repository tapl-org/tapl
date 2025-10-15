# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
import re

from tapl_lang.core import chunker, syntax, tapl_error
from tapl_lang.lib import python_backend, terms2
from tapl_lang.pythonlike import language as python_language


def gather_errors(term: syntax.Term) -> list[syntax.ErrorTerm]:
    error_bucket: list[syntax.ErrorTerm] = []

    def gather_errors_recursive(t: syntax.Term) -> None:
        if isinstance(t, syntax.ErrorTerm):
            error_bucket.append(t)
        for child in t.children():
            gather_errors_recursive(child)

    gather_errors_recursive(term)
    return error_bucket


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


def make_safe_term(term: syntax.Term) -> syntax.Term:
    return syntax.BackendSettingTerm(
        backend_setting_changer=syntax.Layers(
            layers=[
                syntax.BackendSettingChanger(changer=lambda _: syntax.BackendSetting(scope_level=0)),
                syntax.BackendSettingChanger(changer=lambda _: syntax.BackendSetting(scope_level=0)),
            ]
        ),
        term=term,
    )


def compile_tapl(text: str) -> list[ast.AST]:
    chunks = chunker.chunk_text(text)
    language_name = extract_language(chunks[0])
    # TODO: "language" must be linked dynamically
    if language_name != 'pythonlike':
        raise tapl_error.TaplError('Only pythonlike language is supported now.')
    language = python_language.PythonlikeLanguage()
    predef_headers = language.get_predef_headers()
    predef_layers = syntax.Layers(predef_headers)
    module = terms2.Module(body=[predef_layers, syntax.TermList(terms=[], is_placeholder=True)])
    language.parse_chunks(chunks[1:], [module])
    error_bucket: list[syntax.ErrorTerm] = gather_errors(module)
    if error_bucket:
        messages = [repr(e) for e in error_bucket]
        raise tapl_error.TaplError(f'{len(error_bucket)} parsing error(s) found:\n\n' + '\n\n'.join(messages))
    safe_module = make_safe_term(module)
    ls = syntax.LayerSeparator(len(predef_layers.layers))
    layers = ls.build(lambda layer: layer(safe_module))
    return [python_backend.generate_ast(layer, syntax.BackendSetting(scope_level=0)) for layer in layers]
