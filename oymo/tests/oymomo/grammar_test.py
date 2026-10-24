# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.core import spans, syntax
from oymo.oymomo import terms
from oymo.oymomo.grammar import RESERVED, parse
from oymo.oymomo.printer import show

x, y, a, b, f = (terms.Variable(n) for n in 'xyabf')


def test_variable():
    term = parse('x')
    assert term == x
    assert term.span == spans.make(0, 1)


def test_bruijn_index():
    term = parse('$12')
    assert term == terms.BruijnIndex(index=12)
    assert term.span == spans.make(0, 3)
    assert show(parse('λx. f $1 $0.a')) == 'λx. f $1 $0.a'
    assert show(parse('$ 0')) == 'error'
    assert show(parse('$')) == 'error'
    assert show(parse('$1a')) == 'error'
    assert show(parse('$0x1')) == 'error'


@pytest.mark.parametrize('source', ['$fix', '$fix g', '$ fix', '$"fix"'])
def test_no_builtins(source):
    assert show(parse(source)) == 'error'


def test_lambda():
    assert parse('λx. x') == terms.Lambda('x', x)
    assert parse('λx.x') == terms.Lambda('x', x)
    assert parse('λ x . x') == terms.Lambda('x', x)
    assert show(parse('λx. x')) == 'λx. x'


def test_lambda_ascii_backslash_is_the_same_term():
    assert parse('\\x. x') == parse('λx. x')
    assert show(parse('\\x. \\y. x y')) == 'λx. λy. x y'


def test_lambda_extends_right():
    assert parse('λa. λb. a b') == parse('λa. (λb. (a b))')


def test_dot_after_the_binder_ends_it():
    # 2.2: every other dot is projection.
    assert parse('λp. p.a') == terms.Lambda('p', terms.Project(terms.Variable('p'), 'a'))
    assert parse('λp.p.a.b') == parse('λp. ((p.a).b)')


def test_lambda_argument_needs_parens():
    assert show(parse('f (λx. x)')) == 'f (λx. x)'
    assert show(parse('f λx. x')) == 'error'


@pytest.mark.parametrize('source', ['x -> x', 'x → x', 'λ. x', 'λx x', 'λ{}. x', "λx~'i32'. x"])
def test_lambda_errors(source):
    assert show(parse(source)) == 'error'


def test_apply_is_left_associative():
    assert parse('f a b') == parse('(f a) b')
    assert show(parse('f (a b)')) == 'f (a b)'


def test_projection_binds_tighter_than_apply():
    assert parse('f a.x b') == parse('(f (a.x)) b')
    assert show(parse('s.a.b')) == 's.a.b'
    assert show(parse('(f a).x')) == '(f a).x'


def test_struct():
    assert show(parse('{x = a, y = b}')) == '{x = a, y = b}'
    assert show(parse('{x = a,}')) == '{x = a}'
    assert show(parse('{}')) == '{}'
    assert show(parse('{,}')) == 'error'


def test_duplicate_labels_are_rejected():
    term = parse('{x = a, y = b, x = c}')
    assert isinstance(term, syntax.ErrorTerm)
    assert term.message == "Duplicate label 'x'."
    assert term.span == spans.make(15, 5)
    assert isinstance(parse('λp. {a = {l = p, l = p}}'), syntax.ErrorTerm)
    # Empty labels never clash (2.5b).
    assert show(parse('{a, b, c}')) == '{a, b, c}'
    # Equal labels in different structs are fine.
    assert show(parse('{l = {l = a}}')) == '{l = {l = a}}'


def test_let():
    assert show(parse('let x = e in x')) == 'let x = e in x'
    assert parse('let x = e in f x') == parse('let x = e in (f x)')
    assert parse('let x = e1 in let y = e2 in y') == parse('let x = e1 in (let y = e2 in y)')
    assert show(parse('f (let x = e in x)')) == 'f (let x = e in x)'
    assert show(parse("let x~'i32' = e in x")) == 'error'


def test_let_is_an_apply_of_a_lambda():
    assert parse('let x = e in x') == terms.Apply(terms.Lambda('x', x), terms.Variable('e'))


def test_let_and_in_are_reserved():
    assert show(parse('λlet. let')) == 'error'
    assert show(parse('in')) == 'error'
    assert show(parse('f let')) == 'error'
    assert show(parse('λ"let". "in"')) == 'λ"let". "in"'
    assert show(parse('λletter. inner')) == 'λletter. inner'


def test_if():
    assert show(parse('if c then a else b')) == 'if c then a else b'
    assert parse('if c then a else λx. x') == parse('if c then a else (λx. x)')
    assert parse('if c then a else b') == terms.Apply(
        terms.Struct([terms.Field('', b), terms.Field('', a)]), terms.Variable('c')
    )


def test_fix():
    g, a = terms.Variable('g'), terms.Variable('a')
    assert parse('fix g') == terms.Fix(g)
    # 2.3: `fix t` parses as an application does.
    assert parse('fix g.l a') == terms.Apply(terms.Fix(terms.Project(g, 'l')), a)
    assert parse('f (fix g)') == terms.Apply(terms.Variable('f'), terms.Fix(g))
    assert show(parse('fix (λx. x)')) == 'fix (λx. x)'
    assert show(parse('(fix g).l')) == '(fix g).l'
    assert show(parse('fix g.l a')) == 'fix g.l a'
    assert show(parse('f (fix g)')) == 'f (fix g)'
    assert show(parse('f fix g')) == 'error'
    assert show(parse('fix')) == 'error'


def test_fix_is_a_keyword():
    assert show(parse('λfix. fix')) == 'error'
    assert show(parse('fixed')) == 'fixed'
    assert show(parse('λ"fix". "fix"')) == 'λ"fix". "fix"'


def test_reserved_words_are_not_names():
    assert show(parse('if')) == 'error'
    assert show(parse('iffy')) == 'iffy'


def test_byte_array():
    assert parse('[2a000000]') == terms.ByteArray(b'\x2a\x00\x00\x00')
    assert parse('[2a 00 00 00]') == terms.ByteArray(b'\x2a\x00\x00\x00')
    assert show(parse('[]')) == "''"


def test_byte_array_multiline():
    assert parse('[deadbeef cafebabe\n 00112233 44556677]') == terms.ByteArray(
        bytes.fromhex('deadbeefcafebabe0011223344556677')
    )


def test_text_byte_array():
    term = parse("'Hi there'")
    assert term == terms.ByteArray(value=b'Hi there')
    assert term.span == spans.make(0, 10)
    assert parse("''") == terms.ByteArray(b'')
    assert parse("f 'a' 'b'") == parse("(f 'a') 'b'")


def test_text_byte_array_is_utf8():
    # 2.4c: any valid UTF-8 text may be written as text.
    assert parse("'λ'") == terms.ByteArray('λ'.encode())
    assert show(parse("'λ'")) == "'λ'"


def test_text_byte_array_rejects_non_text():
    assert show(parse("'a\\'b'")) == 'error'  # no escapes
    assert show(parse("'a\\b'")) == 'error'
    assert show(parse("'a\nb'")) == 'error'
    assert show(parse("'a\tb'")) == 'error'
    assert show(parse("'abc")) == 'error'


@pytest.mark.parametrize('source', ["x~'i32'", "[01]~'i8'", "{a = 'i8'} => 'i32'", "'i8' ⇒ 'i32'"])
def test_no_forms(source):
    assert show(parse(source)) == 'error'


def test_unlabeled_fields():
    def fields(source):
        return [(fl.label, fl.value) for fl in parse(source).fields]

    one, two = terms.ByteArray(b'1'), terms.ByteArray(b'2')
    assert fields("{'1', '2'}") == [('', one), ('', two)]
    assert fields('{a}') == [('', a)]
    assert fields('{a = b}') == [('a', b)]
    assert fields('{λx. x}') == [('', terms.Lambda('x', x))]
    assert fields("{'1', b = '2'}") == [('', one), ('b', two)]
    assert fields("{'1',}") == [('', one)]
    assert fields('{let y = a in y}')[0][0] == ''
    assert parse('{a}').fields[0].span == spans.make(1, 1)


def test_a_written_label_is_never_empty():
    assert show(parse('{"" = x}')) == 'error'


def test_precedence_order():
    """Loosest to tightest: `λ`/`if`/`let`, apply, `.`."""
    cases = [
        ('λx. f a', 'λx. (f a)'),
        ('λx. s.a', 'λx. (s.a)'),
        ('if c then a else f a', 'if c then a else (f a)'),
        ('let x = f a in g x.b', 'let x = (f a) in (g (x.b))'),
        ('{a = f b}', '{a = (f b)}'),
        ('f s.a', 'f (s.a)'),
        ('f a b', '(f a) b'),
        ('s.a.b', '(s.a).b'),
        ('λx. f a.b c.d', 'λx. ((f (a.b)) (c.d))'),
    ]
    for source, grouped in cases:
        assert show(parse(source)) != 'error', source
        assert parse(source) == parse(grouped), source


def test_parentheses_only_override_precedence():
    """A lambda, `if` or `let` binds looser than any operand, so as an operand it needs parentheses."""
    operands = [
        ('f λx. x', 'f (λx. x)'),
        ('f if c then a else b', 'f (if c then a else b)'),
        ('f let x = a in x', 'f (let x = a in x)'),
    ]
    for bare, parenthesized in operands:
        assert show(parse(bare)) == 'error', bare
        assert show(parse(parenthesized)) != 'error', parenthesized


def test_quoted_names():
    assert show(parse('"a b"')) == '"a b"'
    assert show(parse('λ"if". "if"')) == 'λ"if". "if"'
    assert show(parse('s."a b"')) == 's."a b"'
    assert show(parse('{"x y" = a}')) == '{"x y" = a}'


@pytest.mark.parametrize('word', sorted(RESERVED))
def test_quoted_keyword_is_a_name(word):
    assert show(parse(f'λ{word}. {word}')) == 'error'
    assert show(parse(f'f {word}')) == 'error'
    assert show(parse(f'λ"{word}". "{word}"')) == f'λ"{word}". "{word}"'
    assert show(parse(f'f "{word}"')) == f'f "{word}"'
    assert show(parse(f'{{"{word}" = a}}."{word}"')) == f'{{"{word}" = a}}."{word}"'


def test_quoted_name_equals_plain_name():
    assert parse('λ"x". "x"') == parse('λx. x')


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
    assert show(parse('// id\nλx. // body\n  x // end')) == 'λx. x'


def test_locations_skip_leading_trivia():
    term = parse('  // c\n  f a')
    assert term.span == spans.make(9, 3)
    assert term.function.span == spans.make(9, 1)
    assert term.argument.span == spans.make(11, 1)


def test_gcd_module_parses():
    """The module of 8.9 in the new syntax."""
    source = """
    λm. {
      gcd = {
        gives = 'i32',
        body = λf. {
          start = {
            takes = {a = 'i32', b = 'i32'},
            body = λp.
              let z = 'icmp' {'eq', 'i32', p.b, [00000000]} in
              if z then p.a else f.step.body {a = p.a, b = p.b},
          },
          step = {
            takes = {a = 'i32', b = 'i32'},
            body = λp.
              let r = 'urem' {'i32', p.a, p.b} in
              f.start.body {a = p.b, b = r},
          },
        },
      },
    }
    """
    term = parse(source)
    assert not isinstance(term, syntax.ErrorTerm)
    assert isinstance(term, terms.Lambda)
    assert term.param_name == 'm'
