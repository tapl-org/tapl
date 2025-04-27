# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from abc import ABC, abstractmethod

from tapl_lang import parser
from tapl_lang.chunker import Chunk
from tapl_lang.parser import Grammar
from tapl_lang.syntax import ErrorTerm, Layers, Term


class Context(ABC):
    def parse_chunks(self, chunks: list[Chunk], parent_stack: list[Term]) -> None:
        for chunk in chunks:
            self.parse_chunk(chunk, parent_stack)

    def parse_chunk(self, chunk: Chunk, parent_stack: list[Term]) -> None:
        grammar = self.get_grammar(parent_stack)
        term = parser.parse_line_records(chunk.line_records, grammar)
        if not isinstance(term, ErrorTerm) and chunk.children:
            parent_stack.append(term)
            self.parse_chunks(chunk.children, parent_stack)
            parent_stack.pop()
        parent_stack[-1].add_child(term)

    @abstractmethod
    def get_grammar(self, parent_stack: list[Term]) -> Grammar:
        pass

    @abstractmethod
    def get_predef_layers(self) -> Layers:
        pass
