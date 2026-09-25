# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

import dataclasses
import enum
import logging
from collections.abc import Callable, Iterable

from oymo.core import line_record, syntax, tapl_error

logger = logging.getLogger(__name__)

# Implemented PEG parser - https://en.wikipedia.org/wiki/Parsing_expression_grammar,
# https://pdos.csail.mit.edu/~baford/packrat/thesis/
# Left recursion: https://web.cs.ucla.edu/~todd/research/pepm08.pdf
# Error Detection taken from - https://arxiv.org/abs/1806.11150


ParseFunction = Callable[['Cursor'], syntax.Term]
OrderedParseFunctions = Iterable[ParseFunction | str]
GrammarRuleMap = dict[str, OrderedParseFunctions]


@dataclasses.dataclass(frozen=True)
class Grammar:
    rule_map: GrammarRuleMap
    start_rule: str

    def clone(self) -> Grammar:
        return Grammar(self.rule_map.copy(), self.start_rule)


def parse_function_name(function: ParseFunction | str) -> str:
    if isinstance(function, str):
        return f'|>{function}'
    return f'@{function.__name__}'


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


ParseFailed = syntax.ErrorTerm(message='Parsing failed: Unable to match any rule.')


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


class CellState(enum.IntEnum):
    BLANK = 1
    START = 2
    DONE = 3


@dataclasses.dataclass(frozen=True)
class CellKey:
    row: int
    col: int
    rule: str


@dataclasses.dataclass
class Cell:
    next_row: int
    next_col: int
    growable: bool
    state: CellState
    term: syntax.Term


CellMemo = dict[CellKey, Cell]


class PegEngine:
    def __init__(self, line_records: list[line_record.LineRecord], grammar_rule_map: GrammarRuleMap):
        self.line_records = line_records
        self.grammar_rule_map = grammar_rule_map
        self.cell_memo: CellMemo = {}
        # Set a call stack limit to prevent infinite recursion in rule applications
        self.rule_call_stack_limit = 1000

    def call_parse_function(
        self, key: CellKey, function: ParseFunction | str, config: Config
    ) -> tuple[syntax.Term, int, int]:
        cursor = Cursor(key.row, key.col, config=config, engine=self)

        def create_location() -> syntax.Location:
            start_cursor = Cursor(key.row, key.col, config=config, engine=self)
            return syntax.Location(start=start_cursor.current_position(), end=cursor.current_position())

        def route(rule: str) -> ParseFunction:
            def parse(c: Cursor) -> syntax.Term:
                return c.consume_rule(rule)

            return parse

        try:
            if isinstance(function, str):
                term = route(function)(cursor)
            else:
                term = function(cursor)
            if term is None:
                term = syntax.ErrorTerm(
                    message=f'PegEngine: rule={key.rule}:{parse_function_name(function)} returned None.',
                    location=create_location(),
                )
        except Exception as e:  # noqa: BLE001  The user provided function may raise any exception.
            term = syntax.ErrorTerm(
                message=f'PegEngine: rule={key.rule}:{parse_function_name(function)} error={e}',
                location=create_location(),
            )
        return term, cursor.row, cursor.col

    def call_ordered_parse_functions(self, key: CellKey, config: Config) -> tuple[syntax.Term, int, int]:
        functions = self.grammar_rule_map.get(key.rule)
        if not functions:
            raise tapl_error.TaplError(f'Rule "{key.rule}" is not defined in the Grammar.')
        for fn in functions:
            term, row, col = self.call_parse_function(key, fn, config=config)
            if term is not ParseFailed:
                return term, row, col
        return ParseFailed, key.row, key.col

    def start_rule(self, key: CellKey, cell: Cell, config: Config) -> None:
        cell.state = CellState.START
        cell.term, cell.next_row, cell.next_col = self.call_ordered_parse_functions(key, config)
        cell.state = CellState.DONE
        if cell.growable and not isinstance(cell.term, syntax.ErrorTerm):
            seed_next_row, seed_next_col = cell.next_row, cell.next_col
            iteration_count = 10  # Prevent infinite loop by limiting iterations
            while iteration_count > 0:
                iteration_count -= 1
                term, next_row, next_col = self.call_ordered_parse_functions(key, config)
                if term is ParseFailed:
                    cell.term = syntax.ErrorTerm(
                        message='PegEngine: Once ordered_parse_functions was successful, but it failed afterward. This indicates an inconsistency between ordered parse functions.'
                    )
                    return
                if isinstance(term, syntax.ErrorTerm):
                    cell.term = term
                    return
                # Stop growing when the new next position mathches seed's next position, as this indicates a cycle.
                if next_row == seed_next_row and next_col == seed_next_col:
                    return
                cell.term, cell.next_row, cell.next_col = term, next_row, next_col
            cell.term = syntax.ErrorTerm(message='PegEngine: Growing failed due to too many iterations.')

    def apply_rule(self, row: int, col: int, rule: str, config: Config) -> tuple[syntax.Term, int, int]:
        self.rule_call_stack_limit -= 1
        if self.rule_call_stack_limit < 0:
            error = syntax.ErrorTerm(message='PEG Parser: Rule application limit exceeded.')
            return (error, row, col)
        cell_key = CellKey(row, col, rule)
        cell = self.cell_memo.get(cell_key)
        if not cell:
            cell = Cell(
                next_row=cell_key.row, next_col=cell_key.col, growable=False, state=CellState.BLANK, term=ParseFailed
            )
            self.cell_memo[cell_key] = cell
        try:
            if cell.state == CellState.BLANK:
                self.start_rule(cell_key, cell, config)
                return cell.term, cell.next_row, cell.next_col

            if cell.state == CellState.START:
                # Left recursion detected. Delaying expansion of this rule.
                cell.growable = True
                return cell.term, cell.next_row, cell.next_col

            if cell.state == CellState.DONE:
                # Rule already parsed at this position, so no further action is required.
                return cell.term, cell.next_row, cell.next_col

            cell.term = syntax.ErrorTerm(f'PEG Parser Engine: Unknown cell state [{cell.state}] at {cell_key}.')
            return cell.term, cell.next_row, cell.next_col
        finally:
            self.rule_call_stack_limit += 1


def find_first_position(line_records: list[line_record.LineRecord]) -> tuple[int, int]:
    for row in range(len(line_records)):
        for col in range(len(line_records[row].text)):
            return row, col
    return len(line_records), 0


def parse_line_records(
    line_records: list[line_record.LineRecord], grammar: Grammar, *, debug: bool = False, config: Config | None = None
) -> syntax.Term:
    config = config or Config(mode=syntax.MODE_SAFE)
    engine = PegEngine(line_records, grammar.rule_map)
    row, col = find_first_position(line_records)
    if row == len(line_records) and col == 0:
        return syntax.ErrorTerm(message='Empty text.')
    term, next_row, next_col = engine.apply_rule(row, col, grammar.start_rule, config=config)
    if debug:
        logger.warning('Will print the engine dump soon.')
    if not isinstance(term, syntax.ErrorTerm) and not (next_row == len(line_records) and next_col == 0):
        lineno = line_records[0].line_number if line_records else -1
        return syntax.ErrorTerm(
            message=f'chunk[line:{lineno}] Not all text consumed: indices {next_row}:{next_col}/{len(line_records)}:0.',
        )
    return term


def parse_text(text: str, grammar: Grammar, *, debug: bool = False, config: Config | None = None) -> syntax.Term:
    return parse_line_records(line_record.split_text_to_lines(text), grammar, debug=debug, config=config)
