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

import logging
from dataclasses import dataclass

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
    pass


@dataclass
class MemoEntry:
    match: Match
    in_progress: bool
    left_recursion_detected: bool
    version: int
