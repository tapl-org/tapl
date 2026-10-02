# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from oymo.core import syntax
from oymo.oymomo import terms
from oymo.oymomo.grammar import UNKNOWN_FORM, parse
from oymo.oymomo.printer import show


def test_variable():
    assert parse('x') == terms.Variable(name='x', location=syntax.Location(0, 1))


def test_lambda():
    assert show(parse('x : i32 -> x')) == '(x:i32 → x)'


def test_lambda_unicode_arrow_is_the_same_term():
    assert show(parse('x : i32 → x')) == '(x:i32 → x)'


def test_lambda_extends_right():
    assert show(parse('a -> b -> a b')) == '(a:unknown → (b:unknown → (a b)))'


def test_lambda_argument_needs_parens():
    assert show(parse('f (x -> x)')) == '(f (x:unknown → x))'
    assert show(parse('f x -> x')) == 'error'


def test_apply_is_left_associative():
    assert show(parse('f a b')) == '((f a) b)'


def test_field_access_binds_tighter_than_apply():
    assert show(parse('f a.x b')) == '((f a.x) b)'
    assert show(parse('s.a.b')) == 's.a.b'
    assert show(parse('(f a).x')) == '(f a).x'


def test_struct():
    assert show(parse('{x = a, y = b}')) == '{x = a, y = b}'
    assert show(parse('{x = a,}')) == '{x = a}'
    assert show(parse('{}')) == '{}'
    assert show(parse('{,}')) == 'error'


def test_if():
    assert show(parse('if c then a else b')) == '(if c then a else b)'
    assert show(parse('if c then a else x -> x')) == '(if c then a else (x:unknown → x))'


def test_fix():
    assert show(parse('fix f')) == '(fix f)'
    assert show(parse('fix f x')) == '((fix f) x)'
    assert show(parse('fix s.f')) == '(fix s.f)'


def test_reserved_words_are_not_names():
    assert show(parse('if')) == 'error'
    assert show(parse('iffy')) == 'iffy'


def test_byte_array():
    assert show(parse('[2a000000] : i32')) == '[2a000000]:i32'
    assert show(parse('[2a 00 00 00]:i32')) == '[2a000000]:i32'


def test_byte_array_multiline():
    source = '[deadbeef cafebabe\n 00112233 44556677] : {lo: i64, hi: i64}'
    assert show(parse(source)) == '[deadbeefcafebabe0011223344556677]:{lo: i64, hi: i64}'


def test_byte_array_empty():
    assert show(parse('[] : {}')) == '[]:{}'


def test_byte_array_as_argument():
    assert show(parse('f [01] : u8 [02]')) == '((f [01]:u8) [02]:unknown)'


def test_omitted_forms_are_unknown():
    assert parse('x -> x').param_form == UNKNOWN_FORM
    assert parse('[2a]').form == UNKNOWN_FORM
    assert show(parse('[00] : {x, y: i32}')) == '[00]:{x: unknown, y: i32}'


def test_nested_struct_forms():
    assert show(parse('p : {x: i32, y: {a: u8,},} -> p')) == '(p:{x: i32, y: {a: u8}} → p)'


def test_function_form_in_struct_form_field():
    assert show(parse('d: {putchar: {c: i8} -> i32, errno: i32} -> d')) == (
        '(d:{putchar: ({c: i8} → i32), errno: i32} → d)'
    )


def test_parenthesized_function_form():
    assert show(parse('g: ({c: i8} -> i32) -> g')) == '(g:({c: i8} → i32) → g)'
    assert show(parse('[]: (i8 -> i32)')) == '[]:(i8 → i32)'


def test_function_form_is_right_associative():
    assert show(parse('d: {f: {a: i8} -> {b: i8} -> i32} -> d')) == '(d:{f: ({a: i8} → ({b: i8} → i32))} → d)'
    assert show(parse('d: {f: ({a: i8} -> {b: i8}) -> i32} -> d')) == '(d:{f: (({a: i8} → {b: i8}) → i32)} → d)'


def test_function_form_does_not_swallow_lambda_binder():
    source = 'decls: {f: {} -> i32} -> defs -> {}'
    assert show(parse(source)) == '(decls:{f: ({} → i32)} → (defs:unknown → {}))'


def test_quoted_names():
    assert show(parse('"a b"')) == 'a b'
    assert show(parse('"if" -> "if"')) == '(if:unknown → if)'
    assert show(parse('s."a b"')) == 's.a b'
    assert show(parse('{"x y" = a}')) == '{x y = a}'
    assert show(parse('x : "my form" -> x')) == '(x:my form → x)'


def test_quoted_name_equals_plain_name():
    assert show(parse('"x" -> "x"')) == show(parse('x -> x'))


def test_quoted_name_escapes():
    assert parse(r'"a\"b"').name == 'a"b'
    assert parse(r'"a\\b"').name == 'a\\b'
    assert parse(r'"\u{3bb}"').name == 'λ'


def test_quoted_name_rejects_bad_forms():
    assert show(parse('""')) == 'error'
    assert show(parse(r'"\n"')) == 'error'
    assert show(parse(r'"\u{}"')) == 'error'
    assert show(parse(r'"\u{d800}"')) == 'error'
    assert show(parse(r'"\u{110000}"')) == 'error'
    assert show(parse(r'"\u{3bb"')) == 'error'
    assert show(parse('"a\nb"')) == 'error'


def test_comments_and_whitespace():
    assert show(parse('// id\nx -> // body\n  x // end')) == '(x:unknown → x)'


def test_locations_skip_leading_trivia():
    term = parse('  // c\n  f a')
    assert term.location == syntax.Location(9, 12)
    assert term.function.location == syntax.Location(9, 10)
    assert term.argument.location == syntax.Location(11, 12)


def test_golden_program():
    source = 'prim -> decls: {} -> defs -> {main = a:i32 -> [00000000] : i32}'
    assert show(parse(source)) == '(prim:unknown → (decls:{} → (defs:unknown → {main = (a:i32 → [00000000]:i32)})))'
