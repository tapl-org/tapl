# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import bruijn, terms
from oymo.oymomo.grammar import RESERVED, parse
from oymo.oymomo.printer import show


def resolved(source, free=()):
    """Resolves `source` with the names in `free` bound outside it, outermost first."""
    term = bruijn.resolve(parse(' -> '.join([*free, source])))
    for _ in free:
        term = term.body
    return term


def test_resolve():
    assert show(resolved('x -> y -> x')) == 'x → y → $1'
    assert show(resolved('x -> y -> y')) == 'x → y → $0'
    assert show(resolved('x -> x -> x')) == 'x → x → $0'


@pytest.mark.parametrize('word', sorted(RESERVED))
def test_resolve_quoted_keyword(word):
    assert show(resolved(f'"{word}" -> "{word}"')) == f'"{word}" → $0'
    assert show(resolved(f'x -> "{word}" x', free=(f'"{word}"',))) == 'x → $1 $0'


def test_resolve_keeps_labels():
    assert show(resolved('s -> {a = s}.a')) == 's → {a = $0}.a'


def test_resolve_inside_function_form():
    assert show(resolved('a -> b -> x: (a => b) -> x')) == 'a → b → x:$1 ⇒ $0 → $0'


def test_resolve_keeps_location():
    term = bruijn.resolve(parse('x -> x'))
    assert term.body == terms.BruijnIndex(0)
    assert term.body.location == terms.Location(5, 6)


def test_resolve_unknown_name():
    with pytest.raises(bruijn.BruijnError) as info:
        bruijn.resolve(parse('x -> y'))
    assert info.value.message == "Unknown name 'y'."
    assert info.value.location == terms.Location(5, 6)


def test_resolve_forms_in_the_outer_scope():
    # A param's form can't see the param itself; it sees the binders around the lambda.
    assert show(resolved('x: (a) -> x: (x) -> x', free=('a',))) == 'x:$0 → x:$0 → $0'
    assert show(resolved('[00]: {f = (a)} => (a)', free=('a',))) == '[00]:{f = $0} ⇒ $0'
    with pytest.raises(bruijn.BruijnError, match="Unknown name 'x'"):
        bruijn.resolve(parse('x: (x) -> x'))


def test_shift_and_substitute_reach_forms():
    term = resolved('x: (a) -> [00]: (x)', free=('a',))
    assert show(term) == 'x:$0 → [00]:$0'
    assert show(bruijn.shift(term, 1)) == 'x:$1 → [00]:$0'
    assert show(bruijn.substitute(term, 0, terms.BruijnIndex(5))) == 'x:$5 → [00]:$0'


def test_shift():
    term = resolved('x -> a b x', free=('a', 'b'))
    assert show(term) == 'x → $2 $1 $0'
    assert show(bruijn.shift(term, 1)) == 'x → $3 $2 $0'
    assert show(bruijn.shift(term, 1, cutoff=1)) == 'x → $3 $1 $0'


def test_substitute():
    term = resolved('x -> a b x', free=('a', 'b'))
    # Replaces b (index 0 from the root, $1 under x) with $5, shifted under x to $6.
    assert show(bruijn.substitute(term, 0, terms.BruijnIndex(5))) == 'x → $2 $6 $0'
    assert show(bruijn.substitute(term, 1, terms.BruijnIndex(5))) == 'x → $6 $1 $0'


def test_beta_avoids_capture():
    # (x -> y -> x) y gives y' -> y, where y is the free y, not the inner binder.
    apply = resolved('(x -> y -> x) y', free=('y',))
    assert show(bruijn.beta(apply.function, apply.argument)) == 'y → $1'


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # The lambda's form goes with the argument.
        ("(x : 'i8' -> x) [01]", "[01]:'i8'"),
        # The lambda's form replaces the argument's own form.
        ("(x : 'i8' -> x) [01]:'i16'", "[01]:'i8'"),
        # Only the outer form is replaced: a form inside the term or the form stays.
        ("(x:'i8'->x) ([01]:'i16'):'i32'", "([01]:'i16'):'i8'"),
        ("(x:'i8'->x) [01]:('i16':'i32')", "[01]:'i8'"),
        ('(x : t -> f x) y', 'f (y:t)'),
        # No form on the lambda: the argument goes in as it is, with its own form if any.
        ('(x -> x) [01]', '[01]'),
        ("(x -> x) [01]:'i16'", "[01]:'i16'"),
        ("let x : 'i1' = [01] in x", "[01]:'i1'"),
    ],
)
def test_beta_propagates_form(source, expected):
    free = ('f', 't', 'y')
    apply = resolved(source, free)
    assert bruijn.beta(apply.function, apply.argument) == resolved(expected, free)


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('(x -> x) y', 'y'),
        ('fix g', 'g (fix g)'),
        ('{a = e}.a', 'e'),
        ('if [01] then a else b', 'a'),
        ('if [00] then a else b', 'b'),
        ('(x -> x) ((y -> y) z)', '(y -> y) z'),
        ('(x -> y) ((w -> w w) (w -> w w))', 'y'),
    ],
)
def test_reduce_one_step(source, expected):
    free = ('a', 'b', 'e', 'g', 'y', 'z')
    assert show(bruijn.reduce(resolved(source, free))) == show(resolved(expected, free))


@pytest.mark.parametrize(
    'source',
    [
        'x -> x',
        '{a = e}',
        '[01]',
        'e',
        'prim.add_i32 {a = e, b = e}',
        'args.n',
        'if e then a else b',
        'if [02] then a else b',
        '{a = e}.b',
        '{p = {a = e}}.p.a',
        '((x -> x) (y -> y)) e',
        '(fix g) a',
        'if ((x -> x) [01]) then a else b',
        'x -> (y -> y) x',
    ],
)
def test_reduce_returns_the_term_itself(source):
    term = resolved(source, ('a', 'b', 'e', 'g', 'prim', 'args'))
    assert bruijn.reduce(term) is term


def test_shift_and_substitute_reach_formed():
    term = terms.Formed(terms.BruijnIndex(0), terms.BruijnIndex(1))
    assert bruijn.shift(term, 1) == terms.Formed(terms.BruijnIndex(1), terms.BruijnIndex(2))
    assert bruijn.substitute(term, 1, terms.BruijnIndex(5)) == terms.Formed(terms.BruijnIndex(0), terms.BruijnIndex(5))


def test_resolve_reaches_formed():
    term = bruijn.resolve(
        terms.Lambda(
            'x', terms.Void, terms.Lambda('y', terms.Void, terms.Formed(terms.Variable('y'), terms.Variable('x')))
        )
    )
    assert show(term) == 'x → y → $0:$1'


@pytest.mark.parametrize(('value', 'expected'), [(b'\x01', 'a'), (b'\x00', 'b')])
def test_reduce_if_sees_through_a_form(value, expected):
    a, b = terms.BruijnIndex(1), terms.BruijnIndex(0)
    condition = terms.Formed(terms.ByteArray(value), terms.name_to_form('i1'))
    assert bruijn.reduce(terms.If(condition, a, b)) == {'a': a, 'b': b}[expected]
