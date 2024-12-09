# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import enum
import io
import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass

from tapl_lang.line_record import LineRecord, split_text_to_lines
from tapl_lang.syntax import ErrorTerm, Location, Position, Term
from tapl_lang.tapl_error import TaplError

# Implemented PEG parser - https://en.wikipedia.org/wiki/Parsing_expression_grammar,
# https://pdos.csail.mit.edu/~baford/packrat/thesis/
# Left recursion: https://web.cs.ucla.edu/~todd/research/pepm08.pdf
# Error Detection taken from - https://arxiv.org/abs/1806.11150


class Cursor:
    def __init__(self, row: int, col: int, engine: 'PegEngine') -> None:
        self.row = row
        self.col = col
        self.engine = engine
        self.start_position: Position | None = None

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

    def move_to_next(self) -> bool:
        if self.is_end():
            return False
        self.col += 1
        if self.col == len(self.engine.line_records[self.row].text):
            self.row += 1
            self.col = 0
        return True

    def current_position(self) -> Position:
        if self.is_end():
            line_record = self.engine.line_records[self.row - 1]
            return Position(line_record.line_number, len(line_record.text))
        self.assert_position()
        return Position(self.engine.line_records[self.row].line_number, self.col)

    def mark_start_position(self) -> None:
        self.start_position = self.current_position()

    @property
    def location(self):
        if self.start_position is None:
            raise TaplError('The start position is not marked.')
        return Location(start=self.start_position, end=self.current_position())

    def consume_rule(self, rule) -> Term | None:
        term, self.row, self.col = self.engine.apply_rule(rule, self.row, self.col)
        return term

    def expect_rule(self, rule: str) -> Term | None:
        self.mark_start_position()
        term = self.consume_rule(rule)
        if term is not None:
            return term
        return ErrorTerm(self.location, f'Expected rule "{rule}"')


ParseFunction = Callable[[Cursor], Term | None]
OrderedParseFunctions = list[ParseFunction]
GrammarRuleMap = dict[str, OrderedParseFunctions]


@dataclass
class Grammar:
    rule_map: GrammarRuleMap
    start_rule: str


def first_falsy(*args):
    """Returns the first falsy value from a list of arguments."""
    return next((arg for arg in args if not arg), None)


def route(rule: str) -> ParseFunction:
    def parse(c: Cursor) -> Term | None:
        return c.consume_rule(rule)

    return parse


def skip_whitespaces(c: Cursor) -> None:
    while not c.is_end() and c.current_char().isspace():
        c.move_to_next()


class CellState(enum.IntEnum):
    BLANK = 1
    START = 2
    DONE = 3


@dataclass(frozen=True)
class CellKey:
    row: int
    col: int
    rule: str


@dataclass
class Cell:
    next_row: int
    next_col: int
    creation_order: int
    growable: bool = False
    state: CellState = CellState.BLANK
    term: Term | None = None
    rule_function_index: int | None = None


CellMemo = dict[CellKey, Cell]
APPLY_RULE_ORDER_LIMIT = 10000


class PegEngine:
    def __init__(self, line_records: list[LineRecord], grammar_rule_map: GrammarRuleMap):
        self.line_records = line_records
        self.grammar_rule_map = grammar_rule_map
        self.cell_memo: CellMemo = {}
        self.apply_rule_order = 0

    def get_ordered_parse_functions(self, rule: str) -> OrderedParseFunctions:
        functions = self.grammar_rule_map.get(rule)
        if functions:
            return functions
        raise TaplError(f'Missing or empty OrderedParseFunctions for rule "{rule}".')

    def call_ordered_parse_functions(
        self, functions: OrderedParseFunctions, row: int, col: int
    ) -> tuple[Term | None, int, int, int | None]:
        for i in range(len(functions)):
            cursor = Cursor(row, col, engine=self)
            term = functions[i](cursor)
            if term is not None:
                return term, cursor.row, cursor.col, i
        return None, row, col, None

    def grow_seed(self, functions: OrderedParseFunctions, row: int, col: int, cell: Cell) -> None:
        seed_next_row, seed_next_col = cell.next_row, cell.next_col
        while True:
            term, next_row, next_col, func_index = self.call_ordered_parse_functions(functions, row, col)
            if not term:
                raise TaplError(f'Once rule was successfull, then it has to be successful again. {term}.')
            # Stop growing when the new next position mathches seed's next position, as this indicates a cycle.
            if next_row == seed_next_row and next_col == seed_next_col:
                break
            cell.term, cell.next_row, cell.next_col = term, next_row, next_col
            cell.rule_function_index = func_index

    def apply_rule(self, rule: str, row: int, col: int) -> tuple[Term | None, int, int]:
        self.apply_rule_order += 1
        if self.apply_rule_order > APPLY_RULE_ORDER_LIMIT:
            raise TaplError(
                f'The parser has exceeded {APPLY_RULE_ORDER_LIMIT} rule applications. A hack to prevent or catch infinite recursion.'
            )
        cell_key = CellKey(row, col, rule)
        cell = self.cell_memo.get(cell_key)
        if not cell:
            cell = Cell(next_row=row, next_col=col, creation_order=self.apply_rule_order)
            self.cell_memo[cell_key] = cell
        match cell.state:
            case CellState.BLANK:
                cell.state = CellState.START
                parse_functions = self.get_ordered_parse_functions(rule)
                cell.term, cell.next_row, cell.next_col, cell.rule_function_index = self.call_ordered_parse_functions(
                    parse_functions, row, col
                )
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


def dump_cell_memo(cell_memo: CellMemo) -> str:
    output = io.StringIO()
    output.write('\n')
    sorted_cells = sorted(cell_memo.items(), key=lambda item: (item[0].row, item[0].col, item[1].creation_order))
    for (row, col), group in itertools.groupby(sorted_cells, key=lambda item: (item[0].row, item[0].col)):
        output.write(f'{row}:{col}\n')
        for item in group:
            cell = item[1]
            state = '' if cell.state == CellState.DONE else f'state={cell.state.value} '
            growable_text = 'G ' if cell.growable else ''
            term_class_name = cell.term  # .__class__.__name__
            output.write(
                f'   {item[0].rule}[{cell.rule_function_index}] - end={state}{growable_text}{cell.next_row}:{cell.next_col} term={term_class_name}\n'
            )
    output.write('\n')
    return output.getvalue()


def find_first_position(line_records: list[LineRecord]) -> tuple[int, int]:
    for row in range(len(line_records)):
        for col in range(len(line_records[row].text)):
            return row, col
    return len(line_records), 0


def parse_line_records(line_records: list[LineRecord], grammar: Grammar, *, log_cell_memo: bool = False) -> Term | None:
    engine = PegEngine(line_records, grammar.rule_map)
    row, col = find_first_position(line_records)
    if row == len(line_records) and col == 0:
        return ErrorTerm(Location(start=Position(line=1, column=1)), message='Empty text.')
    term, next_row, next_col = engine.apply_rule(grammar.start_rule, row, col)
    if log_cell_memo:
        logging.warning(dump_cell_memo(engine.cell_memo))
    if term and next_row != len(line_records) and next_col != 0:
        start_pos = Position(line_records[next_row].line_number, next_col + 1)
        return ErrorTerm(
            Location(start=start_pos),
            message=f'Not all text consumed {start_pos.line}:{start_pos.column}/{len(line_records)}:{len(line_records[-1].text)}.',
        )
    return term


def parse_text(text: str, grammar: Grammar, *, log_cell_memo: bool = False) -> Term | None:
    return parse_line_records(split_text_to_lines(text), grammar, log_cell_memo=log_cell_memo)
