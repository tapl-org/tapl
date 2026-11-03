# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The unit tools, `'unit.merge'` and `'unit.rebase'`, called as opcodes."""

import pytest

from oymo.oymomo import reduction, strategy
from oymo.oymomo.grammar import parse

FN = "{'function', {n = 'i32'}, 'i32'}"
OTHER_FN = "{'function', {n = 'i64'}, 'i64'}"
# A body that calls `m.lib.step` and ends in a region.
BODY = 'λm. λp. m [] (λr. {let y = m.lib.step {n = p.n} in y})'


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
    expected_body = 'λm. λp. m [] (λr. {let y = m.dbl.lib.step {n = p.n} in y})'
    assert_gives(f"'unit.rebase' {{{{'dbl'}}, {lib()}}}", f'{{dbl = {lib(expected_body)}}}')


def test_rebase_in_nested_regions_and_under_binders():
    body = 'λm. λp. m [] (λr. {e = λx. m [] (λq. {let y = m.lib.step {n = x} in m.lib.c})})'
    expected = 'λm. λp. m [] (λr. {e = λx. m [] (λq. {let y = m.a.b.lib.step {n = x} in m.a.b.lib.c})})'
    assert_gives(f"'unit.rebase' {{{{'a', 'b'}}, {lib(body)}}}", f'{{a = {{b = {lib(expected)}}}}}')


def test_rebase_copies_data_entries():
    extra = ", c = {type = 'i32', value = [01000000]}, h = {type = 'i32'}"
    expected_body = 'λm. λp. m [] (λr. {let y = m.x.lib.step {n = p.n} in y})'
    assert_gives(f"'unit.rebase' {{{{'x'}}, {lib(extra=extra)}}}", f'{{x = {lib(expected_body, extra)}}}')


def test_rebase_mounts_a_header():
    header = f"{{lib = {{step = {{type = {FN}, link = 'step'}}}}}}"
    assert_gives(f"'unit.rebase' {{{{'libc'}}, {header}}}", f'{{libc = {header}}}')


def test_rebase_with_an_empty_prefix_changes_nothing():
    assert_gives(f"'unit.rebase' {{{{}}, {lib()}}}", lib())


@pytest.mark.parametrize(
    'source',
    [
        # `m` used whole, not as the head of a path or a region.
        f"'unit.rebase' {{{{'x'}}, {lib('λm. λp. p m')}}}",
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
    other = lib('λm. λp. m [] (λr. {let y = m.lib.step {n = p.n} in [02000000]})')
    clash = f"'unit.merge' {{{lib()}, {other}}}"
    assert_no_step(clash)
    merged = normal(f"'unit.merge' {{{lib()}, 'unit.rebase' {{{{'dbl'}}, {other}}}}}")
    assert [f.label for f in merged.fields] == ['lib', 'dbl']
