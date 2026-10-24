# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""LLVM translation (semantics.tex, Section 9): a module (Section 8) becomes LLVM IR.

Oymomo is untyped (9.1). Every LLVM type comes from where a value is used: an opcode's
type operand, the `takes` of a block or function being called, a function's `gives` for
a return, a constant's or global variable's `type`. A byte array takes the type its use
needs; a path `x.l₁⋯lⱼ` becomes `extractvalue`s, each index the label's position in the
struct type the value has.

- A definition becomes `define`; its first block is the entry block. When a block jumps
  to the first block, a new entry block, `start`, jumps to it (9.2b).
- A declaration becomes `declare`, a constant `constant`, a global variable `global`.
- A block's `takes` becomes `phi`s where it has more than one predecessor; otherwise its
  parameters are the values passed.
- A `let` becomes one instruction; a return `ret`; a jump through `f` `br`; a jump
  through `m` `call` then `ret`; a conditional jump `br i1` or `switch`, and an arm that
  is not a jump to a block of its own becomes a small block.

Everything target-specific (the opcodes' instructions) comes in through `Target`.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from llvmlite import ir

from oymo.core import syntax
from oymo.oymomo import anf, opcodes, printer, reduction, terms
from oymo.oymomo import module as modules

_INT_TYPE = re.compile(r'i([1-9][0-9]*)')

# An operand of an opcode as an LLVM value: the field, and the type term it is read at
# (None where the opcode doesn't say; a byte array then has no type and is an error).
type Operand = Callable[[syntax.Term, syntax.Term | None], ir.Value]

# By opcode name: gets the builder, the call's fields (by position) and `Operand`.
type OpcodeImpl = Callable[[ir.IRBuilder, Sequence[syntax.Term], Operand], ir.Value]


class LlvmTranslationError(Exception):
    def __init__(self, message: str, span: int = 0) -> None:
        super().__init__(message)
        self.message = message
        self.span = span


@dataclass
class Target:
    triple: str
    data_layout: str
    opcodes: Mapping[str, OpcodeImpl]


def show_type(term: syntax.Term) -> str:
    return printer.show(term)


def llvm_type(term: syntax.Term) -> ir.Type:
    """The LLVM type a type term names (9.1, D95): `'iN'`, `'ptr'`, a struct of types, or a
    tagged struct (`{'array', n, t}`, `{'vector', n, t}`, `{'packed', ...}`)."""
    if (tagged := opcodes.tagged_type(term)) is not None:
        return _tagged_type(term, *tagged)
    name = term.as_str if isinstance(term, terms.ByteArray) else None
    if name is not None and (match := _INT_TYPE.fullmatch(name)):
        return ir.IntType(int(match.group(1)))
    if name == 'ptr':
        # LLVM's opaque pointer: it says nothing about what it points to.
        return ir.PointerType()
    if isinstance(term, terms.Struct):
        return ir.LiteralStructType([llvm_type(f.value) for f in term.fields])
    raise LlvmTranslationError(f'{show_type(term)} is not an LLVM type.', getattr(term, 'span', 0))


def _tagged_type(term, tag, parts):
    """`[N x E]`, `<N x E>` or `<{...}>`."""
    if tag == 'packed':
        return ir.LiteralStructType([llvm_type(f.value) for f in parts], packed=True)
    count = opcodes.tag_count(parts[0].value) if len(parts) == opcodes.SEQUENCE_PARTS else None
    if count is None:
        raise LlvmTranslationError(f'{show_type(term)} is not an LLVM type.', getattr(term, 'span', 0))
    element = llvm_type(parts[1].value)
    return ir.ArrayType(element, count) if tag == 'array' else ir.VectorType(element, count)


def constant(type_term: syntax.Term, value: syntax.Term) -> ir.Constant:
    """`value`, data, as an LLVM constant of the type `type_term` names: a byte array of an
    integer type's size, or a struct (or array) of constants."""
    span = getattr(value, 'span', 0)
    typ = llvm_type(type_term)
    if isinstance(typ, ir.IntType):
        size = (typ.width + 7) // 8
        if not isinstance(value, terms.ByteArray) or len(value.value) != size:
            raise LlvmTranslationError(f'A constant of type {typ} is a byte array of {size} bytes.', span)
        # Byte arrays are little-endian on every target. LLVM stores the integer in the
        # data layout's byte order, so a big-endian target needs no swap here.
        number = int.from_bytes(value.value, 'little')
        if number >= 1 << typ.width:
            raise LlvmTranslationError(f'The constant does not fit in {typ}.', span)
        return ir.Constant(typ, number)
    parts = _type_parts(type_term)
    if parts is not None and isinstance(value, terms.Struct) and len(value.fields) == len(parts):
        return ir.Constant(typ, [constant(part, f.value) for part, f in zip(parts, value.fields, strict=True)])
    raise LlvmTranslationError(f'No constant of type {typ} is written {printer.show(value)}.', span)


def _type_parts(type_term):
    """The type terms of an aggregate's elements, in order, or None."""
    if (tagged := opcodes.tagged_type(type_term)) is not None:
        tag, parts = tagged
        if tag in opcodes.SEQUENCE_TAGS:
            count = opcodes.tag_count(parts[0].value)
            return None if count is None else [parts[1].value] * count
        return [f.value for f in parts]
    if isinstance(type_term, terms.Struct):
        return [f.value for f in type_term.fields]
    return None


def _field_type(type_term, label, span):
    """`(position, type term)` of the field labeled `label` in a struct type."""
    if isinstance(type_term, terms.Struct) and opcodes.tagged_type(type_term) is None:
        position = reduction.field_position(type_term, label)
        if position is not None:
            return position, type_term.fields[position].value
    shown = 'an unknown type' if type_term is None else show_type(type_term)
    raise LlvmTranslationError(f'.{label} reads a field of {shown}, which has no field {label!r}.', span)


@dataclass
class _Value:
    """An LLVM value and the type term it has (None for a `store`'s result)."""

    value: ir.Value | None
    type: syntax.Term | None


def _path(term):
    labels = []
    while isinstance(term, terms.Project):
        labels.append(term)
        term = term.struct
    return term.index, labels[::-1]


def _jump_target(term):
    """The block label of a jump `f.l.body {…}` (checked by `module.read_module`)."""
    return term.function.struct.label


class _Function:
    """One definition's blocks."""

    def __init__(self, translator, definition, llvm_function):
        self.translator = translator
        self.definition = definition
        self.llvm_function = llvm_function
        self.blocks = {block.label: block for block in definition.blocks}
        self.first = definition.blocks[0].label
        self.reachable = self._reachable()
        self.predecessors = dict.fromkeys(self.reachable, 0)
        for label in self.reachable:
            for target in self._jumps(self.blocks[label]):
                self.predecessors[target] += 1
        # 9.2b: LLVM's entry block has no predecessors, so `start` jumps to the first block.
        self.has_start = self.predecessors[self.first] > 0
        if self.has_start:
            self.predecessors[self.first] += 1
        self.llvm_blocks = {}
        self.params = {}

    def _terminal(self, block):
        term = block.body
        while isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda):
            term = term.function.body
        return term

    def _arms(self, block):
        terminal = self._terminal(block)
        if isinstance(terminal, terms.Apply) and isinstance(terminal.function, terms.Struct):
            return [f.value for f in terminal.function.fields]
        return [terminal]

    def _is_jump(self, term, lets):
        if not isinstance(term, terms.Apply) or isinstance(term.function, terms.ByteArray | terms.Struct):
            return False
        index, _ = _path(term.function)
        return index == lets + 1

    def _jumps(self, block):
        """The blocks `block` jumps to, once per jump."""
        lets = self._let_count(block)
        return [_jump_target(arm) for arm in self._arms(block) if self._is_jump(arm, lets)]

    def _let_count(self, block):
        count, term = 0, block.body
        while isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda):
            count, term = count + 1, term.function.body
        return count

    def _reachable(self):
        seen, stack = set(), [self.first]
        while stack:
            label = stack.pop()
            if label not in seen:
                seen.add(label)
                stack.extend(self._jumps(self.blocks[label]))
        return seen

    def translate(self):
        args = self.llvm_function.args
        for (name, _), arg in zip(self.definition.takes, args, strict=True):
            arg.name = name
        start = self.llvm_function.append_basic_block('start') if self.has_start else None
        for block in self.definition.blocks:
            if block.label in self.reachable:
                self.llvm_blocks[block.label] = self.llvm_function.append_basic_block(block.label)
        for label in self.reachable:
            if self.predecessors[label] > 1:
                builder = ir.IRBuilder(self.llvm_blocks[label])
                self.params[label] = {
                    name: _Value(builder.phi(llvm_type(t), name=name), t) for name, t in self.blocks[label].takes
                }
        first_values = [_Value(arg, t) for arg, (_, t) in zip(args, self.definition.takes, strict=True)]
        if start is None:
            self.params[self.first] = {
                name: value for (name, _), value in zip(self.definition.takes, first_values, strict=True)
            }
        else:
            builder = ir.IRBuilder(start)
            self._pass(self.first, first_values, start)
            builder.branch(self.llvm_blocks[self.first])
        order, done = [self.first], set()
        while order:
            label = order.pop(0)
            if label in done:
                continue
            done.add(label)
            self._block(self.blocks[label])
            order.extend(t for t in self._jumps(self.blocks[label]) if t not in done)

    def _pass(self, target, values, from_block):
        """Gives `target`'s parameters `values`, coming from `from_block`."""
        names = [name for name, _ in self.blocks[target].takes]
        if self.predecessors[target] > 1:
            for name, value in zip(names, values, strict=True):
                self.params[target][name].value.add_incoming(value.value, from_block)
        else:
            self.params[target] = dict(zip(names, values, strict=True))

    def _block(self, block):
        builder = ir.IRBuilder(self.llvm_blocks[block.label])
        lets = []
        term = block.body
        while isinstance(term, terms.Apply) and isinstance(term.function, terms.Lambda):
            name = term.function.param_name
            value = self._operation(builder, block, lets, term.argument)
            if value.value is not None and not isinstance(value.value.type, ir.VoidType):
                value.value.name = name
            lets.append(value)
            term = term.function.body
        self._terminal_code(builder, block, lets, term)

    # Atoms

    def atom(self, block, lets, term, expected, what):
        """An operand (an atom or a struct of operands) as an LLVM value. `expected` is the
        type term its use needs, or None."""
        if isinstance(term, terms.Struct):
            return self._struct(block, lets, term, expected, what)
        if isinstance(term, terms.ByteArray):
            if expected is None:
                raise LlvmTranslationError(
                    f'The byte array {printer.show(term)} needs a type here; {what} does not give one.',
                    term.span,
                )
            return _Value(constant(expected, term), expected)
        value = self._path_value(block, lets, term)
        if expected is not None and value.value is not None and value.value.type != llvm_type(expected):
            raise LlvmTranslationError(
                f'This value has LLVM type {value.value.type}, but {what} needs {llvm_type(expected)}.',
                getattr(term, 'span', 0),
            )
        if value.value is None:
            raise LlvmTranslationError("A store's result has no value.", getattr(term, 'span', 0))
        return value

    def _struct(self, block, lets, term, expected, what):
        """A struct operand (D94): a constant when it is data, else `insertvalue`s into
        `undef`, one per field, in the struct type its use needs."""
        if expected is None:
            raise LlvmTranslationError(
                f'The struct {printer.show(term)} needs a type here; {what} does not give one.', term.span
            )
        if reduction.is_data(term):
            return _Value(constant(expected, term), expected)
        parts = _type_parts(expected)
        if parts is None or len(parts) != len(term.fields):
            raise LlvmTranslationError(
                f'{what} needs {llvm_type(expected)}, which is not a struct of {len(term.fields)} fields.',
                term.span,
            )
        value = ir.Constant(llvm_type(expected), ir.Undefined)
        for i, (part, f) in enumerate(zip(parts, term.fields, strict=True)):
            field = self.atom(block, lets, f.value, part, what)
            value = self._builder.insert_value(value, field.value, i)
        return _Value(value, expected)

    def _path_value(self, block, lets, term):
        index, projections = _path(term)
        builder_value = None
        if index < len(lets):
            builder_value = lets[-1 - index]
        elif index == len(lets):
            first, projections = projections[0], projections[1:]
            builder_value = self.params[block.label][first.label]
        else:
            # `m.l`: the address of a symbol, or the function itself (checked by `module`).
            first, projections = projections[0], projections[1:]
            builder_value = _Value(self.translator.globals[first.label], self.translator.address_type)
        for projection in projections:
            position, field_type = _field_type(builder_value.type, projection.label, projection.span)
            value = self._builder.extract_value(builder_value.value, position)
            builder_value = _Value(value, field_type)
        return builder_value

    # Lets and terminals

    def _operation(self, builder, block, lets, term):
        self._builder = builder
        if isinstance(term.function, terms.ByteArray):
            return self._opcode(builder, block, lets, term)
        return self._call(builder, block, lets, term)

    def _opcode(self, builder, block, lets, term):
        name = term.function.as_str
        if name not in self.translator.target.opcodes:
            raise LlvmTranslationError(f'The target has no opcode {printer.show(term.function)}.', term.span)
        fields = [f.value for f in term.argument.fields]

        def operand(field, expected):
            return self.atom(block, lets, field, expected, f'opcode {name!r}').value

        try:
            value = self.translator.target.opcodes[name](builder, fields, operand)
        except LlvmTranslationError as error:
            error.span = error.span or term.span
            raise
        opcode = opcodes.OPCODES.get(name)
        result_type = opcode.result_type(fields) if opcode is not None else None
        if name == 'store':
            return _Value(None, None)
        return _Value(value, result_type)

    def _call(self, builder, block, lets, term):
        _, projections = _path(term.function)
        callee = self.translator.module.lookup(projections[0].label)
        args = self._arguments(block, lets, term, callee.takes, f'{callee.name!r}')
        return _Value(builder.call(self.translator.globals[callee.name], args), callee.gives)

    def _arguments(self, block, lets, term, takes, what):
        return [
            self.atom(block, lets, f.value, t, f'parameter {name!r} of {what}').value
            for f, (name, t) in zip(term.argument.fields, takes, strict=True)
        ]

    def _terminal_code(self, builder, block, lets, term):
        self._builder = builder
        if isinstance(term, terms.Apply) and isinstance(term.function, terms.Struct):
            self._branch(builder, block, lets, term)
        else:
            self._end(builder, block, lets, term)

    def _end(self, builder, block, lets, term):
        """A return, a jump through `f`, or a jump through `m` (`call` then `ret`)."""
        self._builder = builder
        gives = self.definition.gives
        if anf.is_operand(term):
            builder.ret(self.atom(block, lets, term, gives, f'the result of {self.definition.name!r}').value)
        elif self._is_jump(term, len(lets)):
            target, values = self._jump(block, lets, term)
            self._pass(target, values, builder.block)
            builder.branch(self.llvm_blocks[target])
        else:
            result = self._call(builder, block, lets, term)
            if llvm_type(result.type) != llvm_type(gives):
                raise LlvmTranslationError(
                    f'The call gives {llvm_type(result.type)}, but {self.definition.name!r} gives {llvm_type(gives)}.',
                    term.span,
                )
            builder.ret(result.value)

    def _jump(self, block, lets, term):
        """`(target, values)` of a jump `f.l.body {xᵢ = aᵢ}`."""
        target = _jump_target(term)
        takes = self.blocks[target].takes
        values = self._arguments(block, lets, term, takes, f'block {target!r}')
        return target, [_Value(value, t) for value, (_, t) in zip(values, takes, strict=True)]

    def _branch(self, builder, block, lets, term):
        arms = [f.value for f in term.function.fields]
        condition = self.atom(block, lets, term.argument, None, 'a branch condition').value
        if not isinstance(condition.type, ir.IntType):
            raise LlvmTranslationError(
                f'A branch condition must be an integer, got {condition.type}.', term.argument.span
            )
        targets = [_jump_target(arm) for arm in arms if self._is_jump(arm, len(lets))]
        llvm_arms = []
        for i, arm in enumerate(arms):
            if self._is_jump(arm, len(lets)) and targets.count(_jump_target(arm)) == 1:
                # A jump to a block of its own: a direct edge.
                target, values = self._jump(block, lets, arm)
                self._pass(target, values, builder.block)
                llvm_arms.append(self.llvm_blocks[target])
            else:
                # 9.3c: an arm that returns, calls through m, or shares its block gets a small block.
                small = self.llvm_function.append_basic_block(f'{block.label}.{i}')
                self._end(ir.IRBuilder(small), block, lets, arm)
                self._builder = builder
                llvm_arms.append(small)
        if len(llvm_arms) == 1:
            builder.branch(llvm_arms[0])
        elif len(llvm_arms) == 2:  # noqa: PLR2004
            if condition.type.width != 1:
                condition = builder.icmp_unsigned('!=', condition, ir.Constant(condition.type, 0))
            builder.cbranch(condition, llvm_arms[1], llvm_arms[0])
        else:
            # E-Index and E-Default: arm i for i < n - 1, the last arm otherwise.
            holds = (1 << condition.type.width) + 1
            if len(llvm_arms) > holds:
                raise LlvmTranslationError(
                    f'A branch on {condition.type} has {len(llvm_arms)} arms; it holds {holds}.',
                    term.span,
                )
            *cases, default = llvm_arms
            switch = builder.switch(condition, default)
            for value, target in enumerate(cases):
                switch.add_case(ir.Constant(condition.type, value), target)


class _Translator:
    def __init__(self, module, target):
        self.module = module
        self.target = target
        self.globals: dict[str, ir.GlobalValue] = {}
        self.address_type = terms.ByteArray(b'ptr')

    def translate(self):
        llvm_module = ir.Module()
        llvm_module.triple = self.target.triple
        llvm_module.data_layout = self.target.data_layout
        for symbol in self.module.symbols:
            try:
                self._symbol(llvm_module, symbol)
            except LlvmTranslationError as error:
                error.span = error.span or symbol.span
                raise
        for symbol in self.module.symbols:
            if isinstance(symbol, modules.Definition):
                _Function(self, symbol, self.globals[symbol.name]).translate()
        return llvm_module

    def _symbol(self, llvm_module, symbol):
        match symbol:
            case modules.Constant(name=name, type=type_term, value=value):
                variable = _global(llvm_module, llvm_type(type_term), name)
                variable.global_constant = True
                variable.initializer = constant(type_term, value)
                self.globals[name] = variable
            case modules.Global(name=name, type=type_term, init=init):
                variable = _global(llvm_module, llvm_type(type_term), name)
                variable.initializer = constant(type_term, init)
                self.globals[name] = variable
            case modules.Definition() | modules.Declaration():
                function_type = ir.FunctionType(llvm_type(symbol.gives), [llvm_type(t) for _, t in symbol.takes])
                function = ir.Function(llvm_module, function_type, symbol.name)
                if isinstance(symbol, modules.Declaration):
                    for (name, _), arg in zip(symbol.takes, function.args, strict=True):
                        arg.name = name
                self.globals[symbol.name] = function


def _global(llvm_module, typ, name):
    """A global variable whose address is LLVM's opaque `ptr`, as every pointer here is:
    llvmlite would type it by what it points to."""
    variable = ir.GlobalVariable(llvm_module, typ, name)
    variable.type = ir.PointerType()
    return variable


def translate(module: modules.Module, target: Target) -> ir.Module:
    return _Translator(module, target).translate()
