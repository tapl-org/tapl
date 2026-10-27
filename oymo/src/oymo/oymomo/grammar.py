# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Surface syntax of oymomo.

    expression ::= λx. expression | let x = expression in expression
                 | if expression then expression else expression | apply
    apply      ::= apply project | fix project | project
    project    ::= project.name | primary
    primary    ::= b | {fields} | (expression) | $i | name

A lambda is written `λx. t` or, in ASCII, `\\x. t`; it extends as far right as possible, so as an operand it needs parentheses. `fix t` parses as an application does: `fix g.l a` is `(fix (g.l)) a`. A struct's labels are unique, except the empty
label of an unlabeled field.

`parse` gives each term and field a span (`oymo.core.spans`) of its characters in `text`:
start and length count characters from 0. `source.read` turns them into spans of the
file's row, in UTF-8 bytes.
"""

import unicodedata

from oymo.core import spans, syntax
from oymo.core.peg import MISMATCH, Clause, First, Memoized, Parser, Ref, Separated, Seq, ZeroOrMore, drop
from oymo.core.terminals import Comment, Eof, Fixed, HexBytes, Identifier, Integer, String, Whitespace
from oymo.oymomo import rule_names as rn
from oymo.oymomo import terms

RESERVED = frozenset({'if', 'then', 'else', 'let', 'in', 'fix'})

TRIVIA = Memoized(ZeroOrMore(First(Whitespace(' \t\r\n'), Comment('//'))))


def _skip_trivia(text, pos):
    """Mirrors TRIVIA, so a span starts at the first token rather than at leading trivia."""
    while pos < len(text):
        if text[pos] in ' \t\r\n':
            pos += 1
        elif text.startswith('//', pos):
            while pos < len(text) and text[pos] not in '\r\n':
                pos += 1
        else:
            break
    return pos


def _span(ctx):
    start = _skip_trivia(ctx.text, ctx.pos)
    return spans.make(start, ctx.end - start)


def _token_span(ctx):
    return spans.make(ctx.token_pos, ctx.end - ctx.token_pos)


def _punct(*literals, word_chars=None):
    if word_chars is None:
        return Fixed(*literals, skip=TRIVIA, action=drop)
    return Fixed(*literals, word_chars=word_chars, skip=TRIVIA, action=drop)


def _decode_quoted_name(body):
    """Decodes `\\"`, `\\\\` and `\\u{hex}`. Returns None for an empty name or a bad escape."""
    chars, p = [], 0
    while p < len(body):
        c = body[p]
        if c != '\\':
            chars.append(c)
            p += 1
            continue
        escaped = body[p + 1 : p + 2]
        if escaped in ('"', '\\'):
            chars.append(escaped)
            p += 2
        elif escaped == 'u' and body.startswith('{', p + 2):
            close = body.find('}', p + 3)
            digits = body[p + 3 : close] if close >= 0 else ''
            if not digits or any(d not in '0123456789abcdefABCDEF' for d in digits):
                return None
            try:
                char = chr(int(digits, 16))
            except (ValueError, OverflowError):
                return None
            if unicodedata.category(char) == 'Cs':
                return None
            chars.append(char)
            p = close + 1
        else:
            return None
    return ''.join(chars) or None


class _QuotedName(String):
    def __init__(self, *, skip):
        super().__init__(
            quote='"',
            skip=skip,
            action=lambda c: (name, _token_span(c)) if (name := _decode_quoted_name(c.body)) else None,
        )

    def match(self, parser, pos):
        m = super().match(parser, pos)
        return MISMATCH if m.value is None else m


def is_text_char(char: str) -> bool:
    """Whether a single-quoted byte array may hold `char` as it is: a printable character,
    except `'` and `\\` (no escapes, so `\\` is kept free for adding them later)."""
    return char.isprintable() and char not in "'\\"


class _TextBytes(String):
    """`'text'` as the UTF-8 bytes of its characters."""

    def __init__(self, *, skip):
        super().__init__(
            quote="'",
            escapes=False,
            skip=skip,
            action=lambda c: c.body.encode('utf-8') if all(is_text_char(ch) for ch in c.body) else None,
        )

    def match(self, parser, pos):
        m = super().match(parser, pos)
        return MISMATCH if m.value is None else m


# (name, span) for a plain or a double-quoted identifier.
NAME = Memoized(
    First(
        Identifier(reserved=RESERVED, skip=TRIVIA, action=lambda c: (c.token_text, _token_span(c))),
        _QuotedName(skip=TRIVIA),
    )
)


def _lambda(c):
    (name, _), body = c.values
    return terms.Lambda(param_name=name, body=body, span=_span(c))


def _if(c):
    """`if c then t else e` is `{e, t} c`: `[00]` picks field 0, the else arm."""
    condition, then_clause, else_clause = c.values
    span = _span(c)
    fields = [terms.Field(label='', value=arm, span=getattr(arm, 'span', 0)) for arm in (else_clause, then_clause)]
    return terms.Apply(function=terms.Struct(fields=fields, span=span), argument=condition, span=span)


def _let(c):
    """`let x = e in body` is `(λx. body) e`."""
    (name, _), value, body = c.values
    span = _span(c)
    function = terms.Lambda(param_name=name, body=body, span=span)
    return terms.Apply(function=function, argument=value, span=span)


def _field(c):
    (label, _), value = c.values
    return terms.Field(label=label, value=value, span=_span(c))


def _unlabeled_field(c):
    """A field written without `label =`. Its label is `''`, which no written name can be."""
    return terms.Field(label='', value=c.values[0], span=_span(c))


RULES: dict[str, Clause] = {
    rn.START: Seq(Ref(rn.EXPRESSION), Eof(skip=TRIVIA), action=lambda c: c.values[0]),
    rn.EXPRESSION: First(Ref(rn.LAMBDA), Ref(rn.IF), Ref(rn.LET), Ref(rn.APPLY)),
    # `λ` and `\` are not word characters, so `λx` needs no space.
    rn.LAMBDA: Seq(_punct('λ', '\\', word_chars=''), NAME, _punct('.'), Ref(rn.EXPRESSION), action=_lambda),
    rn.IF: Seq(
        _punct('if'),
        Ref(rn.EXPRESSION),
        _punct('then'),
        Ref(rn.EXPRESSION),
        _punct('else'),
        Ref(rn.EXPRESSION),
        action=_if,
    ),
    rn.LET: Seq(
        _punct('let'),
        NAME,
        _punct('='),
        Ref(rn.EXPRESSION),
        _punct('in'),
        Ref(rn.EXPRESSION),
        action=_let,
    ),
    rn.APPLY: First(
        Seq(
            Ref(rn.APPLY),
            Ref(rn.PROJECT),
            action=lambda c: terms.Apply(function=c.values[0], argument=c.values[1], span=_span(c)),
        ),
        Seq(_punct('fix'), Ref(rn.PROJECT), action=lambda c: terms.Fix(body=c.values[0], span=_span(c))),
        Ref(rn.PROJECT),
    ),
    rn.PROJECT: First(
        Seq(
            Ref(rn.PROJECT),
            _punct('.'),
            NAME,
            action=lambda c: terms.Project(struct=c.values[0], label=c.values[1][0], span=_span(c)),
        ),
        Ref(rn.PRIMARY),
    ),
    rn.PRIMARY: First(Ref(rn.BYTE_ARRAY), Ref(rn.STRUCT), Ref(rn.GROUP), Ref(rn.BRUIJN_INDEX), Ref(rn.VARIABLE)),
    rn.VARIABLE: Seq(NAME, action=lambda c: terms.Variable(name=c.values[0][0], span=c.values[0][1])),
    # `$i`, as the printer writes a BruijnIndex. No trivia between `$` and the digits.
    rn.BRUIJN_INDEX: Seq(
        _punct('$'),
        Integer(bases=(), separator=''),
        action=lambda c: terms.BruijnIndex(index=c.values[0], span=_span(c)),
    ),
    # A field is `label = value` or just `value`. The labeled form is tried first, so `{a}`
    # is an unlabeled field holding the variable `a`, and `{a = b}` is the field `a`.
    rn.STRUCT: Seq(
        _punct('{'),
        Separated(
            First(
                Seq(NAME, _punct('='), Ref(rn.EXPRESSION), action=_field),
                Seq(Ref(rn.EXPRESSION), action=_unlabeled_field),
            ),
            _punct(','),
            trailing=True,
        ),
        _punct('}'),
        action=lambda c: terms.Struct(fields=c.values[0], span=_span(c)),
    ),
    rn.BYTE_ARRAY: Seq(
        First(HexBytes(skip=TRIVIA), _TextBytes(skip=TRIVIA)),
        action=lambda c: terms.ByteArray(value=c.values[0], span=_span(c)),
    ),
    rn.GROUP: Seq(_punct('('), Ref(rn.EXPRESSION), _punct(')'), action=lambda c: c.values[0]),
}


def duplicate_label(term: syntax.Term) -> terms.Field | None:
    """The first field, in source order, whose label an earlier field of the same struct
    already has. Empty labels never clash."""
    if isinstance(term, terms.Struct):
        seen = set()
        for f in term.fields:
            if f.label and f.label in seen:
                return f
            seen.add(f.label)
    for child in term.children():
        if (found := duplicate_label(child)) is not None:
            return found
    return None


def parse(text: str) -> syntax.Term:
    result = Parser().parse(text, rn.START, RULES)
    if result is None:
        return syntax.ErrorTerm(message='Syntax error.', span=spans.make(0, len(text)))
    term = result[1]
    if isinstance(term, syntax.Term):
        if (duplicate := duplicate_label(term)) is not None:
            span = duplicate.span or spans.make(0, len(text))
            return syntax.ErrorTerm(message=f'Duplicate label {duplicate.label!r}.', span=span)
        return term
    raise RuntimeError(f'Unexpected parse result type: {type(term)}')
