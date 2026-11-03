# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Oymomo terms: `x | λx. t | t t | b | {lᵢ = tᵢ} | t.l | fix t`.

A `Variable` is a name as written; `reduction.resolve` turns each one into the
`BruijnIndex` of its binder.
"""

from collections.abc import Generator, Iterator
from dataclasses import dataclass, field

from oymo.core import syntax
from oymo.oymomo.meta import NO_TAG, Tag

Term = syntax.Term


# Every `tag` (`meta.Tag`: where the term comes from, and more; `NO_TAG` for none) is left
# out of `==`, so a parsed term equals the same term built in code.
@dataclass
class Variable(Term):
    name: str
    tag: Tag = field(default=NO_TAG, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield from ()


@dataclass
class BruijnIndex(Term):
    index: int
    tag: Tag = field(default=NO_TAG, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield from ()


@dataclass
class Lambda(Term):
    """`λx. body`."""

    param_name: str
    body: Term
    tag: Tag = field(default=NO_TAG, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.body


@dataclass
class Apply(Term):
    function: Term
    argument: Term
    tag: Tag = field(default=NO_TAG, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.function
        yield self.argument


@dataclass
class Field:
    """`label = value`; an unlabeled field has the label `''`."""

    label: str
    value: Term
    tag: Tag = field(default=NO_TAG, compare=False)


@dataclass
class Struct(Term):
    fields: list[Field]
    tag: Tag = field(default=NO_TAG, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield from (f.value for f in self.fields)


@dataclass
class Project(Term):
    struct: Term
    label: str
    tag: Tag = field(default=NO_TAG, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.struct


@dataclass
class Fix(Term):
    """`fix body`, a fixed point. `fix (λx. t)` is a value; it unfolds, once, where it
    is projected (E-FixProj) or applied (E-FixApp)."""

    body: Term
    tag: Tag = field(default=NO_TAG, compare=False)

    def children(self) -> Generator[Term, None, None]:
        yield self.body


# A type such as `'i32'` is the byte array of its name.
@dataclass
class ByteArray(Term):
    value: bytes
    tag: Tag = field(default=NO_TAG, compare=False)

    @classmethod
    def from_str(cls, text: str) -> 'ByteArray':
        """The UTF-8 bytes of `text`."""
        return cls(text.encode('utf-8'))

    @property
    def as_str(self) -> str | None:
        """The bytes decoded as UTF-8. None if they aren't valid UTF-8."""
        try:
            return self.value.decode('utf-8')
        except UnicodeDecodeError:
            return None

    def children(self) -> Generator[Term, None, None]:
        yield from ()


# A node of a term: a term, or a struct's field. Each node has a tag.
type Node = Term | Field


def nodes(term: Term) -> Iterator[Node]:
    """Every node of `term` in pre-order: a node, then its children; a struct's fields, each
    before its value. A node shared by two parents is visited twice."""
    stack: list[Node] = [term]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(node_children(node)))


def node_children(node: Node) -> list[Node]:
    """The children of a node, as `nodes` visits them."""
    if isinstance(node, Field):
        return [node.value]
    if isinstance(node, Struct):
        return list(node.fields)
    return list(node.children())
