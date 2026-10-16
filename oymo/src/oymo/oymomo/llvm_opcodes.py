# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The default LLVM implementation of each opcode in `opcodes.OPCODES`.

Each implementation reads the BANF fields of its call by position, as `opcodes` does:
`{form, a, b}` for an arithmetic, logic or comparison opcode, `{form, value, to}` for a
conversion, `{form}` or `{form, count}` for `alloca`, `{form, ptr, i0, ...}` for
`getelementptr`. A form field is a `Const` with no form, whose bytes name the form
(`'i32'`), or a `FormField` for a struct form.
"""

from collections.abc import Callable, Sequence

from llvmlite import ir

from oymo.oymomo import banf_terms as banf
from oymo.oymomo import opcodes, terms
from oymo.oymomo.llvm_translate import LlvmTranslationError, llvm_type

# Turns a field into an LLVM value, read at the given form: a `Const` with no form takes
# that form; any other atom is its own value.
type Operand = Callable[[banf.Atom, terms.Term], ir.Value]

# Gets the builder, the call's fields, and `Operand`.
type OpcodeImpl = Callable[[ir.IRBuilder, Sequence[banf.Atom | banf.FormField], Operand], ir.Value]


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

_I32 = terms.ByteArray.from_str('i32')
_I32_BYTES = opcodes.byte_width(opcodes.bit_width(_I32))


def _any_form(name: str, fields: Sequence[banf.Atom | banf.FormField], index: int) -> terms.Term:
    """Field `index`, read as any form: a named one (`'i32'`, `'ptr'`) or a struct."""
    field = fields[index]
    if isinstance(field, banf.FormField):
        return field.form
    if isinstance(field, banf.Const) and field.form is terms.Empty:
        return terms.ByteArray(field.value)
    raise LlvmTranslationError(f"{name!r}: field {index} must be a form, such as 'i32'.")


def _formed(name: str, what: str, atom: banf.Atom | banf.FormField, operand: Operand) -> ir.Value:
    """An operand with no form field to be read at: a bare byte array is an error."""
    if isinstance(atom, banf.FormField) or (isinstance(atom, banf.Const) and atom.form is terms.Empty):
        raise LlvmTranslationError(f"{name!r}: {what} must have a form, such as [01000000]~'i32'.")
    return operand(atom, terms.Empty)


def _opaque(instruction: ir.Instruction) -> ir.Instruction:
    """llvmlite types a pointer it makes by what it points to; LLVM's `ptr` is opaque."""
    instruction.type = ir.PointerType()
    return instruction


def _alloca(builder, fields, operand):
    if len(fields) not in (1, 2):
        raise LlvmTranslationError(f"'alloca' takes a form and an optional count, got {len(fields)} fields.")
    form = llvm_type(_any_form('alloca', fields, 0))
    count = _formed('alloca', 'count', fields[1], operand) if len(fields) > 1 else None
    if count is not None and not isinstance(count.type, ir.IntType):
        raise LlvmTranslationError(f"'alloca': count must be an integer, got {count.type}.")
    return _opaque(builder.alloca(form, size=count))


def _check_indices(form: terms.Term, fields: Sequence[banf.Atom | banf.FormField]) -> None:
    """Every index past the first goes into a part of the form so far: into a struct, it is
    a literal `'i32'` below its field count, as in LLVM."""
    for index, atom in enumerate(fields, start=1):
        if not isinstance(form, terms.Struct):
            raise LlvmTranslationError(
                f"'getelementptr': index {index} goes into {banf.show_form(form)}, which has no parts."
            )
        count = len(form.fields)
        if not (isinstance(atom, banf.Const) and atom.form == _I32 and len(atom.value) == _I32_BYTES):
            raise LlvmTranslationError(
                f"'getelementptr': index {index} into {banf.show_form(form)} must be a literal 'i32' below {count}."
            )
        position = int.from_bytes(atom.value, 'little')
        if position >= count:
            raise LlvmTranslationError(
                f"'getelementptr': index {index} into {banf.show_form(form)} must be a literal 'i32' below {count}."
            )
        form = form.fields[position].value


def _getelementptr(builder, fields, operand):
    if len(fields) < opcodes.GEP_MIN_FIELDS:
        raise LlvmTranslationError(
            f"'getelementptr' takes a form, a pointer and at least one index, got {len(fields)} fields."
        )
    form = _any_form('getelementptr', fields, 0)
    pointer = _formed('getelementptr', 'the pointer', fields[1], operand)
    if not isinstance(pointer.type, ir.PointerType):
        raise LlvmTranslationError(f"'getelementptr' expects a pointer, got {pointer.type}.")
    indices = [_formed('getelementptr', f'index {i}', atom, operand) for i, atom in enumerate(fields[2:])]
    for i, value in enumerate(indices):
        if not isinstance(value.type, ir.IntType):
            raise LlvmTranslationError(f"'getelementptr': index {i} must be an integer, got {value.type}.")
    _check_indices(form, fields[3:])
    return _opaque(builder.gep(pointer, indices, source_etype=llvm_type(form)))


_MEMORY = {'alloca': _alloca, 'getelementptr': _getelementptr}


def _impl(name: str) -> OpcodeImpl:
    if name in _BINARY:
        return _binary(name, _BINARY[name])
    if name in _COMPARE:
        return _compare(name, *_COMPARE[name])
    if name in _MEMORY:
        return _MEMORY[name]
    return _convert(name, _CONVERT[name])


DEFAULT_OPCODES: dict[str, OpcodeImpl] = {name: _impl(name) for name in opcodes.OPCODES}
