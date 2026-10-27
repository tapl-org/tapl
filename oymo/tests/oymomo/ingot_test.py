# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Ingots: reading a program's normal form, and the variables' kinds."""

import pytest

from oymo.core import spans
from oymo.oymomo import ingot, reduction
from oymo.oymomo.grammar import parse

GCD = """
{
  version = '0',
  symbols = {
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
  }
}
"""


def read(source):
    return ingot.ingot_of(parse(source))


def error(source):
    with pytest.raises(ingot.IngotError) as info:
        read(source)
    return info.value.message


def test_gcd():
    """An ingot with gcd: regions, blocks and names."""
    gcd = read(GCD).lookup('gcd')
    assert isinstance(gcd, ingot.Definition)
    assert gcd.args == 'p'
    assert [label for label, _ in gcd.type.params] == ['a', 'b']
    region = gcd.region
    assert region.binder == 'r'
    assert [b.name for b in region.blocks] == ['r.entry', 'r.loop', 'r.done']
    entry, loop, done = region.blocks
    assert isinstance(entry.terminal, ingot.Jump)
    assert entry.terminal.target is loop
    assert [type(q).__name__ for q in entry.terminal.operands] == ['Arg', 'Arg']
    assert [v.name for v in loop.params] == ['a', 'b']
    assert [let.result.name for let in loop.lets] == ['z']
    nested = loop.terminal
    assert isinstance(nested, ingot.Region)
    assert [b.name for b in nested.blocks] == ['q.0', 'q.step']
    branch = nested.blocks[0].terminal
    assert isinstance(branch, ingot.Branch)
    assert [arm.target.name for arm in branch.arms] == ['q.step', 'r.done']
    assert branch.condition.var is loop.lets[0].result
    # Bound names are made distinct in source order: step's `c` comes first.
    assert nested.blocks[1].lets[0].result.name == 'c'
    assert [v.name for v in done.params] == ['c1']
    assert done.jumped
    assert not entry.jumped


def test_entries():
    source = """
    {
      version = '0',
      symbols = {
        puts = {type = {'function', {s = 'ptr'}, 'i32'}},
        errno = {type = 'i32'},
        answer = {type = 'i32', value = [2a000000]},
        counter = {type = 'i32', init = [29000000]},
        main = {type = {'function', {}, 'i32'}, body = λm. λp. m [] (λr. {
          let u = 'store' {'i32', [05000000], m.counter} in
          let y = m.puts {s = m.answer} in
          y
        })},
      },
      target = {triple = 'x86_64-unknown-linux-gnu'},
    }
    """
    result = read(source)
    assert [type(s).__name__ for s in result.symbols] == [
        'Declaration',
        'Declaration',
        'Constant',
        'Global',
        'Definition',
    ]
    puts, errno, answer, counter, main = result.symbols
    assert ingot.function_type(puts).params == [('s', parse("'ptr'"))]
    assert ingot.function_type(errno) is None
    assert answer.value == parse('[2a000000]')
    assert counter.init == parse('[29000000]')
    store, call = main.region.blocks[0].lets
    assert store.opcode == 'store'
    assert isinstance(store.fields[2][1], ingot.Address)
    assert call.callee == 'puts'
    # An unlabeled field 0 is named after the region's binder.
    assert main.region.blocks[0].name == 'r.0'


def test_reduction_first():
    """A program may wrap the ingot and use helpers; reduction removes them."""
    source = """
    (λd. {version = '0', symbols = {
      main = {type = {'function', {n = 'i32'}, 'i32'}, body = λm. λp. m [] (λr. {
        entry = let x = 'add' {'i32', p.n, [01000000]} in let y = d.double x in y
      })}
    }}) {double = λn. 'add' {'i32', n, n}}
    """
    lets = read(source).lookup('main').region.blocks[0].lets
    assert [(let.result.name, let.opcode) for let in lets] == [('x', 'add'), ('y', 'add')]


def test_jump_to_a_labeled_field_0():
    """A labeled field 0 may be jumped to, with no operands."""
    body = "let c = 'icmp' {'eq', 'i32', p.a, [00000000]} in if c then r.entry else r.done, done = p.a"
    region = read(wrap(body)).lookup('main').region
    assert region.blocks[0].jumped


def wrap(body, extra=''):
    return f"""{{version = '0', symbols = {{
      {extra}
      helper = {{type = {{'function', {{x = 'i32'}}, 'i32'}}}},
      k = {{type = 'i32', value = [00000000]}},
      main = {{type = {{'function', {{a = 'i32'}}, 'i32'}}, body = λm. λp. m [] (λr. {{
        entry = {body},
        next = λb. b,
      }})}},
    }}}}"""


def entry(fields):
    return f"{{version = '0', symbols = {{x = {fields}}}}}"


TAIL_CALL = 'A call that ends a function is bound and returned: let y = m.f {…} in y.'


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        ('λm. {}', 'Not an ingot: an ingot is a struct {version, symbols, target}.'),
        (
            "{version = '0', symbols = {}, extra = {}}",
            "Not an ingot: unknown field 'extra'; an ingot has ['version', 'symbols', 'target'].",
        ),
        ('{symbols = {}}', "Not an ingot: it has no 'version'."),
        ("{version = '0'}", "Not an ingot: it has no 'symbols'."),
        ("{version = '1', symbols = {}}", "Unknown ingot version '1'; this oymo reads '0'."),
        ("{version = '0', symbols = [01]}", 'Not an ingot: symbols must be a struct of entries.'),
        ("{version = '0', symbols = {{type = 'i32'}}}", "An entry needs a label: its symbol's name."),
        (entry('[01]'), "Entry 'x' must be a struct {type, ...}."),
        (entry('{value = [01]}'), "Entry 'x' needs a type."),
        (
            entry("{type = 'i8', size = [01]}"),
            "Entry 'x' has an unknown field 'size'; it may have type, body, init, value.",
        ),
        (
            entry("{type = 'i8', init = [01], value = [01]}"),
            "Entry 'x' has init and value; it may have at most one of ['body', 'init', 'value'].",
        ),
        (entry('{type = λy. y}'), 'A type must be data: byte arrays and structs of them.'),
        (entry("{type = 'i8', init = λy. y}"), 'A init must be data: byte arrays and structs of them.'),
        (
            entry("{type = 'i32', body = λm. λp. m [] (λr. {[00000000]})}"),
            "Entry 'x' has a body, so its type must be {'function', {x = t, ...}, t}.",
        ),
        (
            entry("{type = {'function', {'i32'}, 'i32'}}"),
            "A function type is {'function', {x = t, ...}, t}: labeled parameters, then the result.",
        ),
        (
            entry("{type = {'function', {}, 'i32'}, body = λm. [00000000]}"),
            "The body of 'x' must be λm. λp. m [] (λr. {blocks}).",
        ),
        (
            entry("{type = {'function', {}, 'i32'}, body = λm. λp. [00000000]}"),
            "The body of 'x' must be λm. λp. m [] (λr. {blocks}).",
        ),
        # The grammar.
        (
            wrap("'add' {'i32', 'mul' {'i32', p.a, p.a}, p.a}"),
            "'main' is not in ANF: An operand must be a path or data: bind it with a let.",
        ),
        (
            wrap("let x = 'add' {'i32', {p.a}, p.a} in x"),
            "'main' is not in ANF: An operand must be a path or data; a struct value is built with 'insertvalue'.",
        ),
        (
            wrap('let x = m.helper {x = p.a} in {r.next x, [00]} x'),
            "'main' is not in ANF: An arm of a branch only jumps: r.l Q₁ ⋯ Qₙ.",
        ),
        (
            wrap('let x = m.helper {x = p.a} in {r.next x, x} x'),
            'An arm of a branch only jumps: r.l Q₁ ⋯ Qₙ, r a region.',
        ),
        (wrap('m.helper {x = p.a}'), f"'main' is not in ANF: {TAIL_CALL}"),
        (wrap('m [] (λq. {λy. y})'), "'main' is not in ANF: Field 0 of a region is an expression, never a λ."),
        (wrap('m [] (λq. {})'), "'main' is not in ANF: A region holds a struct of blocks, at least one."),
        # Kinds.
        (wrap('p.z'), "'main' has no parameter 'z'; it has ['a']."),
        (wrap('p'), "p is never used whole: read an argument as p.l, l one of ['a']."),
        (wrap('r.next'), 'r.next takes 1 operands, one per parameter; the jump gives 0.'),
        (wrap('r.gone p.a'), "A jump names a block of 'r': one of ['entry', 'next']."),
        (wrap('let x = m.helper {x = r.next} in x'), 'r.l is a block: it only heads a jump.'),
        (wrap('m.nope'), 'm names the symbols: an operand through m is m.l, l a symbol of the module.'),
        (wrap('m'), 'm names the symbols: an operand through m is m.l, l a symbol of the module.'),
        (wrap('m.helper {x = [00000000]}'), TAIL_CALL),
        (
            wrap("let x = 'add' {'i32', p.a, p.a} in x.y"),
            "A value has no fields: read a field of a struct value with 'extractvalue'.",
        ),
        (
            wrap('let x = m.k {} in x'),
            'An instruction calls a function, m.l {...} with l a function of the module.',
        ),
        (wrap('let x = m.helper {} in x'), "The call to 'helper' must give ['x'], in order; it gives []."),
        (wrap('{r.next p.a, r.next p.a} m.k'), 'A branch condition is a value or an argument p.l.'),
        (wrap('p.a [00000000]'), 'Only a block r.l is applied at the end of a block.'),
        (wrap('m [] (λq. {[00000000], [00000000]})'), 'A block after field 0 needs a label, so a jump can name it.'),
        (
            wrap("let x = 'add' {'i32', p.a, p.a} in x [] (λq. {[00000000]})"),
            'Only the module runs a region: m [] (λr. {...}).',
        ),
        (wrap('{} p.a'), 'The program is stuck here: no rule can ever reduce this part.'),
    ],
)
def test_errors(source, message):
    assert error(source) == message


def test_error_locations():
    source = wrap('p.z')
    with pytest.raises(ingot.IngotError) as info:
        read(source)
    assert spans.start(info.value.span) == source.index('p.z')


def test_no_normal_form():
    omega = '(λw. w w) (λw. w w)'
    with pytest.raises(reduction.ReductionError, match='No normal form'):
        ingot.ingot_of(parse(f"{{version = '0', symbols = {{x = {omega}}}}}"), max_steps=100)
