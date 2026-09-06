# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Partial evaluation: reduce what can reduce, keep the rest as the residual.

Reduction is strong, so a redex may fire under a lambda. The shape predicates
below are the `v` and `n` grammars of gap/spec.md: `is_value` says when a
computation rule may fire, and `is_neutral` says when an elimination is
residual rather than an error.
"""

from gap.term import Abs, App, Bits, Bound, Fix, Free, If, Proj, Record, Term


def is_value(term: Term) -> bool:
    """v: variable, abstraction, record of values, or bits. A lambda body may still hold redexes."""
    match term:
        case Bound() | Free() | Abs() | Bits():
            return True
        case Record(fields):
            return all(is_value(field.term) for field in fields)
        case _:
            return False


def is_neutral(term: Term) -> bool:
    """n: an elimination whose innermost subject is a variable, such as `x.a`."""
    match term:
        case Bound() | Free():
            return True
        case App(function, _):
            return is_neutral(function)
        case Proj(subject, _):
            return is_neutral(subject)
        case Fix(inner):
            return is_neutral(inner)
        case If(condition, _, _):
            return is_neutral(condition)
        case _:
            return False


def step(term: Term) -> Term | None:
    """One reduction step, or None when nothing in `term` can fire.

    Dispatch follows the first-match tables of gap/spec.md: try the computation
    rule for the node, then the congruence rules on its children, and keep the
    node unchanged when neither applies. `fix` unfolds only where its result is
    demanded, under `(apply (fix t) s)` or `(fix t).l`.
    """
    raise NotImplementedError


def reduce_term(term: Term) -> Term:
    """Step until nothing fires. What is left is the residual."""
    raise NotImplementedError
