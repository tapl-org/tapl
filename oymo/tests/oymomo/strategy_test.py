# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The strategy of table 6.2 (semantics.tex, Section 6): one test per row, and the cases
of open item 11 in `docs/semantics_discussion.md`."""

import random
from dataclasses import replace

import pytest

from oymo.oymomo import reduction, strategy, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show

OMEGA = '((λw. w w) (λw. w w))'
Z = '(λf. (λx. f (λv. x x v)) (λx. f (λv. x x v)))'
FREE = ('a', 'b', 'c', 'e', 'g', 'm', 'p', 'r', 'z')


def resolved(source, free=FREE):
    """Resolves `source` with the names in `free` bound outside it."""
    term = reduction.resolve(parse(''.join(f'λ{name}. ' for name in free) + source))
    for _ in free:
        term = term.body
    return term


def step(source):
    stepped = strategy.sstep(resolved(source))
    return None if stepped is None else show(stepped)


def normal(source, max_steps=strategy.MAX_STEPS):
    return show(strategy.normalize(resolved(source), max_steps))


def same(source):
    return show(resolved(source))


@pytest.mark.parametrize(
    ('row', 'source', 'expected'),
    [
        ('a', '{x = a, y = (λz. z) b}.y', '(λz. z) b'),
        ('b', '((λs. s) {x = a}).x', '{x = a}.x'),
        ('b', '{y = (λz. z) a}.x', '{y = a}.x'),
        ('c', '(λx. {x, x}) (λy. y)', '{λy. y, λy. y}'),
        ('d', '(λx. x) ((λy. y) a)', '(λx. x) a'),
        ('e', "'add' {'i8', [01], [02]}", '[03]'),
        ('f', '{a, b, c} [01]', 'b'),
        ('g', '{a, b, c} [05]', 'c'),
        ('h', '{a, b} ((λy. y) c)', '{a, b} c'),
        ('i', '((λy. y) g) ((λy. y) a)', 'g ((λy. y) a)'),
        ('j', 'g ((λy. y) a)', 'g a'),
        ('k', '{f = λu. (λy. y) u, g = (λy. y) a}', '{f = λu. (λy. y) u, g = a}'),
        ('l', '{f = λu. (λy. y) u, g = a}', '{f = λu. u, g = a}'),
        ('m', 'λu. (λy. y) u', 'λu. u'),
    ],
)
def test_each_row(row, source, expected):
    assert step(source) == same(expected), row


@pytest.mark.parametrize(
    'source',
    [
        'a',
        '[01]',
        'λx. x',
        '{a, b}',
        'p.n',
        '{x = a}.y',
        'g a',
        "'add' {'i32', p.n, [01000000]}",
        "'store' {[05000000], p}",
        '(λx. [01]) p.n',
        '{a, b} p.n',
        '{} a',
        '[01] (λx. x)',
        '(λx. x).l',
    ],
)
def test_normal_forms_have_no_step(source):
    assert strategy.sstep(resolved(source)) is None


def test_row_d_before_rows_i():
    # The argument of a lambda is reduced before the lambda's body.
    assert step('(λx. (λy. y) x) ((λy. y) a)') == same('(λx. (λy. y) x) a')
    # With a normal argument that is not a value, the body is next.
    assert step('(λx. (λy. y) x) p.n') == same('(λx. x) p.n')


def test_row_h_before_row_i():
    # A branch's condition is reduced before its arms.
    assert step('{(λy. y) a, b} ((λy. y) c)') == same('{(λy. y) a, b} c')


def test_row_k_before_row_l():
    # 6.3d: a field that is not a value comes first.
    assert step('{λu. (λy. y) u, (λy. y) a}') == same('{λu. (λy. y) u, a}')


def test_order_goes_under_lambda_last():
    assert step('{λu. (λy. y) u, {(λy. y) a}}') == same('{λu. (λy. y) u, {a}}')


# Open item 11 (semantics_discussion.md): reduction unit tests.


def test_11a_projection_is_not_a_value():
    # D92: every order ends in the same stuck term; neither gives [01].
    assert normal('(λy. (λx. [01]) y.l) {m = [00]}') == same('(λx. [01]) {m = [00]}.l')


def test_11b_projection_drops_a_looping_field():
    assert normal(f'{{a = {OMEGA}, b = [01]}}.b') == '[01]'


def test_11c_row_k_never_enters_a_looping_lambda():
    assert normal(f'(λx. x.g) {{f = λu. {OMEGA}, g = (λy. y) [01]}}') == '[01]'


def test_11d_projection_first_then_beta():
    assert step('(λx. x x) ({l = (λy. y) [01]}.l)') == same('(λx. x x) ((λy. y) [01])')
    assert normal('(λx. x x) ({l = (λy. y) [01]}.l)') == same('[01] [01]')


def test_11f_z_recursion():
    fact = (
        f"{Z} (λf. λn. if 'icmp' {{'eq', 'i32', n, [00000000]}} then [01000000] "
        "else 'mul' {'i32', n, f ('sub' {'i32', n, [01000000]})})"
    )
    assert normal(f'{fact} [03000000]') == '[06000000]'
    # Recursion on an unknown never stops: the term grows until a limit stops it.
    with pytest.raises(reduction.ReductionError, match=r'No normal form|too deep'):
        normal(f'{fact} p.n', max_steps=300)
    # Y never works under call-by-value.
    y = '(λf. (λx. f (x x)) (λx. f (x x)))'
    with pytest.raises(reduction.ReductionError, match='No normal form'):
        normal(f'{y} (λf. λn. n) [01]', max_steps=300)


def test_11g_projection_drops_a_field_but_a_let_keeps_it():
    assert normal('{a = e, b = [01]}.b') == '[01]'
    assert normal('(λx. {a = x, b = [01]}.b) (m.print {r})') == same('(λx. [01]) (m.print {r})')


def test_11h_a_call_is_never_copied():
    assert normal('(λx. {x, x}) (m.print {r})') == same('(λx. {x, x}) (m.print {r})')


def test_11j_store_stays_outside_load():
    source = "let u = 'store' {[05000000], p} in let x = 'load' {'i32', p} in x"
    assert normal(source) == same(source)


@pytest.mark.parametrize('source', ['{} a', '[01] (λx. x)', '(λx. x).l', "'add' {'i32', 'mul' {'i32', p.n, p.n}, p.n}"])
def test_11i_stuck_and_non_anf_normal_forms(source):
    assert normal(source) == same(source)


def test_normalize_gives_up():
    with pytest.raises(reduction.ReductionError, match='No normal form within 50 steps'):
        normal(OMEGA, max_steps=50)


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # fib 6 = 8.
        (
            f"{Z} (λfib. λn. if 'icmp' {{'ult', 'i32', n, [02000000]}} then n "
            "else 'add' {'i32', fib ('sub' {'i32', n, [01000000]}), fib ('sub' {'i32', n, [02000000]})}) "
            '[06000000]',
            '[08000000]',
        ),
        # Collatz from 7 takes 16 steps.
        (
            f"{Z} (λcollatz. λn. if 'icmp' {{'eq', 'i32', n, [01000000]}} then [00000000] "
            "else 'add' {'i32', [01000000], collatz ("
            "if 'and' {'i32', n, [01000000]} "
            "then 'add' {'i32', 'mul' {'i32', n, [03000000]}, [01000000]} "
            "else 'udiv' {'i32', n, [02000000]})}) [07000000]",
            '[10000000]',
        ),
        # gcd 48 18 = 6.
        (
            f"{Z} (λgcd. λq. if 'icmp' {{'eq', 'i32', q.b, [00000000]}} then q.a "
            "else gcd {a = q.b, b = 'urem' {'i32', q.a, q.b}}) {a = [30000000], b = [12000000]}",
            '[06000000]',
        ),
    ],
)
def test_whole_programs(source, expected):
    assert normal(source) == expected


def all_steps(term):
    """Every `⟶` step from `term` (Sections 4 and 5): the root rule, if any, and a step
    inside each part."""
    found = []
    if (reduced := reduction.reduce(term)) is not term:
        found.append(reduced)
    match term:
        case terms.Lambda(body=body):
            found += [replace(term, body=b) for b in all_steps(body)]
        case terms.Apply(function=function, argument=argument):
            found += [replace(term, function=f) for f in all_steps(function)]
            found += [replace(term, argument=a) for a in all_steps(argument)]
        case terms.Project(struct=struct):
            found += [replace(term, struct=s) for s in all_steps(struct)]
        case terms.Struct(fields=fields):
            for i, f in enumerate(fields):
                for v in all_steps(f.value):
                    found.append(replace(term, fields=[*fields[:i], replace(f, value=v), *fields[i + 1 :]]))
    return found


def random_term(rng, depth, scope):
    """A small random term over `scope` bound variables: lambdas, applications, structs,
    projections and byte arrays, with an Ω now and then."""
    choices = ['bytes', 'lam', 'app', 'app', 'struct', 'proj', 'omega']
    if scope:
        choices += ['var', 'var']
    kind = rng.choice(choices) if depth > 0 else rng.choice(['bytes', 'var'] if scope else ['bytes'])
    match kind:
        case 'var':
            return terms.BruijnIndex(rng.randrange(scope))
        case 'bytes':
            return terms.ByteArray(bytes([rng.randrange(2)]))
        case 'lam':
            return terms.Lambda('x', random_term(rng, depth - 1, scope + 1))
        case 'app':
            return terms.Apply(random_term(rng, depth - 1, scope), random_term(rng, depth - 1, scope))
        case 'struct':
            labels = rng.sample(['l', 'm', ''], rng.randrange(3))
            return terms.Struct([terms.Field(label, random_term(rng, depth - 1, scope)) for label in labels])
        case 'proj':
            return terms.Project(random_term(rng, depth - 1, scope), rng.choice(['l', 'm']))
    return resolved(OMEGA, ())


def normal_forms(term, limit=300):
    """The normal forms reachable from `term` by any order, searching at most `limit` terms;
    None if the search did not finish."""
    seen, todo, normals = set(), [term], set()
    while todo:
        current = todo.pop()
        key = show(current)
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > limit:
            return None
        steps = all_steps(current)
        if not steps:
            normals.add(key)
        todo += steps
    return normals


def test_strategy_agrees_with_every_order():
    """When some order reaches a normal form, `normalize` reaches it too (`Oymomo.guarantee`)
    and it is the only one (`Oymomo.confluence`); `sstep` is a `⟶` step (`Oymomo.sstep_step`)."""
    rng = random.Random(0)  # noqa: S311 (a fixed seed, not for security)
    checked = 0
    for _ in range(3000):
        term = random_term(rng, 4, 0)
        normals = normal_forms(term)
        if not normals:
            continue
        assert len(normals) == 1, show(term)
        stepped = strategy.sstep(term)
        if stepped is not None:
            assert show(stepped) in {show(s) for s in all_steps(term)}, show(term)
        assert show(strategy.normalize(term, max_steps=1000)) in normals, show(term)
        checked += 1
    assert checked > 1000
