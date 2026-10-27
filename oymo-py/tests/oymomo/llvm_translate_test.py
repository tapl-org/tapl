# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""LLVM translation."""

import textwrap

import pytest
from llvmlite import binding

from oymo.oymomo import ingot, llvm_opcodes, llvm_translate
from oymo.oymomo.grammar import parse

TARGET = llvm_translate.Target('x86_64-unknown-linux-gnu', '', llvm_opcodes.DEFAULT_OPCODES)

GCD = """
{version = '0', symbols = {
  gcd = {type = {'function', {a = 'i32', b = 'i32'}, 'i32'},
    body = λm. λp. m [] (λr. {
      entry = r.loop p.a p.b,
      loop = λa. λb.
        let z = 'icmp' {'eq', 'i32', b, [00000000]} in
        m [] (λq. {
          if z then r.done a else q.step,
          step = let c = 'urem' {'i32', a, b} in r.loop b c
        }),
      done = λc. c
    })},
  main = {type = {'function', {}, 'i32'},
    body = λm. λp. m [] (λr. {entry = let y = m.gcd {a = [30000000], b = [12000000]} in y})}
}}
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
    return f"""{{version = '0', symbols = {{
      {extra}
      main = {{type = {{'function', {params}, {result}}}, body = λm. λp. m [] (λr. {{{blocks}}})}},
    }}}}"""


def test_gcd():
    """One block per block, `phi`s for parameters, bound names made distinct."""
    text = llvm(GCD)
    assert function(text, 'gcd') == textwrap.dedent("""\
        define i32 @"gcd"(i32 %"p.a", i32 %"p.b")
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
    {version = '0', symbols = {
      puts = {type = {'function', {s = 'ptr'}, 'i32'}},
      msg = {type = {'array', [03], 'i8'}, value = [686900]},
      main = {type = {'function', {argc = 'i32'}, 'i32'},
        body = λm. λp. m [] (λr. {
          entry =
            let c = 'icmp' {'sgt', 'i32', p.argc, [01000000]} in
            m [] (λq. {
              if c then q.say else r.done,
              say = let u = m.puts {s = m.msg} in r.done
            }),
          done = [00000000]
        })}
    }}
    """
    text = llvm(source)
    assert '@"msg" = constant [3 x i8] c"hi\\00"' in text
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


def test_jump_to_field_0_of_the_body_adds_an_entry_block():
    """LLVM's entry block has no predecessors, so a new one, named after the binder,
    jumps to field 0."""
    blocks = "entry = let c = 'icmp' {'eq', 'i32', p.n, [00000000]} in if c then r.entry else r.done, done = p.n"
    text = function(llvm(single(blocks, params="{n = 'i32'}")), 'main')
    assert text.startswith('define i32 @"main"(i32 %"p.n")\n{\nr:\n  br label %"r.entry"\nr.entry:\n')


def test_jump_to_a_nested_field_0_splits_the_block():
    """Field 0 starts a block of its own; the block it continued ends with `br`."""
    blocks = """entry =
      let a = 'alloca' {'i32'} in
      m [] (λq. {
        again = let v = 'load' {'i32', a} in let c = 'icmp' {'eq', 'i32', v, [00000000]} in
          if c then q.again else r.done,
      }),
      done = [00000000]"""
    text = function(llvm(single(blocks)), 'main')
    assert 'r.entry:\n  %"a" = alloca i32\n  br label %"q.again"\nq.again:\n' in text
    assert 'br i1 %"c", label %"q.again", label %"r.done"' in text


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
            'r.done [07], done = λx. let y = m.f {a = x} in [00000000]',
            extra="f = {type = {'function', {a = 'ptr'}, 'i32'}},",
        )
    ) == ('No constant of type ptr is written [07].')
    assert error(single("r.done p.a, done = λx. let y = 'add' {'i32', x, x} in y", params="{a = 'i8'}")) == (
        "'x' gets two types, i8 and i32: give 'x' one typed argument or typed use."
    )
    assert error(single('r.done [00], done = λx. {r.a, r.a} x, a = [00000000]')) == (
        "give 'x' a typed argument or a typed use."
    )


def test_symbols():
    """Symbols and their initializers."""
    source = """
    {version = '0', symbols = {
      puts = {type = {'function', {s = 'ptr'}, 'i32'}},
      errno = {type = 'i32'},
      answer = {type = 'i32', value = [2a000000]},
      counter = {type = 'i32', init = [29000000]},
      pair = {type = {'i8', 'i16'}, value = {[01], [0200]}},
      table = {type = {'array', [03], 'i8'}, init = {[01], [02], [03]}},
      text = {type = {'array', [03], 'i8'}, value = 'ab' },
      here = {type = 'ptr', value = 'counter'},
      later = {type = 'ptr', value = {'table', [02]}},
      none = {type = 'ptr', init = ''},
      zeros = {type = {'i32', 'ptr'}, init = {}},
      main = {type = {'function', {}, 'i32'}, body = λm. λp. m [] (λr. {
        let u = 'store' {'i32', [05000000], m.counter} in
        let x = 'load' {'i32', m.answer} in
        let e = 'load' {'i32', m.errno} in
        let y = m.puts {s = m.answer} in
        x
      })},
    }}
    """
    with pytest.raises(llvm_translate.LlvmTranslationError, match=r'\[3 x i8\] is a byte array of 3 bytes here'):
        llvm(source)
    source = source.replace("'ab' ", '[616200]')
    text = llvm(source)
    for line in [
        'declare i32 @"puts"(ptr %"s")',
        '@"errno" = external global i32',
        '@"answer" = constant i32 42',
        '@"counter" = global i32 41',
        '@"pair" = constant {i8, i16} {i8 1, i16 2}',
        '@"table" = global [3 x i8] [i8 1, i8 2, i8 3]',
        '@"text" = constant [3 x i8] c"ab\\00"',
        '@"here" = constant ptr @"counter"',
        '@"later" = constant ptr getelementptr (i8, ptr @"table", i64 2)',
        '@"none" = global ptr null',
        '@"zeros" = global {i32, ptr} zeroinitializer',
    ]:
        assert line in text, line
    main = function(text, 'main')
    assert 'store i32 5, ptr @"counter"' in main
    assert '%"x" = load i32, ptr @"answer"' in main
    assert '%"y" = call i32 @"puts"(ptr @"answer")' in main
    assert error(source.replace("value = 'counter'", "value = 'nobody'")) == "'nobody' names no symbol of the ingot."


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
      let g = 'getelementptr' {'i32', a, [01000000]} in
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
        '%"g" = getelementptr i32, ptr %"a", i32 1',
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
                'let y = m.g {x = p.a} in y',
                params="{a = 'i8'}",
                extra="g = {type = {'function', {x = 'i32'}, 'i32'}},",
            ),
            "This value has LLVM type i8, but parameter 'x' of 'g' needs i32.",
        ),
        (
            single('{r.a, r.a} p.c, a = [00000000]', params="{c = 'ptr'}"),
            'A branch condition must be an integer, got ptr.',
        ),
        (single('p.x', params="{x = 'f32'}"), "'f32' is not an LLVM type."),
        (
            single("let u = 'store' {'i32', [00000000], m.k} in u", extra="k = {type = 'i32', init = [00000000]},"),
            "'u' has no value: a store's result has none.",
        ),
        (
            single("let x = 'add' {'i32', m.k, m.k} in x", extra="k = {type = 'i32', init = [00000000]},"),
            "m.k is an address, a ptr, but opcode 'add' needs i32.",
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
