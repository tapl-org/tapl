# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The unit tools, `'unit.merge'`, `'unit.rebase'` and `'unit.make_reducible'`, called as opcodes."""

import pathlib

import pytest

from oymo.oymomo import driver, reduction, strategy
from oymo.oymomo.grammar import parse

FN = "{'function', {n = 'i32'}, 'i32'}"
OTHER_FN = "{'function', {n = 'i64'}, 'i64'}"
# A body that calls `g.lib.step` and ends in a region.
BODY = "λg. λp. 'R' (λr. {let y = g.lib.step {n = p.n} in y})"


def normal(source):
    return strategy.normalize(reduction.resolve(parse(source)))


def assert_gives(source, expected):
    assert normal(source) == normal(expected)


def assert_no_step(source):
    """The call stays as written: its operand is an operand, but the tool gives no result."""
    term = normal(source)
    assert reduction.is_operand(term.argument)
    assert reduction.reduce(term) is term


# Merge


def test_merge_combines_namespaces():
    assert_gives(
        "'unit.merge' {{a = {x = {type = 'i32', link = 'x'}}}, {a = {y = {type = 'i8', link = 'y'}}, b = {}}}",
        "{a = {x = {type = 'i32', link = 'x'}, y = {type = 'i8', link = 'y'}}, b = {}}",
    )


@pytest.mark.parametrize(
    'filler',
    [
        f'{{type = {FN}, body = {BODY}}}',
        f"{{type = {FN}, link = 'step'}}",
        "{type = 'i32', init = [00000000]}",
    ],
)
def test_merge_fills_a_hole(filler):
    hole_type = FN if 'function' in filler else "'i32'"
    hole = f'{{type = {hole_type}}}'
    assert_gives(f"'unit.merge' {{{{f = {hole}}}, {{f = {filler}}}}}", f'{{f = {filler}}}')
    assert_gives(f"'unit.merge' {{{{f = {filler}}}, {{f = {hole}}}}}", f'{{f = {filler}}}')


def test_merge_keeps_one_of_two_equal_holes():
    assert_gives(f"'unit.merge' {{{{f = {{type = {FN}}}}}, {{f = {{type = {FN}}}}}}}", f'{{f = {{type = {FN}}}}}')


def test_merge_keeps_one_of_two_equal_declarations():
    declaration = f"{{type = {FN}, link = 'step'}}"
    assert_gives(f"'unit.merge' {{{{f = {declaration}}}, {{f = {declaration}}}}}", f'{{f = {declaration}}}')
    assert_gives("'unit.merge' {{v = [01]}, {v = [01]}}", '{v = [01]}')


@pytest.mark.parametrize(
    ('first', 'second'),
    [
        # Two definitions, even with equal bodies: a symbol defined twice.
        (f'{{type = {FN}, body = {BODY}}}', f'{{type = {FN}, body = {BODY}}}'),
        # Different types.
        (f"{{type = {FN}, link = 'f'}}", f"{{type = {OTHER_FN}, link = 'f'}}"),
        # A hole and a filler of another type.
        (f'{{type = {FN}}}', f"{{type = {OTHER_FN}, link = 'f'}}"),
        # Two different declarations, or byte arrays.
        (f"{{type = {FN}, link = 'f'}}", f"{{type = {FN}, link = 'g'}}"),
        ('[01]', '[02]'),
        # A namespace and an entry.
        ('{}', f"{{type = {FN}, link = 'f'}}"),
    ],
)
def test_merge_gives_no_step(first, second):
    assert_no_step(f"'unit.merge' {{{{f = {first}}}, {{f = {second}}}}}")


def test_merge_appends_unlabeled_fields():
    assert_gives("'unit.merge' {{[01], a = [02]}, {[01], a = [02]}}", '{[01], a = [02], [01]}')


def test_merge_keeps_the_order_of_first_appearance():
    assert_gives(
        "'unit.merge' {{b = [01], a = {x = [01]}}, {c = [01], a = {y = [01]}, b = [01]}}",
        '{b = [01], a = {x = [01], y = [01]}, c = [01]}',
    )


def test_merge_of_one_or_none():
    assert_gives("'unit.merge' {{a = [01]}}", '{a = [01]}')
    assert_gives("'unit.merge' {}", '{}')


def test_merge_takes_a_struct_of_structs():
    assert_no_step("'unit.merge' {{}, [01]}")
    assert_no_step("'unit.merge' [01]")


# Rebase


def lib(body=BODY, extra=''):
    return f'{{lib = {{step = {{type = {FN}, body = {body}}}{extra}}}}}'


def test_rebase_prefixes_paths_and_puts_the_struct_under_the_prefix():
    expected_body = "λg. λp. 'R' (λr. {let y = g.dbl.lib.step {n = p.n} in y})"
    assert_gives(f"'unit.rebase' {{{{'dbl'}}, {lib()}}}", f'{{dbl = {lib(expected_body)}}}')


def test_rebase_in_nested_regions_and_under_binders():
    body = "λg. λp. 'R' (λr. {e = λx. 'R' (λq. {let y = g.lib.step {n = x} in g.lib.c})})"
    expected = "λg. λp. 'R' (λr. {e = λx. 'R' (λq. {let y = g.a.b.lib.step {n = x} in g.a.b.lib.c})})"
    assert_gives(f"'unit.rebase' {{{{'a', 'b'}}, {lib(body)}}}", f'{{a = {{b = {lib(expected)}}}}}')


def test_rebase_copies_data_entries():
    extra = ", c = {type = 'i32', value = [01000000]}, h = {type = 'i32'}"
    expected_body = "λg. λp. 'R' (λr. {let y = g.x.lib.step {n = p.n} in y})"
    assert_gives(f"'unit.rebase' {{{{'x'}}, {lib(extra=extra)}}}", f'{{x = {lib(expected_body, extra)}}}')


def test_rebase_mounts_a_header():
    header = f"{{lib = {{step = {{type = {FN}, link = 'step'}}}}}}"
    assert_gives(f"'unit.rebase' {{{{'libc'}}, {header}}}", f'{{libc = {header}}}')


def test_rebase_with_an_empty_prefix_changes_nothing():
    assert_gives(f"'unit.rebase' {{{{}}, {lib()}}}", lib())


@pytest.mark.parametrize(
    'source',
    [
        # `g` used whole, not as the head of a path or a region.
        f"'unit.rebase' {{{{'x'}}, {lib('λg. λp. p g')}}}",
        # A body that is not a lambda.
        f"'unit.rebase' {{{{'x'}}, {lib('[01]')}}}",
        # A lambda outside an entry's body.
        "'unit.rebase' {{'x'}, {f = λx. x}}",
        # A prefix label that is not a nonempty text byte array.
        f"'unit.rebase' {{{{[ff]}}, {lib()}}}",
        f"'unit.rebase' {{{{''}}, {lib()}}}",
        # Not `{P, X}` with two structs.
        f"'unit.rebase' {{'x', {lib()}}}",
        "'unit.rebase' {{'x'}}",
    ],
)
def test_rebase_gives_no_step(source):
    assert_no_step(source)


def test_a_rebase_resolves_a_clash():
    other = lib("λg. λp. 'R' (λr. {let y = g.lib.step {n = p.n} in [02000000]})")
    clash = f"'unit.merge' {{{lib()}, {other}}}"
    assert_no_step(clash)
    merged = normal(f"'unit.merge' {{{lib()}, 'unit.rebase' {{{{'dbl'}}, {other}}}}}")
    assert [f.label for f in merged.fields] == ['lib', 'dbl']


# Make reducible

# Factorial of 5 in ingot shape: a loop region, and `main` calling `g.math.fact`.
FACT_INGOT = """{
  math = {fact = {type = {'function', {n = 'i32'}, 'i32'}, body = λg. λp. 'R' (λr. {
    entry = r.loop [01000000] p.n,
    loop = λacc. λn.
      let next = 'mul' {'i32', acc, n} in
      let k = 'sub' {'i32', n, [01000000]} in
      let done = 'icmp' {'eq', 'i32', k, [00000000]} in
      if done then r.exit next else r.loop next k,
    exit = λacc. acc
  })}},
  main = {type = {'function', {}, 'i32'}, link = 'main',
    body = λg. λp. 'R' (λr. {let y = g.math.fact {n = [05000000]} in y})},
  puts = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'puts'},
  counter = {type = 'i32', init = [00000000]}
}"""


def test_make_reducible_runs_a_unit_by_reduction():
    assert_gives(f"(fix ('unit.make_reducible' {FACT_INGOT})).main {{}}", '[78000000]')
    assert_gives(f"(fix ('unit.make_reducible' {FACT_INGOT})).math.fact {{n = [04000000]}}", '[18000000]')


def test_make_reducible_runs_a_void_function_by_reduction():
    ingot = (
        "{nop = {type = {'function', {x = 'i32'}, 'void'}, body = λg. λp. 'R' (λr. {[]})},"
        " main = {type = {'function', {}, 'i32'}, body = λg. λp. 'R' (λr. {let u = g.nop {x = [01000000]} in [2a000000]})}}"
    )
    assert_gives(f"(fix ('unit.make_reducible' {ingot})).nop {{x = [01000000]}}", '[]')
    assert_gives(f"(fix ('unit.make_reducible' {ingot})).main {{}}", '[2a000000]')


# `twice` calls the function it is given, `p.f`, twice; `inc` adds one; `main` passes `g.inc`.
APPLY_INGOT = """{
  inc = {type = {'function', {n = 'i32'}, 'i32'},
    body = λg. λp. 'R' (λr. {let y = 'add' {'i32', p.n, [01000000]} in y})},
  twice = {type = {'function', {f = {'function', {n = 'i32'}, 'i32'}, x = 'i32'}, 'i32'},
    body = λg. λp. 'R' (λr. {let a = p.f {n = p.x} in let b = p.f {n = a} in b})},
  main = {type = {'function', {}, 'i32'},
    body = λg. λp. 'R' (λr. {let y = g.twice {f = g.inc, x = [05000000]} in y})},
}"""


def test_make_reducible_runs_a_function_passed_as_a_value():
    # The instance's `inc` is passed for `f`, and `p.f {…}` applies it: no rule of its own.
    assert_gives(f"(fix ('unit.make_reducible' {APPLY_INGOT})).main {{}}", '[07000000]')


def test_a_call_without_the_labels_is_stuck_by_reduction():
    # Reduction reads p.n by its label, so operands given by position leave a projection with
    # no field; compiled, the translation passes them by position.
    unit = f"(fix ('unit.make_reducible' {APPLY_INGOT}))"
    term = normal(f'{unit}.inc {{[05000000]}}')
    assert reduction.stuck_part(term) is not None


def test_make_reducible_hoists_g_and_runs_regions():
    # Each body's own `λg` moves out to one `λg`; a region becomes `(fix R) [00]`; other
    # entries (a declaration, a global variable) stay as they are.
    assert_gives(
        "'unit.make_reducible' {f = {type = 'i32', body = λg. λp. 'R' (λr. {g.k})}, "
        "k = {type = 'i32', value = [07000000]}, d = {type = 'i32', link = 'd'}}",
        "λg. {f = λp. (fix (λr. {g.k})) [00], k = {type = 'i32', value = [07000000]}, d = {type = 'i32', link = 'd'}}",
    )


def test_make_reducible_after_merge_fills_declarations():
    lib = (
        f"{{lib = {{step = {{type = {FN}, link = 'step', "
        f"body = λg. λp. 'R' (λr. {{let y = 'mul' {{'i32', p.n, [02000000]}} in y}})}}}}}}"
    )
    app = f"{{lib = {{step = {{type = {FN}, link = 'step'}}}}, main = {{type = {FN}, body = {BODY}}}}}"
    assert_gives(f"(fix ('unit.make_reducible' ('unit.merge' {{{app}, {lib}}}))).main {{n = [03000000]}}", '[06000000]')


@pytest.mark.parametrize(
    'operand',
    [
        "{f = {type = 'i32', body = λg. 'R' (λr. {[00]})}}",  # a body that is not λg. λp. …
        '{f = λx. x}',  # a λ outside an entry's body
        "'notastruct'",
    ],
)
def test_make_reducible_gives_no_step(operand):
    assert_no_step(f"'unit.make_reducible' {operand}")


def test_rebase_leaves_regions_alone():
    assert_gives(
        f"'unit.rebase' {{{{'dbl'}}, {{main = {{type = {FN}, body = {BODY}}}}}}}",
        f"{{dbl = {{main = {{type = {FN}, body = λg. λp. 'R' (λr. {{let y = g.dbl.lib.step {{n = p.n}} in y}})}}}}}}",
    )


def test_merge_joins_a_declaration_with_its_definition():
    definition = f"{{type = {FN}, link = 'step', body = {BODY}}}"
    declaration = f"{{type = {FN}, link = 'step'}}"
    assert_gives(f"'unit.merge' {{{{f = {declaration}}}, {{f = {definition}}}}}", f'{{f = {definition}}}')
    assert_gives(f"'unit.merge' {{{{f = {definition}}}, {{f = {declaration}}}}}", f'{{f = {definition}}}')
    # Another link, or another type, is not the same symbol.
    assert_no_step(f"'unit.merge' {{{{f = {{type = {FN}, link = 'other'}}}}, {{f = {definition}}}}}")
    assert_no_step(f"'unit.merge' {{{{f = {{type = {OTHER_FN}, link = 'step'}}}}, {{f = {definition}}}}}")


# The `diamond` golden's normal form (its three units already merged), made reducible.
GOLDENS = pathlib.Path(__file__).parent.parent / 'goldens'
DIAMOND = "'unit.make_reducible' ('driver.read_low' 'diamond/root.normal.oymo')"
# One shared `λg`; each entry is its code; each region `(fix R) [00]` has unfolded to its
# field 0, since the unit has no loop.
DIAMOND_REDUCIBLE = """
λg. {
  d= {twice= λp. let y = 'mul' {'i32', p.n, [02000000]} in y},
  b= {
    f= λp.
      let t = g.d.twice {n= p.n} in
      let y = 'add' {'i32', t, [01000000]} in y,
  },
  c= {
    h= λp.
      let t = g.d.twice {n= p.n} in
      let y = 'add' {'i32', t, [02000000]} in y,
  },
  main= λp.
    let x = g.b.f {n= [01000000]} in
    let y = g.c.h {n= [01000000]} in
    let z = 'add' {'i32', x, y} in z,
}
"""


def test_make_reducible_of_diamond():
    with driver.session(str(GOLDENS)) as build:
        assert_gives(DIAMOND, DIAMOND_REDUCIBLE)
        build.check()
