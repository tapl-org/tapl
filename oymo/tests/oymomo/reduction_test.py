# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import opcodes, reduction, terms
from oymo.oymomo.grammar import RESERVED, parse
from oymo.oymomo.printer import show


def resolved(source, free=()):
    """Resolves `source` with the names in `free` bound outside it, outermost first."""
    term = reduction.resolve(parse(' -> '.join([*free, source])))
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


def test_resolve_keeps_builtins():
    assert resolved("x -> 'add' {'i32', x, x}") == parse("x -> 'add' {'i32', $0, $0}")
    # `prim` is no longer a binder of the program, so it is a plain name.
    assert show(resolved('prim -> prim')) == 'prim → $0'


def test_resolve_keeps_labels():
    assert show(resolved('s -> {a = s}.a')) == 's → {a = $0}.a'


def test_resolve_inside_function_form():
    assert show(resolved('a -> b -> x~(a => b) -> x')) == 'a → b → x~$1 ⇒ $0 → $0'


def test_resolve_keeps_location():
    term = reduction.resolve(parse('x -> x'))
    assert term.body == terms.BruijnIndex(0)
    assert term.body.location == terms.Location(5, 6)


def test_resolve_unknown_name():
    with pytest.raises(reduction.ReductionError) as info:
        reduction.resolve(parse('x -> y'))
    assert info.value.message == "Unknown name 'y'."
    assert info.value.location == terms.Location(5, 6)


def test_resolve_forms_in_the_outer_scope():
    # A param's form can't see the param itself; it sees the binders around the lambda.
    assert show(resolved('x~(a) -> x~(x) -> x', free=('a',))) == 'x~$0 → x~$0 → $0'
    assert show(resolved('[00]~{f = (a)} => (a)', free=('a',))) == '[00]~{f = $0} ⇒ $0'
    with pytest.raises(reduction.ReductionError, match="Unknown name 'x'"):
        reduction.resolve(parse('x~(x) -> x'))


def test_shift_and_substitute_reach_forms():
    term = resolved('x~(a) -> [00]~(x)', free=('a',))
    assert show(term) == 'x~$0 → [00]~$0'
    assert show(reduction.shift(term, 1)) == 'x~$1 → [00]~$0'
    assert show(reduction.substitute(term, 0, terms.BruijnIndex(5))) == 'x~$5 → [00]~$0'


def test_shift():
    term = resolved('x -> a b x', free=('a', 'b'))
    assert show(term) == 'x → $2 $1 $0'
    assert show(reduction.shift(term, 1)) == 'x → $3 $2 $0'
    assert show(reduction.shift(term, 1, cutoff=1)) == 'x → $3 $1 $0'


def test_substitute():
    term = resolved('x -> a b x', free=('a', 'b'))
    # Replaces b (index 0 from the root, $1 under x) with $5, shifted under x to $6.
    assert show(reduction.substitute(term, 0, terms.BruijnIndex(5))) == 'x → $2 $6 $0'
    assert show(reduction.substitute(term, 1, terms.BruijnIndex(5))) == 'x → $6 $1 $0'


def test_beta_avoids_capture():
    # (x -> y -> x) y gives y' -> y, where y is the free y, not the inner binder.
    apply = resolved('(x -> y -> x) y', free=('y',))
    assert show(reduction.beta(apply.function, apply.argument)) == 'y → $1'


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # The lambda's form goes with the argument.
        ("(x~'i8' -> x) [01]", "[01]~'i8'"),
        # The lambda's form replaces the argument's own form.
        ("(x~'i8' -> x) [01]~'i16'", "[01]~'i8'"),
        # Only the outer form is replaced: a form inside the term or the form stays.
        ("(x~'i8'->x) ([01]~'i16')~'i32'", "([01]~'i16')~'i8'"),
        ("(x~'i8'->x) [01]~('i16'~'i32')", "[01]~'i8'"),
        ('(x~t -> f x) y', 'f (y~t)'),
        # No form on the lambda: the argument goes in as it is, with its own form if any.
        ('(x -> x) [01]', '[01]'),
        ("(x -> x) [01]~'i16'", "[01]~'i16'"),
        ("let x~'i1' = [01] in x", "[01]~'i1'"),
    ],
)
def test_beta_propagates_form(source, expected):
    free = ('f', 't', 'y')
    apply = resolved(source, free)
    assert reduction.beta(apply.function, apply.argument) == resolved(expected, free)


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('(x -> x) y', 'y'),
        ('$fix (s -> g)', '(s -> g) ($fix (s -> g))'),
        ('{a = e}.a', 'e'),
        ('if [01] then a else b', 'a'),
        ('if [00] then a else b', 'b'),
        # Any nonzero index is true: past the last field is the last field.
        ('if [02] then a else b', 'a'),
        ('(x -> x) ((y -> y) z)', '(y -> y) z'),
        ('(x -> y) ((w -> w w) (w -> w w))', 'y'),
        ('{a = e, a = b}.a', 'e'),
        ('{e, a = b}.a', 'b'),
        # Through a form, the field's form goes with the value and replaces its own.
        ("({a = e, b = y}~{a = 'f', b = 'g'}).a", "e~'f'"),
        ("({a = e~'g'}~{a = 'f'}).a", "e~'f'"),
    ],
)
def test_reduce_one_step(source, expected):
    free = ('a', 'b', 'e', 'g', 'y', 'z')
    assert show(reduction.reduce(resolved(source, free))) == show(resolved(expected, free))


@pytest.mark.parametrize(
    'source',
    [
        'x -> x',
        '{a = e}',
        '[01]',
        'e',
        "'add' {'i32', e, e}",
        'args.n',
        'if e then a else b',
        '{a = e}.b',
        '{p = {a = e}}.p.a',
        '((x -> x) (y -> y)) e',
        '$fix g a',
        '$fix',
        # `$fix` fires only on a lambda, and `reduce` doesn't reduce its argument to one.
        '$fix g',
        '$fix ((x -> x) (s -> s))',
        '$nope g',
        # `reduce` is root-only: the argument must already be a struct literal.
        '$struct_to_fields e',
        '$struct_to_fields {p = {a = e}}.p',
        "$struct_to_fields {a = e}~'f'",
        '$fields_to_struct e',
        "$fields_to_struct {more = [01], label = 'a', value = e, rest = (y -> y) {more = [00]}}",
        # Malformed lists: no `more`, `more` not [00] or [01], a label that isn't UTF-8,
        # a missing `rest`, a node under a form.
        "$fields_to_struct {label = 'a'}",
        '$fields_to_struct {more = [02]}',
        '$fields_to_struct {more = [01], label = [ff], value = e, rest = {more = [00]}}',
        "$fields_to_struct {more = [01], label = 'a', value = e}",
        "$fields_to_struct {more = [01], label = 'a', value = e, rest = {more = [00]}~'f'}",
        "$fields_to_struct {more = [00]}~'f'",
        'if ((x -> x) [01]) then a else b',
        'x -> (y -> y) x',
        '{e}.a',
        # Through a form: it must be a struct literal with the label, too.
        "({a = e}~{b = 'f'}).a",
        "({a = e}~'f').a",
        '({a = e}~g).a',
        # An opcode folds only where it can evaluate its fields: an integer form, and
        # operands of its size (bare or formed; a written form is not compared), three fields.
        "'add' {'i32', [01]~'i32', [02000000]~'i32'}",
        "'add' {'i32', [01], [02000000]}",
        "'and' {'i1', [02], [01]}",
        "'add' {'i32', e, [02000000]}",
        "'add' {g, [01000000], [02000000]}",
        "'add' {'ptr', [01], [00]}",
        "'zext' {'i32', [01000000], 'i8'}",
        "'add' {'i32'~'f', [01000000], [02000000]}",
        "'add' {'i32', [01000000], [02000000], [00]}",
        "'add' {'i32', [01000000]}",
        "'add' [01000000]",
        # `reduce` is root-only: a field must already be a literal.
        "'add' {'i32', (x -> x) [01000000], [02000000]}",
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
        # A conversion's operand has the source's size and form.
        "'zext' {'i8', [ff000000]~'i32', 'i32'}",
        "'zext' {'i8', [ff00], 'i32'}",
    ],
)
def test_reduce_returns_the_term_itself(source):
    term = resolved(source, ('a', 'b', 'e', 'g', 'args'))
    assert reduction.reduce(term) is term


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ("'add' {'i32', [01000000]~'i32', [02000000]~'i32'}", "[03000000]~'i32'"),
        # A bare literal folds: the signature says how to read it.
        ("'add' {'i32', [01000000], [02000000]}", "[03000000]~'i32'"),
        ("'add' {'i32', [01000000], [02000000]~'i32'}", "[03000000]~'i32'"),
        # Arithmetic wraps.
        ("'add' {'i8', [ff], [01]}", "[00]~'i8'"),
        ("'sub' {'i8', [00], [01]}", "[ff]~'i8'"),
        # Fields are positional: labels are ignored, so this is still 0 - 1.
        ("'sub' {form = 'i8', subtrahend = [00], minuend = [01]}", "[ff]~'i8'"),
        ("'sub' {'i16', [0500], [0300]}", "[0200]~'i16'"),
        ("'mul' {'i16', [0001], [0001]}", "[0000]~'i16'"),
        ("'mul' {'i64', [0300000000000000], [0500000000000000]}", "[0f00000000000000]~'i64'"),
        # Logic, including on i1.
        ("'and' {'i1', [01], [01]}", "[01]~'i1'"),
        ("'or' {'i1', [00], [01]}", "[01]~'i1'"),
        ("'xor' {'i1', [01], [01]}", "[00]~'i1'"),
        ("'and' {'i8', [0f], [3c]}", "[0c]~'i8'"),
        ("'or' {'i32', [01000000], [00000080]}", "[01000080]~'i32'"),
        ("'xor' {'i16', [ffff], [0ff0]}", "[f00f]~'i16'"),
        # Division rounds toward zero; a remainder has the dividend's sign.
        ("'sdiv' {'i8', [f9], [02]}", "[fd]~'i8'"),
        ("'srem' {'i8', [f9], [02]}", "[ff]~'i8'"),
        ("'udiv' {'i8', [f9], [02]}", "[7c]~'i8'"),
        ("'urem' {'i32', [07000000], [03000000]}", "[01000000]~'i32'"),
        ("'udiv' {'i8', [80], [ff]}", "[00]~'i8'"),
        # Shifts by less than the width.
        ("'shl' {'i8', [81], [01]}", "[02]~'i8'"),
        ("'lshr' {'i16', [0080], [0f00]}", "[0100]~'i16'"),
        ("'ashr' {'i16', [0080], [0f00]}", "[ffff]~'i16'"),
        # Comparisons give an i1.
        ("'icmp_eq' {'i8', [07]~'i8', [07]~'i8'}", "[01]~'i1'"),
        ("'icmp_ne' {'i32', [07000000], [07000000]}", "[00]~'i1'"),
        ("'icmp_slt' {'i8', [ff], [00]}", "[01]~'i1'"),
        ("'icmp_ult' {'i8', [ff], [00]}", "[00]~'i1'"),
        # Conversions change the width.
        ("'zext' {'i8', [ff]~'i8', 'i32'}", "[ff000000]~'i32'"),
        ("'sext' {'i8', [ff], 'i32'}", "[ffffffff]~'i32'"),
        ("'sext' {'i1', [01], 'i16'}", "[ffff]~'i16'"),
        ("'trunc' {'i32', [78563412], 'i8'}", "[78]~'i8'"),
        ("'trunc' {'i16', [0300], 'i1'}", "[01]~'i1'"),
    ],
)
def test_reduce_folds_an_opcode(source, expected):
    assert reduction.reduce(resolved(source)) == resolved(expected)


def test_shift_and_substitute_reach_formed():
    term = terms.Formed(terms.BruijnIndex(0), terms.BruijnIndex(1))
    assert reduction.shift(term, 1) == terms.Formed(terms.BruijnIndex(1), terms.BruijnIndex(2))
    assert reduction.substitute(term, 1, terms.BruijnIndex(5)) == terms.Formed(
        terms.BruijnIndex(0), terms.BruijnIndex(5)
    )


def test_resolve_reaches_formed():
    term = reduction.resolve(
        terms.Lambda(
            'x', terms.Empty, terms.Lambda('y', terms.Empty, terms.Formed(terms.Variable('y'), terms.Variable('x')))
        )
    )
    assert show(term) == 'x → y → $0~$1'


@pytest.mark.parametrize(('value', 'expected'), [(b'\x01', 'a'), (b'\x00', 'b'), (b'\x01\x00', 'a')])
def test_reduce_if_sees_through_a_form(value, expected):
    # `if c then a else b` is `{b, a} c`, so the condition is read as an index: any length.
    a, b = terms.BruijnIndex(1), terms.BruijnIndex(0)
    condition = terms.Formed(terms.ByteArray(value), terms.ByteArray(b'i1'))
    branch = terms.Apply(terms.Struct([terms.Field('', b), terms.Field('', a)]), condition)
    assert reduction.reduce(branch) == {'a': a, 'b': b}[expected]


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
        # Duplicate labels: every field is reachable by index.
        ("{a = '1', a = '2'} [01]", "'2'"),
        # Any spelling of the same number is the same index.
        ("{a = '23', b = '45'} [0100]", "'45'"),
        ("{a = '23'} [0000]", "'23'"),
        # A form on the index is ignored.
        ("{a = '23'} ([00]~'i8')", "'23'"),
        # An index past the last field selects the last field.
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
        "{a = '23'} ''",
        # No last field to fall back to.
        '{} [00]',
        '{} [07]',
        "{a = '23'} i",
        "{a = '23'} ((x -> x) [00])",
    ],
)
def test_reduce_struct_apply_stuck(source):
    term = resolved(source, ('i',))
    assert reduction.reduce(term) is term


@pytest.mark.parametrize(
    ('source', 'expected'),
    [('[01]', 1), ('[0001]', 256), ("''", None), ('i', None), ("[02]~'i8'", 2)],
)
def test_index_value(source, expected):
    assert reduction.index_value(resolved(source, ('i',))) == expected


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('$struct_to_fields {}', '{more = [00]}'),
        (
            '$struct_to_fields {a = \'1\', "λ" = x}',
            "{more = [01], label = 'a', value = '1', rest = {more = [01], label = [cebb], value = x, rest = {more = [00]}}}",
        ),
        # An unlabeled field has the label ''. A value stays unreduced.
        ('$struct_to_fields {(y -> y) x}', "{more = [01], label = '', value = (y -> y) x, rest = {more = [00]}}"),
        # Duplicate labels are kept, in order.
        (
            "$struct_to_fields {a = x, a = '2'}",
            "{more = [01], label = 'a', value = x, rest = {more = [01], label = 'a', value = '2', rest = {more = [00]}}}",
        ),
    ],
)
def test_reduce_struct_to_fields(source, expected):
    assert show(reduction.reduce(resolved(source, ('x',)))) == show(resolved(expected, ('x',)))


def test_struct_to_fields_labels_are_bare_byte_arrays():
    field_list = reduction.reduce(resolved('$struct_to_fields {a = x}', ('x',)))
    assert field_list.fields[1] == terms.Field('label', terms.ByteArray(b'a'))


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('$fields_to_struct {more = [00]}', '{}'),
        (
            "$fields_to_struct {more = [01], label = 'a', value = x, rest = {more = [01], label = 'b', value = '2', "
            'rest = {more = [00]}}}',
            "{a = x, b = '2'}",
        ),
        # Duplicate labels are kept; '' is an unlabeled field; a value stays unreduced.
        (
            "$fields_to_struct {more = [01], label = 'a', value = x, rest = {more = [01], label = 'a', "
            "value = (y -> y) x, rest = {more = [01], label = '', value = x, rest = {more = [00]}}}}",
            '{a = x, a = (y -> y) x, x}',
        ),
        # A form on `more` or `label` is ignored; extra fields are ignored; in a node the
        # first of two equal labels counts; field order in a node doesn't matter.
        (
            "$fields_to_struct {value = x, more = [01]~'u8', label = 'a'~'f', label = 'b', extra = x, "
            'rest = {more = [00], label = [ff]}}',
            '{a = x}',
        ),
        ('$fields_to_struct {more = [01], label = [cebb], value = x, rest = {more = [00]}}', '{"λ" = x}'),
    ],
)
def test_reduce_fields_to_struct(source, expected):
    assert show(reduction.reduce(resolved(source, ('x',)))) == show(resolved(expected, ('x',)))


@pytest.mark.parametrize('source', ['{}', '{a = x, "λ" = \'2\', x, a = (y -> y) x}'])
def test_fields_to_struct_undoes_struct_to_fields(source):
    struct = resolved(source, ('x',))
    field_list = reduction.reduce(terms.Apply(terms.Builtin('struct_to_fields'), struct))
    assert reduction.reduce(terms.Apply(terms.Builtin('fields_to_struct'), field_list)) == struct


def test_struct_to_fields_undoes_fields_to_struct():
    field_list = resolved(
        "{more = [01], label = 'a', value = x, rest = {more = [01], label = '', value = '2', rest = {more = [00]}}}",
        ('x',),
    )
    struct = reduction.reduce(terms.Apply(terms.Builtin('fields_to_struct'), field_list))
    assert reduction.reduce(terms.Apply(terms.Builtin('struct_to_fields'), struct)) == field_list


def test_opcodes_are_not_builtins():
    assert not set(opcodes.OPCODES) & reduction.BUILTINS
    unknown = resolved("'add_i32' {[01000000], [02000000]}")
    assert reduction.reduce(unknown) is unknown
