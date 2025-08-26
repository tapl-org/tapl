# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from abc import ABC, abstractmethod

from tapl_lang.core import aux_terms, parser, syntax
from tapl_lang.core.chunker import Chunk
from tapl_lang.core.tapl_error import TaplError


class Language(ABC):
    def parse_chunks(self, chunks: list[Chunk], parent_stack: list[syntax.Term]) -> None:
        body: aux_terms.Block | None = aux_terms.find_delayed_block(parent_stack[-1])
        if body is None:
            # TODO: return an ErrorTerm
            raise TaplError('Delayed body not found.')
        for chunk in chunks:
            term = self.parse_chunk(chunk, parent_stack)
            if isinstance(term, aux_terms.DependentTerm):
                term.merge_into(body)
            else:
                body.terms.append(term)
        body.delayed = False

    def parse_chunk(self, chunk: Chunk, parent_stack: list[syntax.Term]) -> syntax.Term:
        grammar = self.get_grammar(parent_stack)
        term = parser.parse_line_records(chunk.line_records, grammar)
        if not isinstance(term, aux_terms.ErrorTerm) and chunk.children:
            parent_stack.append(term)
            try:
                self.parse_chunks(chunk.children, parent_stack)
            finally:
                parent_stack.pop()
        return term

    @abstractmethod
    def get_grammar(self, parent_stack: list[syntax.Term]) -> parser.Grammar:
        pass

    # TODO: return list of term instead of Layers
    @abstractmethod
    def get_predef_layers(self) -> aux_terms.Layers:
        pass
