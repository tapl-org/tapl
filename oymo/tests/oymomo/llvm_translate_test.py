# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""LLVM translation (Section 9)."""

import textwrap

import pytest
from llvmlite import binding

from oymo.oymomo import llvm_opcodes, llvm_translate, module
from oymo.oymomo.grammar import parse

TARGET = llvm_translate.Target('x86_64-unknown-linux-gnu', '', llvm_opcodes.DEFAULT_OPCODES)

GCD = """
λm. {
  gcd = {gives = 'i32', body = λf. {
      entry = {takes = {a = 'i32', b = 'i32'}, body = λp.
        f.loop.body {a = p.a, b = p.b}
      },
      loop = {takes = {a = 'i32', b = 'i32'}, body = λp.
        let z = 'icmp' {'eq', 'i32', p.b, [00000000]} in
        if z then
          f.done.body {a = p.a}
        else
          f.step.body {a = p.a, b = p.b}
      },
      step = {takes = {a = 'i32', b = 'i32'}, body = λp.
        let r = 'urem' {'i32', p.a, p.b} in
        f.loop.body {a = p.b, b = r}
      },
      done = {takes = {a = 'i32'}, body = λp.
        p.a
      }
    }
  },
  main = {gives = 'i32', body = λf. {
      entry = {takes = {}, body = λp.
        m.gcd {a = [30000000], b = [12000000]}
      }
    }
  }
}
"""


def llvm(source):
    """The LLVM IR of `source`, checked by LLVM's own verifier."""
    ir_module = llvm_translate.translate(module.module_of(parse(source)), TARGET)
    text = str(ir_module)
    binding.parse_assembly(text).verify()
    return text


def function(text, name):
    """The `define` of `@name` in `text`."""
    start = text.index(f'@"{name}"(') if f'@"{name}"(' in text else text.index(f'@{name}(')
    start = text.rindex('define', 0, start)
    return text[start : text.index('\n}', start) + 2] + '\n'


def error(source):
    with pytest.raises(llvm_translate.LlvmTranslationError) as info:
        llvm(source)
    return info.value.message


def single(body, takes='{}', gives="'i32'", extra=''):
    return f"""λm. {{
      {extra}
      main = {{gives = {gives}, body = λf. {{entry = {{takes = {takes}, body = λp. {body}}}}}}},
    }}"""


def test_gcd():
    """8.9: blocks become LLVM blocks; `loop` has two predecessors, so its `takes` are phis."""
    text = llvm(GCD)
    assert function(text, 'gcd') == textwrap.dedent("""\
        define i32 @"gcd"(i32 %"a", i32 %"b")
        {
        entry:
          br label %"loop"
        loop:
          %"a.1" = phi  i32 [%"a", %"entry"], [%"b.1", %"step"]
          %"b.1" = phi  i32 [%"b", %"entry"], [%"r", %"step"]
          %"z" = icmp eq i32 %"b.1", 0
          br i1 %"z", label %"done", label %"step"
        step:
          %"r" = urem i32 %"a.1", %"b.1"
          br label %"loop"
        done:
          ret i32 %"a.1"
        }
        """)
    # 9.3b: a jump through m is `call` then `ret`.
    assert function(text, 'main') == textwrap.dedent("""\
        define i32 @"main"()
        {
        entry:
          %".2" = call i32 @"gcd"(i32 48, i32 18)
          ret i32 %".2"
        }
        """)


def test_jump_to_the_first_block_adds_an_entry_block():
    """9.2b: LLVM's entry block has no predecessors."""
    source = """
    λm. {count = {gives = 'i32', body = λf. {
      top = {takes = {n = 'i32'}, body = λp.
        let z = 'icmp' {'eq', 'i32', p.n, [00000000]} in
        if z then p.n else f.down.body {n = p.n}
      },
      down = {takes = {n = 'i32'}, body = λp.
        let k = 'sub' {'i32', p.n, [01000000]} in
        f.top.body {n = k}
      },
    }}}
    """
    text = function(llvm(source), 'count')
    assert text.startswith('define i32 @"count"(i32 %"n")\n{\nstart:\n  br label %"top"\ntop:\n')
    assert '%"n.1" = phi  i32 [%"n", %"start"], [%"k", %"down"]' in text
    # 9.3c: an arm that returns becomes a small block with a `ret`.
    assert 'br i1 %"z", label %"top.1", label %"down"' in text
    assert 'top.1:\n  ret i32 %"n.1"' in text


def test_switch_and_arms():
    source = """
    λm. {
      other = {takes = {}, gives = 'i32'},
      main = {gives = 'i32', body = λf. {
        entry = {takes = {k = 'i8'}, body = λp. {f.a.body {}, [07000000], m.other {}} p.k},
        a = {takes = {}, body = λp. [01000000]},
      }},
    }
    """
    text = function(llvm(source), 'main')
    assert 'switch i8 %"k", label %"entry.2" [i8 0, label %"a" i8 1, label %"entry.1"]' in text
    assert 'entry.1:\n  ret i32 7' in text
    assert 'call i32 @"other"()' in text


def test_two_arms_on_a_wide_condition_compare_with_zero():
    text = function(llvm(single('{[00000000], [01000000]} p.c', takes="{c = 'i32'}")), 'main')
    assert 'icmp ne i32 %"c", 0' in text


def test_two_arms_to_the_same_block_get_small_blocks():
    source = """
    λm. {main = {gives = 'i32', body = λf. {
      entry = {takes = {c = 'i1'}, body = λp. {f.done.body {x = [00000000]}, f.done.body {x = [01000000]}} p.c},
      done = {takes = {x = 'i32'}, body = λp. p.x},
    }}}
    """
    text = function(llvm(source), 'main')
    assert 'br i1 %"c", label %"entry.1", label %"entry.0"' in text
    assert 'phi  i32 [0, %"entry.0"], [1, %"entry.1"]' in text


def test_symbols():
    source = """
    λm. {
      puts = {takes = {s = 'ptr'}, gives = 'i32'},
      answer = {type = 'i32', value = [2a000000]},
      counter = {type = 'i32', init = [29000000]},
      pair = {type = {'i8', 'i16'}, value = {[01], [0200]}},
      table = {type = {'array', [03], 'i8'}, init = {[01], [02], [03]}},
      main = {gives = 'i32', body = λf. {entry = {takes = {}, body = λp.
        let u = 'store' {'i32', [05000000], m.counter} in
        let x = 'load' {'i32', m.answer} in
        let y = m.puts {s = m.answer} in
        x
      }}},
    }
    """
    text = llvm(source)
    assert 'declare i32 @"puts"(ptr %"s")' in text
    assert '@"answer" = constant i32 42' in text
    assert '@"counter" = global i32 41' in text
    assert '@"pair" = constant {i8, i16} {i8 1, i16 2}' in text
    assert '@"table" = global [3 x i8] [i8 1, i8 2, i8 3]' in text
    main = function(text, 'main')
    assert 'store i32 5, ptr @"counter"' in main
    assert '%"x" = load i32, ptr @"answer"' in main
    assert '%"y" = call i32 @"puts"(ptr @"answer")' in main


def test_paths_become_extractvalue():
    """9.3d: `x.l` is `extractvalue` at the label's position in the value's struct type."""
    source = """
    λm. {
      pair = {takes = {}, gives = {lo = 'i32', hi = {a = 'i8', b = 'i32'}}},
      main = {gives = 'i32', body = λf. {entry = {takes = {q = {x = 'i8', y = 'i32'}}, body = λp.
        let r = m.pair {} in
        let s = 'add' {'i32', p.q.y, r.hi.b} in
        s
      }}},
    }
    """
    main = function(llvm(source), 'main')
    assert 'extractvalue {i8, i32} %"q", 1' in main
    assert 'extractvalue {i32, {i8, i32}} %"r", 1' in main
    assert 'extractvalue {i8, i32} %".5", 1' in main


def test_opcodes():
    body = """
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
    main = function(llvm(single(body, takes="{x = 'i8'}")), 'main')
    for line in [
        '%"a" = alloca i32',
        '%"b" = alloca i8, i32 4',
        '%"g" = getelementptr i32, ptr %"a", i32 1',
        '%"c" = zext i8 %"x" to i32',
        '%"d" = icmp slt i32 %"c", 0',
        '%"e" = sext i1 %"d" to i32',
        '%"t" = trunc i32 %"e" to i8',
        'store i8 %"t", ptr %"b"',
    ]:
        assert line in main, line


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        (single('p.x', takes="{x = 'i8'}"), "This value has LLVM type i8, but the result of 'main' needs i32."),
        (single('[01]'), 'A constant of type i32 is a byte array of 4 bytes.'),
        (single("let x = 'nope' {} in x"), "The target has no opcode 'nope'."),
        (single("let x = 'add' {'i32', [01000000]} in x", takes='{}'), "'add' takes 3 fields, got 2."),
        (
            single("let x = 'add' {'ptr', p.x, p.x} in x", takes="{x = 'i32'}"),
            "'add': field 0 must be an integer type, such as 'i32'.",
        ),
        (single("let x = 'icmp' {'lt', 'i32', p.x, p.x} in x", takes="{x = 'i32'}"), 'E-Opcode'),
        (single('p.q.z', takes="{q = {y = 'i32'}}"), ".z reads a field of {y = 'i32'}, which has no field 'z'."),
        (
            single('m.g {x = p.a}', takes="{a = 'i8'}", extra="g = {takes = {x = 'i32'}, gives = 'i32'},"),
            "This value has LLVM type i8, but parameter 'x' of 'g' needs i32.",
        ),
        (
            single('{[00000000], [01000000]} p.c', takes="{c = 'ptr'}"),
            'A branch condition must be an integer, got ptr.',
        ),
        (single('p.x', takes="{x = 'f32'}"), "'f32' is not an LLVM type."),
    ],
)
def test_errors(source, message):
    if message == 'E-Opcode':
        # `'icmp' {'lt', …}` names no predicate: reduction leaves it, LLVM rejects it.
        message = "'icmp': field 0 must be a predicate, one of ['eq', 'ne', 'slt', 'sle', 'sgt', 'sge', 'ult', 'ule', 'ugt', 'uge']."
    assert error(source) == message
