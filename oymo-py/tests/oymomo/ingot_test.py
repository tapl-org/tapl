# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Ingots: reading a program's normal form, and the variables' kinds."""

import pytest

from oymo.oymomo import ingot, reduction
from oymo.oymomo.grammar import parse

GCD = """
{
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
  main = {type = {'function', {}, 'i32'}, link = 'main',
    body = λm. λp. m [] (λr. {entry = let y = m.gcd {a = [30000000], b = [12000000]} in y})}
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
    gcd = read(GCD).lookup(('gcd',))
    assert isinstance(gcd, ingot.Definition)
    assert gcd.path == ('gcd',)
    assert gcd.link is None
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
      puts = {type = {'function', {s = 'ptr'}, 'i32'}, link = 'puts'},
      errno = {type = 'i32', link = 'errno'},
      answer = {type = 'i32', value = [2a000000]},
      counter = {type = 'i32', init = [29000000], link = 'counter'},
      main = {type = {'function', {}, 'i32'}, link = 'main', body = λm. λp. m [] (λr. {
        let u = 'store' {'i32', [05000000], m.counter} in
        let y = m.puts {s = m.answer} in
        y
      })},
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
    assert [s.link for s in result.symbols] == ['puts', 'errno', None, 'counter', 'main']
    assert ingot.function_type(puts).params == [('s', parse("'ptr'"))]
    assert ingot.function_type(errno) is None
    assert answer.value == parse('[2a000000]')
    assert counter.init == parse('[29000000]')
    store, call = main.region.blocks[0].lets
    assert store.opcode == 'store'
    assert isinstance(store.fields[2][1], ingot.Address)
    assert call.callee == ('puts',)
    # An unlabeled field 0 is named after the region's binder.
    assert main.region.blocks[0].name == 'r.0'


def test_namespaces():
    """Namespaces nest; a symbol's path runs through them, in calls and as an address."""
    source = """
    {
      math = {
        gcd = {type = {'function', {a = 'i32'}, 'i32'}, body = λm. λp. m [] (λr. {p.a})},
        zero = {type = 'i32', value = [00000000]},
        deep = {},
      },
      main = {type = {'function', {}, 'i32'}, link = 'main', body = λm. λp. m [] (λr. {
        let x = 'load' {'i32', m.math.zero} in
        let y = m.math.gcd {a = x} in y
      })},
    }
    """
    result = read(source)
    assert [s.path for s in result.symbols] == [('math', 'gcd'), ('math', 'zero'), ('main',)]
    assert result.lookup(('math',)) is None
    load, call = result.lookup(('main',)).region.blocks[0].lets
    assert load.fields[1][1] == ingot.Address(('math', 'zero'))
    assert call.callee == ('math', 'gcd')


def test_reduction_first():
    """A program may wrap the ingot and use helpers; reduction removes them."""
    source = """
    (λd. {
      main = {type = {'function', {n = 'i32'}, 'i32'}, body = λm. λp. m [] (λr. {
        entry = let x = 'add' {'i32', p.n, [01000000]} in let y = d.double x in y
      })}
    }) {double = λn. 'add' {'i32', n, n}}
    """
    lets = read(source).lookup(('main',)).region.blocks[0].lets
    assert [(let.result.name, let.opcode) for let in lets] == [('x', 'add'), ('y', 'add')]


def test_jump_to_a_labeled_field_0():
    """A labeled field 0 may be jumped to, with no operands."""
    body = "let c = 'icmp' {'eq', 'i32', p.a, [00000000]} in if c then r.entry else r.done, done = p.a"
    region = read(wrap(body)).lookup(('main',)).region
    assert region.blocks[0].jumped


def wrap(body, extra=''):
    return f"""{{
      {extra}
      helper = {{type = {{'function', {{x = 'i32'}}, 'i32'}}, link = 'helper'}},
      k = {{type = 'i32', value = [00000000]}},
      main = {{type = {{'function', {{a = 'i32'}}, 'i32'}}, body = λm. λp. m [] (λr. {{
        entry = {body},
        next = λb. b,
      }})}},
    }}"""


def entry(fields):
    return f'{{x = {fields}}}'


TAIL_CALL = 'A call that ends a function is bound and returned: let y = m.f {…} in y.'
M_PATH = 'm names the symbols: an operand through m is m.l₁ ⋯ lₙ, a path to a symbol of the ingot.'


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        ('λm. {}', 'Not an ingot: an ingot is a namespace, a struct of entries and namespaces.'),
        (
            "{type = 'i32', value = [00000000]}",
            'Not an ingot: a struct with a type is an entry; an ingot is a namespace of entries and namespaces.',
        ),
        ("{{type = 'i32', link = 'x'}}", "A field of a namespace needs a label: its symbol's or namespace's name."),
        (
            "{a = {{type = 'i32', link = 'x'}}}",
            "A field of a namespace needs a label: its symbol's or namespace's name.",
        ),
        (entry('[01]'), "'x' is a reduce-time value left in the ingot: a namespace holds only entries and namespaces."),
        (
            '{a = {f = λy. y}}',
            "'a.f' is a reduce-time value left in the ingot: a namespace holds only entries and namespaces.",
        ),
        (
            entry('{value = [01]}'),
            "'x.value' is a reduce-time value left in the ingot: a namespace holds only entries and namespaces.",
        ),
        (
            entry("{type = 'i8', size = [01]}"),
            "Entry 'x' has an unknown field 'size'; it may have type, body, init, value, link.",
        ),
        (entry("{type = 'i8'}"), "'x' is a hole: give it a body or a link."),
        ("{lexer = {error = {type = {'function', {}, 'i32'}}}}", "'lexer.error' is a hole: give it a body or a link."),
        (entry("{type = 'i8', link = ''}"), "A link is the symbol's name for the linker: a nonempty text byte array."),
        (entry("{type = 'i8', link = {}}"), "A link is the symbol's name for the linker: a nonempty text byte array."),
        (
            entry("{type = 'i8', link = [ff]}"),
            "A link is the symbol's name for the linker: a nonempty text byte array.",
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
        (wrap('m.nope'), M_PATH),
        (wrap('m'), M_PATH),
        (wrap('m.k.x'), M_PATH),
        (wrap('m.ns', extra="ns = {k = {type = 'i32', value = [00000000]}},"), M_PATH),
        (wrap('m.helper {x = [00000000]}'), TAIL_CALL),
        (
            wrap("let x = 'add' {'i32', p.a, p.a} in x.y"),
            "A value has no fields: read a field of a struct value with 'extractvalue'.",
        ),
        (
            wrap('let x = m.k {} in x'),
            'An instruction calls a function, m.l₁ ⋯ lₙ {...}, a path to a function of the ingot.',
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
    assert info.value.tag.start == source.encode().index(b'p.z')


def test_no_normal_form():
    omega = '(λw. w w) (λw. w w)'
    with pytest.raises(reduction.ReductionError, match='No normal form'):
        ingot.ingot_of(parse(f'{{x = {omega}}}'), max_steps=100)
