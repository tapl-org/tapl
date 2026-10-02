# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""The default LLVM implementation of each prim op in banf_prim."""

from collections.abc import Callable

from llvmlite import ir

from oymo.oymomo import banf_prim

type PrimImpl = Callable[[ir.IRBuilder, list[ir.Value]], ir.Value]


def _binary(method):
    return lambda builder, args: getattr(builder, method)(*args)


def _compare(method, op):
    return lambda builder, args: getattr(builder, method)(op, *args)


def _convert(method, result):
    target = ir.IntType(banf_prim.int_bits(result))
    return lambda builder, args: getattr(builder, method)(args[0], target)


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

_CONVERT = {'zext': 'zext', 'sext': 'sext', 'trunc': 'trunc'}


def _impl(signature: banf_prim.PrimSignature) -> PrimImpl:
    template = signature.template
    if template in _BINARY:
        return _binary(_BINARY[template])
    if template in _COMPARE:
        return _compare(*_COMPARE[template])
    return _convert(_CONVERT[template], signature.result)


DEFAULT_PRIMS: dict[str, PrimImpl] = {name: _impl(signature) for name, signature in banf_prim.PRIMS.items()}
