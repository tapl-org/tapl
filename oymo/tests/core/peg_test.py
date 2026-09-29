# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.core.peg import (
    And,
    Any,
    Char,
    Eof,
    First,
    Memoized,
    Not,
    OneOrMore,
    Optional,
    Parser,
    Range,
    Ref,
    Seq,
    Str,
    ZeroOrMore,
    drop,
)


def parse(text, start, rules):
    return Parser().parse(text, start, rules)


# Left recursion + SKIP: E <- E '+' P / E '-' P / P
LEFT_RECURSION_RULES = {
    'N': Range('0', '9', action=lambda c: int(c.text)),
    'Paren': Seq(Char('(', action=drop), Ref('E'), Char(')', action=drop), action=lambda c: c.values[0]),
    'Primary': First(Ref('Paren'), Ref('N')),
    'E': First(
        Seq(Ref('E'), Char('+', action=drop), Ref('Primary'), action=lambda c: c.values[0] + c.values[1]),
        Seq(Ref('E'), Char('-', action=drop), Ref('Primary'), action=lambda c: c.values[0] - c.values[1]),
        Ref('Primary'),
    ),
}


def test_left_associative_with_parens():
    assert parse('9-(3-2)+1', 'E', LEFT_RECURSION_RULES) == (9, 9)


# Repetition, Optional, Eof:  List <- '[' Ws Items? ']' Eof
LIST_RULES = {
    'Ws': ZeroOrMore(Char(' ', action=drop), action=drop),
    'Num': OneOrMore(Range('0', '9'), action=lambda c: int(c.text)),
    'Item': Seq(Ref('Num'), Ref('Ws'), action=lambda c: c.values[0]),
    'Items': Seq(
        Ref('Item'),
        ZeroOrMore(Seq(Char(',', action=drop), Ref('Ws'), Ref('Item'), action=lambda c: c.values[0])),
        action=lambda c: [c.values[0]] + c.values[1],
    ),
    'List': Seq(
        Char('[', action=drop),
        Ref('Ws'),
        Optional(Ref('Items')),
        Char(']', action=drop),
        Eof(),
        action=lambda c: c.values[0] or [],
    ),
}


def test_items_with_whitespace():
    assert parse('[ 1, 22 ,333 ]', 'List', LIST_RULES) == (14, [1, 22, 333])


def test_empty_list():
    assert parse('[]', 'List', LIST_RULES) == (2, [])


def test_trailing_comma_fails():
    assert parse('[1,]', 'List', LIST_RULES) is None


def test_trailing_input_fails_at_eof():
    assert parse('[1] x', 'List', LIST_RULES) is None


LOOKAHEAD_RULES = {
    # Comment <- '#' (!'\n' Any)*
    'Comment': Seq(Str('#'), ZeroOrMore(Seq(Not(Char('\n')), Any())), action=lambda c: c.text),
    # Let <- 'let' ![a-z]
    'Let': Seq(Str('let'), Not(Range('a', 'z')), action=lambda c: c.text),
    'Peek': Seq(And(Str('ab')), Str('a'), action=lambda c: c.values),
}


def test_comment_stops_at_newline():
    assert parse('# hi\nnext', 'Comment', LOOKAHEAD_RULES) == (4, '# hi')


def test_keyword_followed_by_space():
    assert parse('let x', 'Let', LOOKAHEAD_RULES) == (3, 'let')


def test_keyword_prefix_of_identifier_fails():
    assert parse('letter', 'Let', LOOKAHEAD_RULES) is None


def test_and_consumes_nothing():
    assert parse('ab', 'Peek', LOOKAHEAD_RULES) == (1, ['a'])


def counting_word(calls):
    """[a-z]+ that records the position of every evaluation of its action."""
    return OneOrMore(Range('a', 'z'), action=lambda c: calls.append(c.pos) or c.text)


def test_memoized_sub_evaluated_once_across_backtracking():
    calls = []
    word = counting_word(calls)
    rules = {'S': First(Seq(Memoized(word), Char('!')), Seq(Memoized(word), Char('?')))}
    assert parse('hi?', 'S', rules) == (3, ['hi', '?'])
    assert calls == [0]


def test_unmemoized_sub_reevaluated_across_backtracking():
    calls = []
    word = counting_word(calls)
    rules = {'S': First(Seq(word, Char('!')), Seq(word, Char('?')))}
    assert parse('hi?', 'S', rules) == (3, ['hi', '?'])
    assert calls == [0, 0]


def test_memoized_is_per_position():
    calls = []
    word = counting_word(calls)
    rules = {'S': Seq(Memoized(word), Char(' ', action=drop), Memoized(word))}
    assert parse('ab cd', 'S', rules) == (5, ['ab', 'cd'])
    assert calls == [0, 3]


def test_memoized_mismatch():
    assert parse('1', 'S', {'S': Memoized(Range('a', 'z'))}) is None


def test_memoized_action():
    rules = {'S': Memoized(Range('a', 'z'), action=lambda c: c.value.upper())}
    assert parse('q', 'S', rules) == (1, 'Q')
