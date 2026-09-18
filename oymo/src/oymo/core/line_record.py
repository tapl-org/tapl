# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations


# Count the number of spaces at the beginning of the text.
def count_indentation(text: str) -> int:
    count = 0
    for char in text:
        if char == ' ':
            count += 1
        else:
            break
    return count


# True if the last non-whitespace character is ':'.
def ends_with_colon(text: str) -> bool:
    for char in reversed(text):
        if char.isspace():
            continue
        return char == ':'
    return False


class LineRecord:
    def __init__(self, line_number: int, text: str) -> None:
        self.line_number = line_number
        self.text = text
        self.empty: bool = all(char.isspace() for char in text)
        self.ends_with_colon: bool = ends_with_colon(text)
        self.indent: int | None = None
        if not self.empty:
            self.indent = count_indentation(text)

    def __repr__(self) -> str:
        return f'LineRecord(line_number={self.line_number}, indent={self.indent}, empty={self.empty}, ends_with_colon={self.ends_with_colon}, text={self.text!r})'


# True if the first non-whitespace character is '#'.
def is_comment_line(text: str) -> bool:
    for char in text:
        if char.isspace():
            continue
        return char == '#'
    return False


# Split text into lines and return a list of LineRecord objects.
def split_text_to_lines(text: str) -> list[LineRecord]:
    text_lines = text.splitlines(keepends=True)
    return [LineRecord(i + 1, text_lines[i]) for i in range(len(text_lines)) if not is_comment_line(text_lines[i])]
