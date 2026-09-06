# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Term to text, in the same syntax the reader accepts.

Every term prints as a list, `(var x)` and `(bits 42)` included. Substitution
can bring two binders of the same written name into one scope, so a binder
whose name is already taken is printed under a fresh name; reading the result
back gives the same term.
"""

from gap.term import Abs, App, Bits, Bound, Fix, Free, If, Proj, Record, Term, free_names


def print_term(term: Term) -> str:
    return _print(term, [], free_names(term))


def _print(term: Term, binders: list[str], taken: set[str]) -> str:
    match term:
        case Bound(index, hint):
            name = binders[-1 - index] if 0 <= index < len(binders) else f'{hint}?{index}'
            return f'(var {name})'
        case Free(name):
            return f'(var {name})'
        case Bits(_, text):
            return f'(bits {text})'
        case Abs(param, body):
            name = _fresh(param, binders, taken)
            binders.append(name)
            try:
                return f'(lambda {name} {_print(body, binders, taken)})'
            finally:
                binders.pop()
        case App(function, argument):
            return f'(apply {_print(function, binders, taken)} {_print(argument, binders, taken)})'
        case Record(fields):
            written = ' '.join(f'{field.label} = {_print(field.term, binders, taken)}' for field in fields)
            return f'(record {written})'
        case Proj(subject, label):
            return f'(get {_print(subject, binders, taken)} {label})'
        case Fix(inner):
            return f'(fix {_print(inner, binders, taken)})'
        case If(condition, consequent, alternative):
            return (
                f'(if {_print(condition, binders, taken)} '
                f'{_print(consequent, binders, taken)} '
                f'{_print(alternative, binders, taken)})'
            )


def _fresh(name: str, binders: list[str], taken: set[str]) -> str:
    if name not in binders and name not in taken:
        return name
    suffix = 1
    while f'{name}-{suffix}' in binders or f'{name}-{suffix}' in taken:
        suffix += 1
    return f'{name}-{suffix}'
