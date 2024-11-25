# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.parser import LineRecord, split_text_to_lines


class Chunk:
    def __init__(self, line_records: list[LineRecord], children: list['Chunk']) -> None:
        if len(line_records) > 0:
            raise RuntimeError('Empty line records')
        self.lines = line_records
        self.children = children


def min_indentation(lines: list[LineRecord]) -> int | None:
    min_indent = None
    for line in lines:
        if line.empty:
            continue
        if min_indent is None:
            min_indent = line.indent
        else:
            min_indent = min(min_indent, line.indent)
    return min_indent


def get_same_indent_line_numbers(lines: list[LineRecord], indent: int) -> list[int]:
    result = [i for i in range(len(lines)) if lines[i].indent == indent]
    if len(result) > 0 and all(lines[i].empty for i in range(result[0])):
        raise RuntimeError('Empty lines while getting same indent line numbers')
    return result


def find_first_ends_with_colon(lines: list[LineRecord]) -> int | None:
    for i in range(len(lines)):
        line = lines[i]
        if line.ends_with_colon:
            return i
    return None


class Chunker:
    def decode_chunk(self, lines: list[LineRecord]) -> Chunk:
        index = find_first_ends_with_colon(lines)
        if index is not None:
            children_start_index = index + 1
            children = self.decode_chunks(lines[children_start_index:])
            return Chunk(lines[:children_start_index], children)
        return Chunk(lines, [])

    def decode_chunks(self, lines: list[LineRecord]) -> list[Chunk]:
        min_indent = min_indentation(lines)
        if min_indent is None:
            return []
        indexes = get_same_indent_line_numbers(lines, min_indent)
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
    return Chunker().decode_chunks(split_text_to_lines(text))
