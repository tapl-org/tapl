# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Modules (Section 8): reading a program's normal form into symbols."""

import pytest

from oymo.oymomo import module, reduction
from oymo.oymomo.grammar import parse
from oymo.oymomo.printer import show

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


def read(source):
    return module.module_of(parse(source))


def error(source):
    with pytest.raises(module.ModuleError) as info:
        read(source)
    return info.value.message


def test_gcd():
    """The example of 8.9."""
    gcd_module = read(GCD)
    gcd = gcd_module.lookup('gcd')
    assert isinstance(gcd, module.Definition)
    assert [b.label for b in gcd.blocks] == ['entry', 'loop', 'step', 'done']
    assert gcd.takes == [('a', parse("'i32'")), ('b', parse("'i32'"))]
    assert gcd.gives == parse("'i32'")
    assert show(gcd.blocks[3].body) == '$0.a'
    main = gcd_module.lookup('main')
    assert main.takes == []
    assert show(main.blocks[0].body) == '$2.gcd {a = [30000000], b = [12000000]}'


def test_symbols():
    source = """
    λm. {
      puts = {takes = {s = 'ptr'}, gives = 'i32'},
      answer = {type = 'i32', value = [2a000000]},
      counter = {type = 'i32', init = [29000000]},
      main = {gives = 'i32', body = λf. {entry = {takes = {}, body = λp.
        let u = 'store' {'i32', [05000000], m.counter} in
        let x = 'load' {'i32', m.answer} in
        let y = m.puts {s = m.answer} in
        x
      }}},
    }
    """
    symbols = read(source).symbols
    assert [type(s).__name__ for s in symbols] == ['Declaration', 'Constant', 'Global', 'Definition']
    puts, answer, counter, _ = symbols
    assert puts.takes == [('s', parse("'ptr'"))]
    assert answer.value == parse('[2a000000]')
    assert counter.init == parse('[29000000]')


def test_reduction_first():
    """A program may wrap the module and use helpers; reduction removes them (8.1)."""
    source = """
    (λd. λm. {
      main = {gives = 'i32', body = λf. {entry = {takes = {n = 'i32'}, body = λp.
        let x = 'add' {'i32', p.n, [01000000]} in
        let y = d.double x in
        if y then f.entry.body {n = y} else y
      }}},
    }) {double = λn. 'add' {'i32', n, n}}
    """
    main = read(source).lookup('main')
    assert show(main.blocks[0].body) == (
        "let x = 'add' {'i32', $0.n, [01000000]} in let y = 'add' {'i32', $0, $0} in "
        'if $0 then $3.entry.body {n = $0} else $0'
    )


def test_a_helper_on_a_projection_stays_an_application():
    """A projection is not a value (4.3), so a helper applied to p.n is not inlined."""
    source = """
    (λd. λm. {main = {gives = 'i32', body = λf. {entry = {takes = {n = 'i32'}, body = λp.
      d.double p.n
    }}}}) {double = λn. 'add' {'i32', n, n}}
    """
    assert error(source) == (
        "Block 'entry' is not in ANF: A let must bind an opcode call or a function call; "
        'a projection is not a value, so E-Beta never substitutes it (4.3).'
    )


def test_jump_to_the_first_block_and_return_arms():
    # 8.3c: any block may jump to the first; 9.3c: an arm may return.
    source = """
    λm. {
      count = {gives = 'i32', body = λf. {
        top = {takes = {n = 'i32'}, body = λp.
          let z = 'icmp' {'eq', 'i32', p.n, [00000000]} in
          if z then p.n else f.down.body {n = p.n}
        },
        down = {takes = {n = 'i32'}, body = λp.
          let k = 'sub' {'i32', p.n, [01000000]} in
          f.top.body {n = k}
        },
      }},
      main = {gives = 'i32', body = λf. {entry = {takes = {}, body = λp. m.count {n = [03000000]}}}},
    }
    """
    assert [b.label for b in read(source).lookup('count').blocks] == ['top', 'down']


def wrap(body, takes="{a = 'i32'}", extra=''):
    return f"""λm. {{
      {extra}
      helper = {{takes = {{x = 'i32'}}, gives = 'i32'}},
      main = {{gives = 'i32', body = λf. {{
        entry = {{takes = {takes}, body = λp. {body}}},
        next = {{takes = {{b = 'i32'}}, body = λp. p.b}},
      }}}},
    }}"""


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        ('{}', 'A module must be λm. {symbols}, with its outer abstractions applied.'),
        ('λd. λm. {}', 'A module must be λm. {symbols}, with its outer abstractions applied.'),
        ('λm. {[01]}', 'A symbol needs a label: its name.'),
        (
            'λm. {x = {a = [01]}}',
            "Symbol 'x' must be a definition {gives, body}, a declaration {takes, gives}, "
            'a constant {type, value} or a global variable {type, init}.',
        ),
        ("λm. {x = {gives = 'i32', body = λf. {}}}", "The body of 'x' must be λf. {blocks}, with at least one block."),
        ("λm. {x = {gives = 'i32', body = λf. {e = {body = λp. p}}}}", "Block 'e' must be {takes, body}."),
        (
            "λm. {x = {gives = 'i32', body = λf. {e = {takes = {}, body = [01]}}}}",
            "The body of block 'e' must be λp. e.",
        ),
        ("λm. {x = {gives = 'i32', body = λf. {{takes = {}, body = λp. [01]}}}}", 'A block needs a label.'),
        ("λm. {x = {takes = {'i32'}, gives = 'i32'}}", '`takes` must be a struct of labeled types, {x = t, ...}.'),
        ('λm. {x = {type = λy. y, value = [01]}}', 'A type must be data: byte arrays and structs of them.'),
        ("λm. {x = {type = 'i32', init = m.x}}", 'A init must be data: byte arrays and structs of them.'),
        # Checks of block bodies.
        (
            wrap("'add' {'i32', 'mul' {'i32', p.a, p.a}, p.a}"),
            "Block 'entry' is not in ANF: An operand must be an atom: bind it with a let.",
        ),
        (wrap('p.z'), "Block 'entry' reads its parameters as p.x, x one of ['a']."),
        (wrap('p'), "Block 'entry' reads its parameters as p.x, x one of ['a']."),
        (wrap('f.next'), 'f names the blocks; it is only for jumps, f.l.body {...}.'),
        (wrap('m.nope'), 'An atom through m must be m.l, with l a symbol of the module.'),
        (wrap('f.gone.body {}'), "A jump is f.l.body {...}, l one of the blocks ['entry', 'next']."),
        (wrap('f.next {b = p.a}'), "A jump is f.l.body {...}, l one of the blocks ['entry', 'next']."),
        (wrap('let x = f.next.body {b = p.a} in x'), 'A jump through f ends a block: it is never bound by a let.'),
        (wrap('f.next.body {c = p.a}'), "The call to block 'next' must give ['b'], in order; it gives ['c']."),
        (wrap('m.helper {}'), "The call to 'helper' must give ['x'], in order; it gives []."),
        (wrap('m.main.x {}'), 'A call through m is m.l {...}, l a definition or a declaration.'),
        (
            wrap('m.k {}', extra="k = {type = 'i32', value = [00000000]},"),
            'A call through m is m.l {...}, l a definition or a declaration.',
        ),
        (wrap('{} p.a'), 'The program is stuck here: no rule can ever reduce this part.'),
    ],
)
def test_errors(source, message):
    assert error(source) == message


def test_error_locations():
    source = wrap('p.z')
    with pytest.raises(module.ModuleError) as info:
        read(source)
    assert info.value.location.start == source.index('p.z')


def test_no_normal_form():
    omega = '(λw. w w) (λw. w w)'
    with pytest.raises(reduction.ReductionError, match='No normal form'):
        module.module_of(parse(f'λm. {{x = {omega}}}'), max_steps=100)
