# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""ANF and stuck normal forms."""

import pytest

from oymo.core import spans
from oymo.oymomo import anf, reduction, strategy
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show


def block_body(source, free=('m', 'f')):
    """`source` as a block's body: under `λp`, with `m` (the module) and `f` (a region) free."""
    term = reduction.resolve(parse(''.join(f'λ{name}. ' for name in free) + f'λp. {source}'))
    for _ in free:
        term = term.body
    return term.body


def error(source):
    found = anf.anf_error(block_body(source))
    return None if found is None else (found.message, show(found.term))


TAIL_CALL = 'A call that ends a function is bound and returned: let y = m.f {…} in y.'


@pytest.mark.parametrize(
    'source',
    [
        # Returns: a path, data.
        'p.a',
        'm.answer',
        '[2a000000]',
        "''",
        '{[01], {[02]}}',
        # Jumps: a path applied to operands, one by one.
        'f.loop p.a [00]',
        'f.done',
        'f.next {[01], [02]}',
        # Lets of opcode calls and calls.
        "let x = 'add' {'i32', p.a, [01000000]} in x",
        "let x = 'add' {'i32', p.a, p.b} in let y = 'mul' {'i32', x, x} in f.print y",
        "let u = 'store' {'i32', [05000000], m.counter} in let x = 'load' {'i32', m.counter} in x",
        'let x = m.f {a = p.a, b = {[01]}} in f.next x',
        "let s = 'insertvalue' {{'i8', 'i32'}, {[00], [00000000]}, p.a, [01]} in s",
        # An opcode E-Opcode does not compute: undefined behavior, an unknown opcode.
        "let x = 'sdiv' {'i32', [07000000], [00000000]} in x",
        "let x = 'frobnicate' {[01]} in x",
        # Branches: arms that jump, on a path.
        "let z = 'icmp' {'eq', 'i32', p.b, [00000000]} in {f.step p.a p.b, f.done p.a} z",
        '{f.a, f.b, f.c} p.tag',
        # Regions: field 0 an expression, the others blocks.
        'm [] (λq. {q.x, x = p.a})',
        'm [] (λq. {if p.c then q.x [01] else f.y, x = λa. λb. a, y = m [] (λs. {s.z, z = [00]})})',
        'm [] (λq. {l = let x = m.g {} in q.l})',
    ],
)
def test_in_anf(source):
    assert error(source) is None
    # A term in ANF is a normal form (`Oymomo.anf_normal`).
    assert strategy.sstep(block_body(source)) is None


@pytest.mark.parametrize(
    ('source', 'message', 'part'),
    [
        # Normal, but not in ANF; the fix is a let.
        (
            "'add' {'i32', 'mul' {'i32', p.a, p.a}, p.b}",
            'An operand must be a path or data: bind it with a let.',
            "'mul' {'i32', $0.a, $0.a}",
        ),
        (
            "let x = 'add' {'i32', 'mul' {'i32', p.a, p.a}, p.b} in x",
            'An operand must be a path or data: bind it with a let.',
            "'mul' {'i32', $0.a, $0.a}",
        ),
        (
            "'add' {'i32', p.a, p.b}",
            'An opcode call at the end must be bound by a let and its variable returned.',
            "'add' {'i32', $0.a, $0.b}",
        ),
        (
            'let x = m.f {a = m.g {}} in x',
            'An argument must be a path or data: bind it with a let.',
            '$2.g {}',
        ),
        ('let x = m.f p.a in x', 'An instruction applies its operator to a struct of operands.', '$0.a'),
        # A struct operand is data.
        (
            "let x = 'add' {'i32', {p.a}, p.b} in x",
            "An operand must be a path or data; a struct value is built with 'insertvalue'.",
            '{$0.a}',
        ),
        (
            'f.next p.a {p.a}',
            "An operand of a jump must be a path or data; a struct value is built with 'insertvalue'.",
            '{$0.a}',
        ),
        # A call at the end is bound and returned.
        ('m.f {a = p.a}', TAIL_CALL, '$2.f {a = $0.a}'),
        ('(m.f {}).x', 'A return must be a path or data: bind it with a let.', '($2.f {}).x'),
        ('λx. x', 'A return must be a path or data: bind it with a let.', 'λx. $0'),
        # A branch's arms only jump; its condition is a path.
        (
            "{f.a, 'add' {'i32', p.a, p.b}} p.c",
            'An arm of a branch only jumps: r.l Q₁ ⋯ Qₙ.',
            "'add' {'i32', $0.a, $0.b}",
        ),
        ('{f.a, f.b} (m.test {})', 'A branch condition must be a path.', '$2.test {}'),
        # A let binds an instruction.
        (
            'let x = p.a in x',
            'A let must bind an opcode call or a function call; '
            'a projection is not a value, so E-Beta never substitutes it.',
            '$0.a',
        ),
        ('let x = {} in x', 'A let must bind an instruction: an opcode call or a function call.', '{}'),
        # An opcode call that E-Opcode computes (not normal).
        (
            "let x = 'add' {'i8', [01], [02]} in x",
            'E-Opcode computes this opcode call.',
            "'add' {'i8', [01], [02]}",
        ),
        # Regions.
        ('m [] (λq. {λy. y})', 'Field 0 of a region is an expression, never a λ.', 'λy. $0'),
        ('m [] (λq. {})', 'A region holds a struct of blocks, at least one.', '{}'),
        ('m [] (λq. q)', 'A region holds a struct of blocks, at least one.', '$0'),
        (
            'm [] (λq. {q.x, x = λa. let y = a.l in y})',
            'A let must bind an opcode call or a function call; '
            'a projection is not a value, so E-Beta never substitutes it.',
            '$0.l',
        ),
    ],
)
def test_not_in_anf(source, message, part):
    assert error(source) == (message, part)


def test_anf_error_has_the_part_location():
    source = "λm. λp. 'add' {'i32', 'mul' {'i32', p.a, p.a}, p.b}"
    term = reduction.resolve(parse(source)).body.body
    found = anf.anf_error(term)
    assert spans.start(found.span) == source.index("'mul'")


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
