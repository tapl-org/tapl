# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.core.peg import First, Memoized, Parser, Seq, ZeroOrMore
from oymo.core.terminals import (
    Comment,
    Eof,
    Fixed,
    Float,
    HexBytes,
    Identifier,
    Integer,
    Newline,
    String,
    Whitespace,
)


def parse(text, clause):
    return Parser().parse(text, 'S', {'S': clause})


TRIVIA = Memoized(ZeroOrMore(First(Whitespace(), Comment('#'))))


# ---- Fixed -----------------------------------------------------------------


def test_fixed_word_needs_boundary():
    assert parse('if x', Fixed('if')) == (2, 'if')
    assert parse('iffy', Fixed('if')) is None


def test_fixed_symbols_longest_first():
    assert parse('>>= 1', Fixed('>', '>>', '>>=')) == (3, '>>=')
    assert parse('>> 1', Fixed('>', '>>', '>>=')) == (2, '>>')
    assert parse('>a', Fixed('>', '>>', '>>=')) == (1, '>')


def test_fixed_symbol_needs_no_boundary():
    assert parse('+x', Fixed('+')) == (1, '+')


def test_fixed_word_falls_back_to_shorter_literal():
    assert parse('in x', Fixed('in', 'instanceof')) == (2, 'in')
    assert parse('instanceof x', Fixed('in', 'instanceof')) == (10, 'instanceof')
    assert parse('inside', Fixed('in', 'instanceof')) is None


# ---- Identifier ------------------------------------------------------------


def test_identifier():
    assert parse('_foo1 bar', Identifier()) == (5, '_foo1')
    assert parse('1foo', Identifier()) is None


def test_identifier_rejects_reserved_words_only_as_whole_words():
    ident = Identifier(reserved={'if'})
    assert parse('if', ident) is None
    assert parse('iffy', ident) == (4, 'iffy')


def test_identifier_custom_classes():
    assert parse('$el', Identifier(start='$abcdefghijklmnopqrstuvwxyz')) == (3, '$el')


# ---- Integer ---------------------------------------------------------------


def test_integer_bases():
    assert parse('42', Integer()) == (2, 42)
    assert parse('0xFF', Integer()) == (4, 255)
    assert parse('0o17', Integer()) == (4, 15)
    assert parse('0b101', Integer()) == (5, 5)


def test_integer_separator():
    assert parse('1_000_000', Integer()) == (9, 1000000)
    assert parse('0xFF_FF', Integer()) == (7, 0xFFFF)


def test_integer_bad_separators():
    assert parse('1__0', Integer()) is None
    assert parse('_1', Integer()) is None
    assert parse('1_', Integer()) is None


def test_integer_prefix_without_digits():
    assert parse('0x', Integer()) is None
    assert parse('0xG', Integer()) is None


def test_integer_followed_by_word_char():
    assert parse('12abc', Integer()) is None


def test_integer_suffix():
    rules = Integer(suffixes=('u8', 'u16', 'i32'), action=lambda c: (c.value, c.suffix))
    assert parse('255u8', rules) == (5, (255, 'u8'))
    assert parse('7u16', rules) == (4, (7, 'u16'))
    assert parse('7', rules) == (1, (7, None))
    assert parse('7u', rules) is None


def test_integer_stops_before_dot():
    assert parse('1.foo', Integer()) == (1, 1)


# ---- Float -----------------------------------------------------------------


def test_float_forms():
    assert parse('3.14', Float()) == (4, 3.14)
    assert parse('1.5e-3', Float()) == (6, 1.5e-3)
    assert parse('2E+2', Float()) == (4, 200.0)
    assert parse('1_000.000_1', Float()) == (11, 1000.0001)


def test_float_rejects_integers_and_partial_forms():
    assert parse('42', Float()) is None
    assert parse('1.foo', Float()) is None
    assert parse('1.', Float()) is None
    assert parse('.5', Float()) is None
    assert parse('1.5e', Float()) is None


def test_float_without_exponent():
    assert parse('1e5', Float(exponent=False)) is None


def test_float_suffix():
    rules = Float(suffixes=('f32', 'f64'), action=lambda c: (c.value, c.suffix))
    assert parse('1.5f32', rules) == (6, (1.5, 'f32'))


def test_float_before_integer_in_first():
    number = First(Float(), Integer())
    assert parse('1.5', number) == (3, 1.5)
    assert parse('15', number) == (2, 15)


# ---- String ----------------------------------------------------------------


def test_string():
    assert parse('"hi" x', String()) == (4, '"hi"')


def test_string_escapes():
    rules = String(action=lambda c: c.body)
    assert parse(r'"a\"b"', rules) == (6, r'a\"b')
    assert parse(r'"a\\"', rules) == (5, r'a\\')


def test_string_without_escapes():
    assert parse(r'"a\"', String(escapes=False, action=lambda c: c.body)) == (4, 'a\\')


def test_string_unterminated():
    assert parse('"abc', String()) is None
    assert parse('"abc\\', String()) is None


def test_string_single_line_rejects_line_break():
    assert parse('"a\nb"', String()) is None
    assert parse('"a\\\nb"', String()) is None


def test_string_multiline():
    rules = String(quote='"""', multiline=True, action=lambda c: c.body)
    assert parse('"""a\n"b"\n"""', rules) == (12, 'a\n"b"\n')


def test_string_prefixes():
    rules = String(prefixes=('r', 'b', 'rb'), action=lambda c: (c.prefix, c.body))
    assert parse('rb"x"', rules) == (5, ('rb', 'x'))
    assert parse('"x"', rules) == (3, ('', 'x'))
    assert parse('f"x"', rules) is None


def test_string_single_quote():
    assert parse("'a'", String(quote="'")) == (3, "'a'")


# ---- HexBytes --------------------------------------------------------------


def test_hex_bytes():
    assert parse('[2a000000] x', HexBytes()) == (10, b'\x2a\x00\x00\x00')
    assert parse('[DeadBeef]', HexBytes()) == (10, b'\xde\xad\xbe\xef')


def test_hex_bytes_groups():
    assert parse('[2a 00 00 00]', HexBytes()) == (13, b'\x2a\x00\x00\x00')
    assert parse('[ 2a00  0000 ]', HexBytes()) == (14, b'\x2a\x00\x00\x00')


def test_hex_bytes_multiline():
    assert parse('[dead\n  beef]', HexBytes()) == (13, b'\xde\xad\xbe\xef')
    assert parse('[dead\r\n\tbeef\n]', HexBytes()) == (14, b'\xde\xad\xbe\xef')


def test_hex_bytes_empty():
    assert parse('[]', HexBytes()) == (2, b'')
    assert parse('[ \n ]', HexBytes()) == (5, b'')


def test_hex_bytes_rejects_bad_forms():
    assert parse('[abc]', HexBytes()) is None
    assert parse('[2a 0]', HexBytes()) is None
    assert parse('[2g]', HexBytes()) is None
    assert parse('[2ag]', HexBytes()) is None
    assert parse('[2a', HexBytes()) is None
    assert parse('[2a // c\n 00]', HexBytes()) is None
    assert parse('2a', HexBytes()) is None


def test_hex_bytes_custom_delimiters():
    assert parse('<<ff>>', HexBytes(open='<<', close='>>')) == (6, b'\xff')


# ---- trivia, Newline, Eof --------------------------------------------------


def test_leading_trivia_is_skipped():
    rules = Identifier(skip=TRIVIA, action=lambda c: (c.token_pos, c.token_text, c.consumed))
    assert parse('   foo', rules) == (6, (3, 'foo', '   foo'))


def test_comment_stops_before_line_break():
    assert parse('# hi\r\nx', Comment('#')) == (4, '# hi')


def test_newline_after_comment():
    assert parse('  # note\n', Newline(skip=TRIVIA)) == (9, '\n')
    line = Seq(Identifier(skip=TRIVIA), Newline(skip=TRIVIA), Identifier(skip=TRIVIA))
    assert parse('a  # c\nb', line) == (8, ['a', '\n', 'b'])


def test_newline_crlf():
    assert parse('\r\n', Newline()) == (2, '\r\n')
    assert parse('\r', Newline()) is None


def test_trivia_without_newline_does_not_join_lines():
    assert parse('a\nb', Seq(Identifier(skip=TRIVIA), Identifier(skip=TRIVIA))) is None


def test_trivia_with_newline_joins_lines():
    trivia = Memoized(ZeroOrMore(Whitespace(' \t\r\n')))
    assert parse('a\n b', Seq(Identifier(skip=trivia), Identifier(skip=trivia))) == (4, ['a', 'b'])


def test_eof_skips_trailing_trivia():
    assert parse('x  # end', Seq(Identifier(), Eof(skip=TRIVIA))) == (8, ['x'])
    assert parse('x  # end', Seq(Identifier(), Eof())) is None


def test_trivia_memoized_across_alternatives():
    calls = []
    trivia = Memoized(ZeroOrMore(Whitespace(action=lambda c: calls.append(c.pos))))
    rules = First(Fixed('if', skip=trivia), Fixed('else', skip=trivia), Identifier(skip=trivia))
    assert parse('   foo', rules) == (6, 'foo')
    assert calls == [0]
