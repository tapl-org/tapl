# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""LLVM translation."""

import textwrap

import pytest
from llvmlite import binding

from oymo.oymomo import ingot, llvm_opcodes, llvm_translate
from oymo.oymomo.grammar import parse

TARGET = llvm_translate.Target(llvm_opcodes.DEFAULT_OPCODES)

GCD = """
{
  gcd = {type = {'function', {a = 'i32', b = 'i32'}, 'i32'},
    body = λg. λp. 'R' (λr. {
      entry = r.loop p.a p.b,
      loop = λa. λb.
        let z = 'icmp' {'eq', 'i32', b, [00000000]} in
        'R' (λq. {
          if z then r.done a else q.step,
          step = let c = 'urem' {'i32', a, b} in r.loop b c
        }),
      done = λc. c
    })},
  main = {type = {'function', {}, 'i32'}, link = 'main',
    body = λg. λp. 'R' (λr. {entry = let y = g.gcd {a = [30000000], b = [12000000]} in y})}
}
"""


def llvm(source):
    """The LLVM IR of `source`, checked by LLVM's own verifier."""
    ir_module = llvm_translate.translate(ingot.ingot_of(parse(source)), TARGET)
    text = str(ir_module)
    binding.parse_assembly(text).verify()
    return text


def function(text, name):
    """The `define` of `@name` in `text`."""
    start = text.index(f'@"{name}"(')
    start = text.rindex('define', 0, start)
    return text[start : text.index('\n}', start) + 2] + '\n'


def error(source):
    with pytest.raises(llvm_translate.LlvmTranslationError) as info:
        llvm(source)
    return info.value.message


def single(blocks, params='{}', result="'i32'", extra=''):
    """An ingot with one function `main`, whose region holds `blocks`."""
    return f"""{{
      {extra}
      main = {{type = {{'function', {params}, {result}}}, link = 'main', body = λg. λp. 'R' (λr. {{{blocks}}})}},
    }}"""


def test_gcd():
    """One block per block, `phi`s for parameters, bound names made distinct."""
    text = llvm(GCD)
    assert function(text, 'gcd') == textwrap.dedent("""\
        define internal i32 @"gcd"(i32 %"p.a", i32 %"p.b")
        {
        r.entry:
          br label %"r.loop"
        r.loop:
          %"a" = phi  i32 [%"p.a", %"r.entry"], [%"b", %"q.step"]
          %"b" = phi  i32 [%"p.b", %"r.entry"], [%"c", %"q.step"]
          %"z" = icmp eq i32 %"b", 0
          br i1 %"z", label %"r.done", label %"q.step"
        q.step:
          %"c" = urem i32 %"a", %"b"
          br label %"r.loop"
        r.done:
          %"c1" = phi  i32 [%"a", %"r.loop"]
          ret i32 %"c1"
        }
        """)
    assert function(text, 'main') == textwrap.dedent("""\
        define i32 @"main"()
        {
        r.entry:
          %"y" = call i32 @"gcd"(i32 48, i32 18)
          ret i32 %"y"
        }
        """)


def test_example():
    """A nested region's field 0 goes on in the block it continues."""
    source = """
    {
      puts = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'puts'},
      msg = {type = {'array', [03], 'i8'}, value = [686900]},
      main = {type = {'function', {argc = 'i32'}, 'i32'}, link = 'main',
        body = λg. λp. 'R' (λr. {
          entry =
            let c = 'icmp' {'sgt', 'i32', p.argc, [01000000]} in
            'R' (λq. {
              if c then q.say else r.done,
              say = let u = g.puts {s = g.msg} in r.done
            }),
          done = [00000000]
        })}
    }
    """
    text = llvm(source)
    assert '@"msg" = internal constant [3 x i8] c"hi\\00"' in text
    assert 'declare i32 @"puts"(ptr %"s")' in text
    assert function(text, 'main') == textwrap.dedent("""\
        define i32 @"main"(i32 %"p.argc")
        {
        r.entry:
          %"c" = icmp sgt i32 %"p.argc", 1
          br i1 %"c", label %"q.say", label %"r.done"
        q.say:
          %"u" = call i32 @"puts"(ptr @"msg")
          br label %"r.done"
        r.done:
          ret i32 0
        }
        """)


def test_switch():
    """Arm i is case i, the last arm the default."""
    blocks = '{r.a, r.b, r.c} p.k, a = [01000000], b = [02000000], c = [03000000]'
    text = function(llvm(single(blocks, params="{k = 'i8'}")), 'main')
    assert 'switch i8 %"p.k", label %"r.c" [i8 0, label %"r.a" i8 1, label %"r.b"]' in text


def test_two_arms_on_a_wide_condition_switch():
    blocks = '{r.a, r.b} p.c, a = [01000000], b = [02000000]'
    text = function(llvm(single(blocks, params="{c = 'i32'}")), 'main')
    assert 'switch i32 %"p.c", label %"r.b" [i32 0, label %"r.a"]' in text


def test_one_arm_is_a_jump():
    text = function(llvm(single('{r.a} p.c, a = [01000000]', params="{c = 'i1'}")), 'main')
    assert 'r.0:\n  br label %"r.a"' in text


def test_two_arms_to_one_block():
    """With the same operands, one incoming value per arm; else rejected."""
    blocks = "{r.done [00000000], r.done [00000000]} p.c, done = λx. let y = 'add' {'i32', x, x} in y"
    text = function(llvm(single(blocks, params="{c = 'i1'}")), 'main')
    assert 'br i1 %"p.c", label %"r.done", label %"r.done"' in text
    assert 'phi  i32 [0, %"r.0"], [0, %"r.0"]' in text
    different = blocks.replace('r.done [00000000]}', 'r.done [01000000]}')
    assert error(single(different, params="{c = 'i1'}")) == (
        'Two arms jump to r.done with different operands; they must pass the same operands.'
    )


def test_parameter_types():
    """A parameter takes the type of the operands jumped to it and of its uses."""
    # From a use only: `x` gets only byte arrays, and `'add'` reads it at i64.
    blocks = (
        "r.done [01000000 00000000], done = λx. let y = 'add' {'i64', x, x} in let z = 'trunc' {'i64', y, 'i32'} in z"
    )
    assert 'phi  i64 [1, %"r.0"]' in llvm(single(blocks))
    # From the function's result, through a return.
    assert 'phi  i32 [7, %"r.0"]' in llvm(single('r.done [07000000], done = λx. x'))
    # An unused parameter with no type has no phi.
    assert 'phi' not in llvm(single('r.done [07], done = λx. [00000000]'))
    assert error(
        single(
            'r.done [07], done = λx. let y = g.f {a = x} in [00000000]',
            extra="f = {type = {'function', {a = 'ptr'}, 'i32'}, link = 'f'},",
        )
    ) == ('No constant of type ptr is written [07].')
    assert error(single("r.done p.a, done = λx. let y = 'add' {'i32', x, x} in y", params="{a = 'i8'}")) == (
        "'x' gets two types, i8 and i32: give 'x' one typed argument or typed use."
    )
    # Only a branch condition, given byte arrays: their length gives the type.
    assert 'phi  i8 [0, %"r.0"]' in llvm(single('r.done [00], done = λx. {r.a, r.a} x, a = [00000000]'))
    # Byte arrays of two lengths, or of a length with no type, give none.
    assert error(single('r.done [00], done = λx. {r.a, r.a} x, a = [00000000]'.replace('[00],', '[000000],'))) == (
        "give 'x' a typed argument or a typed use."
    )


def test_a_byte_arrays_length_gives_its_type():
    """Where nothing gives a parameter a type, the length of its byte-array operands does."""
    switch = 'r.check [03000000], check = λc. {r.a, r.b, r.c} c, a = [00000000], b = [00000000], c = [00000000]'
    text = llvm(single(switch))
    assert 'phi  i32 [3, %"r.0"]' in text
    assert 'switch i32 %"c"' in text
    for operand in ('[01]', '[0100]', '[01000000]', '[0100000000000000]'):
        width = 8 * (len(operand) - 2) // 2
        blocks = f'r.check {operand}, check = λc. {{r.a, r.b}} c, a = [00000000], b = [00000000]'
        assert f'phi  i{width} [1, %"r.0"]' in llvm(single(blocks))
    # Two lengths.
    two = (
        "let k = 'icmp' {'eq', 'i32', [00000000], [00000000]} in {r.one, r.two} k, "
        'one = r.check [01], two = r.check [01000000], check = λc. {r.a, r.b} c, a = [00000000], b = [00000000]'
    )
    assert error(single(two)) == "give 'c' a typed argument or a typed use."
    # A real type comes first: p.a is an i8, so [03000000] has the wrong size.
    first = (
        "let k = 'icmp' {'eq', 'i8', p.a, p.a} in {r.one, r.two} k, "
        'one = r.check p.a, two = r.check [03000000], check = λc. {r.a, r.b} c, a = [00000000], b = [00000000]'
    )
    assert error(single(first, params="{a = 'i8'}")) == 'A constant of type i8 is a byte array of 1 bytes.'


def test_symbols():
    """Symbols and their initializers."""
    source = """
    {
      puts = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'puts'},
      errno = {type = 'i32', link = 'errno'},
      answer = {type = 'i32', value = [2a000000]},
      counter = {type = 'i32', init = [29000000], link = 'counter'},
      pair = {type = {'i8', 'i16'}, value = {[01], [0200]}, link = 'pair'},
      table = {type = {'array', [03], 'i8'}, init = {[01], [02], [03]}},
      text = {type = {'array', [03], 'i8'}, value = 'ab' },
      none = {type = 'ptr', init = ''},
      zeros = {type = {'i32', 'ptr'}, init = {}},
      main = {type = {'function', {}, 'i32'}, link = 'main', body = λg. λp. 'R' (λr. {
        let u = 'store' {'i32', [05000000], g.counter} in
        let x = 'load' {'i32', g.answer} in
        let e = 'load' {'i32', g.errno} in
        let y = g.puts {s = g.answer} in
        x
      })},
    }
    """
    with pytest.raises(llvm_translate.LlvmTranslationError, match=r'\[3 x i8\] is a byte array of 3 bytes here'):
        llvm(source)
    source = source.replace("'ab' ", '[616200]')
    text = llvm(source)
    for line in [
        'declare i32 @"puts"(ptr %"s")',
        '@"errno" = external global i32',
        '@"answer" = internal constant i32 42',
        '@"counter" = global i32 41',
        '@"pair" = constant {i8, i16} {i8 1, i16 2}',
        '@"table" = internal global [3 x i8] [i8 1, i8 2, i8 3]',
        '@"text" = internal constant [3 x i8] c"ab\\00"',
        '@"none" = internal global ptr null',
        '@"zeros" = internal global {i32, ptr} zeroinitializer',
    ]:
        assert line in text, line
    main = function(text, 'main')
    assert 'store i32 5, ptr @"counter"' in main
    assert '%"x" = load i32, ptr @"answer"' in main
    assert '%"y" = call i32 @"puts"(ptr @"answer")' in main


@pytest.mark.parametrize('value', ["'counter'", "{'counter', [01]}", "{''}", 'λg. {g.counter}'])
def test_ptr_in_an_initializer(value):
    """In an init or value, a `'ptr'` is `''`, the null pointer, or an address under λg."""
    source = single(
        '[00000000]', extra=f"counter = {{type = 'i32', init = [00000000]}}, here = {{type = 'ptr', value = {value}}},"
    )
    assert error(source) == "A 'ptr' in an init or value is '', the null pointer, or an address g.l₁ ⋯ lₙ under λg."


def test_addresses_in_initializers():
    """An address in an init or value λg. C is the symbol's global: a variable, a constant,
    a function or a declaration."""
    text = llvm(
        single(
            '[00000000]',
            extra="""
            hello = {type = {'array', [03], 'i8'}, value = [686900]},
            puts = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'puts'},
            names = {type = {'array', [02], 'ptr'}, value = λg. {g.hello, g.ns.bye}},
            ns = {bye = {type = 'i32', init = [00000000]}},
            first = {type = 'ptr', init = λg. g.puts},
            pair = {type = {'ptr', 'i32'}, value = λg. {g.main, [07000000]}},
            """,
        )
    )
    for line in [
        '@"names" = internal constant [2 x ptr] [ptr @"hello", ptr @"ns.bye"]',
        '@"first" = internal global ptr @"puts"',
        '@"pair" = internal constant {ptr, i32} {ptr @"main", i32 7}',
    ]:
        assert line in text, line


def test_addresses_in_struct_operands():
    """A struct operand is a predef: an address in it is the symbol's global, in an LLVM
    constant struct."""
    main = function(
        llvm(
            single(
                "let u = 'store' {{'ptr', 'i8'}, {g.k, [01]}, g.slot} in "
                "let v = 'extractvalue' {{'ptr', 'i8'}, {g.k, [02]}, [00]} in r.done {g.k, [03]},"
                'done = λs. [00000000]',
                extra="k = {type = 'i32', value = [00000000]}, slot = {type = {'ptr', 'i8'}, init = {}},",
            )
        ),
        'main',
    )
    assert 'store {ptr, i8} {ptr @"k", i8 1}, ptr @"slot"' in main
    assert 'extractvalue {ptr, i8} {ptr @"k", i8 2}, 0' in main


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        (
            single('[00000000]', extra="k = {type = 'i32', value = λg. g.k},"),
            'g.k is an address, a ptr, but this constant is i32.',
        ),
        (
            single(
                "let u = 'store' {{'i32'}, {g.k}, g.k} in [00000000]", extra="k = {type = 'i32', value = [00000000]},"
            ),
            'g.k is an address, a ptr, but this constant is i32.',
        ),
        (
            single("let x = 'load' {{g.k}, g.k} in [00000000]", extra="k = {type = 'i32', value = [00000000]},"),
            "'load': field 0 is a type, and a type holds no address.",
        ),
    ],
)
def test_address_errors(source, message):
    assert error(source) == message


def test_namespaces_and_linkage():
    """A symbol with a link is named by it; an internal one by its path, with internal linkage."""
    source = """
    {
      math = {
        gcd = {type = {'function', {a = 'i32'}, 'i32'}, body = λg. λp. 'R' (λr. {p.a})},
        one = {type = 'i32', value = [01000000]},
        exported = {type = 'i32', init = [02000000], link = 'math_exported'},
      },
      main = {type = {'function', {}, 'i32'}, link = 'main', body = λg. λp. 'R' (λr. {
        let x = 'load' {'i32', g.math.one} in
        let y = g.math.gcd {a = x} in
        let z = 'load' {'i32', g.math.exported} in y
      })},
    }
    """
    text = llvm(source)
    assert 'define internal i32 @"math.gcd"(i32 %"p.a")' in text
    assert '@"math.one" = internal constant i32 1' in text
    assert '@"math_exported" = global i32 2' in text
    main = function(text, 'main')
    assert main.startswith('define i32 @"main"()')
    assert '%"x" = load i32, ptr @"math.one"' in main
    assert '%"y" = call i32 @"math.gcd"(i32 %"x")' in main
    assert '%"z" = load i32, ptr @"math_exported"' in main


def test_one_link_is_one_symbol():
    """Entries with the same link are one LLVM symbol: one `declare`, or one `define`."""
    declarations = single(
        'let x = g.a.puts {s = g.msg} in let y = g.b.write {t = g.msg} in y',
        extra="""
        a = {puts = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'puts'}},
        b = {write = {type = {'function', {t = 'ptr'}, 'i32'}, link = 'puts'}},
        msg = {type = 'i8', value = [00]},
        """,
    )
    text = llvm(declarations)
    assert text.count('@"puts"(') == 3
    assert text.count('declare') == 1
    assert 'declare i32 @"puts"(ptr %"s")' in text
    assert '%"y" = call i32 @"puts"(ptr @"msg")' in text
    definition = single(
        'let x = g.twice {n = [01000000]} in x',
        extra="""
        twice = {type = {'function', {n = 'i32'}, 'i32'}, link = 'twice'},
        impl = {type = {'function', {k = 'i32'}, 'i32'}, link = 'twice',
          body = λg. λp. 'R' (λr. {let y = 'add' {'i32', p.k, p.k} in y})},
        """,
    )
    text = llvm(definition)
    assert 'declare' not in text
    assert 'define i32 @"twice"(i32 %"p.k")' in text
    assert '%"x" = call i32 @"twice"(i32 1)' in text


def test_one_link_errors():
    function_type = "{'function', {s = 'ptr'}, 'i32'}"
    assert (
        error(
            single(
                '[00000000]',
                extra=f"a = {{type = {function_type}, link = 'puts'}}, b = {{type = 'i32', link = 'puts'}},",
            )
        )
        == "The entries linked as 'puts' have different types: i32 (ptr) for 'a', i32 for 'b'."
    )
    body = "body = λg. λp. 'R' (λr. {[00000000]})"
    assert (
        error(
            single(
                '[00000000]',
                extra=f"a = {{type = {function_type}, link = 'f', {body}}}, b = {{type = {function_type}, link = 'f', {body}}},",
            )
        )
        == "Two definitions are linked as 'f': 'a' and 'b'."
    )
    assert (
        error(
            single(
                '[00000000]',
                extra="a = {type = 'i32', value = [00000000], link = 'x'}, b = {type = 'i32', init = [00000000], link = 'x'},",
            )
        )
        == "Two definitions are linked as 'x': 'a' and 'b'."
    )


def test_internal_name_apart_from_link_names():
    """An internal symbol whose path is a link name takes the smallest free number."""
    source = single(
        'let x = g.say {s = g.puts} in let y = g.ns.say {s = g.ns.puts} in y',
        extra="""
        say = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'puts'},
        puts = {type = 'i8', value = [00]},
        ns = {
          say = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'ns.puts'},
          puts = {type = 'i8', value = [01]},
        },
        other = {type = 'i8', init = [02], link = 'puts.1'},
        """,
    )
    text = llvm(source)
    assert '@"puts.2" = internal constant i8 0' in text
    assert '@"ns.puts.1" = internal constant i8 1' in text
    assert '@"puts.1" = global i8 2' in text
    assert '%"x" = call i32 @"puts"(ptr @"puts.2")' in text
    assert '%"y" = call i32 @"ns.puts"(ptr @"ns.puts.1")' in text


def test_struct_values():
    """`insertvalue` and `extractvalue`, at positions."""
    blocks = """
      let s1 = 'insertvalue' {{'i8', {'i32', 'i64'}}, {[00], {[00000000], [00000000 00000000]}}, p.a, [01], [00]} in
      let y = 'extractvalue' {{'i8', {'i32', 'i64'}}, s1, [01], [00]} in y
    """
    main = function(llvm(single(blocks, params="{a = 'i32'}")), 'main')
    assert '%"s1" = insertvalue {i8, {i32, i64}} {i8 0, {i32, i64} {i32 0, i64 0}}, i32 %"p.a", 1, 0' in main
    assert '%"y" = extractvalue {i8, {i32, i64}} %"s1", 1, 0' in main
    assert error(single("let y = 'extractvalue' {{'i8'}, {[00]}, [01]} in y")) == (
        "'extractvalue': the indices go past the parts of {'i8'}."
    )


def test_opcodes():
    blocks = """
      let a = 'alloca' {'i32'} in
      let b = 'alloca' {'i8', [04000000]} in
      let h = 'getelementptr' {'i32', a, [01000000]} in
      let c = 'zext' {'i8', p.x, 'i32'} in
      let d = 'icmp' {'slt', 'i32', c, [00000000]} in
      let e = 'sext' {'i1', d, 'i32'} in
      let t = 'trunc' {'i32', e, 'i8'} in
      let u = 'store' {'i8', t, b} in
      c
    """
    main = function(llvm(single(blocks, params="{x = 'i8'}")), 'main')
    for line in [
        '%"a" = alloca i32',
        '%"b" = alloca i8, i32 4',
        '%"h" = getelementptr i32, ptr %"a", i32 1',
        '%"c" = zext i8 %"p.x" to i32',
        '%"d" = icmp slt i32 %"c", 0',
        '%"e" = sext i1 %"d" to i32',
        '%"t" = trunc i32 %"e" to i8',
        'store i8 %"t", ptr %"b"',
    ]:
        assert line in main, line


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        (single('p.x', params="{x = 'i8'}"), "This value has LLVM type i8, but the result of 'main' needs i32."),
        (single('[01]'), 'A constant of type i32 is a byte array of 4 bytes.'),
        (single("let x = 'nope' {} in x"), "The target has no opcode 'nope'."),
        (single("let x = 'add' {'i32', [01000000]} in x"), "'add' takes 3 fields, got 2."),
        (
            single("let x = 'add' {'ptr', p.x, p.x} in x", params="{x = 'i32'}"),
            "'add': field 0 must be an integer type, such as 'i32'.",
        ),
        (single("let x = 'icmp' {'lt', 'i32', p.x, p.x} in x", params="{x = 'i32'}"), 'E-Opcode'),
        (
            single(
                'let y = g.g {x = p.a} in y',
                params="{a = 'i8'}",
                extra="g = {type = {'function', {x = 'i32'}, 'i32'}, link = 'g'},",
            ),
            "This value has LLVM type i8, but parameter 'x' of 'g' needs i32.",
        ),
        (
            single('{r.a, r.a} p.c, a = [00000000]', params="{c = 'ptr'}"),
            'A branch condition must be an integer, got ptr.',
        ),
        (single('p.x', params="{x = 'f32'}"), "'f32' is not an LLVM type."),
        (
            single("let u = 'store' {'i32', [00000000], g.k} in u", extra="k = {type = 'i32', init = [00000000]},"),
            "'u' has no value: a store's result has none.",
        ),
        (
            single("let x = 'add' {'i32', g.k, g.k} in x", extra="k = {type = 'i32', init = [00000000]},"),
            "g.k is an address, a ptr, but opcode 'add' needs i32.",
        ),
    ],
)
def test_errors(source, message):
    if message == 'E-Opcode':
        # `'icmp' {'lt', …}` names no predicate: reduction leaves it, LLVM rejects it.
        message = "'icmp': field 0 must be a predicate, one of ['eq', 'ne', 'slt', 'sle', 'sgt', 'sge', 'ult', 'ule', 'ugt', 'uge']."
    assert error(source) == message


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        ("'i1'", 'i1'),
        ("'i64'", 'i64'),
        ("'ptr'", 'ptr'),
        ("{x = 'i8', y = 'i32'}", '{i8, i32}'),
        ('{}', '{}'),
        ("{'array', [03], 'i32'}", '[3 x i32]'),
        ("{'vector', [04000000], 'i8'}", '<4 x i8>'),
        ("{'packed', 'i8', 'i32'}", '<{i8, i32}>'),
        ("{'array', [02], {'packed', 'i8', {'i16'}}}", '[2 x <{i8, {i16}}>]'),
        # A function type as a value's type holds a function's address.
        ("{'function', {a = 'i32'}, 'void'}", 'ptr'),
        ("{'array', [02], {'function', {}, 'i32'}}", '[2 x ptr]'),
    ],
)
def test_type_shapes(source, expected):
    """The shapes of type terms."""
    assert str(llvm_translate.llvm_type(parse(source))) == expected


@pytest.mark.parametrize(
    'source', ["'f32'", "'i0'", "{'scalable_vector', [04], 'i8'}", "{'array', 'i32'}", "{'array', [03], 'x'}", '[01]']
)
def test_not_types(source):
    with pytest.raises(llvm_translate.LlvmTranslationError, match='is not an LLVM type'):
        llvm_translate.llvm_type(parse(source))


def test_a_name_of_bytes_that_are_not_text():
    r"""A label that isn't UTF-8 text names its symbol with LLVM's `\HH` escapes."""
    text = llvm(
        r"""{
      "f\FF" = {type = {'function', {}, 'i32'}, body = λg. λp. 'R' (λr. {[07000000]})},
      main = {type = {'function', {}, 'i32'}, link = 'main',
        body = λg. λp. 'R' (λr. {let y = g."f\FF" {} in y})},
    }"""
    )
    assert r'define internal i32 @"f\FF"()' in text


def test_sizes_are_constant_expressions():
    text = llvm(
        single(
            """let n = 'layout.size' {{x = 'i32', next = 'ptr'}} in
            let o = 'layout.offset' {{x = 'i32', next = 'ptr'}, [01]} in
            let a = 'layout.align' {'ptr'} in
            let s = 'add' {'i64', n, o} in let t = 'add' {'i64', s, a} in
            let u = 'trunc' {'i64', t, 'i32'} in u"""
        )
    )
    assert 'ptrtoint (ptr getelementptr ({i32, ptr}, ptr null, i32 1) to i64)' in text
    assert 'ptrtoint (ptr getelementptr ({i32, ptr}, ptr null, i32 0, i32 1) to i64)' in text
    assert 'ptrtoint (ptr getelementptr ({i1, ptr}, ptr null, i32 0, i32 1) to i64)' in text
    # A size's let is a constant, not an instruction.
    assert '%"n"' not in text


@pytest.mark.parametrize(
    ('blocks', 'message'),
    [
        (
            "let o = 'layout.offset' {'i32', [00]} in let u = 'trunc' {'i64', o, 'i32'} in u",
            "'layout.offset': field 0 is a struct type and field 1 a field's position.",
        ),
        (
            "let o = 'layout.offset' {{x = 'i32'}, [01]} in let u = 'trunc' {'i64', o, 'i32'} in u",
            "'layout.offset': the struct has no field 1; its fields are 0 to 0.",
        ),
    ],
)
def test_size_errors(blocks, message):
    assert error(single(blocks)) == message


def test_void_functions_and_statement_calls():
    """`'void'` declarations, definitions, statement calls and `ret void`."""
    source = """
    {
      free = {type = {'function', {p = 'ptr'}, 'void'}, link = 'free'},
      step = {
        type = {'function', {slot = 'ptr', x = 'i32'}, 'void'},
        body = λg. λp. 'R' (λr. {
          entry =
            let z = 'icmp' {'eq', 'i32', p.x, [00000000]} in
            if z then r.skip else r.write,
          skip = [],
          write = let s = 'store' {'i32', p.x, p.slot} in [],
        }),
      },
      unit = {type = {'function', {}, {}}, body = λg. λp. 'R' (λr. {{}})},
      fn_ptr = {type = 'ptr', value = λg. g.step},
      main = {
        type = {'function', {}, 'i32'},
        link = 'main',
        body = λg. λp. 'R' (λr. {
          let a = 'alloca' {'i32'} in
          let u = g.step {slot = a, x = [07000000]} in
          let y = 'load' {'i32', a} in
          let e = g.unit {} in
          let v = g.free {p = {}} in
          y
        }),
      },
    }
    """
    text = llvm(source)
    assert 'declare void @"free"(ptr %"p")' in text
    assert '@"fn_ptr" = internal constant ptr @"step"' in text
    assert function(text, 'step') == textwrap.dedent("""\
        define internal void @"step"(ptr %"p.slot", i32 %"p.x")
        {
        r.entry:
          %"z" = icmp eq i32 %"p.x", 0
          br i1 %"z", label %"r.skip", label %"r.write"
        r.skip:
          ret void
        r.write:
          store i32 %"p.x", ptr %"p.slot"
          ret void
        }
        """)
    assert function(text, 'unit') == textwrap.dedent("""\
        define internal {} @"unit"()
        {
        r.0:
          ret {} zeroinitializer
        }
        """)
    main = function(text, 'main')
    assert '\n  call void @"step"(ptr %"a", i32 7)\n' in main
    assert '\n  call void @"free"(ptr null)\n' in main
    assert '%"e" = call {} @"unit"()' in main
    assert '%"u"' not in main
    assert '%"v"' not in main


def test_linked_void_entries():
    linked = single(
        'let u = g.decl {} in [00000000]',
        extra="""
        decl = {type = {'function', {}, 'void'}, link = 'noop'},
        impl = {type = {'function', {}, 'void'}, link = 'noop', body = λg. λp. 'R' (λr. {[]})},
        """,
    )
    text = llvm(linked)
    assert 'declare' not in text
    assert 'define void @"noop"()' in text
    mismatch = single(
        '[00000000]',
        extra="""
        a = {type = {'function', {}, 'void'}, link = 'f'},
        b = {type = {'function', {}, 'i32'}, link = 'f'},
        """,
    )
    assert error(mismatch) == "The entries linked as 'f' have different types: void () for 'a', i32 () for 'b'."


@pytest.mark.parametrize(
    'type_source',
    [
        "'void'",
        "{x = 'void'}",
        "{'packed', 'void'}",
        "{'array', [02], 'void'}",
        "{'vector', [02], 'void'}",
    ],
)
def test_void_is_not_a_value_type(type_source):
    with pytest.raises(llvm_translate.LlvmTranslationError) as info:
        llvm_translate.llvm_type(parse(type_source))
    assert info.value.message == "'void' is only a function's result type."


@pytest.mark.parametrize(
    'source',
    [
        single('[00000000]', params="{x = 'void'}"),
        single('{}', result="{x = 'void'}"),
        single('[00000000]', extra="g = {type = 'void', link = 'g'},"),
        single('[00000000]', extra="g = {type = 'void', init = {}},"),
        single('[00000000]', extra="k = {type = 'void', value = {}},"),
        single("let a = 'alloca' {'void'} in [00000000]"),
        single("let x = 'load' {'void', p.q} in [00000000]", params="{q = 'ptr'}"),
        single("let u = 'store' {'void', [00], p.q} in [00000000]", params="{q = 'ptr'}"),
        single("let q = 'getelementptr' {'void', p.q, [00000000]} in [00000000]", params="{q = 'ptr'}"),
        single("let c = 'icmp' {'eq', 'void', p.q, p.q} in [00000000]", params="{q = 'ptr'}"),
        single("let x = 'extractvalue' {{'void'}, {}, [00]} in [00000000]"),
        single("let x = 'insertvalue' {{'void'}, {}, {}, [00]} in [00000000]"),
        single("let n = 'layout.size' {'void'} in [00000000]"),
        single("let a = 'layout.align' {'void'} in [00000000]"),
        single("let o = 'layout.offset' {{'void'}, [00]} in [00000000]"),
    ],
)
def test_void_outside_result_type_is_rejected(source):
    assert error(source) == "'void' is only a function's result type."


NOOP = "noop = {type = {'function', {}, 'void'}, link = 'noop'},"
TAKE = "take = {type = {'function', {x = 'i32'}, 'i32'}, link = 'take'},"


@pytest.mark.parametrize('blocks', ['[]', "''", 'let u = g.noop {} in []'])
def test_void_function_returns_written_empty_byte_array(blocks):
    text = llvm(single(blocks, result="'void'", extra=NOOP))
    assert 'ret void' in text


@pytest.mark.parametrize(
    'blocks',
    [
        '[00000000]',
        '{}',
        '{[00]}',
        'p.x',
        'g.k',
        "let y = 'add' {'i32', p.x, p.x} in y",
        'let u = g.noop {} in u',
        'r.done [], done = λx. x',
    ],
)
def test_void_function_must_return_empty_byte_array(blocks):
    extra = NOOP + "k = {type = 'i32', value = [00000000]},"
    assert (
        error(single(blocks, params="{x = 'i32'}", result="'void'", extra=extra))
        == "'main' has result type 'void', so it must return []."
    )


@pytest.mark.parametrize(
    'blocks',
    [
        "let u = g.noop {} in let y = 'add' {'i32', u, [01000000]} in y",
        'let u = g.noop {} in let y = g.take {x = u} in y',
        'let u = g.noop {} in u',
        'let u = g.noop {} in {r.a, r.a} u, a = [00000000]',
        "let u = g.noop {} in r.done u, done = λx. let y = 'add' {'i32', x, x} in y",
        'let u = g.noop {} in r.done u, done = λx. {r.a, r.a} x, a = [00000000]',
        'let u = g.noop {} in r.done u, done = λx. [00000000]',
    ],
)
def test_void_call_result_cannot_be_used(blocks):
    assert error(single(blocks, extra=NOOP + TAKE)) == "'u' has no value: a 'void' call has none."


def test_store_result_jumped_to_unused_parameter_is_rejected():
    source = single(
        "let u = 'store' {'i32', [00000000], g.k} in r.done u, done = λx. [00000000]",
        extra="k = {type = 'i32', init = [00000000]},",
    )
    assert error(source) == "'u' has no value: a store's result has none."


# A function of one `'i32'`, and one of none that returns nothing.
INC = "inc = {type = {'function', {n = 'i32'}, 'i32'}, link = 'inc'},"
TICK = "tick = {type = {'function', {}, 'void'}, link = 'tick'},"
FN_I32 = "{'function', {x = 'i32'}, 'i32'}"


def test_indirect_calls():
    """A call through an argument, a loaded value or a block parameter is `call` through the
    `ptr` it holds, with the function type it has; a function's address is a value of its
    type. Direct calls may leave their labels out."""
    source = single(
        f"""
        entry =
          let a = g.apply {{g.inc, [05000000]}} in
          let h = 'load' {{{FN_I32}, g.slot}} in
          let b = h {{x = a}} in r.pick g.inc b,
        pick = λf. λb. let c = f {{b}} in c
        """,
        extra=INC
        + f'slot = {{type = {FN_I32}, init = λg. g.inc}},'
        + f"""apply = {{type = {{'function', {{f = {FN_I32}, v = 'i32'}}, 'i32'}},
            body = λg. λp. 'R' (λr. {{let y = p.f {{p.v}} in y}})}},""",
    )
    text = llvm(source)
    assert '%"y" = call i32 %"p.f"(i32 %"p.v")' in function(text, 'apply')
    assert function(text, 'main') == textwrap.dedent(
        """\
        define i32 @"main"()
        {
        r.entry:
          %"a" = call i32 @"apply"(ptr @"inc", i32 5)
          %"h" = load ptr, ptr @"slot"
          %"b" = call i32 %"h"(i32 %"a")
          br label %"r.pick"
        r.pick:
          %"f" = phi  ptr [@"inc", %"r.entry"]
          %"b1" = phi  i32 [%"b", %"r.entry"]
          %"c" = call i32 %"f"(i32 %"b1")
          ret i32 %"c"
        }
        """
    )
    assert '@"slot" = internal global ptr @"inc"' in text


def test_indirect_void_call():
    source = single(
        'let u = p.t {} in [00000000]',
        params="{t = {'function', {}, 'void'}}",
    )
    assert '  call void %"p.t"()\n' in llvm(source)


@pytest.mark.parametrize(
    ('blocks', 'message'),
    [
        (
            "let h = 'load' {'ptr', g.slot} in let y = h {[01000000]} in y",
            "'h' heads a call, so its type must be a function type; it is 'ptr'.",
        ),
        (
            "let h = 'load' {{'function', {x = 'i32'}, 'i32'}, g.slot} in let y = h {n = [01000000]} in y",
            "Operand 0 of the call to 'h' is labeled 'n', but parameter 0 is 'x'.",
        ),
        (
            "let h = 'load' {{'function', {x = 'i32'}, 'i32'}, g.slot} in let y = h {} in y",
            "The call to 'h' gives 0 operands; it takes 1, ['x'].",
        ),
        # A byte array's length types f: a number is not a function.
        (
            'entry = r.go [00], go = λf. let y = f {} in y',
            "'f' heads a call, so its type must be a function type; it is 'i8'.",
        ),
        # A non-function address: a global's is a 'ptr'.
        (
            'entry = r.go g.slot, go = λf. let y = f {} in y',
            "'f' heads a call, so its type must be a function type; it is 'ptr'.",
        ),
        (
            "let h = 'load' {{'function', {}, 'void'}, g.slot} in let u = h {} in u",
            "'u' has no value: a 'void' call has none.",
        ),
    ],
)
def test_indirect_call_errors(blocks, message):
    assert error(single(blocks, extra="slot = {type = 'ptr', init = ''},")) == message
