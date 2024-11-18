# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from abc import ABC, abstractmethod
from tapl_lang import syntax
from typing import Optional


class ParseResult:

    def __init__(self, term: syntax.Term, child_parser: Optional['Parser'],
                 sibling_parser: Optional['Parser']) -> None:
        self.term = term
        self.child_parser = child_parser
        self.sibling_parser = sibling_parser


class Parser(ABC):

    @abstractmethod
    def parse(self, lines: list[syntax.Line]) -> ParseResult:
        pass
