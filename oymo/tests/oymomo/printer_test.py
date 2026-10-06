# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import textwrap

import pytest

from oymo.oymomo import bruijn, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show, show_form

FACT = """
prim -> decls: {} -> defs -> {
fact = f -> {
  entry = args:{n: i32} ->
    (t0 -> if t0 then f.then0 {} else f.else0 {n = args.n})
      (prim.eq_i32 {a = args.n, b = [00000000]:i32}),
  then0 = args:{} -> [01000000]:i32,
  else0 = args:{n: i32} ->
    (t1 -> (t2 -> (t3 -> t3) (prim.mul_i32 {a = args.n, b = t2}))
             (defs.fact {n = t1}))
      (prim.sub_i32 {minuend = args.n, subtrahend = [01000000]:i32}),
}}
"""


def pretty(source):
    return show(parse(source), pretty=True)


def test_compact_is_one_line_with_parens_only_where_needed():
    assert show(parse('f a (b -> b)')) == 'f a (b → b)'
    assert show(parse(FACT)).count('\n') == 0


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('f a b', 'f a b'),
        ('f (g a) b', 'f (g a) b'),
        ('(x -> x) y', 'let x = y in x'),
        ('(let x = y in f) a', '(let x = y in f) a'),
        ('f (let x = y in x)', 'f (let x = y in x)'),
        ('f (x -> x)', 'f (x → x)'),
        ('(f a).x', '(f a).x'),
        ('fix f x', 'fix f x'),
        ('fix (f a)', 'fix (f a)'),
        ('f (if c then a else b)', 'f (if c then a else b)'),
        ('if c then x -> x else (y -> y) z', 'if c then x → x else let y = z in y'),
    ],
)
def test_pretty_parenthesizes_only_where_needed(source, expected):
    assert pretty(source) == expected


def test_pretty_omits_unknown_forms():
    assert pretty('x : unknown -> x') == 'x → x'
    assert pretty('[2a]') == '[2a]'
    assert pretty('[]: {x, y: i32}') == '[]: {x, y: i32}'


def test_pretty_function_forms_group_only_outside_struct_fields():
    assert pretty('g: ({c: i8} -> i32) -> g') == 'g: ({c: i8} → i32) → g'
    assert pretty('[]: {f: {c: i8} -> i32}') == '[]: {f: {c: i8} → i32}'
    assert pretty('[]: {f: ({a: i8} -> i8) -> i32}') == '[]: {f: ({a: i8} → i8) → i32}'


def test_pretty_quotes_names_that_need_it():
    assert pretty('"if" -> "a b"') == '"if" → "a b"'
    assert pretty(r'"a\"b\\c"') == r'"a\"b\\c"'
    assert pretty('s."1st"') == 's."1st"'
    assert show(terms.Variable('a\nb', terms.Location(0, 0)), pretty=True) == r'"a\u{a}b"'


def test_pretty_groups_bytes_by_four():
    assert pretty('[deadbeefcafebabe00]: i64') == '[deadbeef cafebabe 00]: i64'


def test_pretty_breaks_long_terms():
    assert pretty(FACT) == textwrap.dedent("""\
        prim → decls: {} → defs → {
          fact = f → {
            entry = args: {n: i32} →
              let t0 = prim.eq_i32 {a = args.n, b = [00000000]: i32} in
              if t0 then f.then0 {} else f.else0 {n = args.n},
            then0 = args: {} → [01000000]: i32,
            else0 = args: {n: i32} →
              let t1 = prim.sub_i32 {minuend = args.n, subtrahend = [01000000]: i32} in
              let t2 = defs.fact {n = t1} in
              let t3 = prim.mul_i32 {a = args.n, b = t2} in t3,
          },
        }""")


def test_compact_let():
    assert show(parse('let x: i8 = e in x')) == 'let x:i8 = e in x'
    assert show(parse('let x = e in x')) == 'let x = e in x'


def test_pretty_let_keeps_written_form():
    assert pretty('let t0: i1 = f a in t0') == 'let t0: i1 = f a in t0'


def test_pretty_breaks_let_chain_one_per_line():
    assert pretty('let a = f x in let b = g a in let c = h b in c') == 'let a = f x in let b = g a in let c = h b in c'
    assert show(parse('let a = f x in let b = g a in let c = h b in c'), pretty=True, width=20) == textwrap.dedent(
        """\
        let a = f x in
        let b = g a in
        let c = h b in c"""
    )


def test_bruijn_index():
    term = bruijn.resolve(parse('a -> b -> let x = a in b x'))
    assert show(term) == 'a → b → let x = $1 in $1 $0'
    assert show(term, pretty=True) == 'a → b → let x = $1 in $1 $0'
    assert show(parse(show(term))) == show(term)


def test_bruijn_index_and_variable_print_as_they_are():
    term = parse('x -> f $1 x')
    assert show(term) == 'x → f $1 x'
    assert show(term, name_indices=True) == 'x → f $1 x'


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('a -> b -> let x = a in b x', 'a → b → let x = a in b x'),
        ('x -> x -> $1', 'x → x → $1'),
        ('x -> y -> x -> f -> f $2 x', 'x → y → x → f → f y x'),
        ('x -> $4 x', 'x → $4 x'),
    ],
)
def test_name_indices_where_safe(source, expected):
    term = bruijn.resolve(parse(source))
    for pretty in (False, True):
        named = show(term, pretty=pretty, name_indices=True)
        assert named == expected
        assert show(bruijn.resolve(parse(named))) == show(term)


def test_width_and_indent_flags():
    term = parse('defs -> {main = f a, id = x -> x}')
    assert show(term, pretty=True) == 'defs → {main = f a, id = x → x}'
    assert show(term, pretty=True, width=20, indent=4) == textwrap.dedent("""\
        defs → {
            main = f a,
            id = x → x,
        }""")


@pytest.mark.parametrize(
    'source',
    [
        FACT,
        'f a (b -> b) (if c then d else e).x',
        '"if" -> "a b" -> s."\\u{3bb}"',
        'd: {putchar: {c: i8} -> i32, errno} -> [] : ({} -> i32)',
        'if c then if d then a else b else fix f',
        'let x: i8 = let y = e in y in f (let z = x in z)',
    ],
)
def test_output_parses_back_to_the_same_term(source):
    assert show(parse(pretty(source))) == show(parse(source))
    assert show(parse(show(parse(source))), pretty=True) == pretty(source)


def test_show_form():
    form = terms.StructForm([('f', terms.FunctionForm('i8', 'i32')), ('x', 'unknown')])
    assert show_form(form) == '{f: i8 → i32, x}'
    assert show_form(form, pretty=True) == '{f: i8 → i32, x}'
