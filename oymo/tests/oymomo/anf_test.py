# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""ANF (Section 7) and stuck normal forms (5.5)."""

import pytest

from oymo.oymomo import anf, reduction, strategy
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show


def block_body(source, free=('m', 'f')):
    """`source` as a block's body: under `λp`, with `m` and `f` free (Section 8)."""
    term = reduction.resolve(parse(''.join(f'λ{name}. ' for name in free) + f'λp. {source}'))
    for _ in free:
        term = term.body
    return term.body


def error(source):
    found = anf.anf_error(block_body(source), local=1)
    return None if found is None else (found.message, show(found.term))


@pytest.mark.parametrize(
    'source',
    [
        # Returns: a let variable, a path from one, a free path, a byte array.
        'p',
        'p.a.b',
        'm.answer',
        '[2a000000]',
        "''",
        # Jumps: a call through a free path with atoms.
        'f.loop.body {a = p.a, b = [00]}',
        'm.gcd {a = p.b, b = m.zero}',
        'f.done.body {}',
        # Lets of opcode calls and calls.
        "let x = 'add' {'i32', p.a, [01000000]} in x",
        "let x = 'add' {'i32', p.a, p.b} in let y = 'mul' {'i32', x, x} in m.print {y}",
        "let u = 'store' {'i32', [05000000], m.counter} in let x = 'load' {'i32', m.counter} in x",
        'let r = m.read {} in r.value',
        # An opcode E-Opcode does not compute: undefined behavior, an unknown opcode.
        "let x = 'sdiv' {'i32', [07000000], [00000000]} in x",
        "let x = 'frobnicate' {[01]} in x",
        # A branch of returns and jumps on a path (7.4, the gcd loop).
        "let z = 'icmp' {'eq', 'i32', p.b, [00000000]} in {f.step.body {a = p.a, b = p.b}, f.done.body {a = p.a}} z",
        '{p.a, m.zero, [00]} p.tag',
        '{a = p.x, b = f.next.body {}} p.c',
    ],
)
def test_in_anf(source):
    assert error(source) is None
    # 7.3: a term in ANF is a normal form (`Oymomo.anf_normal`).
    assert strategy.sstep(block_body(source)) is None


@pytest.mark.parametrize(
    ('source', 'message', 'part'),
    [
        # 5.6: normal, but not in ANF; the fix is a let.
        (
            "'add' {'i32', 'mul' {'i32', p.a, p.a}, p.b}",
            'An operand must be an atom: bind it with a let.',
            "'mul' {'i32', $0.a, $0.a}",
        ),
        (
            "let x = 'add' {'i32', 'mul' {'i32', p.a, p.a}, p.b} in x",
            'An operand must be an atom: bind it with a let.',
            "'mul' {'i32', $0.a, $0.a}",
        ),
        (
            "'add' {'i32', p.a, p.b}",
            'An opcode call at the end must be bound by a let and its variable returned.',
            "'add' {'i32', $0.a, $0.b}",
        ),
        (
            'm.f {a = m.g {}}',
            'An argument must be an atom: bind it with a let.',
            '$2.g {}',
        ),
        ('m.f p.a', 'An argument must be a struct of atoms.', '$0.a'),
        # A call is through a free path, never a let variable.
        ('p.k {}', 'A call must be through a free path, such as m.l or f.l.body.', '$0.k'),
        ("let x = 'load' {'ptr', m.fp} in x {}", 'A call must be through a free path, such as m.l or f.l.body.', '$0'),
        ('(m.f {}).x', 'A return must be an atom, and a jump a function call.', '($2.f {}).x'),
        ('{a = p, b = p}', 'A return must be an atom, and a jump a function call.', '{a = $0, b = $0}'),
        ('λx. x', 'A return must be an atom, and a jump a function call.', 'λx. $0'),
        # A branch's arms are returns or jumps; its condition is a path.
        (
            "{p.a, 'add' {'i32', p.a, p.b}} p.c",
            'A return must be an atom, and a jump a function call.',
            "'add' {'i32', $0.a, $0.b}",
        ),
        ('{p.a, p.b} (m.test {})', 'A branch condition must be a variable or a path.', '$2.test {}'),
        # A let binds an operation.
        (
            'let x = p.a in x',
            'A let must bind an opcode call or a function call; '
            'a projection is not a value, so E-Beta never substitutes it (4.3).',
            '$0.a',
        ),
        ('let x = {} in x', 'A let must bind an opcode call or a function call.', '{}'),
        # An opcode call that E-Opcode computes (not normal).
        (
            "let x = 'add' {'i8', [01], [02]} in x",
            'E-Opcode computes this opcode call.',
            "'add' {'i8', [01], [02]}",
        ),
    ],
)
def test_not_in_anf(source, message, part):
    assert error(source) == (message, part)


def test_anf_error_has_the_part_location():
    source = "λm. λf. λp. 'add' {'i32', 'mul' {'i32', p.a, p.a}, p.b}"
    term = reduction.resolve(parse(source)).body.body.body
    found = anf.anf_error(term, local=1)
    assert found.location.start == source.index("'mul'")


def test_a_term_on_its_own_has_no_let_variables():
    # With `local=0` every variable is free, so a call through it is a call.
    term = reduction.resolve(parse("λg. let x = 'add' {'i32', [01000000], g} in g {x}")).body
    assert anf.is_anf(term)
    # Under the let, `x` is a let variable; with `g` one too, `g {x}` is no call.
    assert anf.is_anf(term.function.body, local=1)
    assert not anf.is_anf(term.function.body, local=2)


@pytest.mark.parametrize(
    'source',
    [
        '{} p',
        '{a, b} (λx. x)',
        '{a, b} {c}',
        '[01] (λx. x)',
        '[01] [01]',
        '(λx. x).l',
        '[01].l',
        '{a = p}.b',
        # Inside a normal form: under a lambda, in a field, in an argument.
        'λx. {} x',
        '{a = [01] [02]}',
        'm.f ((λx. x).l)',
    ],
)
def test_stuck(source):
    term = block_body(source, free=('m', 'a', 'b', 'c'))
    assert strategy.sstep(term) is None
    assert reduction.stuck_part(term) is not None


@pytest.mark.parametrize(
    'source',
    [
        'p.a',
        '(λx. [01]) p.n',
        '{a, b} p.c',
        "'add' {'i32', p.a, [01000000]}",
        "'frobnicate' {[01]}",
        "'sdiv' {'i32', [07000000], [00000000]}",
        'm.f {x = λy. y}',
        'p (λx. x)',
        'λx. x.l',
    ],
)
def test_valid_normal_forms_are_not_stuck(source):
    term = block_body(source, free=('m', 'a', 'b', 'c'))
    assert strategy.sstep(term) is None
    assert reduction.stuck_part(term) is None


def test_stuck_part_is_the_outermost_first():
    term = block_body('{a = {} p, b = [01] [02]}', free=('m',))
    assert show(reduction.stuck_part(term)) == '{} $0'
