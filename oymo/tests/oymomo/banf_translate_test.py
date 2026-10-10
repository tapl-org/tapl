# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import textwrap

import pytest

from oymo.oymomo import banf_terms, terms
from oymo.oymomo.banf_translate import TranslationError, translate
from oymo.oymomo.grammar import parse

I8, I16, I32 = (terms.name_to_form(name) for name in ('i8', 'i16', 'i32'))


def program(defs, decls):
    """A program whose `module` binder's form has the fields `decls` and whose body has the fields `defs`."""
    return f'prim -> module: {{{decls}}} -> {{{defs}}}'


def banf(defs, decls):
    return banf_terms.show(translate(parse(program(defs, decls))))


def text(block):
    """A triple-quoted block, dedented and without its leading newline."""
    return textwrap.dedent(block).removeprefix('\n')


def error(defs, decls):
    with pytest.raises(TranslationError) as info:
        translate(parse(program(defs, decls)))
    return info.value.message


FACT = """
fact = f -> {
  entry = args:{n = 'i32'} ->
    (t0 -> if t0 then f.then0 {} else f.else0 {n = args.n})
      (prim.eq_i32 {a = args.n, b = [00000000]:'i32'}),
  then0 = args:{} -> [01000000]:'i32',
  else0 = args:{n = 'i32'} ->
    (t1 -> (t2 -> (t3 -> t3) (prim.mul_i32 {a = args.n, b = t2}))
             (module.fact {n = t1}))
      (prim.sub_i32 {minuend = args.n, subtrahend = [01000000]:'i32'}),
}
"""


def test_simplest():
    assert banf("main = f -> {entry = args:{a = 'i32'} -> [00000000] : 'i32'}", "main = => 'i32'") == text("""
        main: i32
          entry(a: i32):
            return [00000000]:i32
    """)


def test_empty_params():
    assert banf("main = f -> {entry = args:{} -> [01]:'i8'}", "main = => 'i8'") == text("""
        main: i8
          entry():
            return [01]:i8
    """)


def test_param_is_an_atom():
    assert banf("id = f -> {entry = args:{n = 'i32'} -> args.n}", "id = => 'i32'") == text("""
        id: i32
          entry(n: i32):
            return n
    """)


def test_nested_projection_is_get_field_on_param():
    source = "get = f -> {entry = args:{p = {x = 'i32', y = 'i8'}} -> (x -> x) (args.p.x)}"
    assert banf(source, "get = => 'i32'") == text("""
        get: i32
          entry(p: {x: i32, y: i8}):
            x = p.x
            return x
    """)


def test_let_with_written_form():
    source = "g = f -> {entry = args:{n = 'i32'} -> (t0: 'i1' -> t0) (prim.eq_i32 {a = args.n, b = args.n})}"
    assert banf(source, "g = => 'i1'") == text("""
        g: i1
          entry(n: i32):
            t0: i1 = prim.eq_i32(n, n)
            return t0
    """)


def test_let_form_replaces_op_form():
    # A form is not a type: the written form isn't checked against the op's i1, it replaces it.
    source = "g = f -> {entry = args:{n = 'i32'} -> (t0: 'i32' -> t0) (prim.eq_i32 {a = args.n, b = args.n})}"
    assert banf(source, "g = => 'i32'") == text("""
        g: i32
          entry(n: i32):
            t0: i32 = prim.eq_i32(n, n)
            return t0
    """)


def test_let_form_must_be_a_literal():
    source = "g = f -> {entry = args:{n = 'i32'} -> (t0: args.n -> t0) (prim.eq_i32 {a = args.n, b = args.n})}"
    assert error(source, "g = => 'i1'") == "Let 't0': form must be a literal, got ($0.n)."


def test_call_with_struct_literal_and_forwarded_args():
    source = """
    add = f -> {entry = args:{a = 'i32', b = 'i32'} -> (s -> s) (prim.add_i32 {a = args.a, b = args.b})},
    twice = f -> {entry = args:{a = 'i32', b = 'i32'} -> (t0 -> f.next {a = t0, b = args.b}) (module.add args),
                  next = args:{a = 'i32', b = 'i32'} -> (t1 -> t1) (module.add {a = args.a, b = args.b})},
    """
    assert banf(source, "add = => 'i32', twice = => 'i32'") == text("""
        add: i32
          entry(a: i32, b: i32):
            s = prim.add_i32(a, b)
            return s

        twice: i32
          entry(a: i32, b: i32):
            t0 = add(a, b)
            jump next(t0, b)
          next(a: i32, b: i32):
            t1 = add(a, b)
            return t1
    """)


def test_jump_forwards_args():
    source = "g = f -> {entry = args:{n = 'i8'} -> f.body args, body = args:{n = 'i8'} -> args.n}"
    assert banf(source, "g = => 'i8'") == text("""
        g: i8
          entry(n: i8):
            jump body(n)
          body(n: i8):
            return n
    """)


def test_prim_labels():
    source = "g = f -> {entry = args:{n = 'i32'} -> (t -> t) (prim.sub_i32 {minuend = args.n, subtrahend = args.n})}"
    assert 'prim.sub_i32(n, n)' in banf(source, "g = => 'i32'")


def test_prim_wrong_labels():
    source = "g = f -> {entry = args:{n = 'i32'} -> (t -> t) (prim.sub_i32 {a = args.n, b = args.n})}"
    assert error(source, "g = => 'i32'") == 'prim.sub_i32 takes {minuend, subtrahend}, got {a, b}.'


def test_prim_wrong_width():
    source = "g = f -> {entry = args:{n = 'i8'} -> (t -> t) (prim.add_i32 {a = args.n, b = [00000000]:'i32'})}"
    assert error(source, "g = => 'i32'") == 'prim.add_i32 expects a: i32, got i8.'


def test_conversion():
    source = "g = f -> {entry = args:{n = 'i8'} -> (t -> t) (prim.zext_i8_i32 {value = args.n})}"
    assert banf(source, "g = => 'i32'") == text("""
        g: i32
          entry(n: i8):
            t = prim.zext_i8_i32(n)
            return t
    """)


def test_struct_built_and_read():
    source = "g = f -> {entry = args:{n = 'i8'} -> (s -> (y -> y) (s.y)) ({x = args.n, y = [01]:'i8'})}"
    assert banf(source, "g = => 'i8'") == text("""
        g: i8
          entry(n: i8):
            s = {x = n, y = [01]:i8}
            y = s.y
            return y
    """)


def test_fact():
    assert banf(FACT, "fact = => 'i32'") == text("""
        fact: i32
          entry(n: i32):
            t0 = prim.eq_i32(n, [00000000]:i32)
            branch t0, then0(), else0(n)
          then0():
            return [01000000]:i32
          else0(n: i32):
            t1 = prim.sub_i32(n, [01000000]:i32)
            t2 = fact(t1)
            t3 = prim.mul_i32(n, t2)
            return t3
    """)


def test_recursion_needs_no_let_form():
    # The return form is declared, so a block that only returns a recursive call needs nothing more.
    source = """
    loop = f -> {
      entry = args:{c = 'i1'} -> if args.c then f.a {} else f.b {},
      a = args:{} -> (t -> t) (module.loop {c = [00]:'i1'}),
      b = args:{} -> [07]:'i8',
    }
    """
    assert banf(source, "loop = => 'i8'").startswith('loop: i8\n')
    assert banf('g = f -> {entry = args:{} -> (t -> t) (module.g {})}', "g = => 'i8'") == text("""
        g: i8
          entry():
            t = g()
            return t
    """)


def test_return_form_is_declared():
    assert error("g = f -> {entry = args:{} -> [01]:'i8'}", "g = => 'i32'") == "Function 'g' returns i32, got i8."


def test_explicit_join_block():
    source = """
    pick = f -> {
      entry = args:{c = 'i1', x = 'i32', y = 'i32', z = 'i32'} ->
        if args.c then f.then0 {x = args.x, z = args.z} else f.else0 {y = args.y, z = args.z},
      then0 = args:{x = 'i32', z = 'i32'} -> f.join0 {v = args.x, z = args.z},
      else0 = args:{y = 'i32', z = 'i32'} -> f.join0 {v = args.y, z = args.z},
      join0 = args:{v = 'i32', z = 'i32'} -> (t0 -> t0) (prim.add_i32 {a = args.v, b = args.z}),
    }
    """
    assert banf(source, "pick = => 'i32'") == text("""
        pick: i32
          entry(c: i1, x: i32, y: i32, z: i32):
            branch c, then0(x, z), else0(y, z)
          then0(x: i32, z: i32):
            jump join0(x, z)
          else0(y: i32, z: i32):
            jump join0(y, z)
          join0(v: i32, z: i32):
            t0 = prim.add_i32(v, z)
            return t0
    """)


def test_first_block_is_entry_whatever_its_name():
    source = "g = f -> {start = args:{n = 'i8'} -> f.done args, done = args:{n = 'i8'} -> args.n}"
    assert banf(source, "g = => 'i8'") == text("""
        g: i8
          start(n: i8):
            jump done(n)
          done(n: i8):
            return n
    """)


def test_lets_repeating_a_param_label_are_renamed():
    source = """
    g = f -> {entry = args:{n = 'i8'} ->
      (n -> (n -> n) (prim.mul_i8 {a = n, b = n})) (prim.add_i8 {a = args.n, b = args.n})}
    """
    assert banf(source, "g = => 'i8'") == text("""
        g: i8
          entry(n: i8):
            n_4 = prim.add_i8(n, n)
            n_5 = prim.mul_i8(n_4, n_4)
            return n_5
    """)


def test_repeated_let_is_renamed():
    source = """
    g = f -> {entry = args:{n = 'i8'} ->
      (t -> (t -> t) (prim.add_i8 {a = t, b = t})) (prim.add_i8 {a = args.n, b = args.n})}
    """
    assert banf(source, "g = => 'i8'") == text("""
        g: i8
          entry(n: i8):
            t = prim.add_i8(n, n)
            t_5 = prim.add_i8(t, t)
            return t_5
    """)


def test_atom_let_is_substituted():
    assert banf("g = f -> {entry = args:{n = 'i8'} -> (t -> t) (args.n)}", "g = => 'i8'") == text("""
        g: i8
          entry(n: i8):
            return n
    """)


def test_let_bound_if_is_substituted_into_tail():
    source = """
    g = f -> {entry = args:{c = 'i1'} -> (t -> t) (if args.c then f.a {} else f.b {}),
              a = args:{} -> [01]:'i8', b = args:{} -> [02]:'i8'}
    """
    assert banf(source, "g = => 'i8'") == text("""
        g: i8
          entry(c: i1):
            branch c, a(), b()
          a():
            return [01]:i8
          b():
            return [02]:i8
    """)


@pytest.mark.parametrize(
    ('defs', 'message'),
    [
        (
            "g = f -> {entry = args:{n = 'i32'} -> (t -> t) (prim.add_i32 {a = prim.add_i32 {a = args.n, b = args.n}, "
            'b = args.n})}',
            'Expected an atom: a byte array, a let name, or args.label.',
        ),
        (
            "g = f -> {entry = args:{n = 'i32'} -> prim.add_i32 {a = args.n, b = args.n}}",
            'An op in tail position must be bound by a let, as in let t = op in t.',
        ),
        (
            "g = f -> {entry = args:{c = 'i1'} -> if args.c then [01]:'i8' else f.b {}, b = args:{} -> [01]:'i8'}",
            'Both branches of an if must be jumps, such as blocks.then0 {}.',
        ),
        (
            'g = f -> {entry = args:{} -> f.b {}, b = args:{} -> f.entry {}}',
            'Cannot jump to the entry block.',
        ),
        (
            "g = f -> {entry = args:{c = 'i1'} -> if args.c then f.b {} else f.b {}, b = args:{} -> [01]:'i8'}",
            'Both branches of an if jump to the same block.',
        ),
        ('g = f -> {entry = args:{} -> f.nowhere {}}', "Unknown block 'nowhere'."),
        ('g = f -> {entry = args:{} -> f}', "'blocks' cannot be used as a value."),
        ('g = f -> {entry = args:{} -> args}', "'args' cannot be used as a value."),
        ('g = f -> {entry = args:{} -> (t -> t) (prim)}', "'prim' cannot be used as a value."),
        ('g = f -> {entry = args:{} -> (t -> t) (module)}', "'module' cannot be used as a value."),
        (
            'g = f -> {entry = args:{} -> (t -> t) (fix module)}',
            'Expected an op: prim.op {...}, module.f {...}, module.data, a struct or a projection.',
        ),
        ('g = f -> {entry = args:{} -> (t -> t) (module.g)}', 'module.g must be applied.'),
        ('g = f -> {entry = args:{} -> (t -> t) (prim.add_i8)}', 'prim.add_i8 must be applied.'),
        (
            "g = args:{} -> [01]:'i8'",
            "Definition 'g' must be a struct of blocks, such as blocks -> {entry = args: {} -> ...}.",
        ),
        (
            "g = f -> {entry = n:'i8' -> n}",
            "Block 'entry' must be a lambda taking a struct, such as args: {n = 'i32'} -> ...",
        ),
        ('g = f -> {entry = args:{} -> args.n}', "Block has no param 'n'."),
        ('g = f -> {entry = args:{} -> [01]}', 'Byte array: form must be written.'),
        ('g = f -> {entry = args:{} -> (t -> t) (module.h {})}', "'h' is not declared."),
        ('g = f -> {entry = args:{} -> (t -> t) (prim.add {})}', "Unknown prim op 'add'."),
        (
            "g = f -> {entry = args:{} -> [01]:'i8'}, g = f -> {entry = args:{} -> [01]:'i8'}",
            "Duplicate definition 'g'.",
        ),
    ],
)
def test_shape_errors(defs, message):
    assert error(defs, "g = => 'i8'") == message


def test_branch_condition_must_be_i1():
    source = "g = f -> {entry = args:{c = 'i8'} -> if args.c then f.a {} else f.b {}, a = args:{} -> [01]:'i8', b = args:{} -> [01]:'i8'}"
    assert error(source, "g = => 'i8'") == 'Branch condition must be i1, got i8.'


def test_error_location_points_at_source():
    source = program('g = f -> {entry = args:{} -> f.nowhere {}}', "g = => 'i8'")
    with pytest.raises(TranslationError) as info:
        translate(parse(source))
    location = info.value.location
    assert source[location.start : location.end] == 'f.nowhere {}'


DECLS = "putchar = {c = 'i8'} => 'i32', errno = 'i32', cfg = {w = 'i16', h = 'i16'}, main = => 'i32'"


def test_imports():
    source = """
    main = f -> {entry = args:{} ->
      (t0 -> (t1 -> (c -> (w -> t0) (c.w)) (module.cfg)) (module.errno)) (module.putchar {c = [41]:'i8'})},
    """
    module = translate(parse(program(source, DECLS)))
    assert module.bindings[:3] == [
        banf_terms.Signature('putchar', [('c', I8)], I32),
        banf_terms.Data('errno', I32),
        banf_terms.Data('cfg', terms.Struct([terms.Field('w', I16), terms.Field('h', I16)])),
    ]
    assert banf_terms.show(module) == text("""
        putchar(c: i8): i32
        errno: i32
        cfg: {w: i16, h: i16}

        main: i32
          entry():
            t0 = putchar([41]:i8)
            t1 = errno
            c = cfg
            w = c.w
            return t0
    """)


def test_bindings_are_in_declaration_order():
    source = "main = f -> {entry = args:{} -> (t -> t) (module.putchar {c = [41]:'i8'})}"
    assert banf(source, "main = => 'i32', putchar = {c = 'i8'} => 'i32', errno = 'i32'") == text("""
        main: i32
          entry():
            t = putchar([41]:i8)
            return t

        putchar(c: i8): i32
        errno: i32
    """)


MAIN = "main = f -> {entry = args:{} -> [01]:'i8'}"


@pytest.mark.parametrize(
    ('defs', 'decls', 'message'),
    [
        (
            "main = f -> {entry = args:{} -> (t -> t) (module.putchar {x = [41]:'i8'})}",
            DECLS,
            'module.putchar takes {c}, got {x}.',
        ),
        (
            'main = f -> {entry = args:{} -> (t -> t) (module.putchar)}',
            DECLS,
            'module.putchar must be applied.',
        ),
        (
            'main = f -> {entry = args:{} -> (t -> t) (module.errno {})}',
            DECLS,
            'module.errno is data, so it cannot be applied.',
        ),
        (
            MAIN,
            "main = => 'i8', libc = {putchar = {c = 'i8'} => 'i32'}",
            "Declaration 'libc': function forms nested inside other forms are not supported.",
        ),
        (
            MAIN,
            "main = => 'i8', g = {c = 'i8'} => {d = 'i8'} => 'i32'",
            "Declaration 'g': function forms nested inside other forms are not supported.",
        ),
        (
            MAIN,
            "main = => => 'i8'",
            "Declaration 'main': function forms nested inside other forms are not supported.",
        ),
        (
            MAIN,
            "main = => 'i8', g = 'i8' => 'i32'",
            "Declaration 'g': a function form needs a struct form as its param.",
        ),
        (MAIN, "main = => 'i8', g = (prim)", "Declaration 'g': form must be a literal, got ($0)."),
        (MAIN, "main = => 'i8', main = => 'i8'", "Duplicate declaration 'main'."),
        (MAIN, '', "'main' is defined but not declared."),
        (MAIN, "main = => 'i8', g = => 'i8'", "'g' declares no params, so it must be defined."),
        (
            MAIN,
            "main = {} => 'i8'",
            "'main' declares its params; a definition takes them from its entry block.",
        ),
        (MAIN, "main = 'i8'", "'main' is declared as data; data cannot be defined yet."),
    ],
)
def test_module_errors(defs, decls, message):
    assert error(defs, decls) == message


def test_forms_must_be_literals():
    assert error("main = f -> {entry = args: {n = (prim)} -> [01]:'i8'}", "main = => 'i8'") == (
        "Block 'entry': form must be a literal, got ($2)."
    )
    assert error('main = f -> {entry = args: {} -> [01]: (prim)}', "main = => 'i8'") == (
        'Byte array: form must be a literal, got ($3).'
    )


def test_form_must_be_known():
    assert error('main = f -> {entry = args: {} -> [01]}', "main = => 'i8'") == 'Byte array: form must be written.'


def test_program_shape_errors():
    with pytest.raises(TranslationError, match='Expected a program of the shape'):
        translate(parse('prim -> {}'))
    with pytest.raises(TranslationError, match='needs a struct form'):
        translate(parse('prim -> module -> {}'))


def test_program_binders_are_renamed():
    assert translate(parse('p -> m: {} -> {}')).bindings == []


def test_formed_byte_array_is_a_constant():
    assert banf("main = f -> {entry = args:{} -> [2a]:'i8'}", "main = => 'i8'") == text("""
        main: i8
          entry():
            return [2a]:i8
    """)


def test_formed_atom_has_the_written_form():
    # A form is not a type: the written form replaces the atom's form, unchecked.
    assert banf("main = f -> {entry = args:{n = 'i8'} -> args.n:'i32'}", "main = => 'i32'") == text("""
        main: i32
          entry(n: i8):
            return n:i32
    """)
    assert banf("main = f -> {entry = args:{} -> ([2a]:'i8'):'i16'}", "main = => 'i16'") == text("""
        main: i16
          entry():
            return [2a]:i16
    """)


def test_formed_let_name():
    source = "main = f -> {entry = args:{n = 'i32'} -> let t = prim.add_i32 {a = args.n, b = args.n} in t:'i8'}"
    assert banf(source, "main = => 'i8'") == text("""
        main: i8
          entry(n: i32):
            t = prim.add_i32(n, n)
            return t:i8
    """)


def test_let_with_a_form_and_an_atom_reduces_to_a_formed_atom():
    # The let isn't an op, so it's beta-reduced, and beta carries its form: args.n : 'i32'.
    source = "main = f -> {entry = args:{n = 'i32'} -> let m: 'i32' = args.n in m}"
    assert banf(source, "main = => 'i32'") == text("""
        main: i32
          entry(n: i32):
            return n:i32
    """)


@pytest.mark.parametrize(
    ('defs', 'message'),
    [
        (
            "main = f -> {entry = args:{} -> [2a]:'i8' => 'i8'}",
            'Byte array: function forms nested inside other forms are not supported.',
        ),
    ],
)
def test_formed_errors(defs, message):
    assert error(defs, "main = => 'i8'") == message
