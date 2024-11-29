# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import io

from tapl_lang import chunker, line_record


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


def check(text: str, expected: str) -> None:
    chunks = chunker.chunk_text(text.strip())
    dump = get_dump(chunks)
    assert dump.strip() == expected.strip()


def test_decode_chunk1():
    check(
        """
Hello
World
""",
        """
    0:chunk line_records_length=1 children_length=0
1:0  |Hello\\n
    0:chunk line_records_length=1 children_length=0
2:0  |World
""",
    )


def test_decode_chunk2():
    check(
        """
Hello
 World
""",
        """
    0:chunk line_records_length=2 children_length=0
1:0  |Hello\\n
2:1  | World
""",
    )


def test_decode_chunk3():
    check(
        """
Hello
 World
One
    two
  three
""",
        """
    0:chunk line_records_length=2 children_length=0
1:0  |Hello\\n
2:1  | World\\n
    0:chunk line_records_length=3 children_length=0
3:0  |One\\n
4:4  |    two\\n
5:2  |  three
""",
    )


def test_decode_chunk4():
    check(
        """
Hello:
 World
""",
        """
    0:chunk line_records_length=1 children_length=1
1:0  |Hello:\\n
    1: chunk line_records_length=1 children_length=0
2:1  | World
""",
    )


def test_decode_chunk5():
    check(
        """
def compute_next(n):
  if n % 2 == 0:
    print('even')
    return n / 2
  else:
    print('odd')
    return 3 * n + 1
""",
        """
    0:chunk line_records_length=1 children_length=2
1:0  |def compute_next(n):\\n
    2:  chunk line_records_length=1 children_length=2
2:2  |  if n % 2 == 0:\\n
    4:    chunk line_records_length=1 children_length=0
3:4  |    print('even')\\n
    4:    chunk line_records_length=1 children_length=0
4:4  |    return n / 2\\n
    2:  chunk line_records_length=1 children_length=2
5:2  |  else:\\n
    4:    chunk line_records_length=1 children_length=0
6:4  |    print('odd')\\n
    4:    chunk line_records_length=1 children_length=0
7:4  |    return 3 * n + 1
""",
    )
