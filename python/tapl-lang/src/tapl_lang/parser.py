# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import enum
import io
import logging
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from tapl_lang.line_record import LineRecord, split_text_to_lines
from tapl_lang.syntax import ErrorTerm, Location, Position, Term
from tapl_lang.tapl_error import TaplError

# Implemented PEG parser - https://en.wikipedia.org/wiki/Parsing_expression_grammar,
# https://pdos.csail.mit.edu/~baford/packrat/thesis/
# Left recursion: https://web.cs.ucla.edu/~todd/research/pepm08.pdf
# Error Detection taken from - https://arxiv.org/abs/1806.11150


ParseFunction = Callable[['Cursor'], Term]
OrderedParseFunctions = list[ParseFunction]
GrammarRuleMap = dict[str, OrderedParseFunctions]


@dataclass
class Grammar:
    rule_map: GrammarRuleMap
    start_rule: str


def route(rule: str) -> ParseFunction:
    def parse(c: 'Cursor') -> Term:
        return c.consume_rule(rule)

    return parse


class Cursor:
    def __init__(self, row: int, col: int, engine: 'PegEngine') -> None:
        self.row = row
        self.col = col
        self.engine = engine

    def clone(self) -> 'Cursor':
        return Cursor(self.row, self.col, self.engine)

    def copy_from(self, other: 'Cursor') -> None:
        if self.engine is not other.engine:
            raise TaplError('Both cursors do not have a same engine instance.')
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

    def consume_rule(self, rule) -> Term:
        term, self.row, self.col = self.engine.apply_rule(rule, self.row, self.col)
        return term

    def start_tracker(self) -> 'Tracker':
        return Tracker(self)


class ParseFailedTerm(Term):
    def __repr__(self):
        return 'ParseFailed'


ParseFailed = ParseFailedTerm()


# Note: Tracker should not be passed between functions; use them only within its originating function. Cursor, however, can be passed between functions. This distinction is by design.
class Tracker:
    def __init__(self, cursor: Cursor) -> None:
        self.cursor = cursor
        self.start_position = cursor.current_position()
        self.captured_error: ErrorTerm | None = None

    @property
    def location(self):
        return Location(start=self.start_position, end=self.cursor.current_position())

    def fail(self):
        return self.captured_error or ParseFailed

    def validate(self, term: Term) -> bool:
        if self.captured_error:
            return False
        if isinstance(term, ErrorTerm):
            self.captured_error = term
            return False
        if term and term is not ParseFailed:
            return True
        return False


class CellState(enum.IntEnum):
    BLANK = 1
    START = 2
    DONE = 3


@dataclass(frozen=True)
class CellKey:
    row: int
    col: int
    rule: str

    def __repr__(self) -> str:
        return f'{self.row}:{self.col}:{self.rule}'


@dataclass
class Cell:
    next_row: int
    next_col: int
    growable: bool = False
    state: CellState = CellState.BLANK
    term: Term = ParseFailed


CellMemo = dict[CellKey, Cell]


class PegEngine:
    def __init__(self, line_records: list[LineRecord], grammar_rule_map: GrammarRuleMap):
        self.line_records = line_records
        self.grammar_rule_map = grammar_rule_map
        self.cell_memo: CellMemo = {}

    def get_ordered_parse_functions(self, rule: str) -> OrderedParseFunctions:
        functions = self.grammar_rule_map.get(rule)
        if functions:
            return functions
        raise TaplError(f'Rule "{rule}" is not defined in Grammar.')

    def call_ordered_parse_functions(
        self, functions: OrderedParseFunctions, row: int, col: int
    ) -> tuple[Term, int, int]:
        for i in range(len(functions)):
            cursor = Cursor(row, col, engine=self)
            term = functions[i](cursor)
            if term is None:
                location = Location(
                    start=Cursor(row, col, engine=self).current_position(), end=cursor.current_position()
                )
                term = ErrorTerm(location, message=f'PEG Parser: {functions[i].__name__} returns None')
            if term is not ParseFailed:
                return term, cursor.row, cursor.col
        return ParseFailed, row, col

    def grow_seed(self, functions: OrderedParseFunctions, row: int, col: int, cell: Cell) -> None:
        seed_next_row, seed_next_col = cell.next_row, cell.next_col
        while True:
            term, next_row, next_col = self.call_ordered_parse_functions(functions, row, col)
            if isinstance(term, ErrorTerm) or term is ParseFailed:
                logging.warning(self.dump())
                raise TaplError(f'Once rule was successfull, then it has to be successful again. {term}.')
            # Stop growing when the new next position mathches seed's next position, as this indicates a cycle.
            if next_row == seed_next_row and next_col == seed_next_col:
                break
            cell.term, cell.next_row, cell.next_col = term, next_row, next_col

    def apply_rule(self, rule: str, row: int, col: int) -> tuple[Term, int, int]:
        cell_key = CellKey(row, col, rule)
        cell = self.cell_memo.get(cell_key)
        if not cell:
            cell = Cell(next_row=cell_key.row, next_col=cell_key.col)
            self.cell_memo[cell_key] = cell
        match cell.state:
            case CellState.BLANK:
                cell.state = CellState.START
                parse_functions = self.get_ordered_parse_functions(rule)
                cell.term, cell.next_row, cell.next_col = self.call_ordered_parse_functions(parse_functions, row, col)
                cell.state = CellState.DONE
                if cell.growable and not isinstance(cell.term, ErrorTerm) and cell.term is not ParseFailed:
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

    def dump(self) -> str:
        return 'Use PegEngineDebug to get the engine dump.'


@dataclass
class FunctionCall:
    function_index: int
    rule_calls: list['RuleCallNode'] = dataclass_field(default_factory=list)


@dataclass
class RuleCallNode:
    rule: str
    row: int
    col: int
    next_row: int
    next_col: int
    function_calls: list[FunctionCall] = dataclass_field(default_factory=list)
    status: str = 'empty'


class PegEngineDebug(PegEngine):
    def __init__(self, line_records: list[LineRecord], grammar_rule_map: GrammarRuleMap):
        super().__init__(line_records, grammar_rule_map)
        self.rule_call_stack = [RuleCallNode('_root_', 0, 0, 0, 0, [FunctionCall(0)])]

    def wrap_rule_function(self, function_index: int, function: ParseFunction) -> ParseFunction:
        def rule_function(c: Cursor) -> Term:
            self.rule_call_stack[-1].function_calls.append(FunctionCall(function_index))
            return function(c)

        return rule_function

    def get_ordered_parse_functions(self, rule: str) -> OrderedParseFunctions:
        functions = super().get_ordered_parse_functions(rule)
        result = []
        for i, function in enumerate(functions):
            result.append(self.wrap_rule_function(i, function))
        return result

    def apply_rule(self, rule: str, row: int, col: int) -> tuple[Term, int, int]:
        node = RuleCallNode(rule, row, col, row, col)
        self.rule_call_stack[-1].function_calls[-1].rule_calls.append(node)
        self.rule_call_stack.append(node)
        term, node.next_row, node.next_col = super().apply_rule(rule, row, col)
        self.rule_call_stack.pop()
        if term is None:
            node.status = 'none'
        elif term is ParseFailed:
            node.status = 'fail'
        elif isinstance(term, ErrorTerm):
            node.status = str(term)
        else:
            node.status = 'success'
        return term, node.next_row, node.next_col

    def dump(self) -> str:
        output = io.StringIO()
        output.write('\nPEG Engine Dump')
        # Print line records
        max_len = max(len(line.text) for line in self.line_records)
        output.write('\n  ')
        for i in range(max_len):
            output.write(str(i % 10))
        output.write('\n')
        for i, line in enumerate(self.line_records):
            output.write(f'{i%10}|')
            output.write(line.text)

        output.write('\n\n')

        # Print call tree
        def print_tree(node: RuleCallNode, indent: str = '', prefix: str = ''):
            output.write(
                f'{prefix or indent}{node.rule} {node.row}:{node.col}-{node.next_row}:{node.next_col} {node.status}\n'
            )
            child_indent = indent + '    '
            for call in node.function_calls:
                prefix = f'{indent} {call.function_index}) '
                for rule_call in call.rule_calls:
                    print_tree(rule_call, child_indent, prefix)
                    prefix = ''

        for node in self.rule_call_stack:
            print_tree(node)

        return output.getvalue()


def find_first_position(line_records: list[LineRecord]) -> tuple[int, int]:
    for row in range(len(line_records)):
        for col in range(len(line_records[row].text)):
            return row, col
    return len(line_records), 0


def parse_line_records(line_records: list[LineRecord], grammar: Grammar, *, debug: bool = False) -> Term:
    engine = PegEngineDebug(line_records, grammar.rule_map) if debug else PegEngine(line_records, grammar.rule_map)
    row, col = find_first_position(line_records)
    if row == len(line_records) and col == 0:
        return ErrorTerm(Location(start=Position(line=1, column=1)), message='Empty text.')
    term, next_row, next_col = engine.apply_rule(grammar.start_rule, row, col)
    if debug:
        logging.warning(engine.dump())
    if (
        not isinstance(term, ErrorTerm)
        and term is not ParseFailed
        and not (next_row == len(line_records) and next_col == 0)
    ):
        start_pos = Position(line_records[next_row].line_number, next_col + 1)
        return ErrorTerm(
            Location(start=start_pos),
            message=f'Not all text consumed: indices {next_row}:{next_col}/{len(line_records)}:0.',
        )
    return term


def parse_text(text: str, grammar: Grammar, *, debug: bool = False) -> Term:
    return parse_line_records(split_text_to_lines(text), grammar, debug=debug)
