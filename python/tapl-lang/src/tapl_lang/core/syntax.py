# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast, override

from tapl_lang.core import tapl_error

if TYPE_CHECKING:
    import ast
    from collections.abc import Callable, Generator


class Term:
    def children(self) -> Generator[Term, None, None]:
        """Yields the child terms of this term for tree traversal or visitor operations."""
        raise tapl_error.TaplError(f'{self.__class__.__name__}.children is not implemented.')

    def separate(self, ls: LayerSeparator) -> list[Term]:
        """Separate the term into layers based on the number of layers specified by the LayerSeparator."""
        del ls
        raise tapl_error.TaplError(f'The {self.__class__.__name__} class does not support separate.')

    def unfold(self) -> Term:
        """Unfolds the term if it is a wrapper or syntactic sugar, returning the underlying term.
        If the term is already in its simplest form, it returns itself."""
        return self

    def codegen_ast(self, setting: BackendSetting) -> ast.AST:
        """Generates the AST representation of this term."""
        del setting
        raise tapl_error.TaplError(f'codegen_ast is not implemented in {self.__class__.__name__}')

    def codegen_expr(self, setting: BackendSetting) -> ast.expr:
        """Generates the expression AST representation of this term."""
        del setting
        raise tapl_error.TaplError(f'codegen_expr is not implemented in {self.__class__.__name__}')

    def codegen_stmt(self, setting: BackendSetting) -> list[ast.stmt]:
        """Generates the statement AST representation of this term."""
        del setting
        raise tapl_error.TaplError(f'codegen_stmt is not implemented in {self.__class__.__name__}')

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'


class SiblingTerm(Term):
    """Represents a term that is a sibling to other terms.
    Example: An else statement must be integrated into the preceding sibling if statement.
    """

    def integrate_into(self, previous_siblings: list[Term]) -> None:
        """Integrates this term into the given previous siblings."""
        del previous_siblings
        raise tapl_error.TaplError(f'{self.__class__.__name__}.integrate_into is not implemented.')


class Layers(Term):
    def __init__(self, layers: list[Term]) -> None:
        self.layers = layers
        self._validate_layer_count()

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.layers})'

    def _validate_layer_count(self) -> None:
        if len(self.layers) <= 1:
            raise tapl_error.TaplError('Number of layers must be equal or greater than 2.')

    @override
    def children(self) -> Generator[Term, None, None]:
        yield from self.layers

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        self._validate_layer_count()
        actual_count = len(self.layers)
        if actual_count != ls.layer_count:
            raise tapl_error.TaplError(
                f'Mismatched layer lengths, actual_count={actual_count}, expected_count={ls.layer_count}'
            )
        return self.layers

    @override
    def codegen_ast(self, setting: BackendSetting) -> ast.AST:
        raise tapl_error.TaplError('Layers should be separated before generating AST code.')

    @override
    def codegen_expr(self, setting: BackendSetting) -> ast.expr:
        raise tapl_error.TaplError('Layers should be separated before generating AST code.')

    @override
    def codegen_stmt(self, setting: BackendSetting) -> list[ast.stmt]:
        raise tapl_error.TaplError('Layers should be separated before generating AST code.')


class LayerSeparator:
    def __init__(self, layer_count: int) -> None:
        if layer_count <= 1:
            raise tapl_error.TaplError('layer_count must be equal or greater than 2 to separate.')
        self.layer_count = layer_count

    def build(self, factory: Callable[[Callable[[Term], Term]], Term]) -> list[Term]:
        # Memorize the order of extract_layer calls to ensure consistent layer processing.
        memo: list[tuple[Term, list[Term]]] = []
        memo_index = [0]

        def extract_layer(index: int, term: Term) -> Term:
            if index == 0:
                memo.append((term, term.separate(self)))
            original_term, layers = memo[memo_index[0]]
            memo_index[0] += 1
            if original_term is not term:
                raise tapl_error.TaplError('layer function call order is changed.')
            return layers[index]

        def create_extract_layer_fn(index: int) -> Callable[[Term], Term]:
            return lambda term: extract_layer(index, term)

        layers: list[Term] = []
        for i in range(self.layer_count):
            memo_index[0] = 0
            layers.append(factory(create_extract_layer_fn(i)))
        return layers


@dataclass
class BackendSetting:
    scope_level: int

    def clone(self, scope_level: int | None = None) -> BackendSetting:
        return BackendSetting(
            scope_level=scope_level or self.scope_level,
        )

    # TODO: AstSetting is not the right place for scope_name and forker_name function #refactor
    @property
    def scope_name(self) -> str:
        return f's{self.scope_level}'

    @property
    def forker_name(self) -> str:
        return f'f{self.scope_level}'


@dataclass
class BackendSettingChanger(Term):
    changer: Callable[[BackendSetting], BackendSetting]

    @override
    def children(self) -> Generator[Term, None, None]:
        yield from ()

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        return ls.build(lambda _: BackendSettingChanger(changer=self.changer))


@dataclass
class BackendSettingTerm(Term):
    backend_setting_changer: Term
    term: Term

    @override
    def children(self) -> Generator[Term, None, None]:
        yield self.backend_setting_changer
        yield self.term

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        return ls.build(
            lambda layer: BackendSettingTerm(
                backend_setting_changer=layer(self.backend_setting_changer), term=layer(self.term)
            )
        )

    def new_setting(self, setting: BackendSetting) -> BackendSetting:
        if not isinstance(self.backend_setting_changer, BackendSettingChanger):
            raise tapl_error.TaplError(
                f'Expected setting to be an instance of {BackendSettingChanger.__name__}, got {type(self.backend_setting_changer).__name__}'
            )
        return cast(BackendSettingChanger, self.backend_setting_changer).changer(setting)


@dataclass
class Position:
    line: int
    column: int

    def __repr__(self) -> str:
        return f'{self.line}:{self.column}'


@dataclass
class Location:
    start: Position
    end: Position | None = None

    def __repr__(self) -> str:
        start = repr(self.start) if self.start else '-'
        end = repr(self.end) if self.end else '-'
        return f'({start},{end})'

    def locate(self, *nodes: ast.expr | ast.stmt) -> None:
        for node in nodes:
            node.lineno = self.start.line
            node.col_offset = self.start.column
        if self.end:
            for node in nodes:
                node.end_lineno = self.end.line
                node.end_col_offset = self.end.column


@dataclass
class ErrorTerm(Term):
    message: str
    location: Location | None = None
    recovered: bool = False
    guess: Term | None = None

    @override
    def children(self) -> Generator[Term, None, None]:
        yield from ()

    @override
    def __repr__(self) -> str:
        if self.location:
            return f'{self.location} {self.message}'
        return self.message


@dataclass
class TermList(Term):
    terms: list[Term]
    # True if the statement is a placeholder requiring resolution (e.g., waiting for child chunk parsing).
    is_placeholder: bool = False

    @override
    def children(self) -> Generator[Term, None, None]:
        yield from self.terms

    def flattened(self) -> Generator[Term, None, None]:
        for term in self.terms:
            if isinstance(term, TermList):
                yield from term.flattened()
            else:
                yield term

    @override
    def separate(self, ls: LayerSeparator) -> list[Term]:
        if self.is_placeholder:
            raise tapl_error.TaplError('The placeholder list must be resolved before separation.')
        return ls.build(lambda layer: TermList(terms=[layer(s) for s in self.terms], is_placeholder=False))

    @override
    def codegen_stmt(self, setting: BackendSetting) -> list[ast.stmt]:
        if self.is_placeholder:
            raise tapl_error.TaplError('The placeholder list must be initialized before code generation.')
        return [s for b in self.terms for s in b.codegen_stmt(setting)]


def find_placeholder(term: Term) -> TermList | None:
    placeholder: TermList | None = None

    def loop(t: Term) -> None:
        nonlocal placeholder
        if isinstance(t, TermList) and t.is_placeholder:
            if placeholder is None:
                placeholder = t
            else:
                raise tapl_error.TaplError('Multiple placeholders found.')
        for child in t.children():
            loop(child)

    loop(term)
    return placeholder
