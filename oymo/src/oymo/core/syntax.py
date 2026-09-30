# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

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


class _EmptyTerm(Term):
    def children(self) -> Generator[Term, None, None]:
        yield from ()

    def separate(self, ls):
        return ls.build(lambda _: self)

    def __repr__(self) -> str:
        return 'Empty'


Empty = _EmptyTerm()


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
        # Memorize the order of extract_layer calls to ensure consistent layer processing.
        memo: list[tuple[Term, tuple[Term, Term]]] = []
        memo_index = [0]

        def extract_layer(index: int, term: Term) -> Term:
            if index == 0:
                memo.append((term, term.separate(self)))
            original_term, layers = memo[memo_index[0]]
            memo_index[0] += 1
            if original_term is not term:
                raise RuntimeError('LAYER FUNCTION CALL ORDER IS CHANGED.')
            return layers[index]

        def create_extract_layer_fn(index: int) -> Callable[[Term], Term]:
            return lambda term: extract_layer(index, term)

        memo_index[0] = 0
        lower = factory(create_extract_layer_fn(0))
        memo_index[0] = 0
        upper = factory(create_extract_layer_fn(1))
        return (lower, upper)


@dataclass
class BackendSetting:
    scope_level: int

    def clone(self, scope_level: int | None = None) -> BackendSetting:
        return BackendSetting(
            scope_level=scope_level or self.scope_level,
        )

    @property
    def scope_name(self) -> str:
        return f's{self.scope_level}'

    @property
    def forker_name(self) -> str:
        return f'f{self.scope_level}'


@dataclass
class BackendSettingChanger(Term):
    changer: Callable[[BackendSetting], BackendSetting]

    def children(self) -> Generator[Term, None, None]:
        yield from ()

    def separate(self, ls: LayerSeparator) -> tuple[Term, Term]:
        return ls.build(lambda _: BackendSettingChanger(changer=self.changer))


@dataclass
class BackendSettingTerm(Term):
    backend_setting_changer: Term
    term: Term

    def children(self) -> Generator[Term, None, None]:
        yield self.backend_setting_changer
        yield self.term

    def separate(self, ls: LayerSeparator) -> tuple[Term, Term]:
        return ls.build(
            lambda layer: BackendSettingTerm(
                backend_setting_changer=layer(self.backend_setting_changer), term=layer(self.term)
            )
        )

    def new_setting(self, setting: BackendSetting) -> BackendSetting:
        if not isinstance(self.backend_setting_changer, BackendSettingChanger):
            raise TypeError(
                f'Expected setting to be an instance of {BackendSettingChanger.__name__}, got {type(self.backend_setting_changer).__name__}'
            )
        return cast('BackendSettingChanger', self.backend_setting_changer).changer(setting)


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


@dataclass
class TermList(Term):
    terms: list[Term]
    # True if the statement is a placeholder requiring resolution (e.g., waiting for child chunk parsing).
    is_placeholder: bool = False

    def children(self) -> Generator[Term, None, None]:
        yield from self.terms

    def flattened(self) -> Generator[Term, None, None]:
        for term in self.terms:
            if isinstance(term, TermList):
                yield from term.flattened()
            else:
                yield term

    def separate(self, ls: LayerSeparator) -> tuple[Term, Term]:
        if self.is_placeholder:
            raise RuntimeError('The placeholder list must be resolved before separation.')
        return ls.build(lambda layer: TermList(terms=[layer(s) for s in self.terms], is_placeholder=False))


def find_placeholder(term: Term) -> TermList | None:
    placeholder: TermList | None = None

    def loop(t: Term) -> None:
        nonlocal placeholder
        if isinstance(t, TermList) and t.is_placeholder:
            if placeholder is None:
                placeholder = t
            else:
                raise RuntimeError('Multiple placeholders found.')
        for child in t.children():
            loop(child)

    loop(term)
    return placeholder


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


def gather_errors(term: Term) -> list[ErrorTerm]:
    error_bucket: list[ErrorTerm] = []

    def gather_errors_recursive(t: Term) -> None:
        if isinstance(t, ErrorTerm):
            error_bucket.append(t)
        for child in t.children():
            gather_errors_recursive(child)

    gather_errors_recursive(term)
    return error_bucket
