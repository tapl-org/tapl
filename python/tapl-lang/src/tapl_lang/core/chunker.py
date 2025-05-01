# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from tapl_lang.core.parser import LineRecord, split_text_to_lines
from tapl_lang.core.tapl_error import TaplError


class Chunk:
    def __init__(self, line_records: list[LineRecord], children: list['Chunk']) -> None:
        self.line_records = line_records
        self.children = children


def min_indentation(line_records: list[LineRecord]) -> int | None:
    min_indent = None
    for line in line_records:
        if line.empty:
            continue
        if min_indent is None:
            min_indent = line.indent
        elif line.indent is not None:
            min_indent = min(min_indent, line.indent)
    return min_indent


def get_same_indent_indexes(line_records: list[LineRecord], indent: int) -> list[int]:
    result = [i for i in range(len(line_records)) if line_records[i].indent == indent]
    if len(result) > 0 and result[0] != 0:
        raise TaplError('First line should have the same indent as the given indent.')
    return result


def find_first_ends_with_colon(line_records: list[LineRecord]) -> int | None:
    for i in range(len(line_records)):
        if line_records[i].ends_with_colon:
            return i
    return None


# TODO: left strip white spaces in line_records based on the chunk indent
# TODO: right strip comments in line_records if # is not escaped
class Chunker:
    def decode_chunk(self, line_records: list[LineRecord]) -> Chunk:
        index = find_first_ends_with_colon(line_records)
        if index is not None:
            children_start_index = index + 1
            children = self.decode_chunks(line_records[children_start_index:])
            return Chunk(line_records[:children_start_index], children)
        return Chunk(line_records, [])

    def decode_chunks(self, line_records: list[LineRecord]) -> list[Chunk]:
        min_indent = min_indentation(line_records)
        # If all line records are empty
        if min_indent is None:
            return []
        indexes = get_same_indent_indexes(line_records, min_indent)
        chunks: list[Chunk] = []
        for i in range(len(indexes)):
            start_index = indexes[i]
            if i + 1 < len(indexes):
                end_index = indexes[i + 1]
            else:
                end_index = len(line_records)
            chunk = self.decode_chunk(line_records[start_index:end_index])
            chunks.append(chunk)
        return chunks


def chunk_text(text: str) -> list[Chunk]:
    return Chunker().decode_chunks(split_text_to_lines(text))
