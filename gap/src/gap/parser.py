# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Read one Gap term from s-expression text.

A term is '(' fields ')'. A field is a nested term or a string: a bare atom,
or a C-string when the text has special characters. The parser checks spec.md's
arity table and that record labels are pairwise distinct; it does not check
whether a projection hits, whether `fix` wraps a lambda, or whether an `if`
condition is bits.
"""

from __future__ import annotations

import base64
import binascii

from gap import syntax

_SPACE = ' \t\r\n'
_DELIM = ' \t\r\n()"'
_ESCAPES = {
    'n': '\n',
    't': '\t',
    'r': '\r',
    '0': '\x00',
    '\\': '\\',
    '"': '"',
}


class ParseError(Exception):
    pass


def parse(text: str) -> syntax.Term:
    """Parse one term. Binding indexes stay at their defaults."""
    return Parser(text).parse()


class Parser:
    def __init__(self, text: str) -> None:
        self._text = text
        self._pos = 0

    def parse(self) -> syntax.Term:
        term = self._read_term()
        if self._skip_space() != '':
            raise ParseError('unexpected input after the term')
        return term

    def _peek(self) -> str:
        return '' if self._pos >= len(self._text) else self._text[self._pos]

    def _consume(self) -> str:
        character = self._text[self._pos]
        self._pos += 1
        return character

    def _skip_space(self) -> str:
        while self._peek() in _SPACE and self._peek() != '':
            self._consume()
        return self._peek()

    def _close(self, head: str, arity: int) -> None:
        character = self._skip_space()
        if character == '':
            raise ParseError('unclosed (')
        if character != ')':
            plural = '' if arity == 1 else 's'
            raise ParseError(f'({head} …) takes {arity} subpart{plural}')
        self._consume()

    def _read_string(self, expected: str) -> str:
        character = self._skip_space()
        if character in ('', '(', ')'):
            raise ParseError(f'expected {expected}')
        if character == '"':
            return self._read_cstring()
        return self._read_bare()

    def _read_bare(self) -> str:
        start = self._pos
        while self._peek() not in _DELIM and self._peek() != '':
            self._consume()
        return self._text[start : self._pos]

    def _read_cstring(self) -> str:
        self._consume()
        characters: list[str] = []
        while True:
            character = self._peek()
            if character == '':
                raise ParseError('unclosed string')
            self._consume()
            if character == '"':
                return ''.join(characters)
            if character != '\\':
                characters.append(character)
                continue
            escape = self._peek()
            if escape == '':
                raise ParseError('unclosed string')
            self._consume()
            if escape == 'x':
                characters.append(self._read_hex_byte())
                continue
            if escape not in _ESCAPES:
                raise ParseError(f'unknown escape \\{escape}')
            characters.append(_ESCAPES[escape])

    def _read_hex_digit(self) -> str:
        digit = self._peek()
        if digit not in '0123456789abcdefABCDEF':
            raise ParseError('expected two hex digits after \\x')
        return self._consume()

    def _read_hex_byte(self) -> str:
        return chr(int(self._read_hex_digit() + self._read_hex_digit(), 16))

    def _read_term(self) -> syntax.Term:
        if self._skip_space() != '(':
            raise ParseError('a term is a list')
        self._consume()
        if self._skip_space() == ')':
            raise ParseError('the empty list is invalid')
        if self._peek() == '(':
            raise ParseError('a term list starts with a reserved head')
        head = self._read_string('a reserved head')
        match head:
            case 'var':
                return self._read_var()
            case 'bits':
                return self._read_bits()
            case 'lambda':
                return self._read_lambda()
            case 'record':
                return self._read_record()
            case 'get':
                return self._read_get()
            case 'fix':
                return self._read_fix()
            case 'apply':
                return self._read_apply()
            case 'if':
                return self._read_if()
            case _:
                raise ParseError(f'unknown head {head!r}')

    def _read_var(self) -> syntax.Term:
        name = self._read_string('a variable name')
        self._close('var', 1)
        return syntax.Var(name)

    def _read_bits(self) -> syntax.Term:
        text = self._read_string('base64 bits')
        layout = self._read_string('a bits layout')
        self._close('bits', 2)
        try:
            return syntax.Bits(base64.b64decode(text, validate=True), layout)
        except binascii.Error:
            raise ParseError('expected base64 bits') from None

    def _read_lambda(self) -> syntax.Term:
        parameter = self._read_string('a lambda parameter')
        body = self._read_term()
        self._close('lambda', 2)
        return syntax.Lambda(parameter, body)

    def _read_get(self) -> syntax.Term:
        record = self._read_term()
        field = self._read_string('a label')
        self._close('get', 2)
        return syntax.Get(record, field)

    def _read_fix(self) -> syntax.Term:
        term = self._read_term()
        self._close('fix', 1)
        return syntax.Fix(term)

    def _read_apply(self) -> syntax.Term:
        function = self._read_term()
        argument = self._read_term()
        self._close('apply', 2)
        return syntax.Apply(function, argument)

    def _read_if(self) -> syntax.Term:
        condition = self._read_term()
        true = self._read_term()
        false = self._read_term()
        self._close('if', 3)
        return syntax.If(condition, true, false)

    def _read_record(self) -> syntax.Term:
        fields: list[tuple[str, syntax.Term]] = []
        while self._skip_space() != ')':
            if self._peek() == '':
                raise ParseError('unclosed (')
            label = self._read_string('a label')
            if any(field[0] == label for field in fields):
                raise ParseError(f'record repeats the label {label!r}')
            if self._read_string("'='") != '=':
                raise ParseError(f"'=' after the label {label!r}")
            fields.append((label, self._read_term()))
        self._consume()
        if not fields:
            raise ParseError('a record needs at least one field')
        return syntax.Record(fields)
