# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Terminal clauses: every clause that reads characters. Combinators live in peg.py."""

from __future__ import annotations

import string

from oymo.core.peg import MISMATCH, SKIP, Clause, Ctx

IDENT_START = frozenset(string.ascii_letters + '_')
IDENT_CONTINUE = IDENT_START | frozenset(string.digits)

_DIGITS = {
    2: frozenset('01'),
    8: frozenset('01234567'),
    10: frozenset(string.digits),
    16: frozenset(string.hexdigits),
}


def _longest_first(items):
    return tuple(sorted(items, key=len, reverse=True))


def _scan_digits(text, pos, digits, separator):
    """One or more digits; a single separator is allowed only between two digits.
    Returns the end position, or -1."""
    n = len(text)
    if pos >= n or text[pos] not in digits:
        return -1
    p = pos + 1
    while p < n:
        if text[p] in digits:
            p += 1
        elif separator and text[p] == separator and p + 1 < n and text[p + 1] in digits:
            p += 2
        else:
            break
    return p


def _match_suffix(text, pos, suffixes):
    for suffix in suffixes:
        if text.startswith(suffix, pos):
            return suffix, pos + len(suffix)
    return None, pos


def _continues_word(text, pos, word_chars=IDENT_CONTINUE):
    return pos < len(text) and text[pos] in word_chars


# ---- character terminals ---------------------------------------------------


class TerminalCtx(Ctx):
    __slots__ = ()


class Char(Clause):
    def __init__(self, c, action=None):
        super().__init__(action)
        self.c = c

    def default_action(self, ctx):
        return ctx.consumed

    def match(self, parser, pos):
        if pos < len(parser.text) and parser.text[pos] == self.c:
            return self.make(TerminalCtx(parser.text, pos, 1))
        return MISMATCH


class Range(Clause):
    def __init__(self, lo, hi, action=None):
        super().__init__(action)
        self.lo, self.hi = lo, hi

    def default_action(self, ctx):
        return ctx.consumed

    def match(self, parser, pos):
        if pos < len(parser.text) and self.lo <= parser.text[pos] <= self.hi:
            return self.make(TerminalCtx(parser.text, pos, 1))
        return MISMATCH


class Str(Clause):
    def __init__(self, literal, action=None):
        super().__init__(action)
        self.literal = literal

    def default_action(self, ctx):
        return ctx.consumed

    def match(self, parser, pos):
        if parser.text.startswith(self.literal, pos):
            return self.make(TerminalCtx(parser.text, pos, len(self.literal)))
        return MISMATCH


class Any(Clause):
    """Matches any single character."""

    def default_action(self, ctx):
        return ctx.consumed

    def match(self, parser, pos):
        if pos < len(parser.text):
            return self.make(TerminalCtx(parser.text, pos, 1))
        return MISMATCH


# ---- trivia ----------------------------------------------------------------


class Whitespace(Clause):
    """One or more characters from `chars`. Leave '\\n' out when newlines are significant."""

    def __init__(self, chars=' \t', action=None):
        super().__init__(action)
        self.chars = frozenset(chars)

    def default_action(self, ctx):
        return ctx.consumed

    def match(self, parser, pos):
        text, p = parser.text, pos
        while p < len(text) and text[p] in self.chars:
            p += 1
        if p == pos:
            return MISMATCH
        return self.make(TerminalCtx(text, pos, p - pos))


class Comment(Clause):
    """Line comment: `marker` up to, not including, the line break."""

    def __init__(self, marker, action=None):
        super().__init__(action)
        self.marker = marker

    def default_action(self, ctx):
        return ctx.consumed

    def match(self, parser, pos):
        text = parser.text
        if not text.startswith(self.marker, pos):
            return MISMATCH
        p = pos + len(self.marker)
        while p < len(text) and text[p] not in '\r\n':
            p += 1
        return self.make(TerminalCtx(text, pos, p - pos))


# ---- tokens ----------------------------------------------------------------


class TokenCtx(Ctx):
    """`consumed` includes the skipped trivia; `token_text` is the token alone."""

    __slots__ = ('token_pos',)

    def __init__(self, text, pos, length, token_pos):
        super().__init__(text, pos, length)
        self.token_pos = token_pos

    @property
    def token_text(self):
        return self.text[self.token_pos : self.end]


class Token(Clause):
    """A terminal that first skips `skip` (typically a Memoized clause over whitespace
    and comments), then matches its own text. A mismatching `skip` skips nothing."""

    def __init__(self, *, skip=None, action=None):
        super().__init__(action)
        self.skip = skip

    def default_action(self, ctx):
        return ctx.token_text

    def skip_trivia(self, parser, pos):
        if self.skip is None:
            return pos
        m = self.skip.match(parser, pos)
        return pos if m is MISMATCH else pos + m.len


class Fixed(Token):
    """One of the given literals, tried longest first. A literal ending in a word
    character must not be followed by one, so `if` does not match the start of `iffy`."""

    def __init__(self, *literals, word_chars=IDENT_CONTINUE, skip=None, action=None):
        super().__init__(skip=skip, action=action)
        if not literals or '' in literals:
            raise ValueError('Fixed needs at least one non-empty literal.')
        self.literals = _longest_first(literals)
        self.word_chars = word_chars

    def match(self, parser, pos):
        text, start = parser.text, self.skip_trivia(parser, pos)
        for literal in self.literals:
            if not text.startswith(literal, start):
                continue
            end = start + len(literal)
            if literal[-1] in self.word_chars and _continues_word(text, end, self.word_chars):
                continue
            return self.make(TokenCtx(text, pos, end - pos, start))
        return MISMATCH


class Identifier(Token):
    """A `start` character followed by `cont` characters, not in `reserved`.
    `start` and `cont` are anything supporting `in` on a single character."""

    def __init__(self, *, start=IDENT_START, cont=IDENT_CONTINUE, reserved=(), skip=None, action=None):
        super().__init__(skip=skip, action=action)
        self.start, self.cont, self.reserved = start, cont, frozenset(reserved)

    def match(self, parser, pos):
        text, start = parser.text, self.skip_trivia(parser, pos)
        if start >= len(text) or text[start] not in self.start:
            return MISMATCH
        end = start + 1
        while end < len(text) and text[end] in self.cont:
            end += 1
        if text[start:end] in self.reserved:
            return MISMATCH
        return self.make(TokenCtx(text, pos, end - pos, start))


class NumberCtx(TokenCtx):
    __slots__ = ('suffix', 'value')  # suffix is None when absent

    def __init__(self, text, pos, length, token_pos, value, suffix):
        super().__init__(text, pos, length, token_pos)
        self.value, self.suffix = value, suffix


class Integer(Token):
    """Digits in base 10, or in the base of a prefix from `bases`, with `separator`
    allowed between digits and an optional suffix. The value is an int.
    Put Float before Integer in a First, since `1.5` starts with the integer `1`."""

    def __init__(
        self,
        *,
        bases=(('0x', 16), ('0o', 8), ('0b', 2)),
        separator='_',
        suffixes=(),
        skip=None,
        action=None,
    ):
        super().__init__(skip=skip, action=action)
        self.bases = tuple(sorted(dict(bases).items(), key=lambda item: len(item[0]), reverse=True))
        self.separator = separator
        self.suffixes = _longest_first(suffixes)

    def default_action(self, ctx):
        return ctx.value

    def match(self, parser, pos):
        text, start = parser.text, self.skip_trivia(parser, pos)
        base, digits_pos = 10, start
        for prefix, prefix_base in self.bases:
            if text.startswith(prefix, start):
                base, digits_pos = prefix_base, start + len(prefix)
                break
        digits_end = _scan_digits(text, digits_pos, _DIGITS[base], self.separator)
        if digits_end < 0:
            return MISMATCH
        suffix, end = _match_suffix(text, digits_end, self.suffixes)
        if _continues_word(text, end):
            return MISMATCH
        digits = text[digits_pos:digits_end]
        if self.separator:
            digits = digits.replace(self.separator, '')
        return self.make(NumberCtx(text, pos, end - pos, start, int(digits, base), suffix))


class Float(Token):
    """Decimal `digits '.' digits exponent?` or `digits exponent`, with `separator`
    allowed between digits and an optional suffix. The value is a float.
    `.5` and `1.` are not accepted, so `1.foo` stays an integer followed by `.`."""

    def __init__(self, *, separator='_', exponent=True, suffixes=(), skip=None, action=None):
        super().__init__(skip=skip, action=action)
        self.separator = separator
        self.exponent = exponent
        self.suffixes = _longest_first(suffixes)

    def default_action(self, ctx):
        return ctx.value

    def match(self, parser, pos):
        text, start = parser.text, self.skip_trivia(parser, pos)
        digits = _DIGITS[10]
        p = _scan_digits(text, start, digits, self.separator)
        if p < 0:
            return MISMATCH
        has_fraction = has_exponent = False
        if text.startswith('.', p):
            q = _scan_digits(text, p + 1, digits, self.separator)
            if q >= 0:
                p, has_fraction = q, True
        if self.exponent and p < len(text) and text[p] in 'eE':
            q = p + 1
            if q < len(text) and text[q] in '+-':
                q += 1
            q = _scan_digits(text, q, digits, self.separator)
            if q >= 0:
                p, has_exponent = q, True
        if not (has_fraction or has_exponent):
            return MISMATCH
        suffix, end = _match_suffix(text, p, self.suffixes)
        if _continues_word(text, end):
            return MISMATCH
        number = text[start:p]
        if self.separator:
            number = number.replace(self.separator, '')
        return self.make(NumberCtx(text, pos, end - pos, start, float(number), suffix))


class StringCtx(TokenCtx):
    __slots__ = ('body', 'prefix')  # body is the raw text between the quotes

    def __init__(self, text, pos, length, token_pos, prefix, body):
        super().__init__(text, pos, length, token_pos)
        self.prefix, self.body = prefix, body


class String(Token):
    """An optional prefix from `prefixes`, then `quote` ... `quote`. With `escapes`,
    a backslash makes the next character part of the body. Without `multiline`, a line
    break in the body is a mismatch. Escapes are not decoded: the value is `token_text`,
    and the ctx also has `prefix` ('' when absent) and the raw `body`."""

    def __init__(self, *, quote='"', escapes=True, multiline=False, prefixes=(), skip=None, action=None):
        super().__init__(skip=skip, action=action)
        if not quote:
            raise ValueError('String needs a non-empty quote.')
        self.quote, self.escapes, self.multiline = quote, escapes, multiline
        self.prefixes = _longest_first(prefixes)

    def match(self, parser, pos):
        text, start = parser.text, self.skip_trivia(parser, pos)
        quote, n = self.quote, len(parser.text)
        prefix = ''
        for candidate in self.prefixes:
            if text.startswith(candidate, start) and text.startswith(quote, start + len(candidate)):
                prefix = candidate
                break
        if not text.startswith(quote, start + len(prefix)):
            return MISMATCH
        body_pos = p = start + len(prefix) + len(quote)
        while not text.startswith(quote, p):
            if p >= n:
                return MISMATCH
            if self.escapes and text[p] == '\\':
                p += 1
                if p >= n:
                    return MISMATCH
            if not self.multiline and text[p] in '\r\n':
                return MISMATCH
            p += 1
        end = p + len(quote)
        return self.make(StringCtx(text, pos, end - pos, start, prefix, text[body_pos:p]))


class Newline(Token):
    """A line break: '\\r\\n' or '\\n'."""

    def match(self, parser, pos):
        text, start = parser.text, self.skip_trivia(parser, pos)
        for line_break in ('\r\n', '\n'):
            if text.startswith(line_break, start):
                end = start + len(line_break)
                return self.make(TokenCtx(text, pos, end - pos, start))
        return MISMATCH


class Eof(Token):
    """End of text, after the optional trivia."""

    def default_action(self, _ctx):
        return SKIP

    def match(self, parser, pos):
        start = self.skip_trivia(parser, pos)
        if start == len(parser.text):
            return self.make(TokenCtx(parser.text, pos, start - pos, start))
        return MISMATCH
