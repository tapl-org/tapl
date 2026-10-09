# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import textwrap

import pytest

from oymo.oymomo import bruijn, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show, show_form

FACT = """
prim -> decls: {} -> defs -> {
fact = f -> {
  entry = args:{n = 'i32'} ->
    (t0 -> if t0 then f.then0 {} else f.else0 {n = args.n})
      (prim.eq_i32 {a = args.n, b = [00000000]:'i32'}),
  then0 = args:{} -> [01000000]:'i32',
  else0 = args:{n = 'i32'} ->
    (t1 -> (t2 -> (t3 -> t3) (prim.mul_i32 {a = args.n, b = t2}))
             (defs.fact {n = t1}))
      (prim.sub_i32 {minuend = args.n, subtrahend = [01000000]:'i32'}),
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


def test_pretty_omits_empty_forms():
    assert pretty('x -> x') == 'x → x'
    assert pretty('[00]') == '[00]'


def test_void_is_an_ordinary_form_name():
    assert pretty("x : 'void' -> x") == "x: 'void' → x"


def test_binder_forms_print_at_the_formed_level():
    assert pretty('x: (i32) -> x') == 'x: i32 → x'
    assert pretty('x: (a -> b) -> c') == 'x: (a → b) → c'
    assert pretty("[00]: (f 'i8')") == "[00]: (f 'i8')"  # `:` binds tighter than apply
    assert pretty('x: (i8) => (s.f) -> x') == 'x: i8 ⇒ s.f → x'
    assert pretty('x: (f a) -> x') == 'x: (f a) → x'
    assert pretty("x: ([00]: 'i8') => 'i32' -> x") == "x: ([00]: 'i8') ⇒ 'i32' → x"


def test_struct_shaped_like_a_function_form_prints_as_a_struct():
    assert pretty("x: {tag = ' => ', param = {c = 'i8'}, result = 'i32'} -> x") == (
        "x: {tag = ' => ', param = {c = 'i8'}, result = 'i32'} → x"
    )


def test_pretty_function_forms_group_only_as_params():
    assert pretty("g: ({c = 'i8'} => 'i32') -> g") == "g: {c = 'i8'} ⇒ 'i32' → g"
    assert pretty("[]: {f = {c = 'i8'} => 'i32'}") == "[]: {f = {c = 'i8'} ⇒ 'i32'}"
    assert pretty("[]: {f = ({a = 'i8'} => 'i8') => 'i32'}") == "[]: {f = ({a = 'i8'} ⇒ 'i8') ⇒ 'i32'}"


def test_pretty_quotes_names_that_need_it():
    assert pretty('"if" -> "a b"') == '"if" → "a b"'
    assert pretty(r'"a\"b\\c"') == r'"a\"b\\c"'
    assert pretty('s."1st"') == 's."1st"'
    assert show(terms.Variable('a\nb', terms.Location(0, 0)), pretty=True) == r'"a\u{a}b"'


def test_pretty_groups_bytes_by_four():
    assert pretty("[deadbeefcafebabe00]: 'i64'") == "[deadbeef cafebabe 00]: 'i64'"


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
        ("[4869]: 'i8'", "[4869]:'i8'"),  # a written form keeps hex
        ("'Hi': 'i8'", "[4869]:'i8'"),
        ('[]: {}', '[]:{}'),
    ],
)
def test_text_bytes_print_quoted_without_a_form(source, expected):
    assert show(parse(source)) == expected
    assert show(parse(source), pretty=True) == expected.replace(':', ': ')


def test_text_bytes_print_quoted_only_up_to_128_bytes():
    assert show(parse("'" + 'a' * 128 + "'")) == "'" + 'a' * 128 + "'"
    assert show(parse("'" + 'a' * 129 + "'")) == '[' + '61' * 129 + ']'
    assert show(parse("'abcd'"), pretty=True, width=4) == "'abcd'"  # width does not matter


def test_pretty_breaks_long_terms():
    assert pretty(FACT) == textwrap.dedent("""\
        prim → decls: {} → defs → {
          fact = f → {
            entry = args: {n = 'i32'} →
              let t0 = prim.eq_i32 {a = args.n, b = [00000000]: 'i32'} in
              if t0 then f.then0 {} else f.else0 {n = args.n},
            then0 = args: {} → [01000000]: 'i32',
            else0 = args: {n = 'i32'} →
              let t1 = prim.sub_i32 {minuend = args.n, subtrahend = [01000000]: 'i32'} in
              let t2 = defs.fact {n = t1} in
              let t3 = prim.mul_i32 {a = args.n, b = t2} in t3,
          },
        }""")


def test_compact_let():
    assert show(parse("let x: 'i8' = e in x")) == "let x:'i8' = e in x"
    assert show(parse('let x = e in x')) == 'let x = e in x'


def test_pretty_let_keeps_written_form():
    assert pretty("let t0: 'i1' = f a in t0") == "let t0: 'i1' = f a in t0"


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
        "d: {putchar = {c = 'i8'} => 'i32', errno = 'i32'} -> [] : ({} => 'i32')",
        "{f = {a = 'i8'} => 'i32', g = (f a) => (g => h) => i}",
        "x: ([00]: 'i8') => 'i32' -> f ([01]: 'i8') => g [02]: 'i8'",
        'x: (y) -> [00]: (f x) => {}',
        "'tag'",
        'if c then if d then a else b else fix f',
        "let x: 'i8' = let y = e in y in f (let z = x in z)",
        "f 'Hello world' [48656c6c6f]: 'i8' '' [00]",
        'y : x',
        'f a : g b',
        'a : b : c',
        '(a : b) : c',
        'x -> y -> y : x',
        'f (y : x) z',
        '(f : g) x',
        'y : (a -> b)',
        'y : a => b',
        '(a : b) => c',
        '{a = e : t}',
        'if c : t then a : t else b : t',
        "let x: 'i8' = v : t in x : t",
        '[01] : y',
        "([01] : 'i8') : 'i16'",
        'y : (f a)',
        '(f a) : t',
        'f y : x z',
        'fix f : t',
        '(fix f) : t',
        'x : decls.t',
        "f [01] : 'u8' [02]",
    ],
)
def test_output_parses_back_to_the_same_term(source):
    assert parse(pretty(source)) == parse(source)
    assert parse(show(parse(source))) == parse(source)
    assert show(parse(pretty(source))) == show(parse(source))
    assert show(parse(show(parse(source))), pretty=True) == pretty(source)


def test_show_form():
    i8, i32 = terms.name_to_form('i8'), terms.name_to_form('i32')
    form = terms.Struct(
        [terms.Field('f', terms.FunctionForm(i8, i32)), terms.Field('x', terms.name_to_form('unknown'))]
    )
    assert show_form(form) == "{f = 'i8' ⇒ 'i32', x = 'unknown'}"
    assert show_form(form, pretty=True) == "{f = 'i8' ⇒ 'i32', x = 'unknown'}"
    assert show_form(terms.FunctionForm(form, i32)) == "{f = 'i8' ⇒ 'i32', x = 'unknown'} ⇒ 'i32'"
    assert show_form(terms.Variable('i32')) == 'i32'
    assert show_form(terms.Apply(terms.Variable('f'), i32)) == "(f 'i32')"


def test_formed():
    a, b, c, f, x, y = (terms.Variable(name) for name in 'abcfxy')
    byte = terms.ByteArray(b'\x01')
    assert show(terms.Formed(y, x)) == 'y:x'
    assert show(terms.Formed(y, x), pretty=True) == 'y: x'
    assert show(terms.Formed(byte, terms.name_to_form('i1'))) == "[01]:'i1'"
    assert show(terms.Formed(terms.Apply(f, y), terms.Apply(f, x))) == '(f y):(f x)'
    assert show(terms.Apply(f, terms.Formed(y, x))) == 'f y:x'
    assert show(terms.Apply(terms.Formed(f, x), y)) == 'f:x y'
    assert show(terms.Fix(terms.Formed(f, x))) == 'fix f:x'
    assert show(terms.Formed(terms.Fix(f), x)) == '(fix f):x'
    assert show(terms.Lambda('x', terms.Empty, terms.Formed(y, x))) == 'x → y:x'
    assert show(terms.Formed(y, terms.Lambda('a', terms.Empty, b))) == 'y:(a → b)'
    assert show(terms.Formed(y, terms.FunctionForm(a, b))) == 'y:a ⇒ b'
    assert show(terms.FunctionForm(terms.Formed(a, b), c)) == '(a:b) ⇒ c'
    assert show(terms.Formed(a, terms.Formed(b, c))) == 'a:b:c'
    assert show(terms.Formed(terms.Formed(a, b), c)) == '(a:b):c'
    assert show(terms.Formed(terms.Project(y, 'p'), x)) == 'y.p:x'


def test_formed_byte_array_in_parens_where_needed():
    # `[01]:'i8':'i16'` would read as `[01] : ('i8' : 'i16')`.
    i8, i16 = terms.name_to_form('i8'), terms.name_to_form('i16')
    byte = terms.ByteArray(b'\x01')
    assert show(terms.Formed(terms.Formed(byte, i8), i16)) == "([01]:'i8'):'i16'"
    assert show(terms.Apply(terms.Variable('f'), terms.Formed(byte, i8))) == "f [01]:'i8'"
    assert show(terms.Formed(byte, terms.Formed(i8, i16))) == "[01]:[6938]:'i16'"
