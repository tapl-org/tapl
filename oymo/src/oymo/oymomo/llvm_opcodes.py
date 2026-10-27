# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The default LLVM implementation of each opcode in `opcodes.OPCODES`.

Each implementation reads its call's fields by position, as `opcodes` does: `{type, a, b}`
for an arithmetic or logic opcode, `{predicate, type, a, b}` for `icmp`, `{type, value, to}`
for a conversion, `{type}` or `{type, count}` for `alloca`, `{type, ptr, i₀, …}` for
`getelementptr`, `{type, ptr}` for `load`, `{type, value, ptr}` for `store`,
`{aggtype, agg, i₁, …}` for `extractvalue` and `{aggtype, agg, value, i₁, …}` for
`insertvalue`. A type field is a type term; an operand takes the type the
opcode reads it at, so a bare byte array there is a constant of that type.

Each opcode also tells, by `uses`, the type each field is read at (None for a type field,
or where it doesn't say), so a block's parameter can take its type from its uses.
"""

from collections.abc import Sequence

from llvmlite import ir

from oymo.core import syntax
from oymo.oymomo import opcodes, printer, terms
from oymo.oymomo.llvm_translate import LlvmTranslationError, OpcodeImpl, Operand, llvm_type

_I32 = terms.ByteArray(b'i32')
_I64 = terms.ByteArray(b'i64')
_PTR = terms.ByteArray(b'ptr')


def _index(operand: Operand, field: syntax.Term) -> ir.Value:
    """A count or an index. Written as a byte array, its length gives its type: eight
    bytes are an `i64`, others an `i32`, as clang emits them."""
    if isinstance(field, terms.ByteArray):
        return operand(field, _I64 if len(field.value) == 8 else _I32)  # noqa: PLR2004
    return operand(field, None)


def _int_type(name: str, fields: Sequence[syntax.Term], index: int) -> syntax.Term:
    """Field `index`, an integer type such as `'i32'`."""
    field = fields[index]
    if opcodes.find_bit_width(field) is None:
        raise LlvmTranslationError(f"{name!r}: field {index} must be an integer type, such as 'i32'.")
    return field


def _type(name: str, fields: Sequence[syntax.Term], index: int) -> syntax.Term:
    """Field `index`, any type term."""
    field = fields[index]
    if not opcodes.is_literal_type(field):
        raise LlvmTranslationError(f"{name!r}: field {index} must be a type, such as 'i32'.")
    return field


def _arity(name: str, fields: Sequence[syntax.Term], count: int) -> None:
    if len(fields) != count:
        raise LlvmTranslationError(f'{name!r} takes {count} fields, got {len(fields)}.')


def _binary(name, method):
    def impl(builder, fields, operand):
        _arity(name, fields, opcodes.FIELD_COUNT)
        typ = _int_type(name, fields, 0)
        return getattr(builder, method)(operand(fields[1], typ), operand(fields[2], typ))

    return impl


# `icmp`'s predicates: llvmlite's method and operator.
_PREDICATES = {
    'eq': ('icmp_unsigned', '=='),
    'ne': ('icmp_unsigned', '!='),
    'slt': ('icmp_signed', '<'),
    'sle': ('icmp_signed', '<='),
    'sgt': ('icmp_signed', '>'),
    'sge': ('icmp_signed', '>='),
    'ult': ('icmp_unsigned', '<'),
    'ule': ('icmp_unsigned', '<='),
    'ugt': ('icmp_unsigned', '>'),
    'uge': ('icmp_unsigned', '>='),
}


def _icmp(builder, fields, operand):
    _arity('icmp', fields, opcodes.ICMP_FIELD_COUNT)
    predicate = opcodes.icmp_predicate(fields)
    if predicate is None:
        raise LlvmTranslationError(f"'icmp': field 0 must be a predicate, one of {list(_PREDICATES)}.")
    typ = _type('icmp', fields, 1)
    method, op = _PREDICATES[predicate]
    return getattr(builder, method)(op, operand(fields[2], typ), operand(fields[3], typ))


def _convert(name, method):
    def impl(builder, fields, operand):
        _arity(name, fields, opcodes.FIELD_COUNT)
        typ, to = _int_type(name, fields, 0), _int_type(name, fields, 2)
        return getattr(builder, method)(operand(fields[1], typ), ir.IntType(opcodes.bit_width(to)))

    return impl


_BINARY = {
    'add': 'add',
    'mul': 'mul',
    'and': 'and_',
    'or': 'or_',
    'xor': 'xor',
    'sub': 'sub',
    'sdiv': 'sdiv',
    'udiv': 'udiv',
    'srem': 'srem',
    'urem': 'urem',
    'shl': 'shl',
    'lshr': 'lshr',
    'ashr': 'ashr',
}

_CONVERT = {'zext': 'zext', 'sext': 'sext', 'trunc': 'trunc'}


def _type_of(value: ir.Value) -> ir.Type | None:
    """An LLVM value's type (llvmlite's `Value` declares no `type`, its subclasses do)."""
    return getattr(value, 'type', None)


def _opaque(instruction: ir.Instruction) -> ir.Instruction:
    """llvmlite types a pointer it makes by what it points to; LLVM's `ptr` is opaque."""
    instruction.type = ir.PointerType()
    return instruction


def _alloca(builder, fields, operand: Operand):
    if len(fields) not in (1, 2):
        raise LlvmTranslationError(f"'alloca' takes a type and an optional count, got {len(fields)} fields.")
    typ = llvm_type(_type('alloca', fields, 0))
    count = _index(operand, fields[1]) if len(fields) > 1 else None
    if count is not None and not isinstance(_type_of(count), ir.IntType):
        raise LlvmTranslationError(f"'alloca': count must be an integer, got {_type_of(count)}.")
    return _opaque(builder.alloca(typ, size=count))


def _check_indices(typ: syntax.Term, fields: Sequence[syntax.Term]) -> None:
    """Every index past the first goes into a part of the type so far: into a struct or a
    packed struct, it is a byte array below its field count, as LLVM's constant `i32`; into an
    array or a vector, it may be known only at run time."""
    for index, field in enumerate(fields, start=1):
        tagged = opcodes.tagged_type(typ)
        if tagged is not None and tagged[0] in opcodes.SEQUENCE_TAGS:
            typ = tagged[1][1].value
            continue
        parts = tagged[1] if tagged is not None else typ.fields if isinstance(typ, terms.Struct) else None
        if parts is None:
            raise LlvmTranslationError(f"'getelementptr': index {index} goes into a type that has no parts.")
        count = len(parts)
        position = opcodes.decode_uint(field, _I32)
        if position is None or position >= count:
            raise LlvmTranslationError(
                f"'getelementptr': index {index} into a struct must be a 4-byte array below {count}."
            )
        typ = parts[position].value


def _getelementptr(builder, fields, operand: Operand):
    if len(fields) < opcodes.GEP_MIN_FIELDS:
        raise LlvmTranslationError(
            f"'getelementptr' takes a type, a pointer and at least one index, got {len(fields)} fields."
        )
    typ = _type('getelementptr', fields, 0)
    pointer = operand(fields[1], _PTR)
    indices = [_index(operand, field) for field in fields[2:]]
    for i, value in enumerate(indices):
        if not isinstance(_type_of(value), ir.IntType):
            raise LlvmTranslationError(f"'getelementptr': index {i} must be an integer, got {_type_of(value)}.")
    _check_indices(typ, fields[3:])
    return _opaque(builder.gep(pointer, indices, source_etype=llvm_type(typ)))


def _load(builder, fields, operand: Operand):
    """`load T, ptr p`: no `align`, so LLVM assumes `T`'s ABI alignment."""
    _arity('load', fields, opcodes.LOAD_FIELDS)
    typ = _type('load', fields, 0)
    return builder.load(operand(fields[1], _PTR), typ=llvm_type(typ))


def _store(builder, fields, operand: Operand):
    """`store T v, ptr p`. It gives no LLVM value: its let binds a name nothing reads."""
    _arity('store', fields, opcodes.STORE_FIELDS)
    typ = _type('store', fields, 0)
    return builder.store(operand(fields[1], typ), operand(fields[2], _PTR))


def _positions(name: str, fields: Sequence[syntax.Term]) -> list[int]:
    """The indices of `extractvalue` or `insertvalue`: byte arrays read as positions."""
    positions = [opcodes.tag_count(field) for field in fields]
    if any(position is None for position in positions):
        raise LlvmTranslationError(f'{name!r}: an index is a position, a byte array such as [01].')
    return [position for position in positions if position is not None]


def _aggregate_type(name: str, fields: Sequence[syntax.Term], indices: Sequence[syntax.Term]) -> syntax.Term:
    typ = _type(name, fields, 0)
    if opcodes.element_type(typ, indices) is None:
        raise LlvmTranslationError(f'{name!r}: the indices go past the parts of {printer.show(typ)}.')
    return typ


def _extractvalue(builder, fields, operand: Operand):
    if len(fields) < opcodes.EXTRACT_MIN_FIELDS:
        raise LlvmTranslationError(
            f"'extractvalue' takes a type, a value and at least one index, got {len(fields)} fields."
        )
    typ = _aggregate_type('extractvalue', fields, fields[2:])
    return builder.extract_value(operand(fields[1], typ), _positions('extractvalue', fields[2:]))


def _insertvalue(builder, fields, operand: Operand):
    if len(fields) < opcodes.INSERT_MIN_FIELDS:
        raise LlvmTranslationError(
            f"'insertvalue' takes a type, a value, a part and at least one index, got {len(fields)} fields."
        )
    typ = _aggregate_type('insertvalue', fields, fields[3:])
    part = opcodes.element_type(typ, fields[3:])
    return builder.insert_value(
        operand(fields[1], typ), operand(fields[2], part), _positions('insertvalue', fields[3:])
    )


_MEMORY = {'alloca': _alloca, 'getelementptr': _getelementptr, 'load': _load, 'store': _store}
_STRUCT = {'extractvalue': _extractvalue, 'insertvalue': _insertvalue}


# `uses`: the type term each field is read at, or None.


def _int_or_none(field):
    return field if opcodes.find_bit_width(field) is not None else None


def _type_or_none(field):
    return field if opcodes.is_literal_type(field) else None


def _pad(types, fields):
    return (list(types) + [None] * len(fields))[: len(fields)]


def _uses(name: str):
    def uses(fields: Sequence[syntax.Term]) -> list[syntax.Term | None]:
        first = fields[0] if fields else None
        if name in _BINARY:
            return _pad([None, _int_or_none(first), _int_or_none(first)], fields)
        if name == 'icmp':
            typ = _type_or_none(fields[1]) if len(fields) > 1 else None
            return _pad([None, None, typ, typ], fields)
        if name in _CONVERT:
            return _pad([None, _int_or_none(first)], fields)
        if name in ('getelementptr', 'load'):
            return _pad([None, _PTR], fields)
        if name == 'store':
            return _pad([None, _type_or_none(first), _PTR], fields)
        if name == 'extractvalue':
            return _pad([None, _type_or_none(first)], fields)
        if name == 'insertvalue':
            typ = _type_or_none(first)
            part = opcodes.element_type(typ, fields[3:]) if typ is not None else None
            return _pad([None, typ, part], fields)
        return _pad([], fields)

    return uses


def _emit(name: str):
    if name in _BINARY:
        return _binary(name, _BINARY[name])
    if name == 'icmp':
        return _icmp
    if name in _MEMORY:
        return _MEMORY[name]
    if name in _STRUCT:
        return _STRUCT[name]
    return _convert(name, _CONVERT[name])


DEFAULT_OPCODES: dict[str, OpcodeImpl] = {name: OpcodeImpl(_emit(name), _uses(name)) for name in opcodes.OPCODES}
