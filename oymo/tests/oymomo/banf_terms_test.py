# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import pytest

from oymo.oymomo import terms
from oymo.oymomo.banf_terms import (
    Block,
    Branch,
    Call,
    Const,
    Data,
    FormError,
    Function,
    GetData,
    GetField,
    Jump,
    Let,
    MakeStruct,
    Module,
    PrimCall,
    Return,
    Signature,
    Var,
    form_of,
    show,
    verify,
)

I1, I8, I16, I32, I64 = (terms.name_to_form(name) for name in ('i1', 'i8', 'i16', 'i32', 'i64'))

ZERO = Const(bytes(4), I32)
ONE = Const(bytes([1, 0, 0, 0]), I32)
POINT = terms.Struct([terms.Field('x', I32), terms.Field('y', I32)])


def fact():
    return Function(
        'fact',
        I32,
        [
            Block(
                'entry',
                [('n', I32)],
                [Let('t0', PrimCall('eq_i32', [Var('n'), ZERO]))],
                Branch(Var('t0'), 'then0', [], 'else0', [Var('n')]),
            ),
            Block('then0', [], [], Return(ONE)),
            Block(
                'else0',
                [('n', I32)],
                [
                    Let('t1', PrimCall('sub_i32', [Var('n'), ONE])),
                    Let('t2', Call('fact', [Var('t1')])),
                    Let('t3', PrimCall('mul_i32', [Var('n'), Var('t2')])),
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
        '    t0 = prim.eq_i32(n, [00000000]:i32)\n'
        '    branch t0, then0(), else0(n)\n'
        '  then0():\n'
        '    return [01000000]:i32\n'
        '  else0(n: i32):\n'
        '    t1 = prim.sub_i32(n, [01000000]:i32)\n'
        '    t2 = fact(t1)\n'
        '    t3 = prim.mul_i32(n, t2)\n'
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
                    Let('t2', PrimCall('add_i32', [Var('t0'), Var('t1')])),
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
        '    t1 = putchar([41]:i8)\n'
        '    t2 = prim.add_i32(t0, t1)\n'
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


def test_form_of_each_op():
    module = imports_module()
    forms = {'n': I32, 'p': POINT}
    assert form_of(PrimCall('eq_i32', [Var('n'), ZERO]), forms, module) == I1
    assert form_of(PrimCall('zext_i8_i32', [Const(b'\x01', I8)]), forms, module) == I32
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
    with pytest.raises(FormError, match="'putchar' is not imported data"):
        form_of(GetData('putchar'), {}, module)
    with pytest.raises(FormError, match="'errno' is not a function"):
        form_of(Call('errno', []), {}, module)


def one_block(lets, terminator, params=(), return_form=I32):
    return Module([Function('f', return_form, [Block('entry', list(params), lets, terminator)])])


def test_verify_rejects_wrong_prim_operand_form():
    module = one_block([Let('t0', PrimCall('add_i32', [Const(b'\x01', I8), ZERO]))], Return(Var('t0')))
    with pytest.raises(FormError, match=r'prim.add_i32 expects a: i32, got i8'):
        verify(module)


def test_verify_rejects_wrong_argument_count():
    module = one_block([Let('t0', PrimCall('add_i32', [ZERO]))], Return(Var('t0')))
    with pytest.raises(FormError, match='takes 2 arguments, got 1'):
        verify(module)


def test_verify_rejects_wrong_return_form():
    with pytest.raises(FormError, match="'f' returns i32, got i8"):
        verify(one_block([], Return(Const(b'\x01', I8))))


def test_verify_rejects_non_i1_condition():
    with pytest.raises(FormError, match='must be i1'):
        verify(one_block([], Branch(ZERO, 'a', [], 'b', [])))


def test_verify_rejects_jump_to_entry_and_unknown_block():
    with pytest.raises(FormError, match='entry block'):
        verify(one_block([], Jump('entry', [])))
    with pytest.raises(FormError, match="Unknown block 'nowhere'"):
        verify(one_block([], Jump('nowhere', [])))


def test_verify_rejects_duplicate_names_and_closed_block_violation():
    with pytest.raises(FormError, match="Duplicate name 'n'"):
        verify(one_block([Let('n', GetData('x'))], Return(ZERO), params=[('n', I32)]))
    with pytest.raises(FormError, match="Unknown name 'n'"):
        verify(one_block([], Return(Var('n'))))
