# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The default LLVM implementation of each opcode in `opcodes.OPCODES`.

Each implementation reads its call's fields by position, as `opcodes` does: `{type, a, b}`
for an arithmetic or logic opcode, `{predicate, type, a, b}` for `icmp`, `{type, value, to}`
for a conversion, `{type}` or `{type, count}` for `alloca`, `{type, ptr, i₀, …}` for
`getelementptr`, `{type, ptr}` for `load`, `{type, value, ptr}` for `store`. A type field is
a type term (9.1); an operand takes the type the opcode reads it at, so a bare byte array
there is a constant of that type.
"""

from collections.abc import Sequence

from llvmlite import ir

from oymo.core import syntax
from oymo.oymomo import opcodes, terms
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
    if not opcodes.is_literal_form(field):
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


def _opaque(instruction: ir.Instruction) -> ir.Instruction:
    """llvmlite types a pointer it makes by what it points to; LLVM's `ptr` is opaque."""
    instruction.type = ir.PointerType()
    return instruction


def _alloca(builder, fields, operand: Operand):
    if len(fields) not in (1, 2):
        raise LlvmTranslationError(f"'alloca' takes a type and an optional count, got {len(fields)} fields.")
    typ = llvm_type(_type('alloca', fields, 0))
    count = _index(operand, fields[1]) if len(fields) > 1 else None
    if count is not None and not isinstance(count.type, ir.IntType):
        raise LlvmTranslationError(f"'alloca': count must be an integer, got {count.type}.")
    return _opaque(builder.alloca(typ, size=count))


def _check_indices(typ: syntax.Term, fields: Sequence[syntax.Term]) -> None:
    """Every index past the first goes into a part of the type so far: into a struct or a
    packed struct, it is a byte array below its field count, as LLVM's constant `i32`; into an
    array or a vector, it may be known only at run time."""
    for index, field in enumerate(fields, start=1):
        tagged = opcodes.tagged_form(typ)
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
        if not isinstance(value.type, ir.IntType):
            raise LlvmTranslationError(f"'getelementptr': index {i} must be an integer, got {value.type}.")
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


_MEMORY = {'alloca': _alloca, 'getelementptr': _getelementptr, 'load': _load, 'store': _store}


def _impl(name: str) -> OpcodeImpl:
    if name in _BINARY:
        return _binary(name, _BINARY[name])
    if name == 'icmp':
        return _icmp
    if name in _MEMORY:
        return _MEMORY[name]
    return _convert(name, _CONVERT[name])


DEFAULT_OPCODES: dict[str, OpcodeImpl] = {name: _impl(name) for name in opcodes.OPCODES}
