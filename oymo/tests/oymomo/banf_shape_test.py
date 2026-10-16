# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import banf_shape, reduction, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show


def program(defs):
    return f'module~{{}} -> {{{defs}}}'


def shaped(defs):
    return show(banf_shape.shape(reduction.resolve(parse(program(defs)))))


def same(defs):
    return show(reduction.resolve(parse(program(defs))))


def block(body, params="{n = 'i8'}"):
    return f'main = f -> {{entry = args~{params} -> {body}}}'


def resolved(source, free):
    term = reduction.resolve(parse(' -> '.join([*free, source])))
    for _ in free:
        term = term.body
    return term


FREE = ('e', 'g', 'x')


def test_reduce_until_top_stable():
    free = ('a', 'e')
    assert show(banf_shape.reduce_until_top_stable(resolved('{p = {a = e}}.p.a', free))) == show(resolved('e', free))
    assert show(banf_shape.reduce_until_top_stable(resolved('$fix (self -> n -> n) a', free))) == show(
        resolved('a', free)
    )


def test_fix_reduces_its_argument_to_a_lambda_then_unfolds():
    term = resolved('$fix ((x -> x) (self -> n -> n))', ())
    stepped = banf_shape.step(term)
    assert show(stepped) == show(resolved('$fix (self -> n -> n)', ()))
    assert show(banf_shape.step(stepped)) == show(resolved('(self -> n -> n) ($fix (self -> n -> n))', ()))


def test_fix_does_not_reduce_under_the_lambda():
    term = resolved('$fix (self -> (x -> x) self)', ())
    assert show(reduction.reduce(term)) == show(resolved('(self -> (x -> x) self) ($fix (self -> (x -> x) self))', ()))


@pytest.mark.parametrize('source', ['$fix g', '$fix {a = g}', "$fix 'i8'"])
def test_fix_on_a_non_lambda_is_stuck(source):
    term = resolved(source, FREE)
    assert banf_shape.reduce_until_top_stable(term) is term


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
    assert shaped("main = (x -> x) (f -> {entry = args~{} -> [01]~'i8'})") == same(
        "main = f -> {entry = args~{} -> [01]~'i8'}"
    )


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        # Each position, reached after reduction.
        (
            '(p -> p) (module~{} -> {})',
            'module~{} -> {}',
        ),
        (
            '{d = module~{} -> {}}.d',
            'module~{} -> {}',
        ),
        (
            "module~{} -> (x -> x) {main = f -> (x -> x) {entry = (x -> x) (args~{} -> [01]~'i8')}}",
            "module~{} -> {main = f -> {entry = args~{} -> [01]~'i8'}}",
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
        "[01]~'i8'",
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
      entry = args~{n = 'i32'} ->
        let t0 = 'icmp_eq' {'i32', args.n, [00000000]~'i32'} in
        if t0 then f.then0 {} else f.else0 {n = args.n},
      then0 = args~{} -> [01000000]~'i32',
      else0 = args~{n = 'i32'} ->
        let t1 = 'sub' {'i32', args.n, [01000000]~'i32'} in
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


def test_reduce_until_top_stable_drops_a_form_found_inside_formed():
    # `(x~'i1' -> x) ((y -> y) [01]~'i8')` puts `((y -> y) [01]~'i8')~'i1'` in for `x`: the
    # argument is lazy, so its form shows up only once reduction enters the Formed.
    term = reduction.resolve(parse("(x~'i1' -> x) ((y -> y) [01]~'i8')"))
    assert banf_shape.reduce_until_top_stable(term) == parse("[01]~'i1'")


def test_dynamic_byte_array_form():
    reduced = banf_shape.reduce_until_top_stable(reduction.resolve(parse("(x -> y -> y~x) 'i1' [01]")))
    assert reduced == parse("[01]~'i1'")
    assert show(reduced) == "[01]~'i1'"


def test_struct_to_fields_reduces_its_argument_but_not_the_values():
    term = resolved('$struct_to_fields ({p = {a = (i -> i) x}}.p)', FREE)
    expected = resolved("{more = [01], label = 'a', value = (i -> i) x, rest = {more = [00]}}", FREE)
    assert show(banf_shape.reduce_until_top_stable(term)) == show(expected)


def test_struct_to_fields_on_a_run_time_value_is_stuck():
    term = resolved('$struct_to_fields e', FREE)
    assert banf_shape.reduce_until_top_stable(term) is term


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ('$struct_to_fields ((i -> i) e)', '$struct_to_fields e'),
        ('$fix ((i -> i) g)', '$fix g'),
        # `more` reduces to [02], so the list is malformed: `label` and `rest` are not read.
        (
            "$fields_to_struct {more = (y -> y) [02], label = (y -> y) 'a', rest = (y -> y) e}",
            "$fields_to_struct {more = [02], label = (y -> y) 'a', rest = (y -> y) e}",
        ),
        # Stuck on `rest`: the parts read before it stay reduced.
        (
            "$fields_to_struct {more = (y -> y) [01], label = (y -> y) 'a', value = (y -> y) x, rest = e}",
            "$fields_to_struct {more = [01], label = 'a', value = (y -> y) x, rest = e}",
        ),
    ],
)
def test_a_stuck_builtin_keeps_what_it_reduced(source, expected):
    term = resolved(source, FREE)
    stepped = banf_shape.step(term)
    assert show(stepped) == show(resolved(expected, FREE))
    assert banf_shape.step(stepped) is stepped


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


def test_fields_to_struct_ends_at_more_00():
    source = "$fields_to_struct {more = (y -> y) [00], label = (y -> y) 'a', value = (y -> y) x, rest = (y -> y) e}"
    assert banf_shape.reduce_until_top_stable(resolved(source, FREE)) == terms.Struct([])


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
    term = resolved("'add' {(f -> f) 'i32', (x -> x) [01000000]~'i32', {c = [02000000]}.c}", FREE)
    assert banf_shape.reduce_until_top_stable(term) == resolved("[03000000]~'i32'", FREE)


def test_an_opcode_with_the_wrong_number_of_fields_reduces_its_fields_but_does_not_fold():
    # Reduction's rule for `'name' {...}` doesn't depend on the opcode: it reduces every field.
    term = resolved("'add' {'i32', (i -> i) [01000000]}", FREE)
    assert banf_shape.reduce_until_top_stable(term) == resolved("'add' {'i32', [01000000]}", FREE)


def test_an_opcode_on_a_run_time_operand_keeps_the_fields_it_reduced():
    term = resolved("'add' {'i32', e, (i -> i) [02000000]}", FREE)
    assert show(banf_shape.reduce_until_top_stable(term)) == show(resolved("'add' {'i32', e, [02000000]}", FREE))


def test_seq_reduces_its_fields_then_fires():
    term = resolved('$seq {{a = [01]}.a, (i -> i) [02], x}', FREE)
    assert banf_shape.reduce_until_top_stable(term) == resolved('x', FREE)


def test_a_stuck_seq_keeps_the_fields_it_reduced():
    # `e` is a run-time value: `$seq` stays, with every field reduced, the value too.
    term = resolved('$seq {{a = e}.a, (i -> i) [01], {b = x}.b}', FREE)
    assert show(banf_shape.reduce_until_top_stable(term)) == show(resolved('$seq {e, [01], x}', FREE))


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        # A stuck `$seq` is an atom, so a let on it is substituted, as is one that fires.
        (
            "let t = 'add' {'i8', args.n, args.n} in let c = $seq {t, args.n} in let u = 'mul' {'i8', c, c} in u",
            "let t = 'add' {'i8', args.n, args.n} in let u = 'mul' {'i8', $seq {t, args.n}, $seq {t, args.n}} in u",
        ),
        ("let c = $seq {[01]~'i8', args.n} in c", 'args.n'),
    ],
)
def test_block_body_seq(body, expected):
    assert shaped(block(body)) == same(block(expected))


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        # A let whose op folds is no longer an op, so it is substituted.
        ("let t = 'add' {'i8', [01]~'i8', [02]~'i8'} in t", "[03]~'i8'"),
        (
            "let t = 'add' {'i8', [01]~'i8', [02]~'i8'} in let u = 'add' {'i8', args.n, t} in u",
            "let u = 'add' {'i8', args.n, [03]~'i8'} in u",
        ),
        # An if on a folded comparison picks its arm.
        ("let c = 'icmp_eq' {'i8', [07]~'i8', [07]~'i8'} in if c then f.a {} else f.b {}", 'f.a {}'),
        (
            "let c = 'icmp_ult' {'i8', [ff]~'i8', args.n} in if c then f.a {} else f.b {}",
            "let c = 'icmp_ult' {'i8', [ff]~'i8', args.n} in if c then f.a {} else f.b {}",
        ),
        # A fold can feed the next one.
        (
            "let t = 'add' {'i8', [01]~'i8', [02]~'i8'} in let u = 'mul' {'i8', t, t} in u",
            "[09]~'i8'",
        ),
    ],
)
def test_block_body_folds(body, expected):
    assert shaped(block(body)) == same(block(expected))
