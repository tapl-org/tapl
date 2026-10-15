# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import replace

import pytest

from oymo.oymomo import banf_shape, opcodes, reduction, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show


def program(defs):
    return f'module: {{}} -> {{{defs}}}'


def shaped(defs):
    return show(banf_shape.shape(reduction.resolve(parse(program(defs)))))


def same(defs):
    return show(reduction.resolve(parse(program(defs))))


def block(body, params="{n = 'i8'}"):
    return f'main = f -> {{entry = args: {params} -> {body}}}'


def resolved(source, free):
    term = reduction.resolve(parse(' -> '.join([*free, source])))
    for _ in free:
        term = term.body
    return term


def test_reduce_until_top_stable():
    free = ('a', 'e')
    assert show(banf_shape.reduce_until_top_stable(resolved('{p = {a = e}}.p.a', free))) == show(resolved('e', free))
    assert show(banf_shape.reduce_until_top_stable(resolved('$fix (self -> n -> n) a', free))) == show(
        resolved('a', free)
    )


def test_fix_does_not_reduce_its_argument():
    # `$fix g` unfolds without reducing `g`.
    term = resolved('$fix ((x -> x) g)', ('g',))
    assert show(banf_shape.step(term)) == show(resolved('(x -> x) g ($fix ((x -> x) g))', ('g',)))


def test_step_fires_the_root_rule_or_else_unblocks():
    free = ('e',)
    assert show(banf_shape.step(resolved('{p = {a = e}}.p.a', free))) == show(resolved('{a = e}.a', free))
    term = resolved('e.a', free)
    assert banf_shape.step(term) is term


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
        # Past the last field: the last field.
        ("(i -> {a = '23', b = '45'} i) [07]", "'45'"),
    ],
)
def test_reduce_until_top_stable_reduces_a_struct_apply(source, expected):
    assert show(banf_shape.reduce_until_top_stable(resolved(source, ()))) == show(resolved(expected, ()))


@pytest.mark.parametrize(
    'source',
    [
        # No field at all: stuck.
        '{} [01]',
        # The callee is not a struct, so the argument is not reduced.
        'f ((x -> x) [00])',
    ],
)
def test_reduce_until_top_stable_leaves_a_struct_apply_or_an_argument(source):
    term = resolved(source, ('f',))
    assert banf_shape.reduce_until_top_stable(term) is term


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        # A helper is inlined.
        (
            "(id -> let t = 'add' {'i8', id args.n, args.n} in t) (x -> x)",
            "let t = 'add' {'i8', args.n, args.n} in t",
        ),
        # An atom let is substituted.
        ('let t = args.n in t', 'args.n'),
        (
            "let t = args.n in let u = 'add' {'i8', t, t} in u",
            "let u = 'add' {'i8', args.n, args.n} in u",
        ),
        # $fix unfolds.
        ('$fix (self -> n -> n) args.n', 'args.n'),
        # Heads.
        ('((a -> {n = a.n}) args).n', 'args.n'),
        (
            "let t = {g = x -> 'add' {'i8', x, x}}.g args.n in t",
            "let t = 'add' {'i8', args.n, args.n} in t",
        ),
        (
            "(x -> y -> let t = 'add' {'i8', x, y} in t) args.n ('mul' {'i8', args.n, args.n})",
            "let y = 'mul' {'i8', args.n, args.n} in let t = 'add' {'i8', args.n, y} in t",
        ),
        # Projection.
        (
            "let t = 'add' {'i8', {a = args.n}.a, args.n} in t",
            "let t = 'add' {'i8', args.n, args.n} in t",
        ),
        ('{p = {a = args.n}}.p.a', 'args.n'),
        ('(mk -> (mk args).n) (a -> {n = a.n})', 'args.n'),
        # A let whose op has a redex operand stays a let.
        (
            "let t = 'add' {'i8', (x -> x) args.n, args.n} in t",
            "let t = 'add' {'i8', args.n, args.n} in t",
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
        # The same, written as a struct applied to the condition: `{else, then} c`.
        ('let t = {f.b {}, f.a {}} args.n in t', '{f.b {}, f.a {}} args.n'),
        (
            '{f.b ((x -> x) {}), (x -> f.a x) {}} ((x -> x) args.n)',
            '{f.b {}, f.a {}} args.n',
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
    assert show(banf_shape.shape(reduction.resolve(parse(source)))) == show(reduction.resolve(parse(expected)))


def test_forms_are_ignored():
    assert shaped(block('(x -> x) args.n')) == same(block('args.n'))


@pytest.mark.parametrize(
    'body',
    [
        "[01]: 'i8'",
        'args.n',
        "let t = 'add' {'i8', args.n, args.n} in t",
        'f.a {}',
        'if args.n then f.a {} else f.b {}',
        '{f.b {}, f.a {}} args.n',
        '{x = f.b {}, y = f.a {}} args.n',
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
        block("'add'"),
    ],
)
def test_terms_that_cannot_reach_the_shape_are_left(defs):
    assert shaped(defs) == same(defs)


def test_already_shaped_is_unchanged():
    source = """
    fact = f -> {
      entry = args:{n = 'i32'} ->
        let t0 = 'icmp_eq' {'i32', args.n, [00000000]:'i32'} in
        if t0 then f.then0 {} else f.else0 {n = args.n},
      then0 = args:{} -> [01000000]:'i32',
      else0 = args:{n = 'i32'} ->
        let t1 = 'sub' {'i32', args.n, [01000000]:'i32'} in
        let t2 = module.fact {n = t1} in
        let t3 = 'mul' {'i32', args.n, t2} in
        t3,
    }
    """
    assert shaped(source) == same(source)


def test_runs_out_of_fuel():
    term = reduction.resolve(parse(program(block('$fix (self -> self) args.n'))))
    with pytest.raises(reduction.ReductionError, match='ran out of reduction steps'):
        banf_shape.shape(term, fuel=100)


def test_reduce_until_top_stable_reduces_inside_formed():
    i1 = terms.ByteArray(b'i1')
    one = terms.ByteArray(b'\x01')
    identity = terms.Lambda('x', terms.Empty, terms.BruijnIndex(0))
    reduced = banf_shape.reduce_until_top_stable(terms.Formed(terms.Apply(identity, one), i1))
    assert reduced == terms.Formed(one, i1)


def test_dynamic_byte_array_form():
    reduced = banf_shape.reduce_until_top_stable(reduction.resolve(parse("(x -> y -> y: x) 'i1' [01]")))
    assert reduced == parse("[01]:'i1'")
    assert show(reduced) == "[01]:'i1'"


def test_struct_to_fields_reduces_its_argument_but_not_the_values():
    term = resolved('$struct_to_fields ({p = {a = (i -> i) x}}.p)', FREE)
    expected = resolved("{more = [01], label = 'a', value = (i -> i) x, rest = {more = [00]}}", FREE)
    assert show(banf_shape.reduce_until_top_stable(term)) == show(expected)


def test_struct_to_fields_on_a_run_time_value_is_stuck():
    term = resolved('$struct_to_fields e', FREE)
    assert banf_shape.reduce_until_top_stable(term) is term


def test_fields_to_struct_goal():
    source = "(l -> v -> $fields_to_struct {more = [01], label = l, value = v, rest = {more = [00]}}) 'a' '23'"
    assert banf_shape.reduce_until_top_stable(reduction.resolve(parse(source))) == parse("{a = '23'}")


def test_fields_to_struct_reduces_more_label_and_rest_but_not_values():
    source = (
        "$fields_to_struct ({p = {more = (y -> y) [01], label = {q = 'a'}.q, value = (y -> y) x, "
        'rest = (y -> y) {more = [00]}}}.p)'
    )
    reduced = banf_shape.reduce_until_top_stable(resolved(source, FREE))
    assert show(reduced) == show(resolved('{a = (y -> y) x}', FREE))


def test_fields_to_struct_reads_label_and_rest_only_after_more_is_01():
    given = []

    def record(part):
        given.append(show(part))
        return banf_shape.reduce_until_top_stable(part)

    source = "$fields_to_struct {more = [00], label = (y -> y) 'a', value = (y -> y) x, rest = (y -> y) e}"
    call = resolved(source, FREE)
    assert reduction.BUILTIN_RULES['fields_to_struct'].reduce(call, record) == terms.Struct([])
    assert given == [show(call.argument), '[00]']


def test_fields_to_struct_maps_a_struct():
    source = """
        let map = $fix (map -> f -> l ->
          if l.more then {more = [01], label = l.label, value = f l.value, rest = map f l.rest}
          else l)
        in $fields_to_struct (map (v -> {v}) ($struct_to_fields {a = x, b = e}))
    """
    struct = banf_shape.reduce_until_top_stable(resolved(source, FREE))
    assert [field.label for field in struct.fields] == ['a', 'b']
    values = [banf_shape.reduce_until_top_stable(field.value) for field in struct.fields]
    assert [show(banf_shape.reduce_until_top_stable(v.fields[0].value)) for v in values] == [
        show(resolved('x', FREE)),
        show(resolved('e', FREE)),
    ]


def test_an_endless_field_list_runs_out_of_fuel():
    term = resolved("$fields_to_struct ($fix (l -> {more = [01], label = 'a', value = x, rest = l}))", FREE)
    with pytest.raises(reduction.ReductionError, match='ran out of reduction steps'):
        banf_shape.reduce_until_top_stable(term)


def test_an_opcode_reduces_its_fields_then_folds():
    term = resolved("'add' {(f -> f) 'i32', (x -> x) [01000000]: 'i32', {c = [02000000]}.c}", FREE)
    assert banf_shape.reduce_until_top_stable(term) == resolved("[03000000]: 'i32'", FREE)


def test_an_opcode_with_the_wrong_number_of_fields_reduces_its_fields_but_does_not_fold():
    # The kernel's rule for `'name' {...}` doesn't depend on the opcode: it reduces every field.
    term = resolved("'add' {'i32', (i -> i) [01000000]}", FREE)
    assert banf_shape.reduce_until_top_stable(term) == resolved("'add' {'i32', [01000000]}", FREE)


def test_an_opcode_on_a_run_time_operand_keeps_the_fields_it_reduced():
    term = resolved("'add' {'i32', e, (i -> i) [02000000]}", FREE)
    assert show(banf_shape.reduce_until_top_stable(term)) == show(resolved("'add' {'i32', e, [02000000]}", FREE))


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        # A let whose op folds is no longer an op, so it is substituted.
        ("let t = 'add' {'i8', [01]: 'i8', [02]: 'i8'} in t", "[03]: 'i8'"),
        (
            "let t = 'add' {'i8', [01]: 'i8', [02]: 'i8'} in let u = 'add' {'i8', args.n, t} in u",
            "let u = 'add' {'i8', args.n, [03]: 'i8'} in u",
        ),
        # An if on a folded comparison picks its arm.
        ("let c = 'icmp_eq' {'i8', [07]: 'i8', [07]: 'i8'} in if c then f.a {} else f.b {}", 'f.a {}'),
        (
            "let c = 'icmp_ult' {'i8', [ff]: 'i8', args.n} in if c then f.a {} else f.b {}",
            "let c = 'icmp_ult' {'i8', [ff]: 'i8', args.n} in if c then f.a {} else f.b {}",
        ),
        # A fold can feed the next one.
        (
            "let t = 'add' {'i8', [01]: 'i8', [02]: 'i8'} in let u = 'mul' {'i8', t, t} in u",
            "[09]: 'i8'",
        ),
    ],
)
def test_block_body_folds(body, expected):
    assert shaped(block(body)) == same(block(expected))


# A built-in reduces its own call (plan_struct_pack decision 1). The rules below are test-only.


def _reduce_fields(struct, positions, reduce_part):
    fields = list(struct.fields)
    for i in positions:
        fields[i] = replace(fields[i], value=reduce_part(fields[i].value))
    if all(new.value is old.value for new, old in zip(fields, struct.fields, strict=True)):
        return struct
    return replace(struct, fields=fields)


def _put_back(call, argument):
    return call if argument is call.argument else replace(call, argument=argument)


def _first(call, reduce_part):
    """`$first {a, ...}` gives `a`, once the argument is a struct."""
    argument = reduce_part(call.argument)
    if isinstance(argument, terms.Struct) and argument.fields:
        return argument.fields[0].value
    return _put_back(call, argument)


def _both(call, reduce_part):
    """`$both {a, b}` joins the bytes of `a` and `b`, once both are byte arrays."""
    argument = reduce_part(call.argument)
    if isinstance(argument, terms.Struct):
        argument = _reduce_fields(argument, range(len(argument.fields)), reduce_part)
        values = [f.value for f in argument.fields]
        if all(isinstance(v, terms.ByteArray) for v in values):
            return terms.ByteArray(b''.join(v.value for v in values))
    return _put_back(call, argument)


def _gate(call, reduce_part):
    """`$gate {c, t}` gives `t` reduced if `c` is [01]. `t` is read only then."""
    argument = reduce_part(call.argument)
    if isinstance(argument, terms.Struct) and len(argument.fields) == 2:
        argument = _reduce_fields(argument, [0], reduce_part)
        if reduction.index_value(argument.fields[0].value) == 1:
            return reduce_part(argument.fields[1].value)
    return _put_back(call, argument)


@pytest.fixture
def test_rules(monkeypatch):
    for name, reduce in (('first', _first), ('both', _both), ('gate', _gate)):
        monkeypatch.setitem(reduction.BUILTIN_RULES, name, reduction.BuiltinRule(name, reduce))


FREE = ('e', 'g', 'x')


@pytest.mark.usefixtures('test_rules')
def test_a_builtin_reduces_its_argument_and_fires_in_one_step():
    term = resolved('$first ({p = {a = x}}.p)', FREE)
    assert show(banf_shape.step(term)) == show(resolved('x', FREE))


@pytest.mark.usefixtures('test_rules')
def test_reduction_reduce_does_not_reduce_parts():
    term = resolved('$first ({p = {a = x}}.p)', FREE)
    assert reduction.reduce(term) is term


@pytest.mark.usefixtures('test_rules')
def test_a_builtin_reduces_each_field_then_fires():
    term = resolved('$both {a = (i -> i) [01], b = {c = [02]}.c}', FREE)
    assert banf_shape.reduce_until_top_stable(term) == terms.ByteArray(b'\x01\x02')


@pytest.mark.usefixtures('test_rules')
def test_a_stuck_builtin_keeps_the_parts_it_reduced():
    term = resolved('$both {a = e, b = (i -> i) [02]}', FREE)
    stepped = banf_shape.step(term)
    assert show(stepped) == show(resolved('$both {a = e, b = [02]}', FREE))
    assert banf_shape.step(stepped) is stepped


@pytest.mark.usefixtures('test_rules')
def test_a_builtin_picks_what_to_reduce_by_what_it_sees():
    stays = resolved('$gate {(i -> i) [00], (i -> i) [02]}', FREE)
    assert show(banf_shape.reduce_until_top_stable(stays)) == show(resolved('$gate {[00], (i -> i) [02]}', FREE))
    fires = resolved('$gate {(i -> i) [01], (i -> i) [02]}', FREE)
    assert banf_shape.reduce_until_top_stable(fires) == terms.ByteArray(b'\x02')


# The rules of decision 1, checked for every built-in on sample calls.
SAMPLES = {
    'fix': ['$fix g', '$fix ((x -> x) g)', '$fix {a = g}'],
    'struct_to_fields': ['$struct_to_fields {a = x}', '$struct_to_fields ({p = {a = x}}.p)', '$struct_to_fields e'],
    'fields_to_struct': [
        "$fields_to_struct {more = (y -> y) [01], label = (y -> y) 'a', value = x, rest = (y -> y) {more = [00]}}",
        "$fields_to_struct {more = [01], label = 'a', value = x, rest = e}",
        '$fields_to_struct {more = [00]}',
        '$fields_to_struct e',
    ],
    'first': ['$first ({p = {a = x}}.p)', '$first e', '$first {a = x}'],
    'both': ['$both {a = (i -> i) [01], b = {c = [02]}.c}', '$both {a = e, b = (i -> i) [02]}', '$both [01]'],
    'gate': ['$gate {(i -> i) [00], (i -> i) [02]}', '$gate {(i -> i) [01], (i -> i) [02]}'],
}


def _opcode_samples(signature):
    """Calls of an opcode: one that folds, one that reduces its argument and fields first,
    one stuck on a run-time operand (`e`), and one with wrong labels."""
    form = signature.params[0][1]
    one = f"[{(1).to_bytes(opcodes.byte_width(opcodes.bit_width(form)), 'little').hex()}]: '{form.as_str}'"
    labels = [label for label, _ in signature.params]

    def call(values, labels=labels):
        return '{' + ', '.join(f'{label} = {value}' for label, value in zip(labels, values, strict=True)) + '}'

    reducible = [f'(i -> i) {one}'] * len(labels)
    return [
        f'${signature.name} {call([one] * len(labels))}',
        f'${signature.name} ({{p = {call(reducible)}}}.p)',
        f'${signature.name} {call(["e", *reducible[1:]])}',
        f'${signature.name} {call(reducible, [f"x{i}" for i in range(len(labels))])}',
    ]


SAMPLES |= {
    name: _opcode_samples(signature) for name, signature in opcodes.OPCODES.items() if name in reduction.BUILTIN_RULES
}


def test_every_builtin_has_samples():
    assert set(reduction.BUILTIN_RULES) <= set(SAMPLES)


def _fired(call, result):
    """Whether `result` is not the call (or the call with parts reduced)."""
    return not (isinstance(result, terms.Apply) and result.function == call.function)


# Catches a built-in whose `reduce` is written wrong. Each check below is shown with a
# broken version of a test rule above that it catches, on one of the samples.
#
# Check 1: it must not look at a part without giving it to `reduce_part` first.
#
#     def first(call, reduce_part):                       # broken: never reduces
#         if isinstance(call.argument, terms.Struct):
#             return call.argument.fields[0].value
#         return call
#
#   On `$first {a = x}` it fires without asking `reduce_part` for anything, so the test
#   swaps the argument for the variable `e`: `$first e` doesn't fire. Firing depended on
#   a part it never reduced, so it would also miss `$first ({p = {a = x}}.p)`. Fails.
#
# Check 2: with `keep` (reduce nothing) it must fire or return `call` itself.
#
#     def first(call, reduce_part):                       # broken: always a new call
#         argument = reduce_part(call.argument)
#         if isinstance(argument, terms.Struct):
#             return argument.fields[0].value
#         return replace(call, argument=argument)
#
#   On `$first e` with `keep`, it returns a copy of `call`. `reduction.reduce(t) is t` is
#   then false although nothing happened, and `reduce_until_top_stable` loops. Fails.
#
# Check 3: one call does all it can, so if it doesn't fire, calling it again on what it
# returned gives back that same object (stuck for good).
#
#     def both(call, reduce_part):                        # broken: one field per call
#         ... reduces only the first field that changes, then returns ...
#
#   On `$both {a = (i -> i) [01], b = {c = [02]}.c}` the first call returns
#   `$both {a = [01], b = {c = [02]}.c}`, and the second one still changes `b`. Fails.
@pytest.mark.usefixtures('test_rules')
@pytest.mark.parametrize('source', [source for sources in SAMPLES.values() for source in sources])
def test_builtin_reduce_contract(source):
    call = resolved(source, FREE)
    rule = reduction.BUILTIN_RULES[call.function.name]
    given = []

    def record(part):
        given.append(part)
        return banf_shape.reduce_until_top_stable(part)

    result = rule.reduce(call, record)

    if not any(part is call.argument for part in given):
        other = replace(call, argument=terms.BruijnIndex(len(FREE) - 1))  # `e`
        assert _fired(other, rule.reduce(other, record)) == _fired(call, result)

    kept = rule.reduce(call, reduction.keep)
    assert kept is call or _fired(call, kept)

    if not _fired(call, result):
        assert rule.reduce(result, banf_shape.reduce_until_top_stable) is result
