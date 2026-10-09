# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Surface syntax of the oymomo kernel. See docs/notes.md for the design decisions."""

import unicodedata

from oymo.core import syntax
from oymo.core.peg import MISMATCH, Clause, First, Memoized, Optional, Parser, Ref, Separated, Seq, ZeroOrMore, drop
from oymo.core.terminals import Comment, Eof, Fixed, HexBytes, Identifier, Integer, String, Whitespace
from oymo.oymomo import rule_names as rn
from oymo.oymomo import terms

RESERVED = frozenset({'if', 'then', 'else', 'fix', 'let', 'in'})

TRIVIA = Memoized(ZeroOrMore(First(Whitespace(' \t\r\n'), Comment('//'))))


def _skip_trivia(text, pos):
    """Mirrors TRIVIA, so a Location starts at the first token rather than at leading trivia."""
    while pos < len(text):
        if text[pos] in ' \t\r\n':
            pos += 1
        elif text.startswith('//', pos):
            while pos < len(text) and text[pos] not in '\r\n':
                pos += 1
        else:
            break
    return pos


def _location(ctx):
    return syntax.Location(start=_skip_trivia(ctx.text, ctx.pos), end=ctx.end)


def _token_location(ctx):
    return syntax.Location(start=ctx.token_pos, end=ctx.end)


def _punct(*literals):
    return Fixed(*literals, skip=TRIVIA, action=drop)


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
            action=lambda c: (name, _token_location(c)) if (name := _decode_quoted_name(c.body)) else None,
        )

    def match(self, parser, pos):
        m = super().match(parser, pos)
        return MISMATCH if m.value is None else m


# Bytes a single-quoted byte array may hold: printable ASCII, except `'` and `\`
# (no escapes, so `\` is kept free for adding them later).
ASCII_TEXT = frozenset(chr(b) for b in range(0x20, 0x7F)) - {"'", '\\'}


class _AsciiBytes(String):
    """`'text'` as the bytes of its printable-ASCII characters."""

    def __init__(self, *, skip):
        super().__init__(
            quote="'",
            escapes=False,
            skip=skip,
            action=lambda c: c.body.encode('ascii') if all(ch in ASCII_TEXT for ch in c.body) else None,
        )

    def match(self, parser, pos):
        m = super().match(parser, pos)
        return MISMATCH if m.value is None else m


# (name, Location) for a plain or a double-quoted identifier.
NAME = Memoized(
    First(
        Identifier(reserved=RESERVED, skip=TRIVIA, action=lambda c: (c.token_text, _token_location(c))),
        _QuotedName(skip=TRIVIA),
    )
)


# `: form` after a lambda param, a let name or a byte array; omitted means `Empty`.
# A form is any term. A struct, a byte array or a function form is written as it is;
# any other term needs parentheses. So in `x: 'i32' -> x` the form stops at `->`.
FORM_OPT = Optional(
    Seq(_punct(':'), Ref(rn.FORM), action=lambda c: c.values[0]),
    action=lambda c: c.value if c.matched else terms.Empty,
)


def _function_form(c):
    param, result = c.values
    return terms.FunctionForm(param=param, result=result, location=_location(c))


def _lambda(c):
    (name, _), form, body = c.values
    return terms.Lambda(param_name=name, param_form=form, body=body, location=_location(c))


def _if(c):
    condition, then_clause, else_clause = c.values
    return terms.If(condition=condition, then_clause=then_clause, else_clause=else_clause, location=_location(c))


def _let(c):
    """`let x = e in body` is `(x -> body) e`."""
    (name, _), form, value, body = c.values
    location = _location(c)
    function = terms.Lambda(param_name=name, param_form=form, body=body, location=location)
    return terms.Apply(function=function, argument=value, location=location)


def _field(c):
    (label, _), value = c.values
    return terms.Field(label=label, value=value, location=_location(c))


RULES: dict[str, Clause] = {
    rn.START: Seq(Ref(rn.EXPRESSION), Eof(skip=TRIVIA), action=lambda c: c.values[0]),
    rn.EXPRESSION: First(Ref(rn.LAMBDA), Ref(rn.IF), Ref(rn.LET), Ref(rn.ARROW)),
    rn.LAMBDA: Seq(NAME, FORM_OPT, _punct('->', '→'), Ref(rn.EXPRESSION), action=_lambda),
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
        FORM_OPT,
        _punct('='),
        Ref(rn.EXPRESSION),
        _punct('in'),
        Ref(rn.EXPRESSION),
        action=_let,
    ),
    # `P => R` is a FunctionForm. It binds looser than apply and tighter than `->`, so
    # `decls: {} => 'i32' -> defs -> body` keeps `defs` as a lambda binder.
    rn.ARROW: First(
        Seq(Ref(rn.APPLY), _punct('=>', '⇒'), Ref(rn.ARROW), action=_function_form),
        Ref(rn.APPLY),
    ),
    rn.APPLY: First(
        Seq(
            Ref(rn.APPLY),
            Ref(rn.PROJECT),
            action=lambda c: terms.Apply(function=c.values[0], argument=c.values[1], location=_location(c)),
        ),
        Ref(rn.FIX),
        Ref(rn.PROJECT),
    ),
    rn.FIX: Seq(
        _punct('fix'),
        Ref(rn.PROJECT),
        action=lambda c: terms.Fix(function=c.values[0], location=_location(c)),
    ),
    rn.PROJECT: First(
        Seq(
            Ref(rn.PROJECT),
            _punct('.'),
            NAME,
            action=lambda c: terms.Project(struct=c.values[0], label=c.values[1][0], location=_location(c)),
        ),
        Ref(rn.PRIMARY),
    ),
    rn.PRIMARY: First(Ref(rn.BYTE_ARRAY), Ref(rn.STRUCT), Ref(rn.GROUP), Ref(rn.BRUIJN_INDEX), Ref(rn.VARIABLE)),
    rn.VARIABLE: Seq(NAME, action=lambda c: terms.Variable(name=c.values[0][0], location=c.values[0][1])),
    # `$i`, as the printer writes a BruijnIndex. No trivia between `$` and the digits.
    rn.BRUIJN_INDEX: Seq(
        _punct('$'),
        Integer(bases=(), separator=''),
        action=lambda c: terms.BruijnIndex(index=c.values[0], location=_location(c)),
    ),
    rn.STRUCT: Seq(
        _punct('{'),
        Separated(Seq(NAME, _punct('='), Ref(rn.EXPRESSION), action=_field), _punct(','), trailing=True),
        _punct('}'),
        action=lambda c: terms.Struct(fields=c.values[0], location=_location(c)),
    ),
    rn.BYTE_ARRAY: Seq(
        First(HexBytes(skip=TRIVIA), _AsciiBytes(skip=TRIVIA)),
        FORM_OPT,
        action=lambda c: terms.ByteArray(value=c.values[0], form=c.values[1], location=_location(c)),
    ),
    rn.GROUP: Seq(_punct('('), Ref(rn.EXPRESSION), _punct(')'), action=lambda c: c.values[0]),
    rn.FORM: First(
        Seq(Ref(rn.FORM_ATOM), _punct('=>', '⇒'), Ref(rn.FORM), action=_function_form),
        Ref(rn.FORM_ATOM),
    ),
    rn.FORM_ATOM: First(Ref(rn.STRUCT), Ref(rn.BYTE_ARRAY), Ref(rn.GROUP)),
}


def parse(text: str) -> syntax.Term:
    result = Parser().parse(text, rn.START, RULES)
    if result is None:
        return syntax.ErrorTerm(message='Syntax error.', location=syntax.Location(start=0, end=len(text)))
    term = result[1]
    if isinstance(term, syntax.Term):
        return term
    raise RuntimeError(f'Unexpected parse result type: {type(term)}')
