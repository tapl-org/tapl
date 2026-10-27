# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""ANF: a function's body, as a grammar.

    P ::= x | P.l                                  path
    O ::= P | b                                    operator
    Q ::= P | D                                    operand (D data)
    J ::= P Q₁ ⋯ Qₙ                                jump
    T ::= Q | J | {Jᵢ} P | R                       terminal
    E ::= let x = O {lᵢ = Qᵢ} in E | T             expression
    K ::= E | λx₁. ⋯ λxₙ. E                        block
    R ::= x [] (λx. {lᵢ = Kᵢ}), 0 < k              region; field 0 is an E

Every variable is `x`: the grammar does not tell them apart; `ingot` checks their kinds. An opcode call in ANF is one that E-Opcode does not compute. A term in ANF is a
normal form (`Oymomo.anf_normal`).

`anf_error` checks a term (resolved or not) and names the first part that is not in ANF.
"""

from dataclasses import dataclass

from oymo.core import syntax
from oymo.oymomo import reduction, terms


@dataclass(frozen=True)
class AnfError:
    """Why a term is not in ANF, and the part that breaks it."""

    message: str
    term: syntax.Term

    @property
    def span(self) -> int:
        return getattr(self.term, 'span', 0)


def _root(term):
    """The variable a path starts from, or None if `term` is not a path."""
    while isinstance(term, terms.Project):
        term = term.struct
    return term if isinstance(term, terms.BruijnIndex | terms.Variable) else None


def is_path(term: syntax.Term) -> bool:
    """`P`: a variable followed by labels."""
    return _root(term) is not None


def is_operand(term: syntax.Term) -> bool:
    """`Q`: a path or data."""
    return is_path(term) or reduction.is_data(term)


def region_parts(term: syntax.Term) -> tuple[syntax.Term, terms.Lambda] | None:
    """`(x, λr. {…})` for a term shaped `x [] (λr. {…})`, else None."""
    match term:
        case terms.Apply(
            function=terms.Apply(function=head, argument=terms.ByteArray(value=b'')),
            argument=terms.Lambda() as blocks,
        ) if isinstance(head, terms.BruijnIndex | terms.Variable):
            return head, blocks
    return None


def jump_parts(term: syntax.Term) -> tuple[syntax.Term, list[syntax.Term]] | None:
    """`(P, [Q₁, …, Qₙ])` for a path applied to terms one by one, else None."""
    arguments = []
    while isinstance(term, terms.Apply):
        arguments.append(term.argument)
        term = term.function
    return (term, arguments[::-1]) if is_path(term) else None


def anf_error(term: syntax.Term) -> AnfError | None:
    """None if `term` is an expression `E` in ANF, else the first part that is not."""
    while isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda):
        if (error := _instruction_error(term.argument)) is not None:
            return error
        term = term.function.body
    return _terminal_error(term)


def region_error(term: syntax.Term) -> AnfError | None:
    """None if `term` is a region `R` in ANF, else the first part that is not."""
    parts = region_parts(term)
    if parts is None:
        return AnfError('A region is x [] (λr. {blocks}).', term)
    body = parts[1].body
    if not isinstance(body, terms.Struct) or not body.fields:
        return AnfError('A region holds a struct of blocks, at least one.', body)
    first, *rest = body.fields
    if isinstance(first.value, terms.Lambda):
        return AnfError('Field 0 of a region is an expression, never a λ.', first.value)
    if (error := anf_error(first.value)) is not None:
        return error
    for f in rest:
        block = f.value
        while isinstance(block, terms.Lambda):
            block = block.body
        if (error := anf_error(block)) is not None:
            return error
    return None


def _operand_error(term, what):
    if is_operand(term):
        return None
    if isinstance(term, terms.Struct):
        return AnfError(
            f"{what} must be a path or data; a struct value is built with 'insertvalue'.",
            term,
        )
    return AnfError(f'{what} must be a path or data: bind it with a let.', term)


def _operands_error(struct, what):
    """The first field of `struct`, a struct of operands, that is not an operand."""
    if not isinstance(struct, terms.Struct):
        return AnfError('An instruction applies its operator to a struct of operands.', struct)
    for f in struct.fields:
        if (error := _operand_error(f.value, what)) is not None:
            return error
    return None


def _instruction_error(term):
    """`O {lᵢ = Qᵢ}`: a call, or an opcode call that E-Opcode does not compute."""
    match term:
        case terms.Apply(function=terms.ByteArray()):
            if (error := _operands_error(term.argument, 'An operand')) is not None:
                return error
            if reduction.reduce(term) is not term:
                return AnfError('E-Opcode computes this opcode call.', term)
            return None
        case terms.Apply(function=function) if is_path(function):
            return _operands_error(term.argument, 'An argument')
        case terms.Project():
            return AnfError(
                'A let must bind an opcode call or a function call; '
                'a projection is not a value, so E-Beta never substitutes it.',
                term,
            )
    return AnfError('A let must bind an instruction: an opcode call or a function call.', term)


def _jump_error(term):
    parts = jump_parts(term)
    if parts is None:
        return AnfError('An arm of a branch only jumps: r.l Q₁ ⋯ Qₙ.', term)
    for argument in parts[1]:
        if (error := _operand_error(argument, 'An operand of a jump')) is not None:
            return error
    return None


def _terminal_error(term):
    """`T`: a return, a jump, a branch of jumps on a path, or a region."""
    if region_parts(term) is not None:
        return region_error(term)
    match term:
        case terms.Apply(function=terms.Struct(fields=fields), argument=condition):
            for f in fields:
                if (error := _jump_error(f.value)) is not None:
                    return error
            if not is_path(condition):
                return AnfError('A branch condition must be a path.', condition)
            return None
        case terms.Apply(function=terms.ByteArray()):
            return _operands_error(term.argument, 'An operand') or AnfError(
                'An opcode call at the end must be bound by a let and its variable returned.', term
            )
    if is_operand(term):
        return None
    if (parts := jump_parts(term)) is not None:
        if len(parts[1]) == 1 and isinstance(parts[1][0], terms.Struct) and not is_operand(parts[1][0]):
            return AnfError(TAIL_CALL, term)
        return _jump_error(term)
    return _operand_error(term, 'A return')


TAIL_CALL = 'A call that ends a function is bound and returned: let y = m.f {…} in y.'


def is_anf(term: syntax.Term) -> bool:
    return anf_error(term) is None
