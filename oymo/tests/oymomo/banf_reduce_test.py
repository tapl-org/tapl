# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import banf_reduce, bruijn, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show


def program(defs):
    return f'module: {{}} -> {{{defs}}}'


def shaped(defs):
    return show(banf_reduce.shape(bruijn.resolve(parse(program(defs)))))


def same(defs):
    return show(bruijn.resolve(parse(program(defs))))


def block(body, params="{n = 'i8'}"):
    return f'main = f -> {{entry = args: {params} -> {body}}}'


def resolved(source, free):
    term = bruijn.resolve(parse(' -> '.join([*free, source])))
    for _ in free:
        term = term.body
    return term


def test_whnf_reduces_heads():
    free = ('a', 'e')
    assert show(banf_reduce.whnf(resolved('{p = {a = e}}.p.a', free))) == show(resolved('e', free))
    assert show(banf_reduce.whnf(resolved('$fix (self -> n -> n) a', free))) == show(resolved('a', free))


def _first(_call, argument):
    """A test-only strict rule: `$first s` is the first field of the struct `s`."""
    if isinstance(argument, terms.Struct) and argument.fields:
        return argument.fields[0].value
    return None


@pytest.fixture
def first_rule(monkeypatch):
    monkeypatch.setitem(bruijn.BUILTIN_RULES, 'first', bruijn.BuiltinRule('first', True, 'a struct', _first))


@pytest.mark.usefixtures('first_rule')
def test_a_strict_builtin_reduces_its_argument_first():
    # The argument is reduced to a struct, then the rule fires.
    assert show(banf_reduce.whnf(resolved("$first ((x -> x) {a = '1'})", ()))) == "'1'"
    assert show(banf_reduce.whnf(resolved("$first ({s = {'1', '2'}}.s)", ()))) == "'1'"


@pytest.mark.usefixtures('first_rule')
def test_a_strict_builtin_on_a_stuck_argument_is_unchanged():
    term = resolved('$first e', ('e',))
    assert banf_reduce.whnf(term) is term
    term = resolved('$first args.p', ('args',))
    assert banf_reduce.whnf(term) is term


def test_fix_is_not_strict():
    # `$fix g` unfolds without reducing `g`.
    term = resolved('$fix ((x -> x) g)', ('g',))
    assert show(banf_reduce.step(term)) == show(resolved('(x -> x) g ($fix ((x -> x) g))', ('g',)))


def test_step_reduces_the_root_or_else_the_head():
    free = ('e',)
    assert show(banf_reduce.step(resolved('{p = {a = e}}.p.a', free))) == show(resolved('{a = e}.a', free))
    term = resolved('e.a', free)
    assert banf_reduce.step(term) is term


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # The index comes from a variable.
        ("(i -> {a = '23', b = '45'} i) [01]", "'45'"),
        # A computed callee and a computed index.
        ("{p = {a = '23'}}.p ((x -> x) [00])", "'23'"),
        # Nested: the inner struct apply is the head of the outer one.
        ("{{'1'}} [00] [00]", "'1'"),
        # A struct of functions called by index.
        ("(s -> s [01] '7') {x -> '1', x -> x}", "'7'"),
    ],
)
def test_whnf_reduces_a_struct_apply(source, expected):
    assert show(banf_reduce.whnf(resolved(source, ()))) == show(resolved(expected, ()))


@pytest.mark.parametrize(
    'source',
    [
        # Past the last field: stuck.
        "{a = '23'} [01]",
        # The callee is not a struct, so the argument is not reduced.
        'f ((x -> x) [00])',
    ],
)
def test_whnf_leaves_a_struct_apply_or_an_argument(source):
    term = resolved(source, ('f',))
    assert banf_reduce.whnf(term) is term


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        # A helper is inlined.
        (
            '(id -> let t = $add_i8 {a = id args.n, b = args.n} in t) (x -> x)',
            'let t = $add_i8 {a = args.n, b = args.n} in t',
        ),
        # An atom let is substituted.
        ('let t = args.n in t', 'args.n'),
        (
            'let t = args.n in let u = $add_i8 {a = t, b = t} in u',
            'let u = $add_i8 {a = args.n, b = args.n} in u',
        ),
        # $fix unfolds.
        ('$fix (self -> n -> n) args.n', 'args.n'),
        # Heads.
        ('((a -> {n = a.n}) args).n', 'args.n'),
        (
            'let t = {g = x -> $add_i8 {a = x, b = x}}.g args.n in t',
            'let t = $add_i8 {a = args.n, b = args.n} in t',
        ),
        (
            '(x -> y -> let t = $add_i8 {a = x, b = y} in t) args.n ($mul_i8 {a = args.n, b = args.n})',
            'let y = $mul_i8 {a = args.n, b = args.n} in let t = $add_i8 {a = args.n, b = y} in t',
        ),
        # Projection.
        (
            'let t = $add_i8 {a = {a = args.n}.a, b = args.n} in t',
            'let t = $add_i8 {a = args.n, b = args.n} in t',
        ),
        ('{p = {a = args.n}}.p.a', 'args.n'),
        ('(mk -> (mk args).n) (a -> {n = a.n})', 'args.n'),
        # A let whose op has a redex operand stays a let.
        (
            'let t = $add_i8 {a = (x -> x) args.n, b = args.n} in t',
            'let t = $add_i8 {a = args.n, b = args.n} in t',
        ),
        # A let-bound struct and a GetField on a param stay lets.
        ('let s = {a = args.n} in s', 'let s = {a = args.n} in s'),
        # An if bound by a let is substituted into the tail.
        ('let t = if args.n then f.a {} else f.b {} in t', 'if args.n then f.a {} else f.b {}'),
        # A redex in an if's condition and arms.
        (
            'if (x -> x) args.n then (x -> f.a x) {} else f.b ((x -> x) {})',
            'if args.n then f.a {} else f.b {}',
        ),
        # A jump's argument.
        ('f.a ((x -> {m = x}) args.n)', 'f.a {m = args.n}'),
    ],
)
def test_block_body(body, expected):
    assert shaped(block(body)) == same(block(expected))


def test_get_field_on_struct_param_stays_a_let():
    source = block('let x = args.p.x in x', "{p = {x = 'i8'}}")
    assert shaped(source) == same(source)


def test_a_def_produced_by_an_application():
    assert shaped("main = (x -> x) (f -> {entry = args: {} -> [01]: 'i8'})") == same(
        "main = f -> {entry = args: {} -> [01]: 'i8'}"
    )


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # Each position, reached after reduction.
        (
            '(p -> p) (module: {} -> {})',
            'module: {} -> {}',
        ),
        (
            '{d = module: {} -> {}}.d',
            'module: {} -> {}',
        ),
        (
            "module: {} -> (x -> x) {main = f -> (x -> x) {entry = (x -> x) (args: {} -> [01]: 'i8')}}",
            "module: {} -> {main = f -> {entry = args: {} -> [01]: 'i8'}}",
        ),
    ],
)
def test_positions(source, expected):
    assert show(banf_reduce.shape(bruijn.resolve(parse(source)))) == show(bruijn.resolve(parse(expected)))


def test_forms_are_ignored():
    assert shaped(block('(x -> x) args.n')) == same(block('args.n'))


@pytest.mark.parametrize(
    'body',
    [
        "[01]: 'i8'",
        'args.n',
        'let t = $add_i8 {a = args.n, b = args.n} in t',
        'f.a {}',
        'if args.n then f.a {} else f.b {}',
    ],
)
def test_terminals_stay(body):
    assert shaped(block(body)) == same(block(body))


@pytest.mark.parametrize(
    'defs',
    [
        'main = x -> x',
        block('{a = args.n}.b'),
        block('args'),
        block('$add_i8'),
    ],
)
def test_terms_that_cannot_reach_the_shape_are_left(defs):
    assert shaped(defs) == same(defs)


def test_already_shaped_is_unchanged():
    source = """
    fact = f -> {
      entry = args:{n = 'i32'} ->
        let t0 = $eq_i32 {a = args.n, b = [00000000]:'i32'} in
        if t0 then f.then0 {} else f.else0 {n = args.n},
      then0 = args:{} -> [01000000]:'i32',
      else0 = args:{n = 'i32'} ->
        let t1 = $sub_i32 {minuend = args.n, subtrahend = [01000000]:'i32'} in
        let t2 = module.fact {n = t1} in
        let t3 = $mul_i32 {a = args.n, b = t2} in
        t3,
    }
    """
    assert shaped(source) == same(source)


def test_runs_out_of_fuel():
    term = bruijn.resolve(parse(program(block('$fix (self -> self) args.n'))))
    with pytest.raises(bruijn.BruijnError, match='ran out of reduction steps'):
        banf_reduce.shape(term, fuel=100)


def test_whnf_reduces_inside_formed():
    i1 = terms.ByteArray(b'i1')
    one = terms.ByteArray(b'\x01')
    identity = terms.Lambda('x', terms.Empty, terms.BruijnIndex(0))
    reduced = banf_reduce.whnf(terms.Formed(terms.Apply(identity, one), i1))
    assert reduced == terms.Formed(one, i1)


def test_dynamic_byte_array_form():
    reduced = banf_reduce.whnf(bruijn.resolve(parse("(x -> y -> y: x) 'i1' [01]")))
    assert reduced == parse("[01]:'i1'")
    assert show(reduced) == "[01]:'i1'"
