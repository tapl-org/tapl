# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""LLVM translation: an ingot becomes one LLVM module.

Oymomo is untyped. Every LLVM type comes from where a value is used: an opcode's
type operand, a function's type, an entry's `type`. A byte array takes the type its use
needs; a block's parameter takes the type of the operands jumped to it and of its
uses.

The translation is one to one where it can be: regions are flattened in source
order; field 0 of the body's region is the entry block, field 0 of a nested region goes
on in the block it continues; a `let` becomes one instruction, a return `ret`, a jump
`br`, a branch `br i1` or `switch`, a block's parameters its `phi`s. A jump to field 0 adds
a block: a new entry block named after the region's binder, or a split block plus `br`.

Everything target-specific (the opcodes' instructions) comes in through `Target`.
"""

import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from llvmlite import ir

from oymo.core import syntax
from oymo.oymomo import ingot as ingots
from oymo.oymomo import opcodes, printer, terms

_INT_TYPE = re.compile(r'i([1-9][0-9]*)')

# An operand of an opcode as an LLVM value: the field, and the type term it is read at
# (None where the opcode doesn't say; a byte array then has no type and is an error).
# A field is a data term (a type, a predicate, a constant) or an `ingot.Operand`.
type Operand = Callable[[Any, syntax.Term | None], ir.Value]


@dataclass(frozen=True)
class OpcodeImpl:
    """An opcode's LLVM instruction. `emit` gets the builder, the call's fields (by
    position) and `Operand`; `uses` gives the type each field is read at, or None."""

    emit: Callable[[ir.IRBuilder, Sequence[Any], Operand], ir.Value]
    uses: Callable[[Sequence[Any]], list[syntax.Term | None]]


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
    """The LLVM type a type term names: `'iN'`, `'ptr'`, a struct of types, or a
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


def constant(
    type_term: syntax.Term, value: syntax.Term, symbols: Mapping[str, ir.GlobalValue] | None = None
) -> ir.Constant:
    """`value`, data, as an LLVM constant of the type `type_term` names: a byte array of an
    integer type's size, or a struct (or array) of constants. `{}` is all zeros, for any
    type. Given `symbols` (an entry's `init` or `value`), a byte array in a `'ptr'`
    names a symbol (`''` is null) and `{b₁, b₂}` is the symbol `b₁` plus `b₂` bytes; one
    byte array may hold an `i8` array, its bytes in order."""
    span = getattr(value, 'span', 0)
    typ = llvm_type(type_term)
    if isinstance(value, terms.Struct) and not value.fields:
        return ir.Constant(typ, None)
    if isinstance(typ, ir.PointerType) and symbols is not None:
        return _pointer(value, symbols, span)
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
    if (
        symbols is not None
        and isinstance(value, terms.ByteArray)
        and isinstance(typ, ir.ArrayType)
        and typ.element == ir.IntType(8)
    ):
        if len(value.value) != typ.count:
            raise LlvmTranslationError(f'{typ} is a byte array of {typ.count} bytes here.', span)
        return ir.Constant(typ, bytearray(value.value))
    parts = _type_parts(type_term)
    if parts is not None and isinstance(value, terms.Struct) and len(value.fields) == len(parts):
        return ir.Constant(typ, [constant(part, f.value, symbols) for part, f in zip(parts, value.fields, strict=True)])
    raise LlvmTranslationError(f'No constant of type {typ} is written {printer.show(value)}.', span)


def _pointer(value, symbols, span):
    """A `'ptr'` in an entry's data: a symbol's address, plus a byte offset, or null."""
    offset = None
    if isinstance(value, terms.Struct) and len(value.fields) == 2:  # noqa: PLR2004
        value, offset = value.fields[0].value, value.fields[1].value
        if not isinstance(offset, terms.ByteArray):
            raise LlvmTranslationError('A symbol plus an offset is {symbol, bytes}, the offset a byte array.', span)
    name = value.as_str if isinstance(value, terms.ByteArray) else None
    if name is None:
        raise LlvmTranslationError("A 'ptr' here names a symbol, '' for null, or {symbol, offset}.", span)
    if not name and offset is None:
        return ir.Constant(ir.PointerType(), None)
    if name not in symbols:
        raise LlvmTranslationError(f'{name!r} names no symbol of the ingot.', span)
    symbol = symbols[name]
    if offset is None:
        return symbol
    count = int.from_bytes(offset.value, 'little')
    return ir.FormattedConstant(ir.PointerType(), f'getelementptr (i8, ptr {symbol.get_reference()}, i64 {count})')


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


def _blocks(region: ingots.Region) -> Iterator[ingots.Block]:
    """Every block of `region`, nested ones included, in source order."""
    for block in region.blocks:
        yield block
        if isinstance(block.terminal, ingots.Region):
            yield from _blocks(block.terminal)


def _jumps(block: ingots.Block) -> list[ingots.Jump]:
    match block.terminal:
        case ingots.Jump() as jump:
            return [jump]
        case ingots.Branch(arms=arms):
            return arms
    return []


def _same(a, b) -> bool:
    """Two operands that are the same value."""
    match a, b:
        case ingots.Use(), ingots.Use():
            return a.var is b.var
        case ingots.Arg(), ingots.Arg():
            return a.label == b.label
        case ingots.Address(), ingots.Address():
            return a.name == b.name
        case ((ingots.Use() | ingots.Arg() | ingots.Address()), _):
            return False
        case _, (ingots.Use() | ingots.Arg() | ingots.Address()):
            return False
    return a == b


def _is_data(operand) -> bool:
    return not isinstance(operand, ingots.Use | ingots.Arg | ingots.Address)


class _Function:
    """One definition: its blocks flattened, its parameters typed, its code."""

    def __init__(self, translator: '_Translator', definition: ingots.Definition, llvm_function: ir.Function) -> None:
        self.translator = translator
        self.definition = definition
        self.llvm_function = llvm_function
        self.blocks = list(_blocks(definition.region))
        self.args = {label: arg for (label, _), arg in zip(definition.type.params, llvm_function.args, strict=True)}
        self.arg_types = dict(definition.type.params)
        self.types: dict[ingots.Var, syntax.Term] = {}
        self.values: dict[ingots.Var, ir.Value] = {}
        self.llvm_blocks: dict[ingots.Block, ir.Block] = {}

    # Types

    def _type_of(self, operand) -> syntax.Term | None:
        match operand:
            case ingots.Use(var=var):
                return self.types.get(var)
            case ingots.Arg(label=label):
                return self.arg_types[label]
            case ingots.Address():
                return self.translator.address_type
        return None

    def _let_type(self, let):
        if let.callee is not None:
            return ingots.function_type(self.translator.ingot.lookup(let.callee)).result
        opcode = opcodes.OPCODES.get(let.opcode)
        type_term = opcode.result_type([q for _, q in let.fields]) if opcode is not None else None
        return None if type_term == opcodes.STORE_RESULT else type_term

    def _uses(self, block):
        """`(operand, type)` for each operand of `block` read at a known type."""
        for let in block.lets:
            fields = [q for _, q in let.fields]
            if let.callee is not None:
                params = ingots.function_type(self.translator.ingot.lookup(let.callee)).params
                types = [t for _, t in params]
            elif (impl := self.translator.target.opcodes.get(let.opcode)) is not None:
                types = impl.uses(fields)
            else:
                types = [None] * len(fields)
            yield from zip(fields, types, strict=True)
        match block.terminal:
            case ingots.Return(value=value):
                yield value, self.definition.type.result
        for jump in _jumps(block):
            for var, operand in zip(jump.target.params, jump.operands, strict=True):
                yield operand, self.types.get(var)

    def _add(self, var, type_term, span):
        if type_term is None:
            return False
        if var not in self.types:
            self.types[var] = type_term
            return True
        if llvm_type(self.types[var]) != llvm_type(type_term):
            raise LlvmTranslationError(
                f'{var.name!r} gets two types, {llvm_type(self.types[var])} and {llvm_type(type_term)}: '
                f'give {var.name!r} one typed argument or typed use.',
                span,
            )
        return False

    def infer(self):
        for block in self.blocks:
            for let in block.lets:
                if (type_term := self._let_type(let)) is not None:
                    self.types[let.result] = type_term
        params = {var for block in self.blocks for var in block.params}
        changed = True
        while changed:
            changed = False
            for block in self.blocks:
                for jump in _jumps(block):
                    for var, operand in zip(jump.target.params, jump.operands, strict=True):
                        changed |= self._add(var, self._type_of(operand), getattr(operand, 'span', 0))
                for operand, type_term in list(self._uses(block)):
                    if isinstance(operand, ingots.Use) and operand.var in params:
                        changed |= self._add(operand.var, type_term, operand.span)
        used = {
            operand.var for block in self.blocks for operand, _ in self._uses(block) if isinstance(operand, ingots.Use)
        } | {
            block.terminal.condition.var
            for block in self.blocks
            if isinstance(block.terminal, ingots.Branch) and isinstance(block.terminal.condition, ingots.Use)
        }
        for var in sorted(params - self.types.keys(), key=lambda v: v.name):
            if var in used:
                raise LlvmTranslationError(f'give {var.name!r} a typed argument or a typed use.', var.span)

    # Blocks

    def _layout(self, region, *, top):
        for i, block in enumerate(region.blocks):
            if i == 0 and top and block.jumped:
                # LLVM's entry block has no predecessors.
                self.start = self.llvm_function.append_basic_block(region.binder)
            if i > 0 or top or block.jumped:
                self.llvm_blocks[block] = self.llvm_function.append_basic_block(block.name)
            if isinstance(block.terminal, ingots.Region):
                self._layout(block.terminal, top=False)

    def translate(self):
        for label, arg in self.args.items():
            arg.name = f'{self.definition.args}.{label}'
        self.infer()
        self.start = None
        self._layout(self.definition.region, top=True)
        for block in self.blocks:
            if block in self.llvm_blocks:
                builder = ir.IRBuilder(self.llvm_blocks[block])
                for var in block.params:
                    if var in self.types:
                        self.values[var] = builder.phi(llvm_type(self.types[var]), name=var.name)
        if self.start is not None:
            ir.IRBuilder(self.start).branch(self.llvm_blocks[self.definition.region.blocks[0]])
        self._region(self.definition.region, None)

    def _region(self, region, builder):
        for i, block in enumerate(region.blocks):
            if i == 0 and builder is not None and not block.jumped:
                self._block(block, builder)
                continue
            if i == 0 and builder is not None:
                builder.branch(self.llvm_blocks[block])
            self._block(block, ir.IRBuilder(self.llvm_blocks[block]))

    def _block(self, block, builder):
        for let in block.lets:
            value = self._instruction(builder, let)
            if value is not None and not isinstance(value.type, ir.VoidType):
                if not isinstance(value, ir.Constant):
                    value.name = let.result.name
                self.values[let.result] = value
        match block.terminal:
            case ingots.Return(value=value):
                result = self.definition.type.result
                builder.ret(self.operand(value, result, f'the result of {self.definition.name!r}'))
            case ingots.Jump() as jump:
                self._edge(builder, jump)
                builder.branch(self.llvm_blocks[jump.target])
            case ingots.Branch() as branch:
                self._branch(builder, branch)
            case ingots.Region() as region:
                self._region(region, builder)

    def _edge(self, builder, jump):
        """Gives the target's `phi`s the jump's operands, coming from the current block."""
        for var, operand in zip(jump.target.params, jump.operands, strict=True):
            if var in self.values:
                value = self.operand(operand, self.types[var], f'parameter {var.name!r} of {jump.target.name}')
                self.values[var].add_incoming(value, builder.block)

    def _branch(self, builder, branch):
        condition = self.operand(branch.condition, None, 'a branch condition')
        if not isinstance(condition.type, ir.IntType):
            raise LlvmTranslationError(
                f'A branch condition must be an integer, got {condition.type}.', branch.condition.span
            )
        for i, arm in enumerate(branch.arms):
            for other in branch.arms[:i]:
                if other.target is arm.target and not all(
                    _same(a, b) for a, b in zip(other.operands, arm.operands, strict=True)
                ):
                    raise LlvmTranslationError(
                        f'Two arms jump to {arm.target.name} with different operands; '
                        'they must pass the same operands.',
                        arm.span,
                    )
            self._edge(builder, arm)
        targets = [self.llvm_blocks[arm.target] for arm in branch.arms]
        if len(targets) == 1:
            builder.branch(targets[0])
        elif len(targets) == 2 and condition.type.width == 1:  # noqa: PLR2004
            builder.cbranch(condition, targets[1], targets[0])
        else:
            # E-Index and E-Default: arm i for i < n - 1, the last arm otherwise.
            holds = (1 << condition.type.width) + 1
            if len(targets) > holds:
                raise LlvmTranslationError(
                    f'A branch on {condition.type} has {len(targets)} arms; it holds {holds}.', branch.span
                )
            *cases, default = targets
            switch = builder.switch(condition, default)
            for value, target in enumerate(cases):
                switch.add_case(ir.Constant(condition.type, value), target)

    # Operands and instructions

    def operand(self, operand, expected, what):
        """An operand as an LLVM value; `expected` is the type term its use needs, or None."""
        span = getattr(operand, 'span', 0)
        if _is_data(operand):
            if expected is None:
                raise LlvmTranslationError(
                    f'{printer.show(operand)} needs a type here; {what} does not give one.', span
                )
            return constant(expected, operand)
        match operand:
            case ingots.Use(var=var):
                if var not in self.values:
                    if var in self.types:
                        raise LlvmTranslationError(f'{var.name!r} has no value here.', span)
                    raise LlvmTranslationError(f"{var.name!r} has no value: a store's result has none.", span)
                value = self.values[var]
            case ingots.Arg(label=label):
                value = self.args[label]
            case _:
                value = self.translator.globals[operand.name]
                if expected is not None and not isinstance(llvm_type(expected), ir.PointerType):
                    raise LlvmTranslationError(
                        f'm.{operand.name} is an address, a ptr, but {what} needs {llvm_type(expected)}.', span
                    )
                return value
        if expected is not None and value.type != llvm_type(expected):
            raise LlvmTranslationError(
                f'This value has LLVM type {value.type}, but {what} needs {llvm_type(expected)}.', span
            )
        return value

    def _instruction(self, builder, let):
        if let.callee is not None:
            fn = ingots.function_type(self.translator.ingot.lookup(let.callee))
            args = [
                self.operand(q, t, f'parameter {label!r} of {let.callee!r}')
                for (_, q), (label, t) in zip(let.fields, fn.params, strict=True)
            ]
            return builder.call(self.translator.globals[let.callee], args)
        name = let.opcode
        impl = self.translator.target.opcodes.get(name)
        if impl is None:
            raise LlvmTranslationError(f'The target has no opcode {name!r}.', let.span)

        def operand(field, expected):
            return self.operand(field, expected, f'opcode {name!r}')

        try:
            value = impl.emit(builder, [q for _, q in let.fields], operand)
        except LlvmTranslationError as error:
            error.span = error.span or let.span
            raise
        return None if name == 'store' else value


class _Translator:
    def __init__(self, ingot: ingots.Ingot, target: Target) -> None:
        self.ingot = ingot
        self.target = target
        self.globals: dict[str, ir.GlobalValue] = {}
        self.address_type = terms.ByteArray(b'ptr')

    def translate(self):
        llvm_module = ir.Module()
        llvm_module.triple = self.target.triple
        llvm_module.data_layout = self.target.data_layout
        for step in (self._symbol, self._data):
            for symbol in self.ingot.symbols:
                try:
                    step(llvm_module, symbol)
                except LlvmTranslationError as error:
                    error.span = error.span or symbol.span
                    raise
        for symbol in self.ingot.symbols:
            if isinstance(symbol, ingots.Definition):
                _Function(self, symbol, self.globals[symbol.name]).translate()
        return llvm_module

    def _symbol(self, llvm_module, symbol):
        """Each symbol becomes an LLVM global named by its label."""
        fn = ingots.function_type(symbol)
        if fn is not None:
            function_type = ir.FunctionType(llvm_type(fn.result), [llvm_type(t) for _, t in fn.params])
            function = ir.Function(llvm_module, function_type, symbol.name)
            if isinstance(symbol, ingots.Declaration):
                for (name, _), arg in zip(fn.params, function.args, strict=True):
                    arg.name = name
            self.globals[symbol.name] = function
            return
        variable = ir.GlobalVariable(llvm_module, llvm_type(symbol.type), symbol.name)
        # LLVM's opaque `ptr`, as every pointer here is: llvmlite would type it by what it points to.
        variable.type = ir.PointerType()
        variable.global_constant = isinstance(symbol, ingots.Constant)
        self.globals[symbol.name] = variable

    def _data(self, _llvm_module, symbol):
        """An initializer may name any symbol, so it is read once every symbol exists."""
        match symbol:
            case ingots.Constant(type=type_term, value=value) | ingots.Global(type=type_term, init=value):
                self.globals[symbol.name].initializer = constant(type_term, value, self.globals)


def translate(ingot: ingots.Ingot, target: Target) -> ir.Module:
    return _Translator(ingot, target).translate()
