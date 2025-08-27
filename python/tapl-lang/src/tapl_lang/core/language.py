# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from abc import ABC, abstractmethod

from tapl_lang.core import aux_terms, chunker, parser, syntax, tapl_error


class Language(ABC):
    def parse_chunks(self, chunks: list[chunker.Chunk], parent_stack: list[syntax.Term]) -> None:
        body: list[syntax.Term] | None = parent_stack[-1].get_body()
        if body is None:
            # TODO: return an ErrorTerm
            raise tapl_error.TaplError(
                f'The top of parent_stack[{parent_stack[-1].__class__.__name__}] does not have a body to hold parsed terms.'
            )
        for chunk in chunks:
            term = self.parse_chunk(chunk, parent_stack)
            if isinstance(term, aux_terms.DependentTerm):
                term.merge_into(body)
            else:
                body.append(term)

    def parse_chunk(self, chunk: chunker.Chunk, parent_stack: list[syntax.Term]) -> syntax.Term:
        grammar = self.get_grammar(parent_stack)
        term = parser.parse_line_records(chunk.line_records, grammar)
        if not isinstance(term, syntax.ErrorTerm) and chunk.children:
            parent_stack.append(term)
            try:
                self.parse_chunks(chunk.children, parent_stack)
            finally:
                parent_stack.pop()
        return term

    @abstractmethod
    def get_grammar(self, parent_stack: list[syntax.Term]) -> parser.Grammar:
        """Returns the grammar for the language."""

    @abstractmethod
    def get_predef_headers(self) -> list[syntax.Term]:
        """Returns the list of each layer's predefined headers for the language."""
