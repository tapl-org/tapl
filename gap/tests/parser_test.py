# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from gap.parser import ParseError, parse
from gap.syntax import Apply, Bits, Fix, Get, If, Lambda, Record, Var


def test_var() -> None:
    assert parse('(var env)') == Var('env')


def test_var_cstring() -> None:
    assert parse('(var "weird name")') == Var('weird name')


def test_lambda_var() -> None:
    assert parse('(lambda x (var x))') == Lambda('x', Var('x'))


def test_nested_lambda() -> None:
    assert parse('(lambda env (lambda module (var env)))') == Lambda('env', Lambda('module', Var('env')))


def test_bits() -> None:
    assert parse('(bits SGVsbG8= 5xi8)') == Bits(b'Hello', '5xi8')


def test_bits_cstring() -> None:
    assert parse('(bits "SGVsbG8=" 5xi8)') == Bits(b'Hello', '5xi8')


def test_bits_empty() -> None:
    assert parse('(bits "" 0xi8)') == Bits(b'', '0xi8')


def test_apply() -> None:
    assert parse('(apply (var f) (bits SGVsbG8= 5xi8))') == Apply(Var('f'), Bits(b'Hello', '5xi8'))


def test_get() -> None:
    assert parse('(get (var env) puts)') == Get(Var('env'), 'puts')


def test_get_nested() -> None:
    assert parse('(get (get (var env) puts) x)') == Get(Get(Var('env'), 'puts'), 'x')


def test_record() -> None:
    assert parse('(record a = (var x))') == Record([('a', Var('x'))])


def test_record_keeps_written_order() -> None:
    term = parse('(record main = (bits QQ== i32) helper = (bits "" 0xi8))')
    assert term == Record([('main', Bits(b'A', 'i32')), ('helper', Bits(b'', '0xi8'))])


def test_fix() -> None:
    assert parse('(fix (var f))') == Fix(Var('f'))


def test_if() -> None:
    assert parse('(if (var c) (bits QQ== i32) (bits "" 0xi8))') == If(Var('c'), Bits(b'A', 'i32'), Bits(b'', '0xi8'))


def test_cstring_escapes_in_name() -> None:
    assert parse(r'(var "a\nb\t\"c\\")') == Var('a\nb\t"c\\')


def test_cstring_hex() -> None:
    assert parse(r'(var "\x00\x41")') == Var('\x00A')


def test_bare_name_is_not_a_term() -> None:
    with pytest.raises(ParseError, match='a term is a list'):
        parse('env')


def test_empty_list() -> None:
    with pytest.raises(ParseError, match='the empty list is invalid'):
        parse('()')


def test_unknown_head() -> None:
    with pytest.raises(ParseError, match="unknown head 'foo'"):
        parse('(foo x)')


def test_var_arity() -> None:
    with pytest.raises(ParseError, match=r'\(var …\) takes 1 subpart'):
        parse('(var x y)')


def test_duplicate_record_label() -> None:
    with pytest.raises(ParseError, match="record repeats the label 'a'"):
        parse('(record a = (bits QQ== i32) a = (bits "" 0xi8))')


def test_empty_record() -> None:
    with pytest.raises(ParseError, match='a record needs at least one field'):
        parse('(record)')


def test_unclosed_list() -> None:
    with pytest.raises(ParseError, match=r'unclosed \('):
        parse('(var x')


def test_unclosed_string() -> None:
    with pytest.raises(ParseError, match='unclosed string'):
        parse('(var "hello')


def test_unknown_escape() -> None:
    with pytest.raises(ParseError, match=r'unknown escape \\q'):
        parse(r'(var "\q")')


def test_invalid_base64() -> None:
    with pytest.raises(ParseError, match='expected base64 bits'):
        parse('(bits *** i32)')


def test_extra_input() -> None:
    with pytest.raises(ParseError, match='unexpected input after the term'):
        parse('(var x) (var y)')
