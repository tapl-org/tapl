# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# Left recursion cases from Fig. 2 of "The Squirrel Parser" (Hutchison, arXiv:2601.05012).
# Every rule reference yields (rule_name, value), so results mirror the paper's parse trees.

from oymo.core.peg import First, OneOrMore, Optional, Parser, Ref, Seq, ZeroOrMore
from oymo.core.tokens import Char, Range, Str


def node(name):
    return Ref(name, action=lambda c: (c.name, c.value))


def parse_tree(text, start, rules):
    return Parser().parse(text, '_start', {**rules, '_start': node(start)})


def test_direct_left_recursion():
    # (a) A <- (A 'x') / 'x';
    rules = {'A': First(Seq(node('A'), Char('x')), Char('x'))}
    a1 = ('A', 'x')
    a2 = ('A', [a1, 'x'])
    a3 = ('A', [a2, 'x'])
    assert parse_tree('xxx', 'A', rules) == (3, a3)


def test_indirect_left_recursion():
    # (b) A <- B / 'x';  B <- (A 'y') / (A 'x');
    rules = {
        'A': First(node('B'), Char('x')),
        'B': First(Seq(node('A'), Char('y')), Seq(node('A'), Char('x'))),
    }
    a1 = ('A', 'x')
    a2 = ('A', ('B', [a1, 'x']))
    a3 = ('A', ('B', [a2, 'y']))
    a4 = ('A', ('B', [a3, 'x']))
    assert parse_tree('xxyx', 'A', rules) == (4, a4)


def test_input_dependent_left_recursion_first():
    # (c) A <- B / 'z';  B <- ('x' A) / (A 'y');
    rules = {
        'A': First(node('B'), Char('z')),
        'B': First(Seq(Char('x'), node('A')), Seq(node('A'), Char('y'))),
    }
    z = ('A', 'z')
    zy = ('A', ('B', [z, 'y']))
    zyy = ('A', ('B', [zy, 'y']))
    zyyy = ('A', ('B', [zyy, 'y']))
    xzyyy = ('A', ('B', ['x', zyyy]))
    xxzyyy = ('A', ('B', ['x', xzyyy]))
    assert parse_tree('xxzyyy', 'A', rules) == (6, xxzyyy)


def test_input_dependent_left_recursion_optional():
    # (d) A <- 'x'? (A 'y' / A / 'y');
    rules = {'A': Seq(Optional(Char('x')), First(Seq(node('A'), Char('y')), node('A'), Char('y')))}
    y = ('A', [None, 'y'])
    yy = ('A', [None, [y, 'y']])
    yyy = ('A', [None, [yy, 'y']])
    xyyy = ('A', ['x', yyy])
    xxyyy = ('A', ['x', xyyy])
    assert parse_tree('xxyyy', 'A', rules) == (5, xxyyy)


def test_interwoven_left_recursion_three_cycles():
    # (e) S <- E;  E <- F 'n' / 'n';  F <- E '+' I* / G '-';  G <- H 'm' / E;
    #     H <- G 'l';  I <- '(' A+ ')';  A <- 'a';
    rules = {
        'S': node('E'),
        'E': First(Seq(node('F'), Char('n')), Char('n')),
        'F': First(Seq(node('E'), Char('+'), ZeroOrMore(node('I'))), Seq(node('G'), Char('-'))),
        'G': First(Seq(node('H'), Char('m')), node('E')),
        'H': Seq(node('G'), Char('l')),
        'I': Seq(Char('('), OneOrMore(node('A')), Char(')')),
        'A': Char('a'),
    }
    g_n = ('G', ('E', 'n'))
    h = ('H', [g_n, 'l'])
    g = ('G', [h, 'm'])
    f_minus = ('F', [g, '-'])
    e5 = ('E', [f_minus, 'n'])
    i = ('I', ['(', [('A', 'a')] * 3, ')'])
    f_plus = ('F', [e5, '+', [i]])
    e12 = ('E', [f_plus, 'n'])
    assert parse_tree('nlm-n+(aaa)n', 'S', rules) == (12, ('S', e12))


def test_interwoven_left_recursion_two_cycles():
    # (f) M <- L;  L <- P ".x" / 'x';  P <- P "(n)" / L;
    rules = {
        'M': node('L'),
        'L': First(Seq(node('P'), Str('.x')), Char('x')),
        'P': First(Seq(node('P'), Str('(n)')), node('L')),
    }
    p1 = ('P', ('L', 'x'))
    p3 = ('P', ('L', [p1, '.x']))
    p6 = ('P', [p3, '(n)'])
    p9 = ('P', [p6, '(n)'])
    p11 = ('P', ('L', [p9, '.x']))
    l13 = ('L', [p11, '.x'])
    assert parse_tree('x.x(n)(n).x.x', 'M', rules) == (13, ('M', l13))


def n(digit):
    return ('N', [digit])


N_RULE = OneOrMore(Range('0', '9'))


def test_explicit_left_associativity():
    # (g) E <- E '+' N / N;  N <- [0-9]+;
    rules = {'E': First(Seq(node('E'), Char('+'), node('N')), node('N')), 'N': N_RULE}
    e0 = ('E', n('0'))
    e01 = ('E', [e0, '+', n('1')])
    e012 = ('E', [e01, '+', n('2')])
    e0123 = ('E', [e012, '+', n('3')])
    assert parse_tree('0+1+2+3', 'E', rules) == (7, e0123)


def test_explicit_right_associativity():
    # (h) E <- N '+' E / N;  N <- [0-9]+;
    rules = {'E': First(Seq(node('N'), Char('+'), node('E')), node('N')), 'N': N_RULE}
    e3 = ('E', n('3'))
    e23 = ('E', [n('2'), '+', e3])
    e123 = ('E', [n('1'), '+', e23])
    e0123 = ('E', [n('0'), '+', e123])
    assert parse_tree('0+1+2+3', 'E', rules) == (7, e0123)


def test_ambiguous_associativity_is_right_associative():
    # (i) E <- E '+' E / N;  N <- [0-9]+;
    rules = {'E': First(Seq(node('E'), Char('+'), node('E')), node('N')), 'N': N_RULE}
    e3 = ('E', n('3'))
    e23 = ('E', [('E', n('2')), '+', e3])
    e123 = ('E', [('E', n('1')), '+', e23])
    e0123 = ('E', [('E', n('0')), '+', e123])
    assert parse_tree('0+1+2+3', 'E', rules) == (7, e0123)
