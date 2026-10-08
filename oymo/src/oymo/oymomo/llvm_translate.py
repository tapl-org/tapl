# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""Translates BANF into LLVM IR, one-to-one. Everything LLVM-specific comes in through Target."""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from llvmlite import ir

from oymo.oymomo import banf_terms as banf
from oymo.oymomo import terms

_INT_FORM = re.compile(r'i([1-9][0-9]*)')


class LlvmTranslationError(Exception):
    def __init__(self, message: str, location: terms.Location | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.location = location


@dataclass
class Target:
    triple: str
    data_layout: str
    prims: Mapping[str, Callable[[ir.IRBuilder, list[ir.Value]], ir.Value]]


def llvm_type(form: terms.Term) -> ir.Type:
    if (name := terms.form_name(form)) is not None and (match := _INT_FORM.fullmatch(name)):
        return ir.IntType(int(match.group(1)))
    if (fields := terms.struct_fields(form)) is not None:
        return ir.LiteralStructType([llvm_type(field_form) for _, field_form in fields])
    raise LlvmTranslationError(f'Form {banf.show_form(form)} has no LLVM type.')


def _const(atom: banf.Const) -> ir.Constant:
    name = terms.form_name(atom.form)
    match = _INT_FORM.fullmatch(name) if name is not None else None
    if match is None:
        raise LlvmTranslationError(
            f'Only integer constants are supported, got {banf.show_form(atom.form)}.', atom.location
        )
    bits = int(match.group(1))
    if len(atom.value) != (bits + 7) // 8:
        raise LlvmTranslationError(f'A {name} constant needs {(bits + 7) // 8} bytes.', atom.location)
    # Byte arrays are little-endian on every target. LLVM stores the integer in the
    # data layout's byte order, so a big-endian target needs no swap here.
    value = int.from_bytes(atom.value, 'little')
    if value >= 1 << bits:
        raise LlvmTranslationError(f'Constant does not fit in {name}.', atom.location)
    return ir.Constant(ir.IntType(bits), value)


def _successors(terminator):
    match terminator:
        case banf.Jump(target=target, args=args):
            return [(target, args)]
        case banf.Branch() as branch:
            return [(branch.then_target, branch.then_args), (branch.else_target, branch.else_args)]
    return []


class _FunctionTranslator:
    def __init__(self, module, function, llvm_function, globals_, target):
        self.module = module
        self.function = function
        self.llvm_function = llvm_function
        self.globals = globals_
        self.target = target
        self.blocks = {block.label: block for block in function.blocks}
        self.reachable = self._reachable()
        self.predecessors = dict.fromkeys(self.reachable, 0)
        for label in self.reachable:
            for successor, _ in _successors(self.blocks[label].terminator):
                self.predecessors[successor] += 1
        self.llvm_blocks = {}
        self.values = {}

    def value(self, atom, values):
        if isinstance(atom, banf.Const):
            return _const(atom)
        return values[atom.name]

    def translate(self):
        entry = self.function.blocks[0]
        for block in self.function.blocks:
            if block.label in self.reachable:
                self.llvm_blocks[block.label] = self.llvm_function.append_basic_block(block.label)
        entry_values = {}
        for (name, _), arg in zip(entry.params, self.llvm_function.args, strict=True):
            arg.name = name
            entry_values[name] = arg
        self.values[entry.label] = entry_values
        for block in self.function.blocks:
            if block.label != entry.label and self.predecessors.get(block.label, 0) > 1:
                builder = ir.IRBuilder(self.llvm_blocks[block.label])
                self.values[block.label] = {
                    name: builder.phi(llvm_type(form), name=name) for name, form in block.params
                }
        worklist = [entry.label]
        done = set()
        while worklist:
            label = worklist.pop(0)
            if label in done:
                continue
            done.add(label)
            worklist.extend(successor for successor in self.block(self.blocks[label]) if successor not in done)

    def _reachable(self):
        seen, stack = set(), [self.function.blocks[0].label]
        while stack:
            label = stack.pop()
            if label not in seen:
                seen.add(label)
                stack.extend(successor for successor, _ in _successors(self.blocks[label].terminator))
        return seen

    def block(self, block):
        values = dict(self.values[block.label])
        builder = ir.IRBuilder(self.llvm_blocks[block.label])
        forms = dict(block.params)
        for let in block.lets:
            values[let.name] = self.op(builder, let, values, forms)
            if isinstance(values[let.name], ir.Instruction):
                values[let.name].name = let.name
            forms[let.name] = banf.form_of(let.value, forms, self.module)
        return self.terminator(builder, block.terminator, values)

    def op(self, builder, let, values, forms):
        op = let.value
        match op:
            case banf.PrimCall(op=name, args=args):
                if name not in self.target.prims:
                    raise LlvmTranslationError(f'Target has no implementation of prim.{name}.', op.location)
                return self.target.prims[name](builder, [self.value(arg, values) for arg in args])
            case banf.Call(function=name, args=args):
                return builder.call(self.globals[name], [self.value(arg, values) for arg in args])
            case banf.MakeStruct(fields=fields):
                struct = ir.Constant(llvm_type(banf.form_of(op, forms, self.module)), ir.Undefined)
                for index, (label, atom) in enumerate(fields):
                    struct = builder.insert_value(struct, self.value(atom, values), index, name=f'{let.name}.{label}')
                return struct
            case banf.GetField(struct=struct, label=label):
                index = banf.field_index(banf.atom_form(struct, forms), label)
                return builder.extract_value(self.value(struct, values), index)
            case banf.GetData(name=name):
                return builder.load(self.globals[name])
        raise AssertionError(op)

    def pass_args(self, target, args, values, from_block):
        params = self.blocks[target].params
        passed = [self.value(arg, values) for arg in args]
        if self.predecessors[target] > 1:
            for (name, _), value in zip(params, passed, strict=True):
                self.values[target][name].add_incoming(value, from_block)
        else:
            self.values[target] = {name: value for (name, _), value in zip(params, passed, strict=True)}

    def terminator(self, builder, terminator, values):
        match terminator:
            case banf.Jump(target=target, args=args):
                self.pass_args(target, args, values, builder.block)
                builder.branch(self.llvm_blocks[target])
                return [target]
            case banf.Branch() as branch:
                if branch.then_target == branch.else_target:
                    raise LlvmTranslationError('A branch cannot have the same block as both targets.', branch.location)
                self.pass_args(branch.then_target, branch.then_args, values, builder.block)
                self.pass_args(branch.else_target, branch.else_args, values, builder.block)
                builder.cbranch(
                    self.value(branch.condition, values),
                    self.llvm_blocks[branch.then_target],
                    self.llvm_blocks[branch.else_target],
                )
                return [branch.then_target, branch.else_target]
            case banf.Return(value=value):
                builder.ret(self.value(value, values))
                return []
        raise AssertionError(terminator)


def translate(module: banf.Module, target: Target) -> ir.Module:
    llvm_module = ir.Module()
    llvm_module.triple = target.triple
    llvm_module.data_layout = target.data_layout
    globals_: dict[str, ir.GlobalValue] = {}
    for binding in module.bindings:
        match binding:
            case banf.Data(name=name, form=form):
                globals_[name] = ir.GlobalVariable(llvm_module, llvm_type(form), name)
            case (
                banf.Signature(name=name, params=params, return_form=return_form)
                | banf.Function(name=name, params=params, return_form=return_form)
            ):
                function_type = ir.FunctionType(llvm_type(return_form), [llvm_type(form) for _, form in params])
                llvm_function = ir.Function(llvm_module, function_type, name)
                globals_[name] = llvm_function
                if isinstance(binding, banf.Signature):
                    for (param, _), arg in zip(params, llvm_function.args, strict=True):
                        arg.name = param
    for binding in module.bindings:
        if isinstance(binding, banf.Function):
            _FunctionTranslator(module, binding, globals_[binding.name], globals_, target).translate()
    return llvm_module
