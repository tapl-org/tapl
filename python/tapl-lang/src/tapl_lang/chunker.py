# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import io
from typing import Optional
from tapl_lang import syntax


def count_indentation(line: str) -> int:
    count = 0
    for char in line:
        if char == ' ':
            count += 1
        else:
            break
    return count


class Line:

    def __init__(self, lineno: int, text: str) -> None:
        self.lineno = lineno
        self.text = text
        self.empty: bool = all(char.isspace() for char in text)
        self.indent: Optional[int] = None
        if not self.empty:
            self.indent = count_indentation(text)


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


class ParseResult:

    def __init__(self, term: syntax.Term, child_parser: 'Parser',
                 sibling_parser: 'Parser') -> None:
        self.term = term
        self.child_parser = child_parser
        self.sibling_parser = sibling_parser


class Parser:

    def parse(self, lines: list[str],
              lineno_offset: int) -> Optional[ParseResult]:
        return None
