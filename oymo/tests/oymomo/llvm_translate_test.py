# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import textwrap

import llvmlite.binding as llvm
import pytest

from oymo.oymomo import banf_prim, banf_translate, terms
from oymo.oymomo.banf_terms import Block, Branch, Const, Function, Module, Return, Var
from oymo.oymomo.grammar import parse
from oymo.oymomo.llvm_prims import DEFAULT_PRIMS
from oymo.oymomo.llvm_translate import LlvmTranslationError, Target, translate

TARGET = Target('x86_64-unknown-linux-gnu', '', DEFAULT_PRIMS)
HEADER = '; ModuleID = ""\ntarget triple = "x86_64-unknown-linux-gnu"\ntarget datalayout = ""\n\n'


def banf(defs, decls):
    """The BANF module of an oymomo program, written as its `module` form's fields and its body's fields."""
    return banf_translate.translate(parse(f'prim -> module: {{{decls}}} -> {{{defs}}}'))


def ir_text(defs, decls):
    text = str(translate(banf(defs, decls), TARGET))
    llvm.parse_assembly(text).verify()
    assert text.startswith(HEADER)
    return text.removeprefix(HEADER)


def ir_error(defs, decls):
    with pytest.raises(LlvmTranslationError) as info:
        translate(banf(defs, decls), TARGET)
    return info.value.message


def text(block):
    """A triple-quoted block, dedented and without its leading newline."""
    return textwrap.dedent(block).removeprefix('\n')


def test_default_prims_cover_banf_prims():
    assert DEFAULT_PRIMS.keys() == banf_prim.PRIMS.keys()


def test_fact():
    source = """
    fact = blocks -> {
      entry = args: {n = 'i32'} ->
        let t0 = prim.eq_i32 {a = args.n, b = [00000000]:'i32'} in
        if t0 then blocks.then0 {} else blocks.else0 {n = args.n},
      then0 = args: {} -> [01000000]:'i32',
      else0 = args: {n = 'i32'} ->
        let t1 = prim.sub_i32 {minuend = args.n, subtrahend = [01000000]:'i32'} in
        let t2 = module.fact {n = t1} in
        let t3 = prim.mul_i32 {a = args.n, b = t2} in
        t3,
    }
    """
    assert ir_text(source, "fact = => 'i32'") == text("""
        define i32 @"fact"(i32 %"n")
        {
        entry:
          %"t0" = icmp eq i32 %"n", 0
          br i1 %"t0", label %"then0", label %"else0"
        then0:
          ret i32 1
        else0:
          %"t1" = sub i32 %"n", 1
          %"t2" = call i32 @"fact"(i32 %"t1")
          %"t3" = mul i32 %"n", %"t2"
          ret i32 %"t3"
        }
    """)


def test_signature_data_and_get_data():
    decls = "putchar = {c = 'i8'} => 'i32', errno = 'i32', main = => 'i32'"
    source = """
    main = blocks -> {
      entry = args: {} ->
        let t0 = module.errno in
        let t1 = module.putchar {c = [41]:'i8'} in
        let t2 = prim.add_i32 {a = t0, b = t1} in
        t2,
    }
    """
    assert ir_text(source, decls) == text("""
        declare i32 @"putchar"(i8 %"c")

        @"errno" = external global i32
        define i32 @"main"()
        {
        entry:
          %"t0" = load i32, i32* @"errno"
          %"t1" = call i32 @"putchar"(i8 65)
          %"t2" = add i32 %"t0", %"t1"
          ret i32 %"t2"
        }
    """)


def test_struct_param_make_struct_and_get_field():
    source = """
    swap = blocks -> {
      entry = args: {p = {x = 'i32', y = 'i32'}} ->
        let x = args.p.x in
        let y = args.p.y in
        let q = {x = y, y = x} in
        q,
    }
    """
    assert ir_text(source, "swap = => {x = 'i32', y = 'i32'}") == text("""
        define {i32, i32} @"swap"({i32, i32} %"p")
        {
        entry:
          %"x" = extractvalue {i32, i32} %"p", 0
          %"y" = extractvalue {i32, i32} %"p", 1
          %"q.x" = insertvalue {i32, i32} undef, i32 %"y", 0
          %"q" = insertvalue {i32, i32} %"q.x", i32 %"x", 1
          ret {i32, i32} %"q"
        }
    """)


def test_single_predecessor_binds_params_and_multiple_predecessors_get_phis():
    # Both branches jump to join0, which therefore gets a phi per param.
    source = """
    pick = blocks -> {
      entry = args: {c = 'i1', x = 'i32', z = 'i32'} -> if args.c then blocks.a {x = args.x} else blocks.b {},
      a = args: {x = 'i32'} -> blocks.join0 {v = args.x, w = args.x},
      b = args: {} -> blocks.join0 {v = [00000000]:'i32', w = [07000000]:'i32'},
      join0 = args: {v = 'i32', w = 'i32'} -> let t0 = prim.add_i32 {a = args.v, b = args.w} in t0,
    }
    """
    assert ir_text(source, "pick = => 'i32'") == text("""
        define i32 @"pick"(i1 %"c", i32 %"x", i32 %"z")
        {
        entry:
          br i1 %"c", label %"a", label %"b"
        a:
          br label %"join0"
        b:
          br label %"join0"
        join0:
          %"v" = phi  i32 [%"x", %"a"], [0, %"b"]
          %"w" = phi  i32 [%"x", %"a"], [7, %"b"]
          %"t0" = add i32 %"v", %"w"
          ret i32 %"t0"
        }
    """)


def test_rejects_branch_with_same_target_twice():
    # oymomo translation already rejects this, so the module is built directly.
    i1, i8 = terms.name_to_form('i1'), terms.name_to_form('i8')
    function = Function(
        'g',
        i8,
        [
            Block('entry', [('c', i1)], [], Branch(Var('c'), 'a', [], 'a', [])),
            Block('a', [], [], Return(Const(b'\x01', i8))),
        ],
    )
    with pytest.raises(LlvmTranslationError, match='same block as both targets'):
        translate(Module([function]), TARGET)


def test_constants_are_little_endian_on_a_big_endian_target():
    module = banf("g = blocks -> {entry = args: {} -> [0100]:'i16'}", "g = => 'i16'")
    big = Target('powerpc64-unknown-linux-gnu', 'E-m:e-i64:64-n32:64', DEFAULT_PRIMS)
    ir = str(translate(module, big))
    llvm.parse_assembly(ir).verify()
    assert 'target datalayout = "E-m:e-i64:64-n32:64"' in ir
    assert 'ret i16 1' in ir


def test_rejects_wrong_constant_size():
    assert ir_error("g = blocks -> {entry = args: {} -> [01]:'i32'}", "g = => 'i32'") == 'A i32 constant needs 4 bytes.'


def test_let_form_with_the_same_llvm_type_is_used_as_it_is():
    source = """
    g = blocks -> {
      entry = args: {v = 'i32', w = 'i32'} -> let q: {a = 'i32', b = 'i32'} = {x = args.v, y = args.w} in q,
    }
    """
    assert 'ret {i32, i32} %"q"' in ir_text(source, "g = => {a = 'i32', b = 'i32'}")


def test_rejects_let_form_with_another_llvm_type():
    # BANF accepts any let form, but LLVM never converts: no bitcast, no widening.
    source = """
    g = blocks -> {
      entry = args: {n = 'i32'} -> let t0: 'i32' = prim.eq_i32 {a = args.n, b = [00000000]:'i32'} in t0,
    }
    """
    assert ir_error(source, "g = => 'i32'") == "Let 't0' is formed as i32, but its op gives i1."


def test_formed_var_with_the_same_llvm_type_is_used_as_it_is():
    assert 'ret i32 %"n"' in ir_text("g = blocks -> {entry = args: {n = 'i32'} -> args.n:'i32'}", "g = => 'i32'")


def test_rejects_formed_var_with_another_llvm_type():
    source = "g = blocks -> {entry = args: {n = 'i8'} -> args.n:'i32'}"
    assert ir_error(source, "g = => 'i32'") == "'n' is formed as i32, but its LLVM type is i8."


def test_defined_data_is_a_writable_global_with_an_initializer():
    source = """
    answer = [2a000000],
    main = blocks -> {entry = args: {} -> let t = module.answer in t},
    """
    assert ir_text(source, "answer = 'i32', main = => 'i32'") == text("""
        @"answer" = global i32 42
        define i32 @"main"()
        {
        entry:
          %"t" = load i32, i32* @"answer"
          ret i32 %"t"
        }
    """)


def test_rejects_defined_data_with_a_wrong_byte_count():
    assert ir_error('answer = [2a]', "answer = 'i32'") == 'A i32 constant needs 4 bytes.'


def test_rejects_defined_data_with_a_struct_form():
    assert (
        ir_error('p = [0102]', "p = {x = 'i8', y = 'i8'}")
        == 'Only integer constants are supported, got {x: i8, y: i8}.'
    )
