# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import random

import pytest

from oymo.core import syntax
from oymo.oymomo import layers, reduction, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show


def layered(low, high):
    return syntax.Layers(layers=(low, high))


def separate(source):
    found = layers.separate(parse(source))
    assert found is not None
    return found


def test_one_layer_has_no_separation():
    assert layers.separate(parse('λx. f x {a = b}.a')) is None
    assert not layers.has_layering(parse('f x'))
    assert layers.has_layering(parse('f (x : y)'))


@pytest.mark.parametrize(
    ('source', 'low', 'high'),
    [
        ('a : b', 'a', 'b'),
        ('λx. (a : b)', 'λx. a', 'λx. b'),
        ('(a : b) (c : d)', 'a c', 'b d'),
        ('{l = a : b, m = c}', '{l = a, m = c}', '{l = b, m = c}'),
        ('(s : t).l', 's.l', 't.l'),
        ('fix (f : g)', 'fix f', 'fix g'),
        ('let x = (a : b) in f x', 'let x = a in f x', 'let x = b in f x'),
        ('(λs. s) (t1 : t2)', '(λs. s) t1', '(λs. s) t2'),
        ("'add' {'i32', x, [01] : y}", "'add' {'i32', x, [01]}", "'add' {'i32', x, y}"),
    ],
)
def test_separation_part_by_part(source, low, high):
    assert separate(source) == (parse(low), parse(high))


def test_a_part_with_no_layering_is_shared():
    term = parse('f {a = x : y, b = g z} (λw. w)')
    low, high = layers.separate(term)
    assert isinstance(low, terms.Apply)
    assert isinstance(high, terms.Apply)
    assert low.argument is high.argument is term.argument  # `λw. w` has no layering
    assert low.function.argument.fields[1].value is term.function.argument.fields[1].value
    assert high.function.argument.fields[1].value is term.function.argument.fields[1].value
    assert low.function.function is term.function.function


def test_separation_keeps_binder_names_and_tags():
    term = parse('λq. (q : f q)')
    low, high = layers.separate(term)
    assert isinstance(low, terms.Lambda)
    assert isinstance(high, terms.Lambda)
    assert low.param_name == high.param_name == 'q'
    assert low.tag == high.tag == term.tag


def test_separation_drops_the_layerings_tag():
    term = parse('f (x : y)')
    assert isinstance(term, terms.Apply)
    layering = term.argument
    low, high = layers.separate(term)
    tags = {node.tag for layer in (low, high) for node in terms.nodes(layer)}
    assert layering.tag not in tags
    assert low.argument.tag == layering.layers[0].tag


x, y, a, b, c, d = (terms.Variable(n) for n in 'xyabcd')


@pytest.mark.parametrize(
    ('low', 'high', 'merged'),
    [
        (parse('f x'), parse('f x'), 'f x'),
        (parse('a b'), parse('c d'), '(a : c) (b : d)'),
        (parse('a b'), parse('a d'), 'a (b : d)'),
        (parse('λx. f x'), parse('λx. g x'), 'λx. (f : g) x'),
        (parse('λx. x'), parse('λy. y'), '(λx. x) : (λy. y)'),
        (parse('{l = a, m = b}'), parse('{l = a, m = c}'), '{l = a, m = b : c}'),
        (parse('{l = a, m = b}'), parse('{m = b, l = a}'), '{l = a, m = b} : {m = b, l = a}'),
        (parse('s.l'), parse('t.l'), '(s : t).l'),
        (parse('s.l'), parse('s.m'), 's.l : s.m'),
        (parse('fix f'), parse('fix g'), 'fix (f : g)'),
        (parse('a'), parse('f a'), 'a : f a'),
        (parse('let y = f a in y'), parse('let y = g a in y'), 'let y = (f : g) a in y'),
    ],
)
def test_merge(low, high, merged):
    term = layers.merge(low, high)
    assert show(term) == merged
    assert parse(merged) == term
    assert term.separate(syntax.LayerSeparator()) == (low, high)


def test_merge_of_equal_layers_is_the_low_term():
    low, high = parse('f {a = x}'), parse('f {a = x}')
    assert layers.merge(low, high) is low


def test_merge_keeps_lows_tags():
    low, high = parse('f a'), parse('f  b')
    term = layers.merge(low, high)
    assert term.tag == low.tag
    assert term.function.tag == low.function.tag


def random_term(rng, depth):
    """A small random term with variables, lambdas with a few binder names, applications,
    structs, projections, fixed points and byte arrays."""
    kind = rng.choice(['var', 'bytes', 'lam', 'app', 'app', 'struct', 'proj', 'fix']) if depth > 0 else 'leaf'
    match kind:
        case 'leaf':
            return rng.choice([terms.Variable(rng.choice('xyz')), terms.ByteArray(bytes([rng.randrange(2)]))])
        case 'var':
            return terms.Variable(rng.choice('xyz'))
        case 'bytes':
            return terms.ByteArray(bytes([rng.randrange(2)]))
        case 'lam':
            return terms.Lambda(rng.choice('xy'), random_term(rng, depth - 1))
        case 'app':
            return terms.Apply(random_term(rng, depth - 1), random_term(rng, depth - 1))
        case 'struct':
            labels = rng.sample(['l', 'm', ''], rng.randrange(3))
            return terms.Struct([terms.Field(label, random_term(rng, depth - 1)) for label in labels])
        case 'proj':
            return terms.Project(random_term(rng, depth - 1), rng.choice(['l', 'm']))
    return terms.Fix(random_term(rng, depth - 1))


def mutate(rng, term, depth):
    """`term` with a few parts replaced by random terms, so the two often share parts."""
    if rng.random() < 0.2:
        return random_term(rng, depth)
    match term:
        case terms.Lambda(param_name=name, body=body):
            return terms.Lambda(name, mutate(rng, body, depth))
        case terms.Apply(function=function, argument=argument):
            return terms.Apply(mutate(rng, function, depth), mutate(rng, argument, depth))
        case terms.Struct(fields=fields):
            return terms.Struct([terms.Field(f.label, mutate(rng, f.value, depth)) for f in fields])
        case terms.Project(struct=struct, label=label):
            return terms.Project(mutate(rng, struct, depth), label)
        case terms.Fix(body=body):
            return terms.Fix(mutate(rng, body, depth))
    return term


def test_merge_separates_back_on_random_pairs():
    rng = random.Random(7)
    for _ in range(500):
        low = random_term(rng, 4)
        high = mutate(rng, low, 3) if rng.random() < 0.8 else random_term(rng, 4)
        term = layers.merge(low, high)
        assert term.separate(syntax.LayerSeparator()) == (low, high)
        assert layers.has_layering(term) == (low != high)
        # Every layering it makes has plain sides, and the term prints and parses back.
        assert all(
            not layers.has_layering(side)
            for node in terms.nodes(term)
            if isinstance(node, syntax.Layers)
            for side in node.layers
        )
        assert parse(show(term)) == term
        assert parse(show(term, pretty=True, width=30)) == term


def test_resolve_rejects_a_layering():
    with pytest.raises(RuntimeError, match='layering reached reduction'):
        reduction.resolve(parse('λa. λb. a : b'))
