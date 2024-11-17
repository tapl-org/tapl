# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import io
from tapl_lang import chunker


class Dumper:

    def __init__(self) -> None:
        self.ss = io.StringIO()

    def print_line(self, line: chunker.Line) -> None:
        indent = line.indent if not line.empty else 'E'
        prefix = f'{line.lineno}:{indent}'
        prefix = prefix.ljust(5)
        self.ss.write(f'{prefix}|{line.text}\n')

    def print_chunk(self, chunk: chunker.Chunk) -> None:
        indent = chunk.lines[0].indent
        self.ss.write(f'{indent}:'.rjust(6))
        self.ss.write(' ' * (indent or 0))
        self.ss.write(
            f'chunk lines={len(chunk.lines)} children={len(chunk.children)}\n')
        for line in chunk.lines:
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
    print(dump)
    assert dump.strip() == expected.strip()


def test_decode_chunk1():
    check(
        """
Hello
World
""",
        """
    0:chunk lines=1 children=0
1:0  |Hello
    0:chunk lines=1 children=0
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
    0:chunk lines=2 children=0
1:0  |Hello
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
    0:chunk lines=2 children=0
1:0  |Hello
2:1  | World
    0:chunk lines=3 children=0
3:0  |One
4:4  |    two
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
    0:chunk lines=1 children=1
1:0  |Hello:
    1: chunk lines=1 children=0
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
    0:chunk lines=1 children=2
1:0  |def compute_next(n):
    2:  chunk lines=1 children=2
2:2  |  if n % 2 == 0:
    4:    chunk lines=1 children=0
3:4  |    print('even')
    4:    chunk lines=1 children=0
4:4  |    return n / 2
    2:  chunk lines=1 children=2
5:2  |  else:
    4:    chunk lines=1 children=0
6:4  |    print('odd')
    4:    chunk lines=1 children=0
7:4  |    return 3 * n + 1
""",
    )
