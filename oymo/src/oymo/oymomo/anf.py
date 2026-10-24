# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""ANF (semantics.tex, Section 7): a list of `let`s with a terminal at the end.

    g ::= y | g.l                      free path
    a ::= x | x.l₁⋯lⱼ | g | b          atom
    q ::= a | {lᵢ = qᵢ}                operand
    u ::= g {lᵢ = qᵢ}                  function call
    o ::= b {lᵢ = qᵢ} | u              operation
    r ::= q | u                        return or jump
    τ ::= r | {lᵢ = rᵢ} a              terminal
    e ::= let x = o in e | τ           expression

`x` is a let variable: bound by a `let`, or a block's parameter. `y` is any other
variable, such as a module's `m` or a function's `f`. An opcode call in ANF is one that
E-Opcode does not compute, and a branch's condition is not a byte array. A term in ANF
is a normal form (`Oymomo.anf_normal`).

`anf_error` checks a resolved term (variables are `BruijnIndex`es) and names the first
part that is not in ANF.
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


def anf_error(term: syntax.Term, local: int = 0) -> AnfError | None:
    """None if `term` is an expression `e` in ANF, else the first part that is not.

    `local` counts the innermost binders around `term` that are let variables: 1 for a
    block's body under its parameter `λp`, 0 for a term on its own.
    """
    while isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda):
        if (error := _operation_error(term.argument, local)) is not None:
            return error
        term, local = term.function.body, local + 1
    return _terminal_error(term, local)


def _root(term):
    """The variable a path starts from, or None if `term` is not a path."""
    while isinstance(term, terms.Project):
        term = term.struct
    return term if isinstance(term, terms.BruijnIndex | terms.Variable) else None


def is_path(term: syntax.Term) -> bool:
    """`x.l₁⋯lⱼ` or `g`: a variable, or a projection of a path."""
    return _root(term) is not None


def is_free_path(term: syntax.Term, local: int) -> bool:
    """`g`: a path from a variable that is not a let variable."""
    root = _root(term)
    if isinstance(root, terms.BruijnIndex):
        return root.index >= local
    return root is not None


def is_atom(term: syntax.Term) -> bool:
    return is_path(term) or isinstance(term, terms.ByteArray)


def is_operand(term: syntax.Term) -> bool:
    """`q`: an atom or a struct of operands (D94)."""
    if isinstance(term, terms.Struct):
        return all(is_operand(f.value) for f in term.fields)
    return is_atom(term)


def _operand_error(term, what):
    """The first part of `term` that keeps it from being an operand."""
    if isinstance(term, terms.Struct):
        for f in term.fields:
            if (error := _operand_error(f.value, what)) is not None:
                return error
        return None
    if is_atom(term):
        return None
    return AnfError(f'{what} must be an atom or a struct of operands: bind it with a let.', term)


def _operands_error(struct, what):
    """The first field of `struct` that is not an operand."""
    if not isinstance(struct, terms.Struct):
        return AnfError(f'{what} must be a struct of operands.', struct)
    return _operand_error(struct, what)


def is_call(term: syntax.Term, local: int) -> bool:
    """`u`: a free path applied to a struct of atoms."""
    return (
        isinstance(term, terms.Apply)
        and is_free_path(term.function, local)
        and _operands_error(term.argument, 'An argument') is None
    )


def _call_error(term, local):
    if not is_free_path(term.function, local):
        return AnfError('A call must be through a free path, such as m.l or f.l.body.', term.function)
    return _operands_error(term.argument, 'An argument')


def _operation_error(term, local):
    """`o`: an opcode call that E-Opcode does not compute, or a function call."""
    match term:
        case terms.Apply(function=terms.ByteArray()):
            if (error := _operands_error(term.argument, 'An operand')) is not None:
                return error
            if reduction.reduce(term) is not term:
                return AnfError('E-Opcode computes this opcode call.', term)
            return None
        case terms.Apply():
            return _call_error(term, local)
        case terms.Project():
            return AnfError(
                'A let must bind an opcode call or a function call; '
                'a projection is not a value, so E-Beta never substitutes it (4.3).',
                term,
            )
    return AnfError('A let must bind an opcode call or a function call.', term)


def _return_error(term, local):
    """`r`: an operand or a function call."""
    if is_operand(term):
        return None
    if isinstance(term, terms.Apply) and not isinstance(term.function, terms.ByteArray | terms.Struct):
        return _call_error(term, local)
    return AnfError('A return must be an operand, and a jump a function call.', term)


def _terminal_error(term, local):
    """`τ`: a return or a jump, or a branch of them on a path."""
    match term:
        case terms.Apply(function=terms.Struct(fields=fields), argument=condition):
            for f in fields:
                if (error := _return_error(f.value, local)) is not None:
                    return error
            if not is_path(condition):
                return AnfError('A branch condition must be a variable or a path.', condition)
            return None
        case terms.Apply(function=terms.ByteArray()):
            return _operands_error(term.argument, 'An operand') or AnfError(
                'An opcode call at the end must be bound by a let and its variable returned.', term
            )
    return _return_error(term, local)


def is_anf(term: syntax.Term, local: int = 0) -> bool:
    return anf_error(term, local) is None
