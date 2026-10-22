# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The strategy of table 6.2 (semantics.tex, Section 6): one test per row, and the cases
of open item 11 in `docs/agent_wiki.md` (section 4, "Semantics decisions")."""

import functools
import random
from dataclasses import replace

import pytest

from oymo.oymomo import reduction, strategy, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show

OMEGA = '((λw. w w) (λw. w w))'
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
        ('b', '(fix (λs. {x = a, y = s})).y', '{x = a, y = fix (λs. {x = a, y = s})}.y'),
        ('c', '((λs. s) {x = a}).x', '{x = a}.x'),
        ('c', '{y = (λz. z) a}.x', '{y = a}.x'),
        ('c', '(fix ((λy. y) (λs. s))).x', '(fix (λs. s)).x'),
        ('d', '(λx. {x, x}) (λy. y)', '{λy. y, λy. y}'),
        ('d', '(λx. {x, x}) (fix (λs. s))', '{fix (λs. s), fix (λs. s)}'),
        ('e', '(λx. x) ((λy. y) a)', '(λx. x) a'),
        ('f', '(fix (λs. λn. s n)) ((λy. y) a)', '(λn. fix (λs. λn. s n) n) ((λy. y) a)'),
        ('g', "'add' {'i8', [01], [02]}", '[03]'),
        ('h', '{a, b, c} [01]', 'b'),
        ('i', '{a, b, c} [05]', 'c'),
        ('j', '{a, b} ((λy. y) c)', '{a, b} c'),
        ('k', '((λy. y) g) ((λy. y) a)', 'g ((λy. y) a)'),
        ('l', 'g ((λy. y) a)', 'g a'),
        ('m', '{f = λu. (λy. y) u, g = (λy. y) a}', '{f = λu. (λy. y) u, g = a}'),
        ('n', '{f = λu. (λy. y) u, g = a}', '{f = λu. u, g = a}'),
        ('o', 'λu. (λy. y) u', 'λu. u'),
        ('p', 'fix (λs. (λy. y) s)', 'fix (λs. s)'),
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
        "'store' {'i32', [05000000], p}",
        '(λx. [01]) p.n',
        '{a, b} p.n',
        '{} a',
        '[01] (λx. x)',
        '(λx. x).l',
        'fix (λs. s)',
        'fix (λs. {l = λq. s.l q})',
        'fix [01]',
        'fix p.n',
    ],
)
def test_normal_forms_have_no_step(source):
    assert strategy.sstep(resolved(source)) is None


def test_row_e_before_row_k():
    # The argument of a lambda is reduced before the lambda's body.
    assert step('(λx. (λy. y) x) ((λy. y) a)') == same('(λx. (λy. y) x) a')
    # With a normal argument that is not a value, the body is next.
    assert step('(λx. (λy. y) x) p.n') == same('(λx. x) p.n')


def test_row_j_before_row_k():
    # A branch's condition is reduced before its arms.
    assert step('{(λy. y) a, b} ((λy. y) c)') == same('{(λy. y) a, b} c')


def test_row_m_before_row_n():
    # 6.3d: a field that is not a value comes first.
    assert step('{λu. (λy. y) u, (λy. y) a}') == same('{λu. (λy. y) u, a}')


def test_order_goes_under_lambda_last():
    assert step('{λu. (λy. y) u, {(λy. y) a}}') == same('{λu. (λy. y) u, {a}}')


# Open item 11 (agent_wiki.md, "Semantics decisions"): reduction unit tests.


def test_11a_projection_is_not_a_value():
    # D92: every order ends in the same stuck term; neither gives [01].
    assert normal('(λy. (λx. [01]) y.l) {m = [00]}') == same('(λx. [01]) {m = [00]}.l')


def test_11b_projection_drops_a_looping_field():
    assert normal(f'{{a = {OMEGA}, b = [01]}}.b') == '[01]'


def test_11c_row_m_never_enters_a_looping_lambda():
    assert normal(f'(λx. x.g) {{f = λu. {OMEGA}, g = (λy. y) [01]}}') == '[01]'


def test_11d_projection_first_then_beta():
    assert step('(λx. x x) ({l = (λy. y) [01]}.l)') == same('(λx. x x) ((λy. y) [01])')
    assert normal('(λx. x x) ({l = (λy. y) [01]}.l)') == same('[01] [01]')


def test_11f_fix_recursion():
    # The factorial of 4.8d on an unknown never stops: the term grows until a limit stops it.
    with pytest.raises(reduction.ReductionError, match=r'No normal form|too deep'):
        normal(f'{FACT} p.n', max_steps=300)
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
    source = "let u = 'store' {'i32', [05000000], p} in let x = 'load' {'i32', p} in x"
    assert normal(source) == same(source)


@pytest.mark.parametrize('source', ['{} a', '[01] (λx. x)', '(λx. x).l', "'add' {'i32', 'mul' {'i32', p.n, p.n}, p.n}"])
def test_11i_stuck_and_non_anf_normal_forms(source):
    assert normal(source) == same(source)


def test_normalize_gives_up():
    with pytest.raises(reduction.ReductionError, match='No normal form within 50 steps'):
        normal(OMEGA, max_steps=50)


# Euclid on blocks that jump to each other: the gcd of 8.10, run by reduction. Reduction never
# binds `m` or `f` (8.8), so the program binds them itself with `fix` (8.8b).
GCD_MODULE_PROGRAM = """
let module = λm. {
  gcd = {gives = 'i32', body = λf. {
      entry = {takes = {a = 'i32', b = 'i32'}, body = λp.
        f.loop.body {a = p.a, b = p.b}
      },
      loop = {takes = {a = 'i32', b = 'i32'}, body = λp.
        let t0 = 'icmp' {'eq', 'i32', p.b, [00000000]} in
        if t0 then f.done.body {a = p.a} else f.step.body {a = p.a, b = p.b}
      },
      step = {takes = {a = 'i32', b = 'i32'}, body = λp.
        let t1 = 'urem' {'i32', p.a, p.b} in
        f.loop.body {a = p.b, b = t1}
      },
      done = {takes = {a = 'i32'}, body = λp.
        p.a
      }
    }
  }
} in
let gcd = (fix (fix module).gcd.body).entry.body in
  gcd {a = [30000000], b = [12000000]}
"""

# The factorial of 4.8d.
FACT = """
fix (λf. λn.
  if 'icmp' {'eq', 'i32', n, [00000000]} then [01000000]
  else 'mul' {'i32', n, f ('sub' {'i32', n, [01000000]})})
"""

# fib 6 = 8.
FIB_PROGRAM = """
fix (λfib. λn.
  if 'icmp' {'ult', 'i32', n, [02000000]} then n
  else 'add' {'i32', fib ('sub' {'i32', n, [01000000]}), fib ('sub' {'i32', n, [02000000]})})
[06000000]
"""

# Collatz from 7 takes 16 steps.
COLLATZ_PROGRAM = """
fix (λcollatz. λn.
  if 'icmp' {'eq', 'i32', n, [01000000]} then [00000000]
  else 'add' {'i32', [01000000], collatz (
    if 'and' {'i32', n, [01000000]}
    then 'add' {'i32', 'mul' {'i32', n, [03000000]}, [01000000]}
    else 'udiv' {'i32', n, [02000000]})})
[07000000]
"""


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # 3! = 6.
        (f'{FACT} [03000000]', '[06000000]'),
        (FIB_PROGRAM, '[08000000]'),
        (COLLATZ_PROGRAM, '[10000000]'),
        # gcd 48 18 = 6, in module shape (Section 8).
        (GCD_MODULE_PROGRAM, '[06000000]'),
    ],
)
def test_whole_programs(source, expected):
    assert normal(source) == expected


def test_fix_stays_where_it_is_not_used():
    # 4.8c: a normal form holds a fixed point only where it is not used.
    source = 'fix (λs. {l = λq. s.l q})'
    assert normal(source) == same(source)
    # Used, it unfolds; here the copy is dropped, so the normal form has none.
    assert normal('(fix (λs. {a = [01], b = s})).a') == '[01]'


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
        case terms.Fix(body=body):
            found += [replace(term, body=b) for b in all_steps(body)]
        case terms.Struct(fields=fields):
            for i, f in enumerate(fields):
                for v in all_steps(f.value):
                    found.append(replace(term, fields=[*fields[:i], replace(f, value=v), *fields[i + 1 :]]))
    return found


@functools.cache
def omega_term():
    """Ω, parsed once and shared: no code changes a term in place."""
    return resolved(OMEGA, ())


def random_term(rng, depth, scope):
    """A small random term over `scope` bound variables: lambdas, applications, structs,
    projections, fixed points and byte arrays, with an Ω now and then."""
    choices = ['bytes', 'lam', 'app', 'app', 'struct', 'proj', 'fix', 'omega']
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
        case 'fix':
            return terms.Fix(terms.Lambda('s', random_term(rng, depth - 1, scope + 1)))
    return omega_term()


def key(term):
    """`term` as nested tuples, to compare and hash (the term classes do neither), and its
    size in nodes."""
    match term:
        case terms.BruijnIndex(index=index):
            return ('var', index), 1
        case terms.ByteArray(value=value):
            return ('bytes', value), 1
        case terms.Lambda(param_name=name, body=body):
            body_key, size = key(body)
            return ('lam', name, body_key), size + 1
        case terms.Apply(function=function, argument=argument):
            (function_key, function_size), (argument_key, argument_size) = key(function), key(argument)
            return ('app', function_key, argument_key), function_size + argument_size + 1
        case terms.Project(struct=struct, label=label):
            struct_key, size = key(struct)
            return ('proj', struct_key, label), size + 1
        case terms.Fix(body=body):
            body_key, size = key(body)
            return ('fix', body_key), size + 1
        case terms.Struct(fields=fields):
            parts = [(f.label, key(f.value)) for f in fields]
            return ('struct', *((label, k) for label, (k, _) in parts)), sum(s for _, (_, s) in parts) + 1
    raise TypeError(term)


def normal_forms(term, limit=300, max_size=100):
    """The keys of the normal forms reachable from `term` by any order, searching at most
    `limit` terms; None if the search did not finish. It gives up on a term that grows past
    `max_size` nodes, as a fixed point unfolding without end does."""
    seen, todo, normals = set(), [term], set()
    while todo:
        current = todo.pop()
        try:
            current_key, size = key(current)
        except RecursionError:
            return None
        if size > max_size:
            return None
        if current_key in seen:
            continue
        seen.add(current_key)
        if len(seen) > limit:
            return None
        steps = all_steps(current)
        if not steps:
            normals.add(current_key)
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
            assert key(stepped)[0] in {key(s)[0] for s in all_steps(term)}, show(term)
        assert key(strategy.normalize(term, max_steps=1000))[0] in normals, show(term)
        checked += 1
    assert checked > 1000
