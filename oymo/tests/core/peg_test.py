# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.core.peg import (
    And,
    First,
    Memoized,
    Not,
    OneOrMore,
    Optional,
    Parser,
    Ref,
    Separated,
    Seq,
    ZeroOrMore,
    drop,
)
from oymo.core.tokens import Any, Char, Eof, Range, Str


def parse(text, start, rules):
    return Parser().parse(text, start, rules)


# Left recursion + SKIP: E <- E '+' P / E '-' P / P
LEFT_RECURSION_RULES = {
    'N': Range('0', '9', action=lambda c: int(c.consumed)),
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
    'Num': OneOrMore(Range('0', '9'), action=lambda c: int(c.consumed)),
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


def test_trailing_text_fails_at_eof():
    assert parse('[1] x', 'List', LIST_RULES) is None


LOOKAHEAD_RULES = {
    # Comment <- '#' (!'\n' Any)*
    'Comment': Seq(Str('#'), ZeroOrMore(Seq(Not(Char('\n')), Any())), action=lambda c: c.consumed),
    # Let <- 'let' ![a-z]
    'Let': Seq(Str('let'), Not(Range('a', 'z')), action=lambda c: c.consumed),
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
    return OneOrMore(Range('a', 'z'), action=lambda c: calls.append(c.pos) or c.consumed)


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


DIGIT = Range('0', '9', action=lambda c: int(c.consumed))
SEPARATED_RULES = {
    'Strict': Separated(DIGIT, Char(',')),
    'Trailing': Separated(DIGIT, Char(','), trailing=True),
    'StrictAll': Seq(Separated(DIGIT, Char(',')), Eof()),
    'TrailingAll': Seq(Separated(DIGIT, Char(','), trailing=True), Eof()),
}


def test_separated_values_exclude_separators():
    assert parse('1,2,3', 'Strict', SEPARATED_RULES) == (5, [1, 2, 3])


def test_separated_single_item():
    assert parse('7', 'Strict', SEPARATED_RULES) == (1, [7])


def test_separated_zero_items():
    assert parse('x', 'Strict', SEPARATED_RULES) == (0, [])


def test_separated_leaves_trailing_separator_unconsumed():
    assert parse('1,2,', 'Strict', SEPARATED_RULES) == (3, [1, 2])
    assert parse('1,2,', 'StrictAll', SEPARATED_RULES) is None


def test_separated_consumes_trailing_separator():
    assert parse('1,2,', 'Trailing', SEPARATED_RULES) == (4, [1, 2])
    assert parse('1,2,', 'TrailingAll', SEPARATED_RULES) == (4, [[1, 2]])


def test_separated_trailing_is_optional():
    assert parse('1,2', 'TrailingAll', SEPARATED_RULES) == (3, [[1, 2]])


def test_separated_trailing_only_one_separator():
    assert parse('1,,', 'Trailing', SEPARATED_RULES) == (2, [1])


def test_separated_lone_separator_is_not_trailing():
    assert parse(',', 'Trailing', SEPARATED_RULES) == (0, [])
