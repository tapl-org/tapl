# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Ingots: reading a program's normal form, and the variables' kinds."""

import pytest

from oymo.oymomo import ingot, reduction
from oymo.oymomo.grammar import parse

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
      main = {type = {'function', {}, 'i32'}, link = 'main', body = λg. λp. 'R' (λr. {
        let u = 'store' {'i32', [05000000], g.counter} in
        let y = g.puts {s = g.answer} in
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
        gcd = {type = {'function', {a = 'i32'}, 'i32'}, body = λg. λp. 'R' (λr. {p.a})},
        zero = {type = 'i32', value = [00000000]},
        deep = {},
      },
      main = {type = {'function', {}, 'i32'}, link = 'main', body = λg. λp. 'R' (λr. {
        let x = 'load' {'i32', g.math.zero} in
        let y = g.math.gcd {a = x} in y
      })},
    }
    """
    result = read(source)
    assert [s.path for s in result.symbols] == [('math', 'gcd'), ('math', 'zero'), ('main',)]
    assert result.lookup(('math',)) is None
    load, call = result.lookup(('main',)).region.blocks[0].lets
    assert load.fields[1][1] == ingot.Address(('math', 'zero'))
    assert call.callee == ('math', 'gcd')


def test_predefs():
    """An init or value λg. C, and a struct operand, are predefs: their addresses are kept as
    paths from the index 0, so `address_path` reads them wherever they were written."""
    source = """
    {
      hello = {type = {'array', [03], 'i8'}, value = [686900]},
      names = {type = {'array', [02], 'ptr'}, value = λg. {g.hello, g.main}},
      first = {type = 'ptr', init = λg. g.hello},
      none = {type = 'ptr', init = λg. ''},
      main = {type = {'function', {}, 'i32'}, link = 'main', body = λg. λp. 'R' (λr. {
        let u = 'store' {{'ptr', 'i8'}, {g.hello, [01]}, g.first} in
        r.done {g.names, [00]},
        done = λs. [00000000],
      })},
    }
    """
    result = read(source)
    names, first, none = (result.lookup((name,)) for name in ('names', 'first', 'none'))
    assert [ingot.address_path(f.value) for f in names.value.fields] == [('hello',), ('main',)]
    assert ingot.address_path(first.init) == ('hello',)
    assert none.init == parse("''")
    blocks = result.lookup(('main',)).region.blocks
    stored = blocks[0].lets[0].fields[1][1]
    assert ingot.address_path(stored.fields[0].value) == ('hello',)
    jumped = blocks[0].terminal.operands[0]
    assert [ingot.address_path(f.value) for f in jumped.fields] == [('names',), None]
    assert ingot.addresses(jumped) == [jumped.fields[0].value]


def test_reduction_first():
    """A program may wrap the ingot and use helpers; reduction removes them."""
    source = """
    (λd. {
      main = {type = {'function', {n = 'i32'}, 'i32'}, body = λg. λp. 'R' (λr. {
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
      main = {{type = {{'function', {{a = 'i32'}}, 'i32'}}, body = λg. λp. 'R' (λr. {{
        entry = {body},
        next = λb. b,
      }})}},
    }}"""


def entry(fields):
    return f'{{x = {fields}}}'


TAIL_CALL = 'A call that ends a function is bound and returned: let y = g.f {…} in y.'
ADDRESS = 'An address in a predef is a path g.l₁ ⋯ lₙ to a symbol of the ingot.'
STRUCT_OPERAND = "A struct operand is a predef: build a struct of run-time values with 'insertvalue'."
M_PATH = 'g names the symbols: an operand through g is g.l₁ ⋯ lₙ, a path to a symbol of the ingot.'


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        ('λg. {}', 'Not an ingot: an ingot is a namespace, a struct of entries and namespaces.'),
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
        (entry('{type = λy. y}'), 'A type holds no address: it is byte arrays and structs of them.'),
        (entry("{type = 'i8', init = λy. y}"), ADDRESS),
        (
            entry("{type = 'i32', body = λg. λp. 'R' (λr. {[00000000]})}"),
            "Entry 'x' has a body, so its type must be {'function', {x = t, ...}, t}.",
        ),
        (
            entry("{type = {'function', {'i32'}, 'i32'}}"),
            "A function type is {'function', {x = t, ...}, t}: labeled parameters, then the result.",
        ),
        (
            entry("{type = {'function', {}, 'i32'}, body = λg. [00000000]}"),
            "The body of 'x' must be λg. λp. 'R' (λr. {blocks}).",
        ),
        (
            entry("{type = {'function', {}, 'i32'}, body = λg. λp. [00000000]}"),
            "The body of 'x' must be λg. λp. 'R' (λr. {blocks}).",
        ),
        # The grammar.
        (
            wrap("'add' {'i32', 'mul' {'i32', p.a, p.a}, p.a}"),
            "'main' is not in ANF: An operand must be a path, a byte array or a struct of them: bind it with a let.",
        ),
        (
            wrap("let x = 'add' {'i32', {p.a}, p.a} in x"),
            STRUCT_OPERAND,
        ),
        (
            wrap('let x = g.helper {x = p.a} in {r.next x, [00]} x'),
            "'main' is not in ANF: An arm of a branch only jumps: r.l Q₁ ⋯ Qₙ.",
        ),
        (
            wrap('let x = g.helper {x = p.a} in {r.next x, x} x'),
            'An arm of a branch only jumps: r.l Q₁ ⋯ Qₙ, r a region.',
        ),
        (wrap('g.helper {x = p.a}'), TAIL_CALL),
        (wrap("'R' (λq. {λy. y})"), "'main' is not in ANF: Field 0 of a region is an expression, never a λ."),
        (wrap("'R' (λq. {})"), "'main' is not in ANF: A region holds a struct of blocks, at least one."),
        # Kinds.
        (wrap('p.z'), "'main' has no parameter 'z'; it has ['a']."),
        (wrap('p'), "p is never used whole: read an argument as p.l, l one of ['a']."),
        (wrap('r.next'), 'r.next takes 1 operands, one per parameter; the jump gives 0.'),
        (wrap('r.gone p.a'), "A jump names a block of 'r': one of ['entry', 'next']."),
        (wrap('let x = g.helper {x = r.next} in x'), 'r.l is a block: it only heads a jump.'),
        (wrap('g.nope'), M_PATH),
        (wrap('g'), M_PATH),
        (wrap('g.k.x'), M_PATH),
        (wrap('g.ns', extra="ns = {k = {type = 'i32', value = [00000000]}},"), M_PATH),
        (wrap('g.helper {x = [00000000]}'), TAIL_CALL),
        (
            wrap("let x = 'add' {'i32', p.a, p.a} in x.y"),
            "A value has no fields: read a field of a struct value with 'extractvalue'.",
        ),
        (
            wrap('let x = g.k {} in x'),
            'An instruction calls a function, g.l₁ ⋯ lₙ {...}, a path to a function of the ingot.',
        ),
        (wrap('let x = g.helper {} in x'), "The call to 'helper' must give ['x'], in order; it gives []."),
        (wrap('{r.next p.a, r.next p.a} g.k'), 'A branch condition is a value or an argument p.l.'),
        (wrap('p.a [00000000]'), 'Only a block r.l is applied at the end of a block.'),
        (wrap("'R' (λq. {[00000000], [00000000]})"), 'A block after field 0 needs a label, so a jump can name it.'),
        (
            wrap("let x = 'add' {'i32', p.a, p.a} in x [] (λq. {[00000000]})"),
            "'main' is not in ANF: An operand of a jump must be a path, a byte array or a struct of them: bind it with a let.",
        ),
        (wrap('{} p.a'), 'The program is stuck here: no rule can ever reduce this part.'),
        # An init or value λg. C holds addresses g.l₁ ⋯ lₙ of symbols, and nothing else free.
        (entry("{type = 'ptr', init = λg. g.nope}"), ADDRESS),
        ("{k = {type = 'i32', value = [00]}, x = {type = 'ptr', value = λg. {g.k.v}}}", ADDRESS),
        (
            entry("{type = 'ptr', value = λg. {λy. y}}"),
            'A predef holds byte arrays, addresses g.l₁ ⋯ lₙ and structs of them.',
        ),
        (
            entry("{type = 'ptr', init = {λy. y}}"),
            'An init is a predef: byte arrays and structs of them, or λg. C to hold symbol addresses g.l₁ ⋯ lₙ.',
        ),
        # Inside a struct operand, a path is a symbol address.
        (wrap("let u = 'store' {{'ptr', 'i32'}, {g.k, p.a}, g.k} in [00000000]"), STRUCT_OPERAND),
        (wrap("let x = 'add' {'i32', p.a, p.a} in let u = 'store' {{'i32'}, {x}, g.k} in x"), STRUCT_OPERAND),
        (wrap("let u = 'store' {{'ptr'}, {r.next}, g.k} in [00000000]"), STRUCT_OPERAND),
        (wrap('{g.nope, [01]}'), ADDRESS),
        (wrap('{g}'), ADDRESS),
        (wrap('r.next {p.a}'), STRUCT_OPERAND),
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
