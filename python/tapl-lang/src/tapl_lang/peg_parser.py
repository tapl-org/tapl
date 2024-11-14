# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import enum
from typing import Any, Callable, Optional
from tapl_lang import term

# Implemented PEG parser - https://en.wikipedia.org/wiki/Parsing_expression_grammar
# Error Detection taken from: https://www.sciencedirect.com/science/article/pii/S0167642316301046#se0040 In PEGs,
# it is more complicated to identify the cause of an error and the position where it occurs,
# because failures during parsing are not necessarily errors, but just an indication that the parser cannot proceed
# and a different choice should be made elsewhere.
# https://tuskr.app/learn/error-defect-failure An error leads to a defect, and when these defects go undetected, they lead to failure.


class Output:
    def __init(self) -> None:
        self.value: Optional[term.Term] = None
    
    def assert_value(self) -> term.Term:
        assert self.value is not None
        return self.value


class Cursor:
    def __init__(self, pos: int, engine):
        self.origina_pos = pos
        self.pos = pos
        self.engine = engine
        self.error: Optional[term.SyntaxError] = None
    
    def reset(self) -> None:
        self.pos = self.origina_pos
        self.error = None

    def get_location(self) -> term.Location:
        return term.Location(lineno=0, col_offset=self.origina_pos)
    
    def create_syntax_error(self, error_text: str) -> term.SyntaxError:
        return term.SyntaxError(self.get_location(), error_text)
    
    def skip_whitespaces(self) -> bool:
        while self.pos < len(self.engine.text) and self.engine.text[self.pos].isspace():
            self.pos += 1
        return True

    def consume_text(self, text: str, keep_whitespaces: bool = False) -> bool:
        if not keep_whitespaces: self.skip_whitespaces()
        p = self.pos
        for c in text:
            if p >= len(self.engine.text): return False
            if self.engine.text[p] != c: return False
            p += 1
        self.pos = p
        return True

    def expect_text(self, text: str, keep_whitespaces: bool = False) -> bool:
        result = self.consume_text(text, keep_whitespaces)
        if result == False and self.error == None:
            self.error = self.create_syntax_error(f'Expected "{text}"')
        return result

    def consume_rule(self, rule: str, output: Output) -> bool:
        cell = self.engine.apply_rule(rule, self.pos)
        if term.is_valid(cell.term):
            output.value = cell.term
            self.pos = cell.next_pos
            return True
        else:
            self.error = cell.term
            return False
    
    def expect_rule(self, rule: str, output: Output) -> bool:
        result = self.consume_rule(rule, output)
        if result == False and self.error == None:
            self.error = self.create_syntax_error(f'Expected rule [{rule}]')
        return result


class CellState(enum.Enum):
    BLANK = 1
    START = 2
    DONE = 3


class Cell:
    def __init__(self) -> None:
        self.state: CellState = CellState.BLANK
        self.growable: bool = False
        self.term: Optional[term.Term] = None
        self.next_pos: Optional[int] = None
    
    def __repr__(self) -> str:
        return f'{self.state.name}:{self.growable},next_pos={self.next_pos}, {self.term.__class__.__name__}'


type RuleFunc = Callable[[Cursor], Optional[term.Term]]
type RuleMaps = dict[str, RuleFunc]


class Engine:
    def __init__(self, text: str, rule_maps: RuleMaps):
        self.text = text
        self.rule_maps = rule_maps
        # (rule, position) -> Cell
        self.cell_memo: dict[tuple[str, int], Cell] = {}
        # hack: a rule apply limit to avoid infinite loop
        self.apply_rule_limit = 10000

    def get_rule_function(self, rule: str) -> RuleFunc:
        fn = self.rule_maps.get(rule)
        if fn: return fn
        raise RuntimeError(f'"{rule}" rule does not have an associated function.')
    
    def grow_seed(self, rule_fn: RuleFunc, pos: int, cell: Cell) -> None:
        seed_next_pos = cell.next_pos
        while True:
            cursor = Cursor(pos, engine=self)
            grown_term = rule_fn(cursor)
            next_pos = cursor.pos
            assert term.is_valid(grown_term), f'Once rule was successfull, then it has to be successful again. {grown_term}'
            # Stop growing when the next_pos returns back to seed's next_pos
            # This means that it returns back to seed again.
            if next_pos == seed_next_pos: break
            cell.term = grown_term
            cell.next_pos = next_pos

    def apply_rule(self, rule: str, pos: int):
        self.apply_rule_limit -= 1
        assert self.apply_rule_limit > 0, "apply_rule_limit exceeded."
        memo_key = (rule, pos)
        cell = self.cell_memo.get(memo_key)
        if not cell:
            cell = Cell()
            self.cell_memo[memo_key] = cell
        match cell.state:
            case CellState.BLANK:
                cell.state = CellState.START
                cursor = Cursor(pos, engine=self)
                rule_fn = self.get_rule_function(rule)
                cell.term = rule_fn(cursor)
                cell.next_pos = cursor.pos
                cell.state = CellState.DONE
                if cell.growable and term.is_valid(cell.term):
                    self.grow_seed(rule_fn, pos, cell)
            case CellState.START:
                # we reached left-recursive rule. Let it fail now, and grow it later.
                cell.growable = True
            case CellState.DONE:
                # do nothing, because the rule at this position has been already parsed.
                pass
            case _:
                raise RuntimeError(
                    f"PEG Parser Engine: Unknown cell state [{cell.state}]"
                )
        return cell


def parse(text: str, rule_maps: RuleMaps, initial_rule: str) -> term.Term:
    engine = Engine(text, rule_maps)
    cell = engine.apply_rule(initial_rule, 0)
    if term.is_valid(cell.term) and cell.next_pos != len(text):
        return term.SyntaxError(
            term.Location(lineno=0, col_offset=0),
            error_text=f"Not all text consumed {cell.next_pos}/{len(text)}",
        )
    return cell.term
