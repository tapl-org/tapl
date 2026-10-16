# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import banf_translate, terms
from oymo.oymomo.banf_terms import (
    Block,
    Branch,
    Call,
    Const,
    Data,
    FormError,
    FormField,
    Function,
    GetData,
    GetField,
    GetIndex,
    Jump,
    Let,
    MakeStruct,
    Module,
    OpcodeCall,
    Return,
    Signature,
    Switch,
    Var,
    atom_form,
    form_of,
    let_form,
    show,
    show_form,
    show_op,
    verify,
)
from oymo.oymomo.grammar import parse

I1, I8, I16, I32, I64 = (terms.ByteArray(name) for name in (b'i1', b'i8', b'i16', b'i32', b'i64'))

ZERO = Const(bytes(4), I32)
ONE = Const(bytes([1, 0, 0, 0]), I32)


def field(form):
    """A form as an opcode field: a bare byte array, a `Const` with no form."""
    return Const(form.value, terms.Empty)


POINT = terms.Struct([terms.Field('x', I32), terms.Field('y', I32)])


def fact():
    return Function(
        'fact',
        I32,
        [
            Block(
                'entry',
                [('n', I32)],
                [Let('t0', OpcodeCall('icmp_eq', [field(I32), Var('n'), ZERO], I1))],
                Branch(Var('t0'), 'then0', [], 'else0', [Var('n')]),
            ),
            Block('then0', [], [], Return(ONE)),
            Block(
                'else0',
                [('n', I32)],
                [
                    Let('t1', OpcodeCall('sub', [field(I32), Var('n'), ONE], I32)),
                    Let('t2', Call('fact', [Var('t1')])),
                    Let('t3', OpcodeCall('mul', [field(I32), Var('n'), Var('t2')], I32)),
                ],
                Return(Var('t3')),
            ),
        ],
    )


def test_show_fact():
    module = Module([fact()])
    verify(module)
    assert show(module) == (
        'fact: i32\n'
        '  entry(n: i32):\n'
        "    t0 = icmp_eq 'i32', n, [00000000]:i32\n"
        '    branch t0, then0(), else0(n)\n'
        '  then0():\n'
        '    return [01000000]:i32\n'
        '  else0(n: i32):\n'
        "    t1 = sub 'i32', n, [01000000]:i32\n"
        '    t2 = call fact(t1)\n'
        "    t3 = mul 'i32', n, t2\n"
        '    return t3\n'
    )


def imports_module():
    main = Function(
        'main',
        I32,
        [
            Block(
                'entry',
                [],
                [
                    Let('t0', GetData('errno')),
                    Let('t1', Call('putchar', [Const(bytes([0x41]), I8)])),
                    Let('t2', OpcodeCall('add', [field(I32), Var('t0'), Var('t1')], I32)),
                ],
                Return(Var('t2')),
            )
        ],
    )
    return Module([Signature('putchar', [('c', I8)], I32), Data('errno', I32), main])


def test_show_signature_data_and_get_data():
    module = imports_module()
    verify(module)
    assert show(module) == (
        'putchar(c: i8): i32\n'
        'errno: i32\n'
        '\n'
        'main: i32\n'
        '  entry():\n'
        '    t0 = errno\n'
        '    t1 = call putchar([41]:i8)\n'
        "    t2 = add 'i32', t0, t1\n"
        '    return t2\n'
    )


def test_show_struct_ops_and_jump():
    function = Function(
        'swap',
        POINT,
        [
            Block('entry', [('p', POINT)], [], Jump('body', [Var('p')])),
            Block(
                'body',
                [('p', POINT)],
                [
                    Let('x', GetField(Var('p'), 'x')),
                    Let('y', GetField(Var('p'), 'y')),
                    Let('q', MakeStruct([('x', Var('y')), ('y', Var('x'))])),
                ],
                Return(Var('q')),
            ),
        ],
    )
    module = Module([function])
    verify(module)
    assert show(module) == (
        'swap: {x: i32, y: i32}\n'
        '  entry(p: {x: i32, y: i32}):\n'
        '    jump body(p)\n'
        '  body(p: {x: i32, y: i32}):\n'
        '    x = p.x\n'
        '    y = p.y\n'
        '    q = {x = y, y = x}\n'
        '    return q\n'
    )


def test_show_quotes_names():
    module = Module([Data('my data', I8)])
    assert show(module) == '"my data": i8\n'


def test_show_defined_data():
    assert show(Module([Data('answer', I32, b'\x2a\x00\x00\x00')])) == 'answer: i32 = [2a000000]\n'


def test_show_form():
    assert show_form(terms.Empty) == ''
    assert show_form(I32) == 'i32'
    assert show_form(POINT) == '{x: i32, y: i32}'
    assert show_form(terms.FunctionForm(I8, I32)) == '(i8 => i32)'
    assert show_form(terms.FunctionForm(terms.Empty, I32)) == '(=> i32)'
    assert show_form(terms.Struct([terms.Field('f', terms.FunctionForm(terms.Empty, I32))])) == '{f: => i32}'


def test_form_of_each_op():
    module = imports_module()
    forms = {'n': I32, 'p': POINT}
    assert form_of(OpcodeCall('icmp_eq', [field(I32), Var('n'), ZERO], I1), forms, module) == I1
    assert form_of(OpcodeCall('zext', [field(I8), Const(b'\x01', I8), field(I32)], I32), forms, module) == I32
    assert form_of(Call('putchar', [Const(b'\x41', I8)]), forms, module) == I32
    assert form_of(MakeStruct([('a', Var('n')), ('b', Var('p'))]), forms, module) == terms.Struct(
        [terms.Field('a', I32), terms.Field('b', POINT)]
    )
    assert form_of(GetField(Var('p'), 'y'), forms, module) == I32
    assert form_of(GetData('errno'), forms, module) == I32


def test_form_of_errors():
    module = imports_module()
    with pytest.raises(FormError, match="no field 'z'"):
        form_of(GetField(Var('p'), 'z'), {'p': POINT}, module)
    with pytest.raises(FormError, match="Unknown name 'q'"):
        form_of(GetField(Var('q'), 'x'), {}, module)
    with pytest.raises(FormError, match="'putchar' is not data"):
        form_of(GetData('putchar'), {}, module)
    with pytest.raises(FormError, match="'errno' is not a function"):
        form_of(Call('errno', []), {}, module)


XY = terms.Struct([terms.Field('x', I32), terms.Field('y', I8)])


def test_form_of_get_index():
    assert form_of(GetIndex(Var('p'), 1), {'p': XY}, imports_module()) == I8
    assert form_of(GetIndex(Var('p'), 0), {'p': XY}, imports_module()) == I32
    # Unlabeled fields are reached the same way.
    unlabeled = terms.Struct([terms.Field('', I8), terms.Field('', I64)])
    assert form_of(GetIndex(Var('p'), 1), {'p': unlabeled}, imports_module()) == I64
    # Past the last field: the last field, as in reduction.
    assert form_of(GetIndex(Var('p'), 2), {'p': XY}, imports_module()) == I8
    assert form_of(GetIndex(Var('p'), 256), {'p': XY}, imports_module()) == I8


def test_show_get_index():
    assert show_op(GetIndex(Var('p'), 1)) == 'p.1'
    # A label written as digits is quoted, so the two never print the same.
    assert show_op(GetField(Var('p'), '1')) == 'p."1"'


@pytest.mark.parametrize(
    ('form', 'index', 'message'),
    [
        (terms.Struct([]), 0, 'Form {} has no field at index 0.'),
        (I32, 0, 'Form i32 has no field at index 0.'),
    ],
)
def test_get_index_errors_are_form_errors(form, index, message):
    location = terms.Location(3, 9)
    with pytest.raises(FormError) as info:
        form_of(GetIndex(Var('p'), index, location), {'p': form}, imports_module())
    assert info.value.message == message
    assert info.value.location == location


def test_verify_checks_get_index():
    params = [('p', XY)]
    verify(one_block([Let('t0', GetIndex(Var('p'), 0))], Return(Var('t0')), params))
    with pytest.raises(FormError, match='has no field at index 0'):
        verify(one_block([Let('t0', GetIndex(Var('p'), 0))], Return(Var('t0')), [('p', I32)]))
    # The i8 fields returned from an i32 function: the return form is not compared.
    verify(one_block([Let('t0', GetIndex(Var('p'), 1))], Return(Var('t0')), params))
    verify(one_block([Let('t0', GetIndex(Var('p'), 2))], Return(Var('t0')), params))


def one_block(lets, terminator, params=(), return_form=I32):
    return Module([Function('f', return_form, [Block('entry', list(params), lets, terminator)])])


def test_verify_does_not_compare_opcode_operand_form():
    verify(one_block([Let('t0', OpcodeCall('add', [field(I32), Const(b'\x01', I8), ZERO], I32))], Return(Var('t0'))))


@pytest.mark.parametrize(
    'op',
    [
        OpcodeCall('add', [field(I1), ZERO, ZERO], I1),
        OpcodeCall('zext', [field(I32), ZERO, field(I8)], I8),
        OpcodeCall('add', [field(I32), ZERO], I32),
    ],
)
def test_verify_leaves_opcode_fields_to_the_opcode(op):
    # Any forms, any number of fields: the opcode reads them, and the backend may reject them.
    verify(one_block([Let('t0', op)], Return(Var('t0'))))


PTR = terms.ByteArray(b'ptr')


def test_a_pointer_can_not_be_a_literal():
    with pytest.raises(FormError, match="A pointer can't be a literal"):
        verify(one_block([], Return(Const(bytes(8), PTR)), return_form=PTR))


def test_show_memory_opcodes():
    alloca = OpcodeCall('alloca', [FormField(POINT)], PTR)
    assert show_op(alloca) == 'alloca {x: i32, y: i32}'
    gep = OpcodeCall('getelementptr', [FormField(POINT), Var('q'), Const(bytes(8), I64), ONE], PTR)
    assert show_op(gep) == 'getelementptr {x: i32, y: i32}, q, [0000000000000000]:i64, [01000000]:i32'
    assert show_op(OpcodeCall('alloca', [field(I32)], PTR)) == "alloca 'i32'"
    # A form field is not a name: the verifier doesn't look it up.
    verify(one_block([Let('q', alloca)], Return(Var('q')), return_form=PTR))


STORE_RESULT = terms.Struct([])


def _store_then(terminator, *lets):
    """`p = alloca i32; s = store [00000000]:i32, p`, then `lets` and `terminator`."""
    return one_block(
        [
            Let('p', OpcodeCall('alloca', [field(I32)], PTR)),
            Let('s', OpcodeCall('store', [ZERO, Var('p')], STORE_RESULT)),
            *lets,
        ],
        terminator,
    )


def test_show_and_verify_load_and_store():
    load = Let('v', OpcodeCall('load', [field(I32), Var('p')], I32))
    module = _store_then(Return(Var('v')), load)
    verify(module)
    assert show(module) == (
        "f: i32\n  entry():\n    p = alloca 'i32'\n    s = store [00000000]:i32, p\n"
        "    v = load 'i32', p\n    return v\n"
    )


@pytest.mark.parametrize(
    ('lets', 'terminator'),
    [
        ([], Return(Var('s'))),
        ([Let('t', MakeStruct([('a', Var('s'))]))], Return(ZERO)),
        ([Let('v', OpcodeCall('load', [field(I32), Var('s')], I32))], Return(Var('v'))),
    ],
)
def test_a_store_result_is_used_nowhere(lets, terminator):
    with pytest.raises(FormError, match=r"'s' is the result of a store; only \$seq can use it\."):
        verify(_store_then(terminator, *lets))


@pytest.mark.parametrize(
    ('op', 'message'),
    [
        (OpcodeCall('store', [ZERO], STORE_RESULT), "'store' takes 2 fields, got 1."),
        (OpcodeCall('load', [field(I32), Var('p'), ZERO], I32), "'load' takes 2 fields, got 3."),
        (OpcodeCall('load', [field(I32), Var('n')], I32), "'load' expects ptr: ptr, got i32."),
        (OpcodeCall('store', [ZERO, Var('n')], STORE_RESULT), "'store' expects ptr: ptr, got i32."),
        (OpcodeCall('load', [field(I32), field(I32)], I32), "'load' expects ptr: ptr, got a bare byte array."),
        (
            OpcodeCall('store', [field(I32), Var('p')], STORE_RESULT),
            "'store': value must have a form, such as [01000000]~'i32'.",
        ),
    ],
)
def test_load_and_store_errors(op, message):
    module = one_block([Let('t', op)], Return(ZERO), params=[('p', PTR), ('n', I32)])
    with pytest.raises(FormError) as info:
        verify(module)
    assert info.value.message == message


def test_verify_rejects_unknown_opcode_and_name():
    with pytest.raises(FormError, match="Unknown opcode 'foo'"):
        verify(one_block([Let('t0', OpcodeCall('foo', [ZERO], I32))], Return(Var('t0'))))
    with pytest.raises(FormError, match="Unknown name 'n'"):
        verify(one_block([Let('t0', OpcodeCall('add', [field(I32), Var('n'), ZERO], I32))], Return(Var('t0'))))


def test_verify_does_not_compare_return_form():
    verify(one_block([], Return(Const(b'\x01', I8))))


def test_verify_does_not_compare_condition_form():
    entry = Block('entry', [], [], Branch(ZERO, 'a', [], 'b', []))
    a, b = Block('a', [], [], Return(ZERO)), Block('b', [], [], Return(ZERO))
    verify(Module([Function('f', I32, [entry, a, b])]))


def test_verify_rejects_jump_to_entry_and_unknown_block():
    with pytest.raises(FormError, match='entry block'):
        verify(one_block([], Jump('entry', [])))
    with pytest.raises(FormError, match="Unknown block 'nowhere'"):
        verify(one_block([], Jump('nowhere', [])))


def switch_module(selector_form, terminator):
    """`entry` takes a selector `k` of the oymomo form `selector_form` and an `x`, and ends
    with `terminator`. `a` and `b` take nothing and return zero; `c` takes an i32 and
    returns it. Oymomo source can't write a switch yet, so `entry` is written as a jump and
    its terminator replaced."""
    source = f"""
    module~{{f = => 'i32'}} -> {{f = f -> {{
      entry = args~{{k = {selector_form}, x = 'i32'}} -> f.a {{}},
      a = args~{{}} -> [00000000]~'i32',
      b = args~{{}} -> [00000000]~'i32',
      c = args~{{x = 'i32'}} -> args.x,
    }}}}
    """
    module = banf_translate.translate(parse(source))
    function = module.bindings[0]
    assert isinstance(function, Function)
    function.blocks[0].terminator = terminator
    return module


THREE_WAY = Switch(Var('k'), [('a', []), ('b', []), ('c', [Var('x')])])


def test_show_switch():
    module = switch_module("'i8'", THREE_WAY)
    verify(module)
    assert show(module).splitlines()[2] == '    switch k, a(), b(), c(x)'


def test_verify_accepts_any_selector_form():
    # BANF puts nothing on the selector's form, as reduction puts nothing on an index.
    verify(switch_module("'i1'", THREE_WAY))
    verify(switch_module("{x = 'i8'}", THREE_WAY))


def test_verify_checks_switch_targets():
    with pytest.raises(FormError, match='Block c takes 1 arguments, got 0'):
        verify(switch_module("'i8'", Switch(Var('k'), [('a', []), ('c', [])])))
    with pytest.raises(FormError, match='Block b takes 0 arguments, got 1'):
        verify(switch_module("'i8'", Switch(Var('k'), [('a', []), ('b', [Var('x')])])))
    with pytest.raises(FormError, match="Unknown block 'nowhere'"):
        verify(switch_module("'i8'", Switch(Var('k'), [('a', []), ('nowhere', [])])))
    with pytest.raises(FormError, match='entry block'):
        verify(switch_module("'i8'", Switch(Var('k'), [('a', []), ('entry', [])])))
    with pytest.raises(FormError, match="Unknown name 'j'"):
        verify(switch_module("'i8'", Switch(Var('j'), [('a', []), ('b', [])])))
    with pytest.raises(FormError, match='A switch needs a target'):
        verify(switch_module("'i8'", Switch(Var('k'), [])))


def test_verify_checks_args_to_a_repeated_switch_target():
    verify(switch_module("'i8'", Switch(Var('k'), [('c', [Var('x')]), ('a', []), ('c', [Var('x')])])))
    with pytest.raises(FormError, match="A switch passes different args to 'c'"):
        verify(switch_module("'i8'", Switch(Var('k'), [('c', [Var('x')]), ('a', []), ('c', [ZERO])])))


def test_formed_var_has_the_written_form():
    # n is i8; n:i32 is i32, unchecked, so it can be passed where i32 is expected.
    assert atom_form(Var('n', I32), {'n': I8}) == I32
    assert atom_form(Var('n'), {'n': I8}) == I8
    with pytest.raises(FormError, match="Unknown name 'm'"):
        atom_form(Var('m', I32), {})
    module = one_block(
        [Let('t0', OpcodeCall('add', [field(I32), Var('n', I32), ZERO], I32))], Return(Var('t0')), params=[('n', I8)]
    )
    verify(module)
    assert show(module).splitlines()[2] == "    t0 = add 'i32', n:i32, [00000000]:i32"


def test_let_form_replaces_op_form():
    # icmp_eq gives i1; the written i32 replaces it, and the return is checked against i32.
    let = Let('t0', OpcodeCall('icmp_eq', [field(I32), ZERO, ZERO], I1), I32)
    module = one_block([let], Return(Var('t0')))
    verify(module)
    assert let_form(let, {}, module) == I32
    assert let_form(Let('t0', OpcodeCall('icmp_eq', [field(I32), ZERO, ZERO], I1)), {}, module) == I1
    assert show(module).splitlines()[2] == "    t0: i32 = icmp_eq 'i32', [00000000]:i32, [00000000]:i32"


def test_verify_rejects_duplicate_names_and_closed_block_violation():
    with pytest.raises(FormError, match="Duplicate name 'n'"):
        verify(one_block([Let('n', GetData('x'))], Return(ZERO), params=[('n', I32)]))
    with pytest.raises(FormError, match="Unknown name 'n'"):
        verify(one_block([], Return(Var('n'))))


def _tagged(tag, *parts):
    return terms.Struct([terms.Field('', terms.ByteArray(tag.encode())), *parts])


def _count(n):
    return terms.Field('', terms.Formed(terms.ByteArray(n.to_bytes(4, 'little')), I32))


@pytest.mark.parametrize(
    ('form', 'shown'),
    [
        (_tagged('array', _count(3), terms.Field('', I32)), '[3 x i32]'),
        (_tagged('vector', _count(4), terms.Field('', I32)), '<4 x i32>'),
        (_tagged('scalable_vector', _count(4), terms.Field('', I32)), '<vscale x 4 x i32>'),
        (_tagged('packed', terms.Field('', I8), terms.Field('', I32)), '<{i8, i32}>'),
        # A packed struct keeps its field labels, as a struct does.
        (_tagged('packed', terms.Field('a', I8), terms.Field('b', I32)), '<{a: i8, b: i32}>'),
        (
            terms.Struct([terms.Field('p', _tagged('array', _count(2), terms.Field('', POINT)))]),
            '{p: [2 x {x: i32, y: i32}]}',
        ),
        # Not a tag, or malformed: printed as the struct it is.
        (terms.Struct([terms.Field('', I32), terms.Field('x', I8)]), '{i32, x: i8}'),
        (_tagged('array', terms.Field('', I32)), '{array, i32}'),
    ],
)
def test_show_tagged_forms(form, shown):
    assert show_form(form) == shown
