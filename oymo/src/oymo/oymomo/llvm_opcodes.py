# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The default LLVM implementation of each opcode in `opcodes.OPCODES`.

Each implementation reads the BANF fields of its call by position, as `opcodes` does:
`{form, a, b}` for an arithmetic, logic or comparison opcode, `{form, value, to}` for a
conversion. A form field is a `Const` with no form, whose bytes name the form (`'i32'`).
"""

from collections.abc import Callable, Sequence

from llvmlite import ir

from oymo.oymomo import banf_terms as banf
from oymo.oymomo import opcodes, terms
from oymo.oymomo.llvm_translate import LlvmTranslationError

# Turns a field into an LLVM value, read at the given form: a `Const` with no form takes
# that form; any other atom is its own value.
type Operand = Callable[[banf.Atom, terms.Term], ir.Value]

# Gets the builder, the call's fields, and `Operand`.
type OpcodeImpl = Callable[[ir.IRBuilder, Sequence[banf.Atom], Operand], ir.Value]


def _form(name: str, fields: Sequence[banf.Atom], index: int) -> terms.Term:
    """Field `index`, read as an integer form, such as `'i32'`."""
    field = fields[index]
    form = terms.ByteArray(field.value) if isinstance(field, banf.Const) and field.form is terms.Empty else None
    if form is None or opcodes.find_bit_width(form) is None:
        raise LlvmTranslationError(f"{name!r}: field {index} must be an integer form, such as 'i32'.")
    return form


def _arity(name: str, fields: Sequence[banf.Atom]) -> None:
    if len(fields) != opcodes.FIELD_COUNT:
        raise LlvmTranslationError(f'{name!r} takes {opcodes.FIELD_COUNT} fields, got {len(fields)}.')


def _binary(name, method):
    def impl(builder, fields, operand):
        _arity(name, fields)
        form = _form(name, fields, 0)
        return getattr(builder, method)(operand(fields[1], form), operand(fields[2], form))

    return impl


def _compare(name, method, op):
    def impl(builder, fields, operand):
        _arity(name, fields)
        form = _form(name, fields, 0)
        return getattr(builder, method)(op, operand(fields[1], form), operand(fields[2], form))

    return impl


def _convert(name, method):
    def impl(builder, fields, operand):
        _arity(name, fields)
        form, to = _form(name, fields, 0), _form(name, fields, 2)
        return getattr(builder, method)(operand(fields[1], form), ir.IntType(opcodes.bit_width(to)))

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

_COMPARE = {
    'icmp_eq': ('icmp_unsigned', '=='),
    'icmp_ne': ('icmp_unsigned', '!='),
    'icmp_slt': ('icmp_signed', '<'),
    'icmp_sle': ('icmp_signed', '<='),
    'icmp_sgt': ('icmp_signed', '>'),
    'icmp_sge': ('icmp_signed', '>='),
    'icmp_ult': ('icmp_unsigned', '<'),
    'icmp_ule': ('icmp_unsigned', '<='),
    'icmp_ugt': ('icmp_unsigned', '>'),
    'icmp_uge': ('icmp_unsigned', '>='),
}

_CONVERT = {'zext': 'zext', 'sext': 'sext', 'trunc': 'trunc'}


def _impl(name: str) -> OpcodeImpl:
    if name in _BINARY:
        return _binary(name, _BINARY[name])
    if name in _COMPARE:
        return _compare(name, *_COMPARE[name])
    return _convert(name, _CONVERT[name])


DEFAULT_OPCODES: dict[str, OpcodeImpl] = {name: _impl(name) for name in opcodes.OPCODES}
