# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import io

from tapl_lang.core import chunker, line_record


class Dumper:
    def __init__(self) -> None:
        self.ss = io.StringIO()

    def print_line(self, line_record: line_record.LineRecord) -> None:
        indent = line_record.indent if not line_record.empty else 'E'
        prefix = f'{line_record.line_number}:{indent}'
        prefix = prefix.ljust(5)
        escaped_text = line_record.text.encode('unicode_escape').decode('utf-8')
        self.ss.write(f'{prefix}|{escaped_text}\n')

    def print_chunk(self, chunk: chunker.Chunk) -> None:
        indent = chunk.line_records[0].indent
        self.ss.write(f'{indent}:'.rjust(6))
        self.ss.write(' ' * (indent or 0))
        self.ss.write(f'chunk line_records_length={len(chunk.line_records)} children_length={len(chunk.children)}\n')
        for line in chunk.line_records:
            self.print_line(line)
        self.print_chunks(chunk.children)

    def print_chunks(self, chunks: list[chunker.Chunk]) -> None:
        for chunk in chunks:
            self.print_chunk(chunk)


def get_dump(chunks: list[chunker.Chunk]) -> str:
    dumper = Dumper()
    dumper.print_chunks(chunks)
    return dumper.ss.getvalue()
