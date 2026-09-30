# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


class Term:
    def children(self) -> Generator[Term, None, None]:
        """Yields the child terms of this term for tree traversal or visitor operations."""
        raise NotImplementedError(f'{self.__class__.__name__} must override Term.children() to yield its child terms.')

    def separate(self, ls: LayerSeparator) -> tuple[Term, Term]:
        """Separates this term into two layers, one for evaluation and one for type checking.

        The LayerSeparator is used to create the two layers. The `lower` layer is evaluated;
        the `upper` layer is used for type checking.
        """
        del ls
        raise NotImplementedError(
            f'{self.__class__.__name__} must override Term.separate() to separate the term into layers.'
        )

    def unfold(self) -> Term:
        """Rewrites this term one step into simpler terms that mean the same thing.

        Wrapper and syntactic-sugar terms return their desugared form, which may itself
        be unfolded again. Primitive terms that a backend handles directly return `self`;
        callers use `term.unfold() is term` to detect that no further unfolding is possible.
        """
        raise NotImplementedError(
            f'{self.__class__.__name__} must override Term.unfold() to unfold the term if it is a wrapper or syntactic sugar.'
        )

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'


@dataclass
class Layers(Term):
    """Two-layer term `lower : upper`.

    `lower` (layers[0]) is evaluated; `upper` (layers[1]) is used for type checking.
    """

    layers: tuple[Term, Term]

    def children(self) -> Generator[Term, None, None]:
        yield from self.layers

    def separate(self, ls: LayerSeparator) -> tuple[Term, Term]:
        del ls
        return self.layers


class LayerSeparator:
    def build(self, factory: Callable[[Callable[[Term], Term]], Term]) -> tuple[Term, Term]:
        # The factory must call its layer function on the same terms in the same order on both passes,
        # so the upper pass can reuse the separations computed during the lower pass.
        separated: list[tuple[Term, tuple[Term, Term]]] = []

        def lower_layer(term: Term) -> Term:
            layers = term.separate(self)
            separated.append((term, layers))
            return layers[0]

        lower = factory(lower_layer)
        replay = iter(separated)

        def upper_layer(term: Term) -> Term:
            original_term, layers = next(replay, (None, None))
            if original_term is not term or layers is None:
                raise RuntimeError('Layer function call order changed between the lower and upper passes.')
            return layers[1]

        upper = factory(upper_layer)
        return (lower, upper)


@dataclass
class TermList(Term):
    terms: list[Term]

    def children(self) -> Generator[Term, None, None]:
        yield from self.terms

    def flattened(self) -> Generator[Term, None, None]:
        for term in self.terms:
            if isinstance(term, TermList):
                yield from term.flattened()
            else:
                yield term

    def separate(self, ls: LayerSeparator) -> tuple[Term, Term]:
        return ls.build(lambda layer: TermList(terms=[layer(s) for s in self.terms]))


class _EmptyTerm(Term):
    def children(self) -> Generator[Term, None, None]:
        yield from ()

    def separate(self, ls):
        return ls.build(lambda _: self)

    def __repr__(self) -> str:
        return 'Empty'


Empty = _EmptyTerm()


@dataclass
class ModeTerm(Term):
    typecheck: bool = False
    use_scope: bool = False

    def children(self) -> Generator[Term, None, None]:
        yield from ()

    def separate(self, ls: LayerSeparator) -> tuple[Term, Term]:
        return ls.build(lambda _: self)


MODE_EVALUATE = ModeTerm(typecheck=False, use_scope=False)
MODE_EVALUATE_WITH_SCOPE = ModeTerm(typecheck=False, use_scope=True)
MODE_TYPECHECK = ModeTerm(typecheck=True, use_scope=True)
MODE_TYPECHECK_NO_SCOPE = ModeTerm(typecheck=True, use_scope=False)
MODE_SAFE = Layers(layers=(MODE_EVALUATE, MODE_TYPECHECK))
MODE_LIFT = Layers(layers=(MODE_EVALUATE, MODE_EVALUATE_WITH_SCOPE))


@dataclass
class Location:
    start: int | None = None
    end: int | None = None

    def __repr__(self) -> str:
        return f'{self.start if self.start else "-"}:{self.end if self.end else "-"}'


@dataclass
class ErrorTerm(Term):
    message: str
    location: Location

    def children(self) -> Generator[Term, None, None]:
        yield from ()


def gather_errors(term: Term) -> list[ErrorTerm]:
    error_bucket: list[ErrorTerm] = []

    def gather_errors_recursive(t: Term) -> None:
        if isinstance(t, ErrorTerm):
            error_bucket.append(t)
        for child in t.children():
            gather_errors_recursive(child)

    gather_errors_recursive(term)
    return error_bucket
