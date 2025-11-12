# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from __future__ import annotations

import enum
import io
import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from tapl_lang.core import line_record, syntax, tapl_error
from tapl_lang.lib import terms

# Implemented PEG parser - https://en.wikipedia.org/wiki/Parsing_expression_grammar,
# https://pdos.csail.mit.edu/~baford/packrat/thesis/
# Left recursion: https://web.cs.ucla.edu/~todd/research/pepm08.pdf
# Error Detection taken from - https://arxiv.org/abs/1806.11150


ParseFunction = Callable[['Cursor'], syntax.Term]
OrderedParseFunctions = list[ParseFunction | str]
GrammarRuleMap = dict[str, OrderedParseFunctions]


@dataclass
class Grammar:
    rule_map: GrammarRuleMap
    start_rule: str


def route(rule: str) -> ParseFunction:
    def parse(c: Cursor) -> syntax.Term:
        return c.consume_rule(rule)

    return parse


# Python backend AST has ctx attribute. Rename this class name to prevent confusion.
@dataclass
class Context:
    mode: syntax.Term


class Cursor:
    def __init__(self, row: int, col: int, context: Context, engine: PegEngine) -> None:
        self.row = row
        self.col = col
        self.context = context
        self.engine = engine

    def clone(self) -> Cursor:
        return Cursor(self.row, self.col, self.context, self.engine)

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

    def consume_rule(self, rule) -> syntax.Term:
        term, self.row, self.col = self.engine.apply_rule(self.row, self.col, rule, self.context)
        return term

    def start_tracker(self) -> Tracker:
        return Tracker(self)


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


@dataclass(frozen=True)
class CellKey:
    row: int
    col: int
    rule: str


@dataclass
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

    def parse_function_name(self, function: ParseFunction | str) -> str:
        if isinstance(function, str):
            return f'|>{function}'
        return f'@{function.__name__}'

    def call_parse_function(
        self, key: CellKey, function: ParseFunction | str, context: Context
    ) -> tuple[syntax.Term, int, int]:
        cursor = Cursor(key.row, key.col, context=context, engine=self)

        def create_location() -> syntax.Location:
            start_cursor = Cursor(key.row, key.col, context=context, engine=self)
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
                    message=f'PegEngine: rule={key.rule}:{self.parse_function_name(function)} returned None.',
                    location=create_location(),
                )
        except Exception as e:  # noqa: BLE001  The user provided function may raise any exception.
            term = syntax.ErrorTerm(
                message=f'PegEngine: rule={key.rule}:{self.parse_function_name(function)} error={e}',
                location=create_location(),
            )
        return term, cursor.row, cursor.col

    def call_ordered_parse_functions(self, key: CellKey, context: Context) -> tuple[syntax.Term, int, int]:
        functions = self.grammar_rule_map.get(key.rule)
        if not functions:
            raise tapl_error.TaplError(f'Rule "{key.rule}" is not defined in the Grammar.')
        for i in range(len(functions)):
            term, row, col = self.call_parse_function(key, functions[i], context=context)
            if term is not ParseFailed:
                return term, row, col
        return ParseFailed, key.row, key.col

    def grow_seed(self, key: CellKey, cell: Cell, context: Context) -> None:
        seed_next_row, seed_next_col = cell.next_row, cell.next_col
        iteration_count = 10  # Prevent infinite loop by limiting iterations
        while iteration_count > 0:
            iteration_count -= 1
            term, next_row, next_col = self.call_ordered_parse_functions(key, context)
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

    def apply_rule(self, row: int, col: int, rule: str, context: Context) -> tuple[syntax.Term, int, int]:
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
        match cell.state:
            case CellState.BLANK:
                cell.state = CellState.START
                cell.term, cell.next_row, cell.next_col = self.call_ordered_parse_functions(cell_key, context)
                cell.state = CellState.DONE
                if cell.growable and not isinstance(cell.term, syntax.ErrorTerm):
                    self.grow_seed(cell_key, cell, context)
            case CellState.START:
                # Left recursion detected. Delaying expansion of this rule.
                cell.growable = True
            case CellState.DONE:
                # Rule already parsed at this position, so no further action is required.
                pass
            case _:
                cell.term = syntax.ErrorTerm(f'PEG Parser Engine: Unknown cell state [{cell.state}] at {cell_key}.')
        self.rule_call_stack_limit += 1
        return cell.term, cell.next_row, cell.next_col

    def dump(self) -> str:
        return 'Use PegEngineDebug to get the engine dump.'


@dataclass
class ParseTrace:
    start_row: int
    start_col: int
    end_row: int
    end_col: int
    rule: str
    function_name: str
    term: syntax.Term
    start_call_order: int
    end_call_order: int
    growing_id: int | None
    applyied_rules: list[str]


class PegEngineDebug(PegEngine):
    def __init__(self, line_records: list[line_record.LineRecord], grammar_rule_map: GrammarRuleMap):
        super().__init__(line_records, grammar_rule_map)
        self.parse_traces: list[ParseTrace] = []
        self._next_call_order = 0
        self.growing_id: int | None = None
        self.next_growing_id = 0
        self.applied_rules: list[str] = []

    def next_call_order(self) -> int:
        self._next_call_order += 1
        return self._next_call_order

    @override
    def call_parse_function(
        self, key: CellKey, function: ParseFunction | str, context: Context
    ) -> tuple[syntax.Term, int, int]:
        old_applied_rules = self.applied_rules
        self.applied_rules = []
        start_call_order = self.next_call_order()
        term, row, col = super().call_parse_function(key, function, context=context)
        self.parse_traces.append(
            ParseTrace(
                start_row=key.row,
                start_col=key.col,
                end_row=row,
                end_col=col,
                rule=key.rule,
                function_name=self.parse_function_name(function),
                term=term,
                start_call_order=start_call_order,
                end_call_order=self.next_call_order(),
                growing_id=self.growing_id,
                applyied_rules=self.applied_rules,
            )
        )
        self.applied_rules = old_applied_rules
        return term, row, col

    @override
    def grow_seed(self, key: CellKey, cell: Cell, context: Context) -> None:
        old_growing_id = self.growing_id
        self.next_growing_id += 1
        self.growing_id = self.next_growing_id
        super().grow_seed(key, cell, context)
        self.growing_id = old_growing_id

    @override
    def apply_rule(self, row: int, col: int, rule: str, context: Context) -> tuple[syntax.Term, int, int]:
        self.applied_rules.append(f'{row}:{col}:{rule}')
        term, next_row, next_col = super().apply_rule(row, col, rule, context)
        if self.cell_memo[CellKey(row, col, rule)].state == CellState.START:
            self.applied_rules[-1] += ' (left recursion)'
        return term, next_row, next_col

    def dump_term(self, term: syntax.Term | None) -> tuple[str, str]:
        if term is None:
            return 'Error', 'None'
        if term is ParseFailed:
            return 'Fail', ''
        if isinstance(term, syntax.ErrorTerm):
            return 'Error', term.message
        return 'Success', f'term={term.__class__.__qualname__}'

    def dump_table(self, output: io.StringIO, table: list[list[str]]) -> None:
        col_widths = [max(len(str(item)) for item in col) for col in zip(*table, strict=True)]
        row_format = ' '.join(f'{{:<{width+2}}}' for width in col_widths[:-1]) + ' {}'
        for row in table:
            output.write(row_format.format(*row) + '\n')

    def dump_cell_memo(self) -> list[list[str]]:
        table = [['Start/Rule', 'End', 'Status', 'Details']]
        sorted_cells = sorted(self.cell_memo.items(), key=lambda item: (item[0].row, item[0].col, item[0].rule))
        for (row, col), group in itertools.groupby(sorted_cells, key=lambda item: (item[0].row, item[0].col)):
            table.append([f'{row}:{col}', '', '', ''])
            for item in group:
                cell = item[1]
                if cell.state == CellState.DONE:
                    state, details = self.dump_term(cell.term)
                else:
                    state = cell.state.name.capitalize()
                    details = ''
                state += ' Grown' if cell.growable else ''
                table.append([f'   {item[0].rule}', f'{cell.next_row}:{cell.next_col}', state, details])
        return table

    def tableize_parse_traces(self) -> list[list[str]]:
        sorted_traces = sorted(self.parse_traces, key=lambda t: (t.start_row, t.start_col, t.rule, t.start_call_order))
        table = [['Start/Rule', 'End', 'Order#', 'Status/Grow', 'Applied rules', 'Details']]
        last_pos = None
        for (row, col, rule), group in itertools.groupby(
            sorted_traces, key=lambda t: (t.start_row, t.start_col, t.rule)
        ):
            pos = f'{row}:{col}'
            if last_pos != pos:
                table.append(['', '', '', '', '', ''])
            last_pos = pos
            table.append([f'{row}:{col}:{rule}', '', '', '', '', ''])
            for trace in group:
                rule_key = f'   {trace.function_name}'
                status, details = self.dump_term(trace.term)
                if trace.growing_id:
                    status += ' G' + str(trace.growing_id)
                table.append(
                    [
                        rule_key,
                        f'{trace.end_row}:{trace.end_col}',
                        f'{trace.start_call_order}..{trace.end_call_order}',
                        status,
                        ', '.join(trace.applyied_rules),
                        details,
                    ]
                )
        return table

    @override
    def dump(self) -> str:
        output = io.StringIO()
        output.write('\n------PEG Engine Dump (Rows sorted by row,col,rule,call_order)--------')
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
        self.dump_table(output, self.dump_cell_memo())
        output.write('\n\n')
        self.dump_table(output, self.tableize_parse_traces())
        output.write('\n------End of PEG Engine Dump------------------------------------------\n')
        return output.getvalue()


def find_first_position(line_records: list[line_record.LineRecord]) -> tuple[int, int]:
    for row in range(len(line_records)):
        for col in range(len(line_records[row].text)):
            return row, col
    return len(line_records), 0


def parse_line_records(
    line_records: list[line_record.LineRecord], grammar: Grammar, *, debug: bool = False, context: Context | None = None
) -> syntax.Term:
    context = context or Context(mode=terms.MODE_SAFE)
    engine = PegEngineDebug(line_records, grammar.rule_map) if debug else PegEngine(line_records, grammar.rule_map)
    row, col = find_first_position(line_records)
    if row == len(line_records) and col == 0:
        return syntax.ErrorTerm(message='Empty text.')
    term, next_row, next_col = engine.apply_rule(row, col, grammar.start_rule, context=context)
    if debug:
        logging.warning(engine.dump())
    if not isinstance(term, syntax.ErrorTerm) and not (next_row == len(line_records) and next_col == 0):
        lineno = line_records[0].line_number if line_records else -1
        return syntax.ErrorTerm(
            message=f'chunk[line:{lineno}] Not all text consumed: indices {next_row}:{next_col}/{len(line_records)}:0.',
        )
    return term


def parse_text(text: str, grammar: Grammar, *, debug: bool = False, context: Context | None = None) -> syntax.Term:
    return parse_line_records(line_record.split_text_to_lines(text), grammar, debug=debug, context=context)
