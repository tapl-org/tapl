# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import textwrap

import pytest

from oymo.oymomo import reduction, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show

FACT = """
λm. {
fact = λf. {
  entry = λp.
    (λt0. if t0 then f.then0 {} else f.else0 {n = p.n})
      ('icmp' {'eq', 'i32', p.n, [00000000]}),
  then0 = λp. [01000000],
  else0 = λp.
    (λt1. (λt2. (λt3. t3) ('mul' {'i32', p.n, t2}))
             (m.fact {n = t1}))
      ('sub' {'i32', p.n, [01000000]}),
}}
"""


def pretty(source):
    return show(parse(source), pretty=True)


def test_compact_is_one_line_with_parens_only_where_needed():
    assert show(parse('f a (λb. b)')) == 'f a (λb. b)'
    assert show(parse(FACT)).count('\n') == 0


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('f a b', 'f a b'),
        ('f (g a) b', 'f (g a) b'),
        ('(λx. x) y', 'let x = y in x'),
        ('(let x = y in f) a', '(let x = y in f) a'),
        ('f (let x = y in x)', 'f (let x = y in x)'),
        ('f (λx. x)', 'f (λx. x)'),
        ('(f a).x', '(f a).x'),
        ('f (if c then a else b)', 'f (if c then a else b)'),
        ('if c then λx. x else (λy. y) z', 'if c then λx. x else let y = z in y'),
    ],
)
def test_pretty_parenthesizes_only_where_needed(source, expected):
    assert pretty(source) == expected


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # `if c then t else e` is `{e, t} c`, and every such struct apply prints as `if`.
        ('{e, t} c', 'if c then t else e'),
        ("{'1', '2'} [01]", "if [01] then '2' else '1'"),
        ('f ({e, t} c)', 'f (if c then t else e)'),
        ('{e, t} (f x)', 'if f x then t else e'),
        ('{e, {b, a} d} c', 'if c then if d then a else b else e'),
        # A label would be lost by `if`, and `if` has two arms.
        ('{x = e, t} c', '{x= e, t} c'),
        ('{e, t, d} c', '{e, t, d} c'),
        ('{e} c', '{e} c'),
    ],
)
def test_two_field_struct_apply_prints_as_if(source, expected):
    assert pretty(source) == expected
    assert parse(expected) == parse(source)


def test_pretty_quotes_names_that_need_it():
    assert pretty('λ"if". "a b"') == 'λ"if". "a b"'
    assert pretty(r'"a\"b\\c"') == r'"a\"b\\c"'
    assert pretty('s."1st"') == 's."1st"'
    assert show(terms.Variable('a\nb', terms.Location(0, 0)), pretty=True) == r'"a\u{a}b"'


def test_pretty_groups_bytes_by_four():
    assert pretty('[deadbeefcafebabe00]') == '[deadbeef cafebabe 00]'
    assert show(parse('[deadbeefcafebabe00]')) == '[deadbeefcafebabe00]'


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('[48656c6c6f20776f726c64]', "'Hello world'"),
        ('[2a]', "'*'"),
        ('[]', "''"),
        ("'Hello'", "'Hello'"),
        ('[486900]', '[486900]'),  # 00 is not text
        ('[4127]', '[4127]'),  # no escapes, so `'` stays hex
        ('[415c]', '[415c]'),  # and so does `\`
        ('[cebb]', "'λ'"),  # UTF-8 text
        ('[ce]', '[ce]'),  # not valid UTF-8
    ],
)
def test_text_bytes_print_quoted(source, expected):
    assert show(parse(source)) == expected
    assert show(parse(source), pretty=True) == expected


def test_text_bytes_print_quoted_only_up_to_128_bytes():
    assert show(parse("'" + 'a' * 128 + "'")) == "'" + 'a' * 128 + "'"
    assert show(parse("'" + 'a' * 129 + "'")) == '[' + '61' * 129 + ']'
    assert show(parse("'abcd'"), pretty=True, width=4) == "'abcd'"  # width does not matter


def test_pretty_breaks_long_terms():
    assert pretty(FACT) == textwrap.dedent("""\
        λm. {
          fact= λf. {
            entry= λp.
              let t0 = 'icmp' {'eq', 'i32', p.n, [00000000]} in
              if t0 then f.then0 {} else f.else0 {n= p.n},
            then0= λp. [01000000],
            else0= λp.
              let t1 = 'sub' {'i32', p.n, [01000000]} in
              let t2 = m.fact {n= t1} in
              let t3 = 'mul' {'i32', p.n, t2} in t3,
          },
        }""")


def test_compact_let():
    assert show(parse('let x = e in x')) == 'let x = e in x'


def test_pretty_breaks_let_chain_one_per_line():
    # A chain of two or more lets breaks even when it fits in the width.
    assert pretty('let a = f x in let b = g a in let c = h b in c') == textwrap.dedent(
        """\
        let a = f x in
        let b = g a in
        let c = h b in c"""
    )
    assert pretty('{x= let a = f in let b = g in b}') == textwrap.dedent(
        """\
        {
          x= let a = f in
          let b = g in b,
        }"""
    )


def test_pretty_keeps_single_let_on_one_line():
    assert pretty('let a = f x in a') == 'let a = f x in a'
    assert pretty('{x= let a = f in a}') == '{x= let a = f in a}'


def test_bruijn_index():
    term = reduction.resolve(parse('λa. λb. let x = a in b x'))
    assert show(term) == 'λa. λb. let x = $1 in $1 $0'
    assert show(term, pretty=True) == 'λa. λb. let x = $1 in $1 $0'
    assert show(parse(show(term))) == show(term)


def test_bruijn_index_and_variable_print_as_they_are():
    term = parse('λx. f $1 x')
    assert show(term) == 'λx. f $1 x'
    assert show(term, name_indices=True) == 'λx. f $1 x'


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('λa. λb. let x = a in b x', 'λa. λb. let x = a in b x'),
        ('λx. λx. $1', 'λx. λx. $1'),
        ('λx. λy. λx. λf. f $2 x', 'λx. λy. λx. λf. f y x'),
        ('λx. $4 x', 'λx. $4 x'),
    ],
)
def test_name_indices_where_safe(source, expected):
    term = reduction.resolve(parse(source))
    for pretty_mode in (False, True):
        named = show(term, pretty=pretty_mode, name_indices=True)
        assert named == expected
        assert show(reduction.resolve(parse(named))) == show(term)


def test_width_and_indent_flags():
    term = parse('λm. {main = f a, id = λx. x}')
    assert show(term, pretty=True) == 'λm. {main= f a, id= λx. x}'
    assert show(term, pretty=True, width=20, indent=4) == textwrap.dedent("""\
        λm. {
            main= f a,
            id= λx. x,
        }""")


@pytest.mark.parametrize(
    'source',
    [
        FACT,
        'f a (λb. b) (if c then d else e).x',
        'λ"if". λ"a b". s."\\u{3bb}"',
        "'tag'",
        'if c then if d then a else b else f a',
        'let x = let y = e in y in f (let z = x in z)',
        "f 'Hello world' [48656c6c6f] '' [00]",
        "{'1', '2'}",
        "{'1', b = '2'}",
        '{a}',
        '{λx. x, let y = a in y, a}',
        "'add' {'i32', x, x}",
        '$0',
        "'λ'",
    ],
)
def test_output_parses_back_to_the_same_term(source):
    assert parse(pretty(source)) == parse(source)
    assert parse(show(parse(source))) == parse(source)
    assert show(parse(pretty(source))) == show(parse(source))
    assert show(parse(show(parse(source))), pretty=True) == pretty(source)


def test_unlabeled_fields_print_only_their_value():
    term = parse("{'1', b = '2', c}")
    assert show(term) == "{'1', b = '2', c}"
    assert show(term, pretty=True) == "{'1', b= '2', c}"
    assert show(term, pretty=True, width=10) == textwrap.dedent("""\
        {
          '1',
          b= '2',
          c,
        }""")


def test_pretty_breaks_a_long_fixed_point():
    # `fix t` breaks inside `t`, and the result parses back to the same term (4.8).
    source = '(fix (λs. {aaaaaaaaaaaaaaaa = λq. s.aaaaaaaaaaaaaaaa q, bbbbbbbbbbbbbbbb = λq. s.bbbbbbbbbbbbbbbb q})).aaaaaaaaaaaaaaaa'
    text = pretty(source)
    assert text.startswith('(fix (λs. {\n')
    assert parse(text) == parse(source)
