# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import textwrap

from oymo.oymomo import banf_rename, bruijn
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show


def renamed(source):
    return banf_rename.rename(bruijn.resolve(parse(source)))


def pretty(source):
    return show(renamed(source), pretty=True, name_indices=True, width=200)


def program(defs):
    return f'module: {{}} -> {{{defs}}}'


def body(source, params="{n = 'i8'}"):
    """The pretty-printed body of the one block of `main`, after renaming."""
    text = pretty(program(f'main = f -> {{entry = args: {params} -> {source}}}'))
    pretty_params = params.replace(' = ', '= ')
    prefix = f'module: {{}} → {{main= blocks → {{entry= args: {pretty_params} → '
    assert text.startswith(prefix), text
    return text.removeprefix(prefix).removesuffix('}}')


def test_fresh():
    assert banf_rename.fresh('t', 6, set()) == 't'
    assert banf_rename.fresh('t', 6, {'t'}) == 't_6'
    assert banf_rename.fresh('t', 7, {'t', 't_7'}) == 't__7'


def test_structural_binders_get_fixed_names():
    assert pretty("m: {} -> {main = b -> {entry = x: {} -> [01]: 'i8'}}") == (
        "module: {} → {main= blocks → {entry= args: {} → [01]: 'i8'}}"
    )


def test_references_follow_their_binders():
    source = "m: {} -> {main = b -> {entry = x: {n = 'i8'} -> let t = $add_i8 {a = x.n, b = x.n} in b.next t}}"
    assert pretty(source) == (
        "module: {} → {main= blocks → {entry= args: {n= 'i8'} → "
        'let t = $add_i8 {a= args.n, b= args.n} in blocks.next t}}'
    )


def test_a_let_that_clashes_with_nothing_keeps_its_name():
    assert body('let t = {n = args.m} in t', "{m = 'i8'}") == 'let t = {n= args.m} in t'
    assert body('let entry = {} in entry') == 'let entry = {} in entry'


def test_repeated_lets():
    assert body('let t = {} in let t = {a = t} in let t = {b = t} in t') == (
        'let t = {} in let t_4 = {a= t} in let t_5 = {b= t_4} in t_5'
    )


def test_lets_repeating_a_param_label():
    assert body('let n = {a = args.n} in let n = {b = n} in n') == 'let n_3 = {a= args.n} in let n_4 = {b= n_3} in n_4'


def test_lets_named_after_fixed_names():
    assert body('let args = {} in args') == 'let args_3 = {} in args_3'
    assert body('let blocks = {} in blocks') == 'let blocks_3 = {} in blocks_3'
    assert body('let module = {} in module') == 'let module_3 = {} in module_3'
    # `prim` is no longer a binder, so it is a plain name.
    assert body('let prim = {} in prim') == 'let prim = {} in prim'


def test_sibling_blocks_both_keep_their_names():
    source = program('main = f -> {entry = args: {} -> let t = {} in t, next = args: {} -> let t = {} in t}')
    assert pretty(source) == (
        'module: {} → {main= blocks → {entry= args: {} → let t = {} in t, next= args: {} → let t = {} in t}}'
    )


def test_user_names_that_look_renamed():
    assert body('let t = {} in let t = {a = t} in let t_4 = {b = t} in t_4') == (
        'let t = {} in let t_4 = {a= t} in let t_4_5 = {b= t_4} in t_4_5'
    )
    assert body('let t = {} in let t_5 = {a = t} in let t = {b = t_5} in t') == (
        'let t = {} in let t_5 = {a= t} in let t__5 = {b= t_5} in t__5'
    )


def test_param_labels_are_never_renamed():
    assert body('let args = {n = args.n} in args.n') == 'let args_3 = {n= args.n} in args_3.n'


def test_unshaped_position_keeps_or_suffixes():
    assert pretty(program('main = (b -> {}) {}')) == 'module: {} → {main= let b = {} in {}}'
    assert pretty(program('main = (module -> {}) {}')) == 'module: {} → {main= let module_1 = {} in {}}'


def test_a_second_run_changes_nothing():
    source = program("""
    main = f -> {
      entry = args: {n = 'i8'} ->
        let n = {a = args.n} in let t = {b = n} in let t = {c = t} in let t_6 = {d = t} in f.next t_6,
      next = args: {} -> [01]: 'i8',
    }
    """)
    once = renamed(source)
    twice = banf_rename.rename(once)
    assert show(twice) == show(once)
    assert show(twice, pretty=True, name_indices=True) == show(once, pretty=True, name_indices=True)


def test_shows_as_source():
    source = program("main = f -> {entry = args: {n = 'i8'} -> let n = $add_i8 {a = args.n, b = args.n} in n}")
    assert show(renamed(source), pretty=True, name_indices=True, width=60) == textwrap.dedent("""\
        module: {} → {
          main= blocks → {
            entry= args: {n= 'i8'} →
              let n_3 = $add_i8 {a= args.n, b= args.n} in n_3,
          },
        }""")
