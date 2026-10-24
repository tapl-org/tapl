# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The strategy (semantics.tex, Section 6): one order of the steps of `⟶`.

`sstep(t)` takes the step that table 6.2 chooses, or returns None when `t` is a normal
form. Rows are tried top to bottom within a term's group (projection, application,
struct, lambda, fixed point), and a part is chosen only when it has a step. It follows Lean's
`Oymomo.SStep`, one branch per row, so the theorems carry over:

- every step is a `⟶` step (`Oymomo.sstep_step`);
- it returns None only on a normal form (`Oymomo.sstep_complete`);
- if `t` has a normal form, `normalize(t)` reaches it (`Oymomo.guarantee`).

A part has a step exactly when `sstep` gives it one (completeness), so the
"has a step" conditions of the table reuse that step.
"""

from dataclasses import replace

from oymo.core import syntax
from oymo.oymomo import reduction, terms

# `normalize` gives up after this many steps: a term with no normal form never stops.
MAX_STEPS = 100_000


def sstep(term: syntax.Term) -> syntax.Term | None:
    """The step of table 6.2 from `term`, or None if `term` is a normal form."""
    match term:
        case terms.Project():
            return _project(term)
        case terms.Apply():
            return _apply(term)
        case terms.Struct():
            return _struct(term)
        case terms.Lambda(body=body):
            # Row o: E-Abs on the body.
            stepped = sstep(body)
            return None if stepped is None else replace(term, body=stepped)
        case terms.Fix(body=body):
            # Row p: E-Fix1 on the body.
            stepped = sstep(body)
            return None if stepped is None else replace(term, body=stepped)
    return None


def _project(term: terms.Project) -> syntax.Term | None:
    # Rows a and b: E-Proj, E-FixProj.
    if (reduced := reduction.reduce(term)) is not term:
        return reduced
    # Row c: E-Proj1 on the projected term.
    stepped = sstep(term.struct)
    return None if stepped is None else replace(term, struct=stepped)


def _apply(term: terms.Apply) -> syntax.Term | None:
    # Rows d, f, g, h, i: E-Beta, E-FixApp, E-Opcode, E-Index, E-Default at the root.
    if (reduced := reduction.reduce(term)) is not term:
        return reduced
    function, argument = term.function, term.argument
    if isinstance(function, terms.Lambda | terms.Struct):
        # Row e: the argument of a lambda (not a value, or E-Beta would fire).
        # Row j: a branch's condition (not a byte array, or E-Index would fire).
        stepped = sstep(argument)
        if stepped is not None:
            return replace(term, argument=stepped)
        # Rows k and l: the argument has no step, so only the function can.
        stepped = sstep(function)
        return None if stepped is None else replace(term, function=stepped)
    # Row k: E-App1 on the function.
    if (stepped := sstep(function)) is not None:
        return replace(term, function=stepped)
    # Row l: E-App2 on the argument.
    stepped = sstep(argument)
    return None if stepped is None else replace(term, argument=stepped)


def _struct(term: terms.Struct) -> syntax.Term | None:
    steps: dict[int, syntax.Term | None] = {}

    def field_step(i):
        if i not in steps:
            steps[i] = sstep(term.fields[i].value)
        return steps[i]

    def with_field(i):
        fields = list(term.fields)
        fields[i] = replace(fields[i], value=steps[i])
        return replace(term, fields=fields)

    # Row m: E-Struct on the first field that is not a value and has a step.
    for i, f in enumerate(term.fields):
        if not reduction.is_value(f.value) and field_step(i) is not None:
            return with_field(i)
    # Row n: E-Struct on the first field with a step.
    for i in range(len(term.fields)):
        if field_step(i) is not None:
            return with_field(i)
    return None


def normalize(term: syntax.Term, max_steps: int = MAX_STEPS) -> syntax.Term:
    """The normal form of `term`, by the order of table 6.2. Raises `ReductionError` when
    `max_steps` steps don't reach one (the term may have none), or when the term grows too
    deep to step."""
    for _ in range(max_steps):
        try:
            stepped = sstep(term)
        except RecursionError:
            raise reduction.ReductionError('Term too deep to reduce.', getattr(term, 'span', 0)) from None
        if stepped is None:
            return term
        term = stepped
    raise reduction.ReductionError(f'No normal form within {max_steps} steps.', getattr(term, 'span', 0))
