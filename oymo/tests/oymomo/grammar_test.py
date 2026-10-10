# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.core import syntax
from oymo.oymomo import terms
from oymo.oymomo.grammar import RESERVED, parse
from oymo.oymomo.printer import show


def test_variable():
    term = parse('x')
    assert term == terms.Variable(name='x')
    assert term.location == syntax.Location(0, 1)


def test_bruijn_index():
    term = parse('$12')
    assert term == terms.BruijnIndex(index=12)
    assert term.location == syntax.Location(0, 3)
    assert show(parse('x -> f $1 $0.a')) == 'x → f $1 $0.a'
    assert show(parse('$ 0')) == 'error'
    assert show(parse('$')) == 'error'
    assert show(parse('$1a')) == 'error'
    assert show(parse('$0x1')) == 'error'


def test_lambda():
    assert show(parse("x : 'i32' -> x")) == "x:'i32' → x"


def test_lambda_unicode_arrow_is_the_same_term():
    assert show(parse("x : 'i32' → x")) == "x:'i32' → x"


def test_lambda_extends_right():
    assert show(parse('a -> b -> a b')) == show(parse('a -> (b -> (a b))'))


def test_lambda_argument_needs_parens():
    assert show(parse('f (x -> x)')) == 'f (x → x)'
    assert show(parse('f x -> x')) == 'error'


def test_apply_is_left_associative():
    assert show(parse('f a b')) == show(parse('(f a) b'))
    assert show(parse('f (a b)')) == 'f (a b)'


def test_projection_binds_tighter_than_apply():
    assert show(parse('f a.x b')) == show(parse('(f (a.x)) b'))
    assert show(parse('s.a.b')) == 's.a.b'
    assert show(parse('(f a).x')) == '(f a).x'


def test_struct():
    assert show(parse('{x = a, y = b}')) == '{x = a, y = b}'
    assert show(parse('{x = a,}')) == '{x = a}'
    assert show(parse('{}')) == '{}'
    assert show(parse('{,}')) == 'error'


def test_let():
    assert show(parse('let x = e in x')) == 'let x = e in x'
    assert show(parse("let t0: 'i1' = f a in t0")) == "let t0:'i1' = f a in t0"
    assert show(parse('let x = e in f x')) == show(parse('let x = e in (f x)'))
    assert show(parse('let x = e1 in let y = e2 in y')) == show(parse('let x = e1 in (let y = e2 in y)'))
    assert show(parse('f (let x = e in x)')) == 'f (let x = e in x)'


def test_let_is_an_apply_of_a_lambda():
    term = parse('let x = e in x')
    assert isinstance(term, terms.Apply)
    assert isinstance(term.function, terms.Lambda)
    assert term.function.param_name == 'x'


def test_let_and_in_are_reserved():
    assert show(parse('let -> let')) == 'error'
    assert show(parse('in')) == 'error'
    assert show(parse('f let')) == 'error'
    assert show(parse('"let" -> "in"')) == '"let" → "in"'
    assert show(parse('letter -> inner')) == 'letter → inner'


def test_if():
    assert show(parse('if c then a else b')) == 'if c then a else b'
    assert show(parse('if c then a else x -> x')) == show(parse('if c then a else (x -> x)'))


def test_fix():
    assert show(parse('fix f')) == 'fix f'
    assert show(parse('fix f x')) == show(parse('(fix f) x'))
    assert show(parse('fix s.f')) == 'fix s.f'


def test_reserved_words_are_not_names():
    assert show(parse('if')) == 'error'
    assert show(parse('iffy')) == 'iffy'


def test_byte_array():
    assert show(parse("[2a000000] : 'i32'")) == "[2a000000]:'i32'"
    assert show(parse("[2a 00 00 00]:'i32'")) == "[2a000000]:'i32'"


def test_byte_array_multiline():
    source = "[deadbeef cafebabe\n 00112233 44556677] : {lo = 'i64', hi = 'i64'}"
    assert show(parse(source)) == "[deadbeefcafebabe0011223344556677]:{lo = 'i64', hi = 'i64'}"


def test_byte_array_empty():
    assert show(parse('[] : {}')) == '[]:{}'


def test_text_byte_array():
    term = parse("'Hi there'")
    assert term == terms.ByteArray(value=b'Hi there')
    assert term.location == syntax.Location(0, 10)
    assert show(parse("'Hi' : 'i16'")) == "[4869]:'i16'"
    assert show(parse("''")) == "''"
    assert show(parse("f 'a' 'b'")) == show(parse("(f 'a') 'b'"))


def test_text_byte_array_rejects_non_text():
    assert show(parse("'a\\'b'")) == 'error'  # no escapes
    assert show(parse("'a\\b'")) == 'error'
    assert show(parse("'a\nb'")) == 'error'
    assert show(parse("'a\tb'")) == 'error'
    assert show(parse("'λ'")) == 'error'
    assert show(parse("'abc")) == 'error'


def test_byte_array_as_argument():
    # `:` binds tighter than apply, so a byte array with a form is an argument as it is.
    assert parse("f [01] : 'u8' [02]") == parse("f ([01] : 'u8') [02]")
    assert show(parse("f ([01] : 'u8') [02]")) == "f [01]:'u8' [02]"
    assert parse("(f [01]) : 'u8'") == terms.Formed(
        terms.Apply(terms.Variable('f'), terms.ByteArray(b'\x01')), terms.name_to_form('u8')
    )


def test_omitted_forms_are_empty():
    assert parse('x -> x').param_form is terms.Empty
    assert parse('let x = e in x').function.param_form is terms.Empty


def test_forms_are_terms():
    assert parse("[00] : {x = 'i8', y = 'i32'}").form == terms.Struct(
        [terms.Field('x', terms.name_to_form('i8')), terms.Field('y', terms.name_to_form('i32'))]
    )
    assert parse("x: 'i32' -> x").param_form == terms.name_to_form('i32')
    assert parse('x: [69 33 32] -> x').param_form == terms.name_to_form('i32')


def test_every_struct_field_needs_a_value():
    assert show(parse("[00] : {x, y = 'i32'}")) == 'error'
    assert show(parse("[00] : {x: 'i8'}")) == 'error'


def test_void_is_an_ordinary_form_name():
    assert parse("x: 'void' -> x").param_form == terms.name_to_form('void')


def test_binder_form_is_an_ordinary_expression():
    assert parse('x: i32 -> x').param_form == terms.Variable('i32')
    assert show(parse('x: i32 -> x')) == 'x:i32 → x'
    assert show(parse('x: (i32) -> x')) == 'x:i32 → x'
    assert parse('x: s.f -> x').param_form == terms.Project(terms.Variable('s'), 'f')
    assert show(parse('x: decls.t -> x')) == 'x:decls.t → x'
    assert show(parse('let x: decls.t = v in x')) == 'let x:decls.t = v in x'
    # The form never holds a lambda, so it ends at the first `->`.
    term = parse('x: a -> b -> c')
    assert term.param_form == terms.Variable('a')
    assert term.body == terms.Lambda('b', terms.Empty, terms.Variable('c'))
    # A lambda or an application in a form needs parentheses.
    assert show(parse('x: (a -> b) -> c')) == 'x:(a → b) → c'
    assert isinstance(parse('x: (a -> b) -> c').param_form, terms.Lambda)
    assert parse('x: (f a) -> x').param_form == terms.Apply(terms.Variable('f'), terms.Variable('a'))
    assert show(parse('x: (f a) -> x')) == 'x:(f a) → x'
    assert show(parse("x: 'i8' : 'i16' -> x")) == "x:[6938]:'i16' → x"  # a formed byte array is hex


def test_byte_array_form_stops_before_an_argument():
    assert parse("f [00]: 'i32' y") == parse("(f ([00]: 'i32')) y")


def test_nested_struct_forms():
    assert show(parse("p : {x = 'i32', y = {a = 'u8'}} -> p")) == "p:{x = 'i32', y = {a = 'u8'}} → p"


def test_function_form_in_struct_form_field():
    assert show(parse("d: {putchar = {c = 'i8'} => 'i32', errno = 'i32'} -> d")) == (
        "d:{putchar = {c = 'i8'} ⇒ 'i32', errno = 'i32'} → d"
    )


def test_function_form_after_colon_needs_no_parens():
    assert show(parse("g: {c = 'i8'} => 'i32' -> g")) == "g:{c = 'i8'} ⇒ 'i32' → g"
    assert show(parse("g: ({c = 'i8'} => 'i32') -> g")) == "g:{c = 'i8'} ⇒ 'i32' → g"
    assert show(parse("[]: 'i8' => 'i32'")) == "[]:'i8' ⇒ 'i32'"
    assert show(parse("let f: 'i8' => 'i32' = g in f")) == "let f:'i8' ⇒ 'i32' = g in f"


def test_function_form_is_right_associative():
    assert show(parse("d: {f = {a = 'i8'} => {b = 'i8'} => 'i32'} -> d")) == show(
        parse("d: {f = {a = 'i8'} => ({b = 'i8'} => 'i32')} -> d")
    )
    assert (
        show(parse("d: {f = ({a = 'i8'} => {b = 'i8'}) => 'i32'} -> d"))
        == "d:{f = ({a = 'i8'} ⇒ {b = 'i8'}) ⇒ 'i32'} → d"
    )


def test_function_form_is_its_own_term():
    sugar = parse("{c = 'i8'} => 'i32'")
    assert sugar == terms.FunctionForm(
        terms.Struct([terms.Field('c', terms.name_to_form('i8'))]), terms.name_to_form('i32')
    )
    assert sugar == parse("{c = 'i8'} ⇒ 'i32'")
    assert isinstance(parse("{tag = ' => ', param = {c = 'i8'}, result = 'i32'}"), terms.Struct)


def test_function_form_without_param():
    i1 = terms.name_to_form('i1')
    assert parse("=> 'i1'") == terms.FunctionForm(terms.Empty, i1)
    assert parse("⇒ 'i1'") == terms.FunctionForm(terms.Empty, i1)
    assert parse("=> => 'i1'") == terms.FunctionForm(terms.Empty, terms.FunctionForm(terms.Empty, i1))
    # `{} => R` declares zero params; `=> R` leaves the param out.
    assert parse("{} => 'i1'") == terms.FunctionForm(terms.Struct([]), i1)
    assert parse("{main = => 'i1'}") == terms.Struct([terms.Field('main', terms.FunctionForm(terms.Empty, i1))])
    # With something on its left, `=>` takes it as the param; as an argument it needs parens.
    f, b = terms.Variable('f'), terms.Variable('b')
    assert parse('f => b') == terms.FunctionForm(f, b)
    assert parse('f (=> b)') == terms.Apply(f, terms.FunctionForm(terms.Empty, b))
    assert parse("a => => 'i1'") == terms.FunctionForm(terms.Variable('a'), terms.FunctionForm(terms.Empty, i1))


def test_function_form_is_an_expression():
    assert show(parse("{f = {a = 'i8'} => 'i32'}")) == "{f = {a = 'i8'} ⇒ 'i32'}"
    assert show(parse("let f = 'i8' => 'i32' in f")) == "let f = 'i8' ⇒ 'i32' in f"
    assert show(parse('f a => g b')) == show(parse('f (a => g) b'))
    assert show(parse('(f a) => (g b)')) == '(f a) ⇒ (g b)'
    assert show(parse('x -> a => b')) == show(parse('x -> (a => b)'))
    assert show(parse('(f => g) x')) == 'f ⇒ g x'
    assert show(parse('f (a => b)')) == 'f a ⇒ b'


def test_precedence_order():
    """Loosest to tightest: `->`/`if`/`let`, apply and `fix`, `:`, `=>`, `.`. Each pair, then each associativity."""
    cases = [
        # `->`, `if`, `let` take everything to their right.
        ('x -> y : t', 'x -> (y : t)'),
        ('if c then a else b : t', 'if c then a else (b : t)'),
        ('let x = v : t in b', 'let x = (v : t) in b'),
        ('{a = e : t}', '{a = (e : t)}'),
        ('x -> f a', 'x -> (f a)'),
        ('x -> fix f', 'x -> (fix f)'),
        ('x -> a => b', 'x -> (a => b)'),
        ('x -> s.a', 'x -> (s.a)'),
        ('x -> f a : t', 'x -> (f (a : t))'),
        ('if c then a else f a => b', 'if c then a else (f (a => b))'),
        ('let x = f a in g x => s.b', 'let x = (f a) in (g (x => (s.b)))'),
        # apply and `fix` against `:`, `=>` and `.`.
        ('f a : g b', 'f (a : g) b'),
        ('f y : x z', 'f (y : x) z'),
        ('y : f a', '(y : f) a'),
        ('fix f : t', 'fix (f : t)'),
        ('fix f a', '(fix f) a'),
        ('f fix', 'error'),
        ('f a => b', 'f (a => b)'),
        ('a => b c', '(a => b) c'),
        ('fix a => b', 'fix (a => b)'),
        ('f s.a', 'f (s.a)'),
        ('fix s.a', 'fix (s.a)'),
        # `:` against `=>` and `.`.
        ('x : a => b', 'x : (a => b)'),
        ('a => b : c', '(a => b) : c'),
        ('s.a : t.b', '(s.a) : (t.b)'),
        ('x : decls.t', 'x : (decls.t)'),
        # `=>` against `.`.
        ('s.a => t.b', '(s.a) => (t.b)'),
        # Associativity: apply left, `:` right, `=>` right, `.` left.
        ('f a b', '(f a) b'),
        ('a : b : c', 'a : (b : c)'),
        ('a => b => c', 'a => (b => c)'),
        ('s.a.b', '(s.a).b'),
        # All levels at once.
        ('x -> fix f a => s.b c.d => e g', 'x -> ((((fix f) (a => (s.b))) ((c.d) => e)) g)'),
        ('x -> f a.b => c : g d => e : h', 'x -> ((f (((a.b) => c) : g)) ((d => e) : h))'),
    ]
    for source, grouped in cases:
        if grouped == 'error':
            assert show(parse(source)) == 'error', source
        else:
            assert show(parse(source)) != 'error', source
            assert show(parse(source)) == show(parse(grouped)), source
            assert parse(source) == parse(grouped), source


def test_parentheses_only_override_precedence():
    """Code that was an error only for lacking parentheses has a meaning (plan_annotation.md, problem 3)."""
    y, x = terms.Variable('y'), terms.Variable('x')
    assert parse('y : x') == terms.Formed(y, x)
    assert parse('x: i32 -> x') == terms.Lambda('x', terms.Variable('i32'), x)
    assert parse('x: s.f -> x') == terms.Lambda('x', terms.Project(terms.Variable('s'), 'f'), x)
    # A lambda, `if`, `let` or `fix` binds looser than any operand, so as an operand it needs parentheses.
    operands = [
        ('f x -> x', 'f (x -> x)'),
        ('f if c then a else b', 'f (if c then a else b)'),
        ('f let x = a in x', 'f (let x = a in x)'),
        ('a => x -> x', 'a => (x -> x)'),
        ('fix x -> b', 'fix (x -> b)'),
        ('f fix g', 'f (fix g)'),
    ]
    for bare, parenthesized in operands:
        assert show(parse(bare)) == 'error', bare
        assert show(parse(parenthesized)) != 'error', parenthesized


def test_formed():
    y, x = terms.Variable('y'), terms.Variable('x')
    term = parse('y : x')
    assert term == terms.Formed(y, x)
    assert term.location == syntax.Location(0, 5)
    assert parse('(x -> y -> y : x) a b').function.function.body.body == terms.Formed(
        terms.Variable('y'), terms.Variable('x')
    )
    assert parse("y : 'i8' => 'i32'") == terms.Formed(
        y, terms.FunctionForm(terms.name_to_form('i8'), terms.name_to_form('i32'))
    )


def test_formed_leaves_binder_forms_alone():
    # A lambda is tried first. A byte array is only bytes, so its `: form` is a Formed.
    assert isinstance(parse("x : 'i8' -> x"), terms.Lambda)
    assert parse("x : 'i8'") == terms.Formed(terms.Variable('x'), terms.name_to_form('i8'))
    assert parse("[01] : 'i8'") == terms.Formed(terms.ByteArray(b'\x01'), terms.name_to_form('i8'))
    assert parse('[01] : y') == terms.Formed(terms.ByteArray(b'\x01'), terms.Variable('y'))
    assert parse("[01] : 'i8'").location == syntax.Location(0, 11)


def test_byte_array_with_a_form_in_a_binder_form():
    i8 = terms.name_to_form('i8')
    assert parse("x: [00]: 'i8' -> x").param_form == terms.Formed(terms.ByteArray(b'\x00'), i8)
    assert show(parse("x: [00]: 'i8' -> x")) == "x:[00]:'i8' → x"
    assert show(parse("x: ([00]: 'i8') => 'i32' -> x")) == "x:([00]:'i8') ⇒ 'i32' → x"


def test_function_form_param_with_a_form_needs_parens():
    term = parse("([00]: 'i8') => 'i32'")
    assert term.param == terms.Formed(terms.ByteArray(b'\x00'), terms.name_to_form('i8'))
    assert show(term) == "([00]:'i8') ⇒ 'i32'"
    assert parse("[00]: 'i8' => 'i32'").form == parse("'i8' => 'i32'")


def test_function_form_does_not_swallow_lambda_binder():
    source = "decls: {f = {} => 'i32'} -> defs -> {}"
    assert show(parse(source)) == "decls:{f = {} ⇒ 'i32'} → defs → {}"
    assert show(parse("decls: {} => 'i32' -> defs -> {}")) == "decls:{} ⇒ 'i32' → defs → {}"


def test_quoted_names():
    assert show(parse('"a b"')) == '"a b"'
    assert show(parse('"if" -> "if"')) == '"if" → "if"'
    assert show(parse('s."a b"')) == 's."a b"'
    assert show(parse('{"x y" = a}')) == '{"x y" = a}'
    assert show(parse("x : 'my form' -> x")) == "x:'my form' → x"


@pytest.mark.parametrize('word', sorted(RESERVED))
def test_quoted_keyword_is_a_name(word):
    assert show(parse(f'{word} -> {word}')) == 'error'
    assert show(parse(f'f {word}')) == 'error'
    assert show(parse(f'"{word}" -> "{word}"')) == f'"{word}" → "{word}"'
    assert show(parse(f'f "{word}"')) == f'f "{word}"'
    assert show(parse(f'{{"{word}" = a}}."{word}"')) == f'{{"{word}" = a}}."{word}"'


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
    assert show(parse('// id\nx -> // body\n  x // end')) == 'x → x'


def test_locations_skip_leading_trivia():
    term = parse('  // c\n  f a')
    assert term.location == syntax.Location(9, 12)
    assert term.function.location == syntax.Location(9, 10)
    assert term.argument.location == syntax.Location(11, 12)


def test_golden_program():
    source = "prim -> decls: {} -> defs -> {main = a:'i32' -> [00000000] : 'i32'}"
    assert show(parse(source)) == "prim → decls:{} → defs → {main = a:'i32' → [00000000]:'i32'}"
