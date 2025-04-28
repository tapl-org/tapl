# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from abc import ABC, abstractmethod

from tapl_lang import parser, syntax
from tapl_lang.chunker import Chunk
from tapl_lang.tapl_error import TaplError


class Context(ABC):
    def parse_chunks(self, chunks: list[Chunk], parent_stack: list[syntax.Term]) -> None:
        body: syntax.TermList | None = self.find_delayed_body(parent_stack[-1])
        if body is None:
            raise TaplError('Delayed body not found.')
        for chunk in chunks:
            term = self.parse_chunk(chunk, parent_stack)
            body.terms.append(term)
        body.delayed = False

    def parse_chunk(self, chunk: Chunk, parent_stack: list[syntax.Term]) -> syntax.Term:
        grammar = self.get_grammar(parent_stack)
        term = parser.parse_line_records(chunk.line_records, grammar)
        if not isinstance(term, syntax.ErrorTerm) and chunk.children:
            parent_stack.append(term)
            try:
                self.parse_chunks(chunk.children, parent_stack)
            finally:
                parent_stack.pop()
        return term

    def find_delayed_body(self, term: syntax.Term) -> syntax.TermList | None:
        delayed_body: syntax.TermList | None = None

        def loop(t: syntax.Term) -> None:
            nonlocal delayed_body
            if isinstance(t, syntax.TermList) and t.delayed:
                if delayed_body is None:
                    delayed_body = t
                else:
                    raise TaplError('Multiple delayed blocks found.')
            for child in t.children():
                loop(child)

        loop(term)
        return delayed_body

    @abstractmethod
    def get_grammar(self, parent_stack: list[syntax.Term]) -> parser.Grammar:
        pass

    @abstractmethod
    def get_predef_layers(self) -> syntax.Layers:
        pass
