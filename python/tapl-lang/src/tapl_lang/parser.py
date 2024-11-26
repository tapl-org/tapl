# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import enum
import logging
from collections.abc import Callable

from tapl_lang.line_record import LineRecord, split_text_to_lines
from tapl_lang.syntax import ErrorTerm, Position, Term, TermInfo
from tapl_lang.tapl_error import TaplError

# Implemented PEG parser - https://en.wikipedia.org/wiki/Parsing_expression_grammar,
# Error Detection taken from - https://arxiv.org/abs/1806.11150


class Cursor:
    def __init__(self, row: int, col: int, engine: 'PegEngine') -> None:
        self.row = row
        self.col = col
        self.engine = engine

    def clone(self) -> 'Cursor':
        return Cursor(self.row, self.col, self.engine)

    def copy_from(self, other: 'Cursor') -> None:
        if self.engine is not other.engine:
            raise TaplError('Other engine does not have a same engine instance.')
        self.row = other.row
        self.col = other.col

    def assert_position(self) -> None:
        if not (0 <= self.row < len(self.engine.line_records)):
            raise TaplError('Cursor row is out of range.')
        if not (0 <= self.col < len(self.engine.line_records[self.row].text)):
            raise TaplError('Cursor col is out of range.')

    def current_char(self) -> str:
        self.assert_position()
        return self.engine.line_records[self.row].text[self.col]

    def is_end(self) -> bool:
        if self.row == len(self.engine.line_records):
            if self.col != 0:
                raise TaplError('When cursor ends, col must be 0.')
            return True
        self.assert_position()
        return False

    def current_position(self) -> Position:
        if self.is_end():
            return Position(self.engine.line_records[self.row - 1].line_number + 1, 0)
        self.assert_position()
        return Position(self.engine.line_records[self.row].line_number, self.col + 1)

    def move_to_next(self) -> bool:
        if self.is_end():
            return False
        self.col += 1
        if self.col == len(self.engine.line_records[self.row].text):
            self.row += 1
            self.col = 0
        return True

    def apply_rule(self, rule) -> Term | None:
        term, self.row, self.col = self.engine.apply_rule(rule, self.row, self.col)
        return term


ParseFunction = Callable[[Cursor], Term | None]
OrderedParseFunctions = list[ParseFunction]
GrammarRuleMap = dict[str, OrderedParseFunctions]


class CellState(enum.IntEnum):
    BLANK = 1
    START = 2
    DONE = 3


class Cell:
    def __init__(self, next_row: int, next_col: int) -> None:
        self.state: CellState = CellState.BLANK
        self.growable: bool = False
        self.next_row: int = next_row
        self.next_col: int = next_col
        self.term: Term | None = None

    def __repr__(self) -> str:
        state = '' if self.state == CellState.DONE else f'state={self.state.value} '
        growable_text = 'G ' if self.growable else ''
        term_name = self.term.__class__.__name__ if self.term else 'None'
        return f'{state}{growable_text}{self.next_row}:{self.next_col}-{term_name}'


class PegEngine:
    def __init__(self, line_records: list[LineRecord], grammar_rule_map: GrammarRuleMap):
        self.line_records = line_records
        self.grammar_rule_map = grammar_rule_map
        # (rule, row, col) -> Cell
        self.cell_memo: dict[tuple[str, int, int], Cell] = {}
        # hack: a rule apply limit to avoid infinite loop
        self.apply_rule_limit = 10000

    def get_ordered_parse_functions(self, rule: str) -> OrderedParseFunctions:
        functions = self.grammar_rule_map.get(rule)
        if functions:
            return functions
        raise TaplError(f'Missing or empty OrderedParseFunctions for rule "{rule}".')

    def call_ordered_parse_functions(
        self, functions: OrderedParseFunctions, row: int, col: int
    ) -> tuple[Term | None, int, int]:
        for function in functions:
            cursor = Cursor(row, col, engine=self)
            term = function(cursor)
            if term is not None:
                return term, cursor.row, cursor.col
        return None, row, col

    def grow_seed(self, functions: OrderedParseFunctions, row: int, col: int, cell: Cell) -> None:
        seed_next_row, seed_next_col = cell.next_row, cell.next_col
        while True:
            term, next_row, next_col = self.call_ordered_parse_functions(functions, row, col)
            if not term:
                raise TaplError(f'Once rule was successfull, then it has to be successful again. {term}.')
            # Stop growing when the new next position mathches seed's next position, as this indicates a cycle.
            if next_row == seed_next_row and next_col == seed_next_col:
                break
            cell.term, cell.next_row, cell.next_col = term, next_row, next_col

    def apply_rule(self, rule: str, row: int, col: int) -> tuple[Term | None, int, int]:
        self.apply_rule_limit -= 1
        if self.apply_rule_limit < 0:
            raise TaplError('apply_rule_limit exceeded.')
        memo_key = (rule, row, col)
        cell = self.cell_memo.get(memo_key)
        if not cell:
            cell = Cell(row, col)
            self.cell_memo[memo_key] = cell
        match cell.state:
            case CellState.BLANK:
                cell.state = CellState.START
                parse_functions = self.get_ordered_parse_functions(rule)
                cell.term, cell.next_row, cell.next_col = self.call_ordered_parse_functions(parse_functions, row, col)
                cell.state = CellState.DONE
                if cell.growable and cell.term:
                    self.grow_seed(parse_functions, row, col, cell)
            case CellState.START:
                # Left recursion detected. Delaying expansion of this rule.
                cell.growable = True
            case CellState.DONE:
                # Rule already parsed at this position, so no further action is required.
                pass
            case _:
                raise TaplError(f'PEG Parser Engine: Unknown cell state [{cell.state}].')
        return cell.term, cell.next_row, cell.next_col


def find_first_position(line_records: list[LineRecord]) -> tuple[int, int]:
    for row in range(len(line_records)):
        for col in range(len(line_records[row].text)):
            return row, col
    return len(line_records), 0


def parse_lines(
    line_records: list[LineRecord], grammar_rule_map: GrammarRuleMap, initial_rule: str, *, log_cell_memo: bool = False
) -> Term | None:
    engine = PegEngine(line_records, grammar_rule_map)
    row, col = find_first_position(line_records)
    if row == len(line_records) and col == 0:
        return ErrorTerm(TermInfo(start=Position(line=1, column=1)), message='Empty text.')
    term, next_row, next_col = engine.apply_rule(initial_rule, row, col)
    if log_cell_memo:
        logging.warning(engine.cell_memo)
    if term and next_row != len(line_records) and next_col != 0:
        start_pos = Position(line_records[next_row].line_number, next_col + 1)
        return ErrorTerm(
            TermInfo(start=start_pos),
            message=f'Not all text consumed {start_pos.line}:{start_pos.column}/{len(line_records)+1}:1.',
        )
    return term


def parse_text(text: str, rule_maps: GrammarRuleMap, initial_rule: str, *, log_cell_memo: bool = False) -> Term | None:
    return parse_lines(split_text_to_lines(text), rule_maps, initial_rule, log_cell_memo=log_cell_memo)
