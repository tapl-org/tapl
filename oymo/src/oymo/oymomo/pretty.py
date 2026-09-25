# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.core import syntax
from oymo.oymomo import terms


def print_term(term: syntax.Term) -> str:
    return print_atom(term)


def print_atom(term: syntax.Term) -> str:
    if isinstance(term, terms.Integer):
        return f'{term.value}:{term.form}'
    return f'({print_term(term)})'
