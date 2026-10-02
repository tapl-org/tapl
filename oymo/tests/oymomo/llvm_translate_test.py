# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import llvmlite.binding as llvm
import pytest

from oymo.oymomo import banf_prim, terms
from oymo.oymomo.banf_terms import (
    Block,
    Branch,
    Call,
    Const,
    Data,
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
)
from oymo.oymomo.llvm_prims import DEFAULT_PRIMS
from oymo.oymomo.llvm_translate import LlvmTranslationError, Target, translate

TARGET = Target('x86_64-unknown-linux-gnu', '', 'little', DEFAULT_PRIMS)
POINT = terms.StructForm([('x', 'i32'), ('y', 'i32')])
ZERO = Const(bytes(4), 'i32')
ONE = Const(bytes([1, 0, 0, 0]), 'i32')


def fact():
    return Function(
        'fact',
        'i32',
        [
            Block(
                'entry',
                [('n', 'i32')],
                [Let('t0', PrimCall('eq_i32', [Var('n'), ZERO]))],
                Branch(Var('t0'), 'then0', [], 'else0', [Var('n')]),
            ),
            Block('then0', [], [], Return(ONE)),
            Block(
                'else0',
                [('n', 'i32')],
                [
                    Let('t1', PrimCall('sub_i32', [Var('n'), ONE])),
                    Let('t2', Call('fact', [Var('t1')])),
                    Let('t3', PrimCall('mul_i32', [Var('n'), Var('t2')])),
                ],
                Return(Var('t3')),
            ),
        ],
    )


def imports_module():
    lets = [
        Let('t0', GetData('errno')),
        Let('t1', Call('putchar', [Const(bytes([0x41]), 'i8')])),
        Let('t2', PrimCall('add_i32', [Var('t0'), Var('t1')])),
    ]
    main = Function('main', 'i32', [Block('entry', [], lets, Return(Var('t2')))])
    return Module([Signature('putchar', [('c', 'i8')], 'i32'), Data('errno', 'i32'), main])


HEADER = '; ModuleID = ""\ntarget triple = "x86_64-unknown-linux-gnu"\ntarget datalayout = ""\n\n'


def ir_text(module):
    text = str(translate(module, TARGET))
    llvm.parse_assembly(text).verify()
    assert text.startswith(HEADER)
    return text.removeprefix(HEADER)


def test_default_prims_cover_banf_prims():
    assert DEFAULT_PRIMS.keys() == banf_prim.PRIMS.keys()


def test_fact():
    assert ir_text(Module([fact()])) == (
        'define i32 @"fact"(i32 %"n")\n'
        '{\n'
        'entry:\n'
        '  %"t0" = icmp eq i32 %"n", 0\n'
        '  br i1 %"t0", label %"then0", label %"else0"\n'
        'then0:\n'
        '  ret i32 1\n'
        'else0:\n'
        '  %"t1" = sub i32 %"n", 1\n'
        '  %"t2" = call i32 @"fact"(i32 %"t1")\n'
        '  %"t3" = mul i32 %"n", %"t2"\n'
        '  ret i32 %"t3"\n'
        '}\n'
    )


def test_signature_data_and_get_data():
    assert ir_text(imports_module()) == (
        'declare i32 @"putchar"(i8 %"c")\n'
        '\n'
        '@"errno" = external global i32\n'
        'define i32 @"main"()\n'
        '{\n'
        'entry:\n'
        '  %"t0" = load i32, i32* @"errno"\n'
        '  %"t1" = call i32 @"putchar"(i8 65)\n'
        '  %"t2" = add i32 %"t0", %"t1"\n'
        '  ret i32 %"t2"\n'
        '}\n'
    )


def test_struct_param_make_struct_and_get_field():
    function = Function(
        'swap',
        POINT,
        [
            Block(
                'entry',
                [('p', POINT)],
                [
                    Let('x', GetField(Var('p'), 'x')),
                    Let('y', GetField(Var('p'), 'y')),
                    Let('q', MakeStruct([('x', Var('y')), ('y', Var('x'))])),
                ],
                Return(Var('q')),
            )
        ],
    )
    assert ir_text(Module([function])) == (
        'define {i32, i32} @"swap"({i32, i32} %"p")\n'
        '{\n'
        'entry:\n'
        '  %"x" = extractvalue {i32, i32} %"p", 0\n'
        '  %"y" = extractvalue {i32, i32} %"p", 1\n'
        '  %"q.x" = insertvalue {i32, i32} undef, i32 %"y", 0\n'
        '  %"q" = insertvalue {i32, i32} %"q.x", i32 %"x", 1\n'
        '  ret {i32, i32} %"q"\n'
        '}\n'
    )


def pick():
    """Both branches jump to join0, which therefore gets a phi per param."""
    return Function(
        'pick',
        'i32',
        [
            Block('entry', [('c', 'i1'), ('x', 'i32'), ('z', 'i32')], [], Branch(Var('c'), 'a', [Var('x')], 'b', [])),
            Block('a', [('x', 'i32')], [], Jump('join0', [Var('x'), Var('x')])),
            Block('b', [], [], Jump('join0', [Const(bytes(4), 'i32'), Const(bytes([7, 0, 0, 0]), 'i32')])),
            Block(
                'join0',
                [('v', 'i32'), ('w', 'i32')],
                [Let('t0', PrimCall('add_i32', [Var('v'), Var('w')]))],
                Return(Var('t0')),
            ),
        ],
    )


def test_single_predecessor_binds_params_and_multiple_predecessors_get_phis():
    assert ir_text(Module([pick()])) == (
        'define i32 @"pick"(i1 %"c", i32 %"x", i32 %"z")\n'
        '{\n'
        'entry:\n'
        '  br i1 %"c", label %"a", label %"b"\n'
        'a:\n'
        '  br label %"join0"\n'
        'b:\n'
        '  br label %"join0"\n'
        'join0:\n'
        '  %"v" = phi  i32 [%"x", %"a"], [0, %"b"]\n'
        '  %"w" = phi  i32 [%"x", %"a"], [7, %"b"]\n'
        '  %"t0" = add i32 %"v", %"w"\n'
        '  ret i32 %"t0"\n'
        '}\n'
    )


def test_rejects_branch_with_same_target_twice():
    function = Function(
        'g',
        'i8',
        [
            Block('entry', [('c', 'i1')], [], Branch(Var('c'), 'a', [], 'a', [])),
            Block('a', [], [], Return(Const(b'\x01', 'i8'))),
        ],
    )
    with pytest.raises(LlvmTranslationError, match='same block as both targets'):
        translate(Module([function]), TARGET)


def test_big_endian_constants():
    function = Function('g', 'i16', [Block('entry', [], [], Return(Const(bytes([1, 0]), 'i16')))])
    big = Target('x86_64-unknown-linux-gnu', '', 'big', DEFAULT_PRIMS)
    assert 'ret i16 256' in str(translate(Module([function]), big))


def test_rejects_wrong_constant_size():
    function = Function('g', 'i32', [Block('entry', [], [], Return(Const(b'\x01', 'i32')))])
    with pytest.raises(LlvmTranslationError, match='needs 4 bytes'):
        translate(Module([function]), TARGET)
