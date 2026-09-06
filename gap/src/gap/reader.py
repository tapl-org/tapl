# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Text to Term.

Every term is a list with a reserved head, so a bare name or token is not a
term: a variable is `(var x)`, bits are `(bits 42)`, a projection is
`(get t l)`.

The reader checks the arity table of gap/spec.md: reserved heads only, the
right number of subterms, `var` names and labels and lambda parameters that are
names rather than bits, and pairwise distinct labels in one record. It does not check
whether a projection will find its field, whether `fix` wraps a lambda, or
whether an `if` condition is bits; those stay for reduction, which leaves them
residual instead of failing.
"""

import enum
import re
from dataclasses import dataclass

from gap.error import ReadError
from gap.term import Abs, App, Bits, BitsKind, Bound, Field, Fix, Free, If, Proj, Record, Term

_INTEGER = re.compile(r'[0-9]+\Z')
_HEX = re.compile(r'0x[0-9A-Fa-f]+\Z')
_PUNCTUATION = {'(': 'OPEN', ')': 'CLOSE', '=': 'EQUAL'}
_DELIMITERS = set('().="') | set(' \t\r\n')
_TERM_ARITY = {'fix': 1, 'apply': 2, 'if': 3}  # heads whose subparts are all terms
_HEADS = ('var', 'bits', 'lambda', 'record', 'get', 'fix', 'apply', 'if')


class TokenKind(enum.Enum):
    OPEN = 'OPEN'
    CLOSE = 'CLOSE'
    EQUAL = 'EQUAL'
    ATOM = 'ATOM'
    BITS = 'BITS'
    END = 'END'


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    text: str
    position: int
    bits_kind: BitsKind | None = None  # set exactly when kind is BITS

    def bits(self) -> Bits:
        if self.bits_kind is None:
            raise _unexpected('bits', self)
        return Bits(self.bits_kind, self.text)


def tokenize(text: str) -> list[Token]:
    """Split `text` into tokens. A token that matches `b` is bits, never a variable."""
    tokens: list[Token] = []
    position = 0
    while position < len(text):
        character = text[position]
        if character.isspace():
            position += 1
        elif character in _PUNCTUATION:
            tokens.append(Token(TokenKind[_PUNCTUATION[character]], character, position))
            position += 1
        elif character == '.':
            raise ReadError("'.' is not part of the syntax; write a projection as (get t l)", position)
        elif character == '"':
            end = text.find('"', position + 1)
            if end < 0:
                raise ReadError('unterminated string', position)
            tokens.append(Token(TokenKind.BITS, text[position : end + 1], position, BitsKind.STRING))
            position = end + 1
        else:
            end = position
            while end < len(text) and text[end] not in _DELIMITERS:
                end += 1
            tokens.append(_atom_or_bits(text[position:end], position))
            position = end
    tokens.append(Token(TokenKind.END, '', len(text)))
    return tokens


def _atom_or_bits(text: str, position: int) -> Token:
    if _HEX.match(text):
        return Token(TokenKind.BITS, text, position, BitsKind.HEX)
    if _INTEGER.match(text):
        return Token(TokenKind.BITS, text, position, BitsKind.INTEGER)
    if text[0].isdigit():
        raise ReadError(f'{text!r} starts like bits but matches no bits syntax', position)
    return Token(TokenKind.ATOM, text, position)


def _unexpected(what: str, token: Token) -> ReadError:
    found = f', found {token.text!r}' if token.text else ''
    return ReadError(f'expected {what}{found}', token.position)


class Reader:
    def __init__(self, text: str):
        self._tokens = tokenize(text)
        self._index = 0
        self._binders: list[str] = []  # innermost last; an occurrence reads its de Bruijn index here

    def read(self) -> Term:
        term = self._read_term()
        token = self._peek()
        if token.kind is not TokenKind.END:
            raise ReadError(f'unexpected {token.text!r} after the term', token.position)
        return term

    def _peek(self) -> Token:
        return self._tokens[self._index]

    def _advance(self) -> Token:
        token = self._tokens[self._index]
        self._index += 1
        return token

    def _expect(self, kind: TokenKind, what: str) -> Token:
        token = self._advance()
        if token.kind is not kind:
            raise _unexpected(what, token)
        return token

    def _read_term(self) -> Term:
        token = self._advance()
        if token.kind is not TokenKind.OPEN:
            raise _unexpected("'(' to open a term", token)
        return self._read_form()

    def _read_name(self, what: str) -> Token:
        """A name: an atom that is not bits. Labels, lambda parameters, and `var` names are names."""
        token = self._advance()
        if token.kind is TokenKind.BITS:
            raise ReadError(f'{token.text!r} is bits, so it cannot be {what}', token.position)
        if token.kind is not TokenKind.ATOM:
            raise _unexpected(what, token)
        return token

    def _read_form(self) -> Term:
        head = self._advance()
        if head.kind is TokenKind.CLOSE:
            raise ReadError('the empty list is invalid', head.position)
        if head.kind is not TokenKind.ATOM or head.text not in _HEADS:
            raise ReadError(f'{head.text!r} is not a head; the heads are {", ".join(_HEADS)}', head.position)
        match head.text:
            case 'var':
                return self._read_var(head)
            case 'bits':
                return self._read_bits(head)
            case 'lambda':
                return self._read_lambda(head)
            case 'record':
                return self._read_record(head)
            case 'get':
                return self._read_get(head)
            case _:
                arity = _TERM_ARITY[head.text]
                subterms = [self._read_term() for _ in range(arity)]
                self._close(head, arity)
                if head.text == 'fix':
                    return Fix(subterms[0])
                if head.text == 'apply':
                    return App(subterms[0], subterms[1])
                return If(subterms[0], subterms[1], subterms[2])

    def _read_var(self, head: Token) -> Term:
        name = self._read_name('a variable name').text
        self._close(head, 1)
        for depth, binder in enumerate(reversed(self._binders)):
            if binder == name:
                return Bound(depth, name)
        return Free(name)

    def _read_bits(self, head: Token) -> Term:
        token = self._advance()
        if token.kind is not TokenKind.BITS:
            raise _unexpected('a bits token', token)
        self._close(head, 1)
        return token.bits()

    def _read_get(self, head: Token) -> Term:
        subject = self._read_term()
        label = self._read_name('a label').text
        self._close(head, 2)
        return Proj(subject, label)

    def _read_lambda(self, head: Token) -> Term:
        parameter = self._read_name('a lambda parameter')
        self._binders.append(parameter.text)
        try:
            body = self._read_term()
        finally:
            self._binders.pop()
        self._close(head, 2)
        return Abs(parameter.text, body)

    def _read_record(self, head: Token) -> Term:
        fields: list[Field] = []
        while self._peek().kind is not TokenKind.CLOSE:
            if self._peek().kind is TokenKind.END:
                raise ReadError('unclosed (record …)', self._peek().position)
            label = self._read_name('a label')
            if any(field.label == label.text for field in fields):
                raise ReadError(f'record repeats the label {label.text!r}', label.position)
            self._expect(TokenKind.EQUAL, f"'=' after the label {label.text!r}")
            fields.append(Field(label.text, self._read_term()))
        self._advance()
        if not fields:
            raise ReadError('a record needs at least one field', head.position)
        return Record(tuple(fields))

    def _close(self, head: Token, arity: int) -> None:
        token = self._peek()
        if token.kind is not TokenKind.CLOSE:
            plural = '' if arity == 1 else 's'
            raise ReadError(f'({head.text} …) takes {arity} subpart{plural}', head.position)
        self._advance()


def read(text: str) -> Term:
    """Read one term. Names the term leaves unbound become `Free`."""
    return Reader(text).read()
