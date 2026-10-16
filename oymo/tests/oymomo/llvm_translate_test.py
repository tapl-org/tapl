# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ctypes
import itertools
import textwrap

import llvmlite.binding as llvm
import pytest
from llvmlite import ir

from oymo.oymomo import banf_terms, banf_translate, opcodes, terms
from oymo.oymomo.grammar import parse
from oymo.oymomo.llvm_opcodes import DEFAULT_OPCODES
from oymo.oymomo.llvm_translate import LlvmTranslationError, Target, translate

TARGET = Target('x86_64-unknown-linux-gnu', '', DEFAULT_OPCODES)
HEADER = '; ModuleID = ""\ntarget triple = "x86_64-unknown-linux-gnu"\ntarget datalayout = ""\n\n'


def banf(defs, decls):
    """The BANF module of an oymomo program, written as its `module` form's fields and its body's fields."""
    return banf_translate.translate(parse(f'module~{{{decls}}} -> {{{defs}}}'))


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


def test_default_opcodes_cover_opcodes():
    assert DEFAULT_OPCODES.keys() == opcodes.OPCODES.keys()


def test_fact():
    source = """
    fact = f -> {
      entry = args~{n = 'i32'} ->
        let t0 = 'icmp_eq' {'i32', args.n, [00000000]~'i32'} in
        if t0 then f.then0 {} else f.else0 {n = args.n},
      then0 = args~{} -> [01000000]~'i32',
      else0 = args~{n = 'i32'} ->
        let t1 = 'sub' {'i32', args.n, [01000000]~'i32'} in
        let t2 = module.fact {n = t1} in
        let t3 = 'mul' {'i32', args.n, t2} in
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
    main = f -> {
      entry = args~{} ->
        let t0 = module.errno in
        let t1 = module.putchar {c = [41]~'i8'} in
        let t2 = 'add' {'i32', t0, t1} in
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


def test_seq_leaves_no_trace():
    decls = "putchar = {c = 'i32'} => 'i32', main = => 'i32'"
    source = """
    main = f -> {
      entry = args~{} ->
        let q = module.putchar {c = [68000000]~'i32'} in
        let r = module.putchar {c = $seq {q, [69000000]~'i32'}} in
        r,
    }
    """
    assert ir_text(source, decls) == text("""
        declare i32 @"putchar"(i32 %"c")

        define i32 @"main"()
        {
        entry:
          %"q" = call i32 @"putchar"(i32 104)
          %"r" = call i32 @"putchar"(i32 105)
          ret i32 %"r"
        }
    """)


def test_struct_param_make_struct_and_get_field():
    source = """
    swap = f -> {
      entry = args~{p = {x = 'i32', y = 'i32'}} ->
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


def test_make_struct_names_an_unlabeled_field_by_its_index():
    source = """
    pair = f -> {
      entry = args~{a = 'i32', b = 'i8'} ->
        let q = {args.a, y = args.b, args.a} in
        q,
    }
    """
    assert ir_text(source, "pair = => {'i32', y = 'i8', 'i32'}") == text("""
        define {i32, i8, i32} @"pair"(i32 %"a", i8 %"b")
        {
        entry:
          %"q.0" = insertvalue {i32, i8, i32} undef, i32 %"a", 0
          %"q.y" = insertvalue {i32, i8, i32} %"q.0", i8 %"b", 1
          %"q" = insertvalue {i32, i8, i32} %"q.y", i32 %"a", 2
          ret {i32, i8, i32} %"q"
        }
    """)


def test_get_index_is_extractvalue():
    def first(read):
        source = f"g = f -> {{entry = args~{{p = {{x = 'i32', y = 'i8'}}}} -> let x = {read} in x}}"
        return ir_text(source, "g = => 'i32'")

    expected = text("""
        define i32 @"g"({i32, i8} %"p")
        {
        entry:
          %"x" = extractvalue {i32, i8} %"p", 0
          ret i32 %"x"
        }
    """)
    assert first('args.p [00]') == expected
    assert first('args.p.x') == expected


def test_get_index_on_an_unlabeled_struct():
    source = "g = f -> {entry = args~{p = {'i32', 'i8'}} -> let y = args.p [01] in y}"
    assert '%"y" = extractvalue {i32, i8} %"p", 1' in ir_text(source, "g = => 'i8'")


def test_get_index_past_the_last_field_extracts_the_last_field():
    source = "g = f -> {entry = args~{p = {'i32', 'i8'}} -> let y = args.p [07] in y}"
    assert '%"y" = extractvalue {i32, i8} %"p", 1' in ir_text(source, "g = => 'i8'")


def test_single_predecessor_binds_params_and_multiple_predecessors_get_phis():
    # Both branches jump to join0, which therefore gets a phi per param.
    source = """
    pick = f -> {
      entry = args~{c = 'i1', x = 'i32', z = 'i32'} -> if args.c then f.a {x = args.x} else f.b {},
      a = args~{x = 'i32'} -> f.join0 {v = args.x, w = args.x},
      b = args~{} -> f.join0 {v = [00000000]~'i32', w = [07000000]~'i32'},
      join0 = args~{v = 'i32', w = 'i32'} -> let t0 = 'add' {'i32', args.v, args.w} in t0,
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


def test_struct_branch_lowers_like_if():
    def pick(entry_body):
        return f"""
        pick = f -> {{
          entry = args~{{c = 'i1', x = 'i32', z = 'i32'}} -> {entry_body},
          a = args~{{x = 'i32'}} -> f.join0 {{v = args.x, w = args.x}},
          b = args~{{}} -> f.join0 {{v = [00000000]~'i32', w = [07000000]~'i32'}},
          join0 = args~{{v = 'i32', w = 'i32'}} -> let t0 = 'add' {{'i32', args.v, args.w}} in t0,
        }}
        """

    struct_ir = ir_text(pick('{f.b {}, f.a {x = args.x}} args.c'), "pick = => 'i32'")
    if_ir = ir_text(pick('if args.c then f.a {x = args.x} else f.b {}'), "pick = => 'i32'")
    assert struct_ir == if_ir
    assert 'br i1 %"c", label %"a", label %"b"' in struct_ir


def test_rejects_branch_with_same_target_twice():
    # BANF allows this (Cranelift does too), but an LLVM phi can't tell the two edges apart.
    defs = "g = f -> {entry = args~{c = 'i1'} -> {f.a {}, f.a {}} args.c, a = args~{} -> [01]~'i8'}"
    assert ir_error(defs, "g = => 'i8'") == 'A branch cannot have the same block as both targets.'


def switch_defs(jumps, selector_form="'i8'"):
    """`pick(k, x)`, with `k` of the oymomo form `selector_form`, is `{jumps} args.k`, among
    `f.a {x = args.x}`, `f.b {}`, `f.c {}` and `f.d {}`, which join
    with `x`, 0, 7 and 9. Blocks no switch reaches are not lowered."""
    return f"""
    pick = f -> {{
      entry = args~{{k = {selector_form}, x = 'i32'}} -> {{{jumps}}} args.k,
      a = args~{{x = 'i32'}} -> f.join {{v = args.x}},
      b = args~{{}} -> f.join {{v = [00000000]~'i32'}},
      c = args~{{}} -> f.join {{v = [07000000]~'i32'}},
      d = args~{{}} -> f.join {{v = [09000000]~'i32'}},
      join = args~{{v = 'i32'}} -> args.v,
    }}
    """


PICK = "pick = => 'i32'"
THREE_WAY = 'f.a {x = args.x}, f.b {}, f.c {}'
FOUR_WAY = f'{THREE_WAY}, f.d {{}}'


def test_switch_defaults_to_its_last_target_and_joins_with_phis():
    assert ir_text(switch_defs(THREE_WAY), PICK) == text("""
        define i32 @"pick"(i8 %"k", i32 %"x")
        {
        entry:
          switch i8 %"k", label %"c" [i8 0, label %"a" i8 1, label %"b"]
        a:
          br label %"join"
        b:
          br label %"join"
        c:
          br label %"join"
        join:
          %"v" = phi  i32 [%"x", %"a"], [0, %"b"], [7, %"c"]
          ret i32 %"v"
        }
    """)


def test_four_way_switch():
    llvm_text = ir_text(switch_defs(FOUR_WAY), PICK)
    assert 'switch i8 %"k", label %"d" [i8 0, label %"a" i8 1, label %"b" i8 2, label %"c"]' in llvm_text
    assert '%"v" = phi  i32 [%"x", %"a"], [0, %"b"], [7, %"c"], [9, %"d"]' in llvm_text


def test_switch_past_its_last_target_takes_the_last_target():
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    machine = llvm.Target.from_default_triple().create_target_machine()
    llvm_module = llvm.parse_assembly(str(translate(banf(switch_defs(THREE_WAY), PICK), TARGET)))
    engine = llvm.create_mcjit_compiler(llvm_module, machine)
    engine.finalize_object()
    pick = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_uint8, ctypes.c_uint32)(engine.get_function_address('pick'))
    # Read as unsigned, as reduction reads an index: 255 is past the last target, not -1.
    assert [pick(k, 5) for k in (0, 1, 2, 3, 128, 255)] == [5, 0, 7, 7, 7, 7]


def test_switch_on_i1_holds_three_targets():
    assert 'switch i1 %"k"' in ir_text(switch_defs(THREE_WAY, "'i1'"), PICK)
    assert ir_error(switch_defs(FOUR_WAY, "'i1'"), PICK) == 'A switch on i1 has 4 targets; it holds 3.'


def test_rejects_switch_on_a_non_integer_selector():
    message = ir_error(switch_defs(THREE_WAY, "{x = 'i8'}"), PICK)
    assert message == 'Switch selector must be an integer form, got {x: i8}.'


def test_switch_may_repeat_a_target():
    # a is case 0 and the default: two edges from entry, so a phi with two equal entries.
    jumps = 'f.a {x = args.x}, f.b {}, f.a {x = args.x}'
    llvm_text = ir_text(switch_defs(jumps), PICK)
    assert 'switch i8 %"k", label %"a" [i8 0, label %"a" i8 1, label %"b"]' in llvm_text
    assert 'phi  i32 [%"x", %"entry"], [%"x", %"entry"]' in llvm_text
    # Two cases, neither the default, to one block.
    jumps = 'f.a {x = args.x}, f.a {x = args.x}, f.b {}'
    llvm_text = ir_text(switch_defs(jumps), PICK)
    assert 'switch i8 %"k", label %"b" [i8 0, label %"a" i8 1, label %"a"]' in llvm_text
    assert 'phi  i32 [%"x", %"entry"], [%"x", %"entry"]' in llvm_text


def test_constants_are_little_endian_on_a_big_endian_target():
    module = banf("g = f -> {entry = args~{} -> [0100]~'i16'}", "g = => 'i16'")
    big = Target('powerpc64-unknown-linux-gnu', 'E-m:e-i64:64-n32:64', DEFAULT_OPCODES)
    ir = str(translate(module, big))
    llvm.parse_assembly(ir).verify()
    assert 'target datalayout = "E-m:e-i64:64-n32:64"' in ir
    assert 'ret i16 1' in ir


def test_rejects_wrong_constant_size():
    assert ir_error("g = f -> {entry = args~{} -> [01]~'i32'}", "g = => 'i32'") == 'A i32 constant needs 4 bytes.'


def test_let_form_with_the_same_llvm_type_is_used_as_it_is():
    source = """
    g = f -> {
      entry = args~{v = 'i32', w = 'i32'} -> let q~{a = 'i32', b = 'i32'} = {x = args.v, y = args.w} in q,
    }
    """
    assert 'ret {i32, i32} %"q"' in ir_text(source, "g = => {a = 'i32', b = 'i32'}")


def test_rejects_let_form_with_another_llvm_type():
    # BANF accepts any let form, but LLVM never converts: no bitcast, no widening.
    source = """
    g = f -> {
      entry = args~{n = 'i32'} -> let t0~'i32' = 'icmp_eq' {'i32', args.n, [00000000]~'i32'} in t0,
    }
    """
    assert ir_error(source, "g = => 'i32'") == "Let 't0' is formed as i32, but its op gives i1."


def test_formed_var_with_the_same_llvm_type_is_used_as_it_is():
    assert 'ret i32 %"n"' in ir_text("g = f -> {entry = args~{n = 'i32'} -> args.n~'i32'}", "g = => 'i32'")


def test_rejects_formed_var_with_another_llvm_type():
    source = "g = f -> {entry = args~{n = 'i8'} -> args.n~'i32'}"
    assert ir_error(source, "g = => 'i32'") == "'n' is formed as i32, but its LLVM type is i8."


def test_defined_data_is_a_writable_global_with_an_initializer():
    source = """
    answer = [2a000000],
    main = f -> {entry = args~{} -> let t = module.answer in t},
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


def _resize(builder, value, bits):
    """`value` truncated or zero-extended to `bits` bits."""
    width = value.type.width
    if width > bits:
        return builder.trunc(value, ir.IntType(bits))
    if width < bits:
        return builder.zext(value, ir.IntType(bits))
    return value


# Conversions, by name: whether LLVM's `to` must be wider (else narrower) than `form`.
_CONVERSIONS = {'zext': True, 'sext': True, 'trunc': False}


def _instances():
    """Each opcode with each choice of integer forms, as `(name, forms)`: `(form,)`, or
    `(form, to)` for a conversion, where LLVM converts."""
    for name, opcode in opcodes.OPCODES.items():
        if not opcode.pure:
            continue
        if name not in _CONVERSIONS:
            for form in opcodes.INT_FORMS:
                yield name, (form,)
            continue
        for form, to in itertools.product(opcodes.INT_FORMS, repeat=2):
            source, target = (opcodes.bit_width(terms.ByteArray.from_str(f)) for f in (form, to))
            if target != source and (target > source) == _CONVERSIONS[name]:
                yield name, (form, to)


INSTANCES = list(_instances())


def _instance_id(instance):
    name, forms = instance
    return '_'.join([name, *forms])


def _operand_count(name):
    return 1 if name in _CONVERSIONS else 2


@pytest.fixture(scope='module')
def jit():
    """Each opcode instance, compiled by LLVM from its `DEFAULT_OPCODES` code (what
    `llvm_translate` emits for an `OpcodeCall`), as `i64 name(i64, ...)`: each operand is
    truncated to the `form` field's width, and the result zero-extended to 64 bits."""
    module = ir.Module()
    i64 = ir.IntType(64)
    for instance in INSTANCES:
        name, forms = instance
        count = _operand_count(name)
        function = ir.Function(module, ir.FunctionType(i64, [i64] * count), _instance_id(instance))
        builder = ir.IRBuilder(function.append_basic_block())
        bits = opcodes.bit_width(terms.ByteArray.from_str(forms[0]))
        args = {f'x{i}': _resize(builder, arg, bits) for i, arg in enumerate(function.args)}
        fields = [
            banf_terms.Const(forms[0].encode(), terms.Empty),
            *(banf_terms.Var(name) for name in args),
            *(banf_terms.Const(form.encode(), terms.Empty) for form in forms[1:]),
        ]
        result = DEFAULT_OPCODES[name](builder, fields, lambda atom, _form, args=args: args[atom.name])
        builder.ret(_resize(builder, result, 64))
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    machine = llvm.Target.from_default_triple().create_target_machine()
    engine = llvm.create_mcjit_compiler(llvm.parse_assembly(str(module)), machine)
    engine.finalize_object()

    def run(function_name, operands):
        prototype = ctypes.CFUNCTYPE(ctypes.c_uint64, *[ctypes.c_uint64] * len(operands))
        return prototype(engine.get_function_address(function_name))(*operands)

    return run


def _edges(bits):
    """0, 1, 2, `bits - 1` (the largest defined shift), the signed maximum, the signed
    minimum and -1, as unsigned `bits`-bit values."""
    edges = {0, 1, 2, bits - 1, (1 << (bits - 1)) - 1, 1 << (bits - 1), (1 << bits) - 1}
    return sorted(edge for edge in edges if edge < 1 << bits)


@pytest.mark.parametrize('instance', INSTANCES, ids=_instance_id)
def test_fold_matches_llvm(jit, instance):
    name, forms = instance
    form = terms.ByteArray.from_str(forms[0])
    bits = opcodes.bit_width(form)
    for operands in itertools.product(*[_edges(bits)] * _operand_count(name)):
        fields = [
            form,
            *(terms.ByteArray(value.to_bytes(opcodes.byte_width(bits), 'little')) for value in operands),
            *(terms.ByteArray.from_str(f) for f in forms[1:]),
        ]
        folded = opcodes.OPCODES[name].evaluate(fields)
        if folded is not None:
            assert int.from_bytes(folded.value, 'little') == jit(_instance_id(instance), operands), (instance, operands)


def test_a_ptr_param_and_result():
    source = "g = f -> {entry = args~{h = 'ptr'} -> args.h}"
    assert ir_text(source, "g = => 'ptr'") == text("""
        define ptr @"g"(ptr %"h")
        {
        entry:
          ret ptr %"h"
        }
    """)


def test_an_import_with_a_ptr_param_and_result():
    decls = "malloc = {size = 'i64'} => 'ptr', free = {p = 'ptr'} => 'i32', main = => 'i32'"
    source = """
    main = f -> {entry = args~{} ->
      let p = module.malloc {size = [1000000000000000]~'i64'} in
      let r = module.free {p = p} in
      r},
    """
    assert ir_text(source, decls) == text("""
        declare ptr @"malloc"(i64 %"size")

        declare i32 @"free"(ptr %"p")

        define i32 @"main"()
        {
        entry:
          %"p" = call ptr @"malloc"(i64 16)
          %"r" = call i32 @"free"(ptr %"p")
          ret i32 %"r"
        }
    """)


@pytest.mark.parametrize(
    ('op', 'expected'),
    [
        ("'alloca' {'i32'}", 'alloca i32'),
        ("'alloca' {'i32', [1000000000000000]~'i64'}", 'alloca i32, i64 16'),
        ("'alloca' {'i32', args.n}", 'alloca i32, i64 %"n"'),
        ("'alloca' {{x = 'i32', y = 'i64'}}", 'alloca {i32, i64}'),
        ("'alloca' {'ptr'}", 'alloca ptr'),
    ],
)
def test_alloca(op, expected):
    source = f"g = f -> {{entry = args~{{n = 'i64'}} -> let p = {op} in p}}"
    assert f'%"p" = {expected}\n' in ir_text(source, "g = => 'ptr'")


@pytest.mark.parametrize(
    ('op', 'expected'),
    [
        # The address of a struct's second field, as in the plan's goal.
        (
            "'getelementptr' {{x = 'i32', y = 'i64'}, args.q, [0000000000000000]~'i64', [01000000]~'i32'}",
            'getelementptr {i32, i64}, ptr %"q", i64 0, i32 1',
        ),
        # A byte offset, known only at run time.
        ("'getelementptr' {'i8', args.q, args.n}", 'getelementptr i8, ptr %"q", i64 %"n"'),
        # Into a nested struct.
        (
            "'getelementptr' {{a = 'i8', b = {c = 'i16', d = 'i32'}}, args.q, args.n, [01000000]~'i32', [01000000]~'i32'}",
            'getelementptr {i8, {i16, i32}}, ptr %"q", i64 %"n", i32 1, i32 1',
        ),
    ],
)
def test_getelementptr(op, expected):
    source = f"g = f -> {{entry = args~{{q = 'ptr', n = 'i64'}} -> let p = {op} in p}}"
    assert f'%"p" = {expected}\n' in ir_text(source, "g = => 'ptr'")


def test_a_pointer_passed_to_a_loop_is_a_phi():
    source = """
    g = f -> {
      entry = args~{n = 'i64'} ->
        let p = 'alloca' {'i8', args.n} in
        f.loop {p = p, i = args.n},
      loop = args~{p = 'ptr', i = 'i64'} ->
        let q = 'getelementptr' {'i8', args.p, [0100000000000000]~'i64'} in
        let j = 'sub' {'i64', args.i, [0100000000000000]~'i64'} in
        let done = 'icmp_eq' {'i64', j, [0000000000000000]~'i64'} in
        if done then f.exit {p = q} else f.loop {p = q, i = j},
      exit = args~{p = 'ptr'} -> args.p,
    }
    """
    assert '%"p" = phi  ptr [%"p.1", %"entry"], [%"q", %"loop"]' in ir_text(source, "g = => 'ptr'")


@pytest.mark.parametrize(
    ('op', 'message'),
    [
        (
            "'getelementptr' {{x = 'i32', y = 'i64'}, args.q, args.n, args.i}",
            "'getelementptr': index 1 into {x: i32, y: i64} must be a literal 'i32' below 2.",
        ),
        (
            "'getelementptr' {{x = 'i32'}, args.q, args.n, [01000000]~'i32'}",
            "'getelementptr': index 1 into {x: i32} must be a literal 'i32' below 1.",
        ),
        (
            "'getelementptr' {'i32', args.q, args.n, [00000000]~'i32'}",
            "'getelementptr': index 1 goes into i32, which has no parts.",
        ),
        (
            "'getelementptr' {'i8', args.q, [01]}",
            "'getelementptr': index 0 must have a form, such as [01000000]~'i32'.",
        ),
        ("'getelementptr' {'i8', args.n, args.n}", "'getelementptr' expects a pointer, got i64."),
        ("'alloca' {'i32', [10]}", "'alloca': count must have a form, such as [01000000]~'i32'."),
        ("'alloca' {'i32', args.q}", "'alloca': count must be an integer, got ptr."),
    ],
)
def test_memory_opcode_errors(op, message):
    source = f"g = f -> {{entry = args~{{q = 'ptr', n = 'i64', i = 'i32'}} -> let p = {op} in p}}"
    assert ir_error(source, "g = => 'ptr'") == message


BUMP = """
bump = f -> {
  entry = args~{n = 'i32'} ->
    let p = 'alloca' {'i32'} in
    let s = 'store' {N, p} in
    let v = 'load' {'i32', $seq {s, p}} in
    let w = 'add' {'i32', v, [01000000]} in
    w,
}
"""


def test_load_after_store():
    # The plan's goal: the store's let binds no LLVM value.
    assert ir_text(BUMP.replace('N', 'args.n'), "bump = => 'i32'") == text("""
        define i32 @"bump"(i32 %"n")
        {
        entry:
          %"p" = alloca i32
          store i32 %"n", ptr %"p"
          %"v" = load i32, ptr %"p"
          %"w" = add i32 %"v", 1
          ret i32 %"w"
        }
    """)


def test_load_after_store_folds_under_o2():
    # Reduction leaves the memory lets alone (decision 13); LLVM's mem2reg folds them.
    llvm_text = str(translate(banf(BUMP.replace('N', "[29000000]~'i32'"), "bump = => 'i32'"), TARGET))
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    machine = llvm.Target.from_default_triple().create_target_machine()
    module = llvm.parse_assembly(llvm_text)
    builder = llvm.create_pass_builder(machine, llvm.create_pipeline_tuning_options(speed_level=2))
    builder.getModulePassManager().run(module, builder)
    assert 'ret i32 42' in str(module)
    assert 'alloca' not in str(module)


def _round_trip(name, form):
    """`name(x) = load(store(x))`, through an `alloca` of `form`."""
    return f"""
    {name} = f -> {{
      entry = args~{{x = {form}}} ->
        let p = 'alloca' {{{form}}} in
        let s = 'store' {{args.x, p}} in
        let v = 'load' {{{form}, $seq {{s, p}}}} in
        v,
    }},
    """


_ROUND_TRIPS = {
    'i1': (ctypes.c_bool, True),
    'i8': (ctypes.c_uint8, 0xAB),
    'i16': (ctypes.c_uint16, 0xABCD),
    'i32': (ctypes.c_uint32, 0xDEADBEEF),
    'i64': (ctypes.c_uint64, 0x0123456789ABCDEF),
    'ptr': (ctypes.c_void_p, 0x1234_5678),
}

_STRUCT = "{x = 'i32', y = 'i64'}"

# A struct is stored whole, then each field is read back.
_STRUCT_ROUND_TRIP = f"""
pair = f -> {{
  entry = args~{{a = 'i32', b = 'i64'}} ->
    let q = {{x = args.a, y = args.b}} in
    let p = 'alloca' {{{_STRUCT}}} in
    let s = 'store' {{q, p}} in
    let r = 'load' {{{_STRUCT}, $seq {{s, p}}}} in
    let x = r.x in
    let wide = 'zext' {{'i32', x, 'i64'}} in
    let y = r.y in
    let sum = 'add' {{'i64', wide, y}} in
    sum,
}},
"""


def test_a_store_then_a_load_gives_the_stored_value():
    defs = ''.join(_round_trip(f'rt_{form}', f"'{form}'") for form in _ROUND_TRIPS) + _STRUCT_ROUND_TRIP
    decls = ', '.join([*(f"rt_{form} = => '{form}'" for form in _ROUND_TRIPS), "pair = => 'i64'"])
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    machine = llvm.Target.from_default_triple().create_target_machine()
    engine = llvm.create_mcjit_compiler(llvm.parse_assembly(str(translate(banf(defs, decls), TARGET))), machine)
    engine.finalize_object()
    for form, (c_type, value) in _ROUND_TRIPS.items():
        function = ctypes.CFUNCTYPE(c_type, c_type)(engine.get_function_address(f'rt_{form}'))
        assert function(value) == value, form
    pair = ctypes.CFUNCTYPE(ctypes.c_uint64, ctypes.c_uint32, ctypes.c_uint64)(engine.get_function_address('pair'))
    assert pair(7, 1 << 40) == 7 + (1 << 40)


@pytest.mark.parametrize(('name', 'count'), [('load', 3), ('store', 1)])
def test_load_and_store_check_their_field_count(name, count):
    # The verifier checks this first; the LLVM code doesn't rely on it.
    fields = [banf_terms.Var('q')] * count
    with pytest.raises(LlvmTranslationError) as info:
        DEFAULT_OPCODES[name](None, fields, None)
    assert info.value.message == f'{name!r} takes 2 fields, got {count}.'
