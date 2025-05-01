# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from tapl_lang.core import chunk_dumper, chunker


def check(text: str, expected: str) -> None:
    chunks = chunker.chunk_text(text.strip())
    dump = chunk_dumper.get_dump(chunks)
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
