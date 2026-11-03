# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import meta, opcodes, reduction, terms
from oymo.oymomo.grammar import RESERVED, parse
from oymo.oymomo.printer import show


def place(node):
    """A node's place: its start and length in bytes."""
    return node.tag.start, node.tag.length


def resolved(source, free=()):
    """Resolves `source` with the names in `free` bound outside it, outermost first."""
    term = reduction.resolve(parse(''.join(f'λ{name}. ' for name in free) + source))
    for _ in free:
        term = term.body
    return term


def test_resolve():
    assert show(resolved('λx. λy. x')) == 'λx. λy. $1'
    assert show(resolved('λx. λy. y')) == 'λx. λy. $0'
    assert show(resolved('λx. λx. x')) == 'λx. λx. $0'


@pytest.mark.parametrize('word', sorted(RESERVED))
def test_resolve_quoted_keyword(word):
    assert show(resolved(f'λ"{word}". "{word}"')) == f'λ"{word}". $0'
    assert show(resolved(f'λx. "{word}" x', free=(f'"{word}"',))) == 'λx. $1 $0'


def test_resolve_keeps_opcodes():
    assert resolved("λx. 'add' {'i32', x, x}") == parse("λx. 'add' {'i32', $0, $0}")


def test_resolve_keeps_labels():
    assert show(resolved('λs. {a = s}.a')) == 'λs. {a = $0}.a'


def test_resolve_keeps_location():
    term = reduction.resolve(parse('λx. x'))
    assert term.body == terms.BruijnIndex(0)
    assert place(term.body) == (len('λx. '.encode()), 1)


def test_resolve_unknown_name():
    with pytest.raises(reduction.ReductionError) as info:
        reduction.resolve(parse('λx. y'))
    assert info.value.message == "Unknown name 'y'."
    assert place(info.value) == (len('λx. '.encode()), 1)


def test_shift():
    term = resolved('λx. a b x', free=('a', 'b'))
    assert show(term) == 'λx. $2 $1 $0'
    assert show(reduction.shift(term, 1)) == 'λx. $3 $2 $0'
    assert show(reduction.shift(term, 1, cutoff=1)) == 'λx. $3 $1 $0'


def test_substitute():
    term = resolved('λx. a b x', free=('a', 'b'))
    # Replaces b (index 0 from the root, $1 under x) with $5, shifted under x to $6.
    assert show(reduction.substitute(term, 0, terms.BruijnIndex(5))) == 'λx. $2 $6 $0'
    assert show(reduction.substitute(term, 1, terms.BruijnIndex(5))) == 'λx. $6 $1 $0'


def test_beta_avoids_capture():
    # (λx. λy. x) y gives λy'. y, where y is the free y, not the inner binder.
    apply = resolved('(λx. λy. x) y', free=('y',))
    assert show(reduction.beta(apply.function, apply.argument)) == 'λy. $1'


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('(λx. x) y', 'y'),
        # E-Beta substitutes a value: a variable, a lambda, a byte array, a struct of values.
        ('(λx. {x, x}) (λy. y)', '{λy. y, λy. y}'),
        ('(λx. {x, x}) [01]', '{[01], [01]}'),
        ('(λx. {x, x}) {a = y, b = {[01]}}', '{{a = y, b = {[01]}}, {a = y, b = {[01]}}}'),
        ('{a = e}.a', 'e'),
        ('if [01] then a else b', 'a'),
        ('if [00] then a else b', 'b'),
        # Any nonzero index is true: past the last field is the last field.
        ('if [02] then a else b', 'a'),
        # The empty byte array is 0.
        ("if '' then a else b", 'b'),
        ('{e, a = b}.a', 'b'),
        # A tagged struct is a struct: β builds one as any other.
        ("(λe. {'array', [03000000], e}) 'i8'", "{'array', [03000000], 'i8'}"),
        # A fixed point is a value: E-Beta copies it.
        ('(λx. {x, x}) (fix (λs. s))', '{fix (λs. s), fix (λs. s)}'),
        # E-FixProj and E-FixApp: the fixed point unfolds once where it is used.
        ('(fix (λs. {a = e, b = s})).b', '{a = e, b = fix (λs. {a = e, b = s})}.b'),
        ('(fix (λs. λn. s n)) e', '(λn. fix (λs. λn. s n) n) e'),
        ('(fix (λs. λn. s n)) ((λy. y) e)', '(λn. fix (λs. λn. s n) n) ((λy. y) e)'),
    ],
)
def test_reduce_one_step(source, expected):
    free = ('a', 'b', 'e', 'g', 'y', 'z')
    assert show(reduction.reduce(resolved(source, free))) == show(resolved(expected, free))


@pytest.mark.parametrize(
    'source',
    [
        'λx. x',
        '{a = e}',
        '[01]',
        'e',
        "'add' {'i32', e, e}",
        'p.n',
        'if e then a else b',
        '{a = e}.b',
        '{q = {a = e}}.q.a',
        '((λx. x) (λy. y)) e',
        'if ((λx. x) [01]) then a else b',
        'λx. (λy. y) x',
        '{e}.a',
        # E-Beta is call-by-value: the argument must be a value. A projection is not one.
        '(λx. x) ((λy. y) z)',
        '(λx. y) ((λw. w w) (λw. w w))',
        '(λx. {x, x}) p.n',
        "(λx. {x, x}) ('add' {'i32', e, e})",
        '(λx. x) {a = (λy. y) z}',
        '(λx. x) {a = {b = p.n}}',
        # E-Opcode needs data operands: never a variable, a lambda or a projection.
        "'add' {'i32', {[01]}, [02]}",
        "'icmp' {'eq', 'i8', λx. x, [01]}",
        "'icmp' {'eq', 'i8', p.n, [01]}",
        "'icmp' {'lt', 'i8', [01], [01]}",
        "'icmp' {'i8', [01], [01]}",
        # An opcode folds only where it can evaluate its fields: an integer form, and
        # operands of its size, three fields.
        "'add' {'i32', [01], [02000000]}",
        "'and' {'i1', [02], [01]}",
        "'add' {'i32', e, [02000000]}",
        "'add' {g, [01000000], [02000000]}",
        "'add' {'ptr', [01], [00]}",
        "'zext' {'i32', [01000000], 'i8'}",
        "'add' {'i32', [01000000], [02000000], [00]}",
        "'add' {'i32', [01000000]}",
        "'add' [01000000]",
        # `reduce` is root-only: a field must already be a literal.
        "'add' {'i32', (λx. x) [01000000], [02000000]}",
        # No fold where LLVM has no defined result.
        "'sdiv' {'i32', [07000000], [00000000]}",
        "'udiv' {'i8', [07], [00]}",
        "'srem' {'i16', [0700], [0000]}",
        "'urem' {'i64', [0700000000000000], [0000000000000000]}",
        "'sdiv' {'i8', [80], [ff]}",
        "'srem' {'i8', [80], [ff]}",
        "'shl' {'i8', [01], [08]}",
        "'lshr' {'i32', [01000000], [20000000]}",
        "'ashr' {'i16', [0100], [ffff]}",
        # A conversion's operand has the source's size.
        "'zext' {'i8', [ff00], 'i32'}",
        # Memory opcodes are impure: reduction never folds them.
        "'alloca' {'i32'}",
        "'getelementptr' {'i8', e, [01000000]}",
        "'store' {'i32', [2a000000], e}",
        "'load' {'i32', e}",
        # Unknown opcode names never fold.
        "'add_i32' {[01000000], [02000000]}",
        # A fixed point on its own never steps at the root; nor one of a non-lambda.
        'fix (λs. s)',
        '(fix e).a',
        '(fix ((λs. s) (λs. s))).a',
    ],
)
def test_reduce_returns_the_term_itself(source):
    term = resolved(source, ('a', 'b', 'e', 'g', 'p', 'y', 'z'))
    assert reduction.reduce(term) is term


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # E-Opcode gives a bare byte array.
        ("'add' {'i32', [01000000], [02000000]}", '[03000000]'),
        # Arithmetic wraps.
        ("'add' {'i8', [ff], [01]}", '[00]'),
        ("'sub' {'i8', [00], [01]}", '[ff]'),
        # Fields are positional: labels are ignored, so this is still 0 - 1.
        ("'sub' {form = 'i8', subtrahend = [00], minuend = [01]}", '[ff]'),
        ("'sub' {'i16', [0500], [0300]}", '[0200]'),
        ("'mul' {'i16', [0001], [0001]}", '[0000]'),
        ("'mul' {'i64', [0300000000000000], [0500000000000000]}", '[0f00000000000000]'),
        # Logic, including on i1.
        ("'and' {'i1', [01], [01]}", '[01]'),
        ("'or' {'i1', [00], [01]}", '[01]'),
        ("'xor' {'i1', [01], [01]}", '[00]'),
        ("'and' {'i8', [0f], [3c]}", '[0c]'),
        ("'or' {'i32', [01000000], [00000080]}", '[01000080]'),
        ("'xor' {'i16', [ffff], [0ff0]}", '[f00f]'),
        # Division rounds toward zero; a remainder has the dividend's sign.
        ("'sdiv' {'i8', [f9], [02]}", '[fd]'),
        ("'srem' {'i8', [f9], [02]}", '[ff]'),
        ("'udiv' {'i8', [f9], [02]}", '[7c]'),
        ("'urem' {'i32', [07000000], [03000000]}", '[01000000]'),
        ("'udiv' {'i8', [80], [ff]}", '[00]'),
        # Shifts by less than the width.
        ("'shl' {'i8', [81], [01]}", '[02]'),
        ("'lshr' {'i16', [0080], [0f00]}", '[0100]'),
        ("'ashr' {'i16', [0080], [0f00]}", '[ffff]'),
        # Comparisons give an i1.
        ("'icmp' {'eq', 'i8', [07], [07]}", '[01]'),
        ("'icmp' {'ne', 'i32', [07000000], [07000000]}", '[00]'),
        ("'icmp' {'slt', 'i8', [ff], [00]}", '[01]'),
        ("'icmp' {'ult', 'i8', [ff], [00]}", '[00]'),
        # Operands may be any data, labels ignored.
        ("'add' {form = 'i8', a = [01], b = [02]}", '[03]'),
        # Conversions change the width.
        ("'zext' {'i8', [ff], 'i32'}", '[ff000000]'),
        ("'sext' {'i8', [ff], 'i32'}", '[ffffffff]'),
        ("'sext' {'i1', [01], 'i16'}", '[ffff]'),
        ("'trunc' {'i32', [78563412], 'i8'}", '[78]'),
        ("'trunc' {'i16', [0300], 'i1'}", '[01]'),
    ],
)
def test_reduce_folds_an_opcode(source, expected):
    assert reduction.reduce(resolved(source)) == resolved(expected)


def test_if_parses_to_a_struct_apply():
    assert parse('if c then t else e') == parse('{e, t} c')


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('{e, t} c', ('c', 't', 'e')),
        ('if c then t else e', ('c', 't', 'e')),
        ('{x = e, t} c', None),
        ('{e, t, d} c', None),
        ('{e, t}', None),
    ],
)
def test_branch(source, expected):
    found = reduction.branch(parse(source))
    assert (None if found is None else tuple(v.name for v in found)) == expected


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ("{a = '23'} [00]", "'23'"),
        ("{a = '23', b = '45'} [01]", "'45'"),
        # Unlabeled fields.
        ("{'1', '2'} [01]", "'2'"),
        ("{'1', b = '2'} [00]", "'1'"),
        # Any spelling of the same number is the same index; '' is 0.
        ("{a = '23', b = '45'} [0100]", "'45'"),
        ("{a = '23'} [0000]", "'23'"),
        ("{a = '23', b = '45'} ''", "'23'"),
        # An index past the last field selects the last field (E-Default).
        ("{a = '23'} [01]", "'23'"),
        ("{a = '23'} [0001]", "'23'"),
        ("{'1', '2', '3'} [07]", "'3'"),
        ("{x = '1', y = '2'} [05]", "'2'"),
        # So `if` takes any nonzero index as true.
        ("{'else', 'then'} [02]", "'then'"),
    ],
)
def test_reduce_struct_apply(source, expected):
    assert reduction.reduce(resolved(source)) == resolved(expected)


@pytest.mark.parametrize(
    'source',
    [
        # No last field to fall back to.
        '{} [00]',
        '{} [07]',
        "{a = '23'} i",
        "{a = '23'} ((λx. x) [00])",
    ],
)
def test_reduce_struct_apply_stuck(source):
    term = resolved(source, ('i',))
    assert reduction.reduce(term) is term


@pytest.mark.parametrize(
    ('source', 'expected'),
    [('[01]', 1), ('[0001]', 256), ("''", 0), ('i', None)],
)
def test_index_value(source, expected):
    assert reduction.index_value(resolved(source, ('i',))) == expected


@pytest.mark.parametrize(
    ('source', 'value', 'data'),
    [
        ('x', True, False),
        ('λy. (λz. z) y', True, False),
        ('[01]', True, True),
        ("''", True, True),
        ('{}', True, True),
        ("{a = [01], b = {'i32'}}", True, True),
        ('{a = x, b = λy. y}', True, False),
        # A projection is never a value, nor a struct holding one.
        ('x.l', False, False),
        ('{a = x.l}', False, False),
        ('{l = [01]}.l', False, False),
        ('(λy. y) x', False, False),
        ("'add' {'i32', [01000000], [02000000]}", False, False),
        ('{a = [01], b = (λy. y) x}', False, False),
        # A fixed point of a lambda is a value, never data.
        ('fix (λs. s)', True, False),
        ('{fix (λs. s)}', True, False),
        ('fix x', False, False),
    ],
)
def test_is_value_and_is_data(source, value, data):
    term = resolved(source, ('x',))
    assert reduction.is_value(term) is value
    assert reduction.is_data(term) is data


@pytest.mark.parametrize(
    ('source', 'stuck'),
    [
        ('fix [01]', 'fix [01]'),
        ('{a = fix {}}', 'fix {}'),
        ('fix (λs. s)', None),
        ('fix x', None),
    ],
)
def test_stuck_fix(source, stuck):
    # `fix b` and `fix {…}` never become a fixed point of a lambda.
    found = reduction.stuck_part(resolved(source, ('x',)))
    assert (None if found is None else show(found)) == stuck


# The tag of a step's result: keep, copy, new, drop. Every node is checked by identity.


def test_e_beta_copies_share_the_argument_tag_and_the_body_keeps_its_own():
    argument = parse('[07]')
    term = resolved('(λx. {x, x}) a', free=('a',))
    term = terms.Apply(term.function, argument, tag=meta.Tag(meta.File.of('a.alcor', 'alcor', b'abc'), 1, 1))
    body = term.function.body
    result = reduction.reduce(term)
    assert isinstance(result, terms.Struct)
    assert result.tag is body.tag
    assert [f.tag for f in result.fields] == [f.tag for f in body.fields]
    assert all(f.value.tag is argument.tag for f in result.fields)
    assert all(f.value is argument for f in result.fields)


def test_e_beta_shifted_copies_keep_the_argument_tag():
    # (λx. λz. x) y: the copy of y is shifted under λz, a new term with y's tag.
    term = resolved('(λx. λz. x) y', free=('y',))
    result = reduction.reduce(term)
    assert isinstance(result, terms.Lambda)
    assert result.body == terms.BruijnIndex(1)
    assert result.body.tag is term.argument.tag
    assert result.tag is term.function.body.tag


def test_e_opcode_result_takes_the_redex_tag():
    term = resolved("'add' {'i8', [01], [02]}")
    result = reduction.reduce(term)
    assert result == terms.ByteArray(b'\x03')
    assert result.tag is term.tag


def test_e_proj_keeps_the_field_value_and_its_tag():
    term = resolved('{a = [01], b = [02]}.b')
    field = term.struct.fields[1]
    result = reduction.reduce(term)
    assert result is field.value
    assert result.tag is not term.tag


def test_e_index_keeps_the_selected_field_value():
    term = resolved('{[01], [02]} [01]')
    assert reduction.reduce(term) is term.function.fields[1].value


def test_e_fix_proj_keeps_the_projection_and_copies_share_the_fixed_point_tag():
    term = resolved('(fix (λf. {a = f})).a')
    fixed = term.struct
    result = reduction.reduce(term)
    assert isinstance(result, terms.Project)
    assert result.tag is term.tag
    unfolded = result.struct
    assert isinstance(unfolded, terms.Struct)
    assert unfolded.tag is fixed.body.body.tag
    assert unfolded.fields[0].tag is fixed.body.body.fields[0].tag
    assert unfolded.fields[0].value is fixed


# E-Opcode on opcode operands: a byte array, a struct of operands, or a closed lambda or
# fixed point of a lambda in normal form.


@pytest.fixture
def whole_operand_opcode(monkeypatch):
    """A test opcode `'wrap' A` that reads its whole operand: `{A, A}`."""

    def apply(operand):
        return terms.Struct([terms.Field('', operand), terms.Field('', operand)])

    opcode = opcodes.Opcode('wrap', lambda _fields: None, lambda _fields: None, apply=apply)
    monkeypatch.setitem(opcodes.OPCODES, 'wrap', opcode)
    return opcode


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ("'wrap' [01]", '{[01], [01]}'),
        ("'wrap' {a = [01]}", '{{a = [01]}, {a = [01]}}'),
        ("'wrap' (λx. x)", '{λx. $0, λx. $0}'),
        ("'wrap' (fix (λf. λx. f x))", '{fix (λf. λx. $1 $0), fix (λf. λx. $1 $0)}'),
    ],
)
def test_opcode_reads_its_whole_operand(whole_operand_opcode, source, expected):
    del whole_operand_opcode
    assert show(reduction.reduce(resolved(source))) == expected


@pytest.mark.parametrize(
    'source',
    [
        # A lambda that is not normal yet is not an operand yet.
        "'wrap' (λx. (λy. y) x)",
        # An open lambda never is.
        "'wrap' (λx. p)",
        # A call still to run is not a value: an opcode never gets it.
        "'wrap' {'load' {'i32', [00]}}",
        # Nor a projection or an application.
        "'wrap' (p.a)",
    ],
)
def test_opcode_waits_for_an_operand(whole_operand_opcode, source):
    del whole_operand_opcode
    term = resolved(source, free=('p',))
    assert reduction.reduce(term) is term


def test_opcode_result_takes_the_redex_tag_unless_it_has_one(whole_operand_opcode):
    del whole_operand_opcode
    term = resolved("'wrap' [01]")
    term.tag = meta.Tag(start=3, length=4)
    result = reduction.reduce(term)
    assert result.tag is term.tag
    assert result.fields[0].value is term.argument


def test_opcode_gives_a_closed_term(monkeypatch):
    monkeypatch.setitem(
        opcodes.OPCODES,
        'open',
        opcodes.Opcode('open', lambda _f: None, lambda _f: None, apply=lambda _a: terms.BruijnIndex(0)),
    )
    with pytest.raises(TypeError, match='not closed'):
        reduction.reduce(resolved("'open' [01]"))


@pytest.mark.parametrize(
    ('source', 'operand'),
    [
        ('[01]', True),
        ('{[01], a = {}}', True),
        ('λx. x', True),
        ('fix (λf. f)', True),
        ('λx. (λy. y) x', False),
        ('λx. p', False),
        ("{'load' {'i32', [00]}}", False),
        ("'add' {'i32', [01000000], [01000000]}", False),
        ('p', False),
    ],
)
def test_is_operand(source, operand):
    assert reduction.is_operand(resolved(source, free=('p',))) is operand


@pytest.mark.parametrize(
    ('source', 'normal'),
    [
        ('λx. x', True),
        ('λx. (λy. y) x', False),
        ("λx. 'add' {'i32', [01000000], [01000000]}", False),
        ("λx. 'add' {'i32', x, [01000000]}", True),
        ("'load' {'i32', [00]}", True),
    ],
)
def test_is_normal(source, normal):
    assert reduction.is_normal(resolved(source)) is normal
