# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import textwrap

from oymo.oymomo import banf_rename, bruijn
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show


def renamed(source):
    return banf_rename.rename(bruijn.resolve(parse(source)))


def pretty(source):
    return show(renamed(source), pretty=True, name_indices=True)


def program(defs):
    return f'module: {{}} -> {{{defs}}}'


def block(source, params="{n = 'i8'}"):
    """The pretty-printed program whose `main` has one block, `entry`, after renaming."""
    return pretty(program(f'main = f -> {{entry = args: {params} -> {source}}}'))


def dedent(text):
    return textwrap.dedent(text).strip('\n')


def test_fresh():
    assert banf_rename.fresh('t', 6, set()) == 't'
    assert banf_rename.fresh('t', 6, {'t'}) == 't_6'
    assert banf_rename.fresh('t', 7, {'t', 't_7'}) == 't__7'


def test_structural_binders_get_fixed_names():
    assert pretty("m: {} -> {main = b -> {entry = x: {} -> [01]: 'i8'}}") == (
        "module: {} → {main= blocks → {entry= args: {} → [01]: 'i8'}}"
    )


def test_references_follow_their_binders():
    source = "m: {} -> {main = b -> {entry = x: {n = 'i8'} -> let t = 'add' {'i8', x.n, x.n} in b.next t}}"
    assert pretty(source) == dedent("""
        module: {} → {
          main= blocks → {
            entry= args: {n= 'i8'} →
              let t = 'add' {'i8', args.n, args.n} in blocks.next t,
          },
        }
    """)


def test_a_let_that_clashes_with_nothing_keeps_its_name():
    assert block('let t = {n = args.m} in t', "{m = 'i8'}") == dedent("""
        module: {} → {
          main= blocks → {entry= args: {m= 'i8'} → let t = {n= args.m} in t},
        }
    """)
    assert block('let entry = {} in entry') == (
        "module: {} → {main= blocks → {entry= args: {n= 'i8'} → let entry = {} in entry}}"
    )


def test_repeated_lets():
    assert block('let t = {} in let t = {a = t} in let t = {b = t} in t') == dedent("""
        module: {} → {
          main= blocks → {
            entry= args: {n= 'i8'} →
              let t = {} in
              let t_4 = {a= t} in
              let t_5 = {b= t_4} in t_5,
          },
        }
    """)


def test_lets_repeating_a_param_label():
    assert block('let n = {a = args.n} in let n = {b = n} in n') == dedent("""
        module: {} → {
          main= blocks → {
            entry= args: {n= 'i8'} →
              let n_3 = {a= args.n} in
              let n_4 = {b= n_3} in n_4,
          },
        }
    """)


def test_lets_named_after_fixed_names():
    for name in ('args', 'blocks', 'module'):
        assert block(f'let {name} = {{}} in {name}') == dedent(f"""
            module: {{}} → {{
              main= blocks → {{entry= args: {{n= 'i8'}} → let {name}_3 = {{}} in {name}_3}},
            }}
        """)
    # `prim` is no longer a binder, so it is a plain name.
    assert block('let prim = {} in prim') == (
        "module: {} → {main= blocks → {entry= args: {n= 'i8'} → let prim = {} in prim}}"
    )


def test_sibling_blocks_both_keep_their_names():
    source = program('main = f -> {entry = args: {} -> let t = {} in t, next = args: {} -> let t = {} in t}')
    assert pretty(source) == dedent("""
        module: {} → {
          main= blocks → {
            entry= args: {} → let t = {} in t,
            next= args: {} → let t = {} in t,
          },
        }
    """)


def test_user_names_that_look_renamed():
    assert block('let t = {} in let t = {a = t} in let t_4 = {b = t} in t_4') == dedent("""
        module: {} → {
          main= blocks → {
            entry= args: {n= 'i8'} →
              let t = {} in
              let t_4 = {a= t} in
              let t_4_5 = {b= t_4} in t_4_5,
          },
        }
    """)
    assert block('let t = {} in let t_5 = {a = t} in let t = {b = t_5} in t') == dedent("""
        module: {} → {
          main= blocks → {
            entry= args: {n= 'i8'} →
              let t = {} in
              let t_5 = {a= t} in
              let t__5 = {b= t_5} in t__5,
          },
        }
    """)


def test_param_labels_are_never_renamed():
    assert block('let args = {n = args.n} in args.n') == dedent("""
        module: {} → {
          main= blocks → {entry= args: {n= 'i8'} → let args_3 = {n= args.n} in args_3.n},
        }
    """)


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
    source = program("main = f -> {entry = args: {n = 'i8'} -> let n = 'add' {'i8', args.n, args.n} in n}")
    assert show(renamed(source), pretty=True, name_indices=True, width=60) == textwrap.dedent("""\
        module: {} → {
          main= blocks → {
            entry= args: {n= 'i8'} →
              let n_3 = 'add' {'i8', args.n, args.n} in n_3,
          },
        }""")
