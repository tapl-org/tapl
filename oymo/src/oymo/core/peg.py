# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# References:
# Use PEG parser - https://en.wikipedia.org/wiki/Parsing_expression_grammar,
# https://pdos.csail.mit.edu/~baford/packrat/thesis/
# Left recursion: https://web.cs.ucla.edu/~todd/research/pepm08.pdf
# Error Detection - https://arxiv.org/abs/1806.11150
# The Squirrel Parser - https://arxiv.org/pdf/2601.05012
# https://www.jstage.jst.go.jp/article/ipsjjip/29/0/29_174/_pdf
# https://tratt.net/laurie/research/pubs/papers/tratt__direct_left_recursive_parsing_expression_grammars.pdf

from __future__ import annotations

from dataclasses import dataclass
import logging

from oymo.core import syntax

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class Match:
    term: syntax.Term
    row: int
    col: int
    next_row: int
    next_col: int


MISMATCH = Match(term=syntax.ErrorTerm(message='Parse mismatch.'), row=-1, col=-1, next_row=-1, next_col=-1)

@dataclass
class Clause:

    def match(self, c: Cursor) -> Match:
        del c
        raise NotImplementedError


@dataclass
class MemoEntry:
    match: Match
    in_progress: bool
    left_recursion_detected: bool
    version: int


class Parser:
    def __init__(self, line_records: list[line_record.LineRecord], grammar_rules: dict[str, Clause]) -> None:
        self.line_records = line_records
        self.grammar_rules = grammar_rules
        self.memo_table: dict[tuple[int, int, str], MemoEntry] = {}
        self.latest_version: dict[tuple[int, int], int] = {}
    
    def apply_rule(self, row: int, col: int, rule: str) -> Match:
        entry = self.memo_table.get((row, col, rule))
        if entry is None:
            entry = MemoEntry(match=MISMATCH, in_rec_path=False, in_left_rec_path=False, cycle_depth=-1)
            self.memo_table[(row, col, rule)] = entry
            self.latest_version[(row, col)] = 0
        if entry.version < self.latest_version[(row, col)]:
            self.process_rule(entry, row, col, self.grammar_rules[rule])
            entry.version = self.latest_version[(row, col)]
        return entry.match
    
    def apply_clause(self, entry: MemoEntry, row: int, col: int, clause: Clause) -> None:
        if entry.in_progress:
            entry.left_recursion_detected = True
        entry.in_progress = True
        while True:
            new_match = clause.match(Cursor(row, col, self))
            if new_match.next_row < entry.match.next_row or (new_match.next_row == entry.match.next_row and new_match.next_col <= entry.match.next_col):
                break
            entry.match = new_match
            if not entry.left_recursion_detected:
                break
            entry.version = self.latest_version[(row, col)]
            self.latest_version[(row, col)] += 1
        entry.in_progress = False




@dataclasses.dataclass
class Config:
    mode: syntax.Term


class Cursor:
    def __init__(self, row: int, col: int, config: Config, engine: PegEngine) -> None:
        self.row = row
        self.col = col
        self.config = config
        self.engine = engine

    def clone(self) -> Cursor:
        return Cursor(self.row, self.col, self.config, self.engine)

    def copy_position_from(self, other: Cursor) -> None:
        if self.engine is not other.engine:
            raise tapl_error.TaplError('Both cursors do not have a same engine instance.')
        self.row = other.row
        self.col = other.col

    def assert_position(self) -> None:
        if not (0 <= self.row < len(self.engine.line_records)):
            raise tapl_error.TaplError('Cursor row is out of range.')
        if not (0 <= self.col < len(self.engine.line_records[self.row].text)):
            raise tapl_error.TaplError('Cursor col is out of range.')

    def current_char(self) -> str:
        self.assert_position()
        return self.engine.line_records[self.row].text[self.col]

    def is_end(self) -> bool:
        if self.row == len(self.engine.line_records):
            if self.col != 0:
                raise tapl_error.TaplError('When cursor ends, col must be 0.')
            return True
        self.assert_position()
        return False

    def move_to_next(self) -> bool:
        if self.is_end():
            return False
        self.col += 1
        if self.col == len(self.engine.line_records[self.row].text):
            self.row += 1
            self.col = 0
        return True

    def current_position(self) -> syntax.Position:
        if self.is_end():
            line_record = self.engine.line_records[self.row - 1]
            return syntax.Position(line_record.line_number, len(line_record.text))
        self.assert_position()
        return syntax.Position(self.engine.line_records[self.row].line_number, self.col)

    def consume_rule(self, rule: str, config: Config | None = None) -> syntax.Term:
        term, self.row, self.col = self.engine.apply_rule(self.row, self.col, rule, config or self.config)
        return term

    def start_tracker(self) -> Tracker:
        return Tracker(self)

    def skip_whitespace(self) -> None:
        while not self.is_end() and self.current_char().isspace():
            self.move_to_next()

    def consume_text(self, text: str) -> bool:
        for char in text:
            if self.is_end() or self.current_char() != char:
                return False
            self.move_to_next()
        return True


ParseFailed = syntax.ErrorTerm(message='ParseFailed')


# Tracker is designed for use within its originating function only and should not be passed between functions.
# Cursor, on the other hand, can be passed freely between functions.
class Tracker:
    def __init__(self, cursor: Cursor) -> None:
        self.cursor = cursor
        self.start_position = cursor.current_position()
        self.captured_error: syntax.ErrorTerm | None = None

    @property
    def location(self):
        return syntax.Location(start=self.start_position, end=self.cursor.current_position())

    def fail(self):
        return self.captured_error or ParseFailed

    def validate(self, term: syntax.Term) -> bool:
        if self.captured_error:
            return False
        if term is ParseFailed:
            return False
        if isinstance(term, syntax.ErrorTerm):
            self.captured_error = term
            return False
        return term is not None