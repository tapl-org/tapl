# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from typing import Optional
from tapl_lang.syntax import Line, Term
from tapl_lang.parser import Parser, ParseResult


class Chunk:

    def __init__(self, lines: list[Line], children: list['Chunk']) -> None:
        assert len(lines) > 0
        self.lines = lines
        self.children = children


def min_indentation(lines: list[Line]) -> Optional[int]:
    min_indent = None
    for line in lines:
        if line.empty:
            continue
        if min_indent is None:
            min_indent = line.indent
        else:
            min_indent = min(min_indent, line.indent)
    return min_indent


def get_same_indent_lineno_list(lines: list[Line], indent: int) -> list[int]:
    result: list[int] = []
    for i in range(len(lines)):
        if lines[i].indent == indent:
            result.append(i)
    if len(result) > 0:
        assert all(lines[i].empty for i in range(result[0]))
    return result


def find_first_ends_with_colon(lines: list[Line]) -> Optional[int]:
    for i in range(len(lines)):
        line = lines[i]
        if line.empty:
            continue
        if line.text[-1] == ':':
            return i
    return None


class Chunker:

    def decode_chunk(self, lines: list[Line]) -> Chunk:
        index = find_first_ends_with_colon(lines)
        if index is not None:
            children_start_index = index + 1
            children = self.decode_chunks(lines[children_start_index:])
            return Chunk(lines[:children_start_index], children)
        else:
            return Chunk(lines, [])

    def decode_chunks(self, lines: list[Line]) -> list[Chunk]:
        min_indent = min_indentation(lines)
        if min_indent is None:
            return []
        indexes = get_same_indent_lineno_list(lines, min_indent)
        chunks: list[Chunk] = []
        for i in range(len(indexes)):
            start_index = indexes[i]
            if i + 1 < len(indexes):
                end_index = indexes[i + 1]
            else:
                end_index = len(lines)
            chunks.append(self.decode_chunk(lines[start_index:end_index]))
        return chunks


def chunk_text(text: str) -> list[Chunk]:
    text_lines = text.splitlines()
    lines = [Line(i + 1, text_lines[i]) for i in range(len(text_lines))]
    return Chunker().decode_chunks(lines)


class ChunkParser:

    def parse_chunks(self, parser: Parser, parent_term: Term, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            result = self.parse_chunk(parser, chunk)
            parent_term.append_to_body(result)
            parser = result.sibling_parser or parser
    
    def parse_chunk(self, parser: Parser, chunk: Chunk) -> None:
        result = parser.parse(chunk.lines)
        if chunk.children:
            self.parse_chunks(result.child_parser or parser, result.term, chunk.children)
        return result


def parse_text(text: str, parser: Parser, parent_term: Term) -> Term:
    chunks = chunk_text(text)
    result = ChunkParser().parse_chunks(parser, parent_term, chunks)