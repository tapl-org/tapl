# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass


class Type(ABC):
    @abstractmethod
    def normalize(self) -> 'Type':
        pass


@dataclass(frozen=True)
class Base(Type):
    name: str

    def normalize(self) -> Type:
        return self


# Top and Bottom
Any = Base('Any')
Nothing = Base('Nothing')
NoneType = Base('None')

# Proper types
Bool = Base('Bool')
Int = Base('Int')
Float = Base('Float')
Complex = Base('Complex')
Str = Base('Str')


@dataclass(frozen=True)
class List(Type):
    element: Type

    def normalize(self):
        return List(self.element.normalize())


@dataclass(frozen=True)
class Dict(Type):
    key: Type
    value: type

    def normalize(self):
        return Dict(self.key.normalize(), self.value.normalize())


@dataclass(frozen=True)
class Union(Type):
    operands: list[Type]

    def normalize(self) -> Type:
        """Normalization

        - Union of unions are flattened
        - Unions of a single argument vanish
        - Reduntant arguments are skipped
        - When comparing unions, argument order ignored
        """
        result: set[Type] = set()
        for operand in self.operands:
            normalized = operand.normalize()
            if isinstance(normalized, Union):
                result.update(normalized.operands)
            else:
                result.add(normalized)
        if len(result) == 1:
            return next(iter(result))
        return Union(list(result))


@dataclass(frozen=True)
class Intersection:
    operands: list[Type]

    def normalize(self):
        return self


def check_valid_type(arg: Type) -> bool:
    return isinstance(arg, Type)


def raise_error_if_not_valid(arg: Type) -> None:
    if not check_valid_type(arg):
        raise TypeError(f'Invalid type: {arg}')


def create_union(args: list[Type]) -> Type:
    return Union(args).normalize()


def tc_unary_op(op: ast.unaryop, arg: Type) -> Type:
    if isinstance(op, ast.Not):
        check_valid_type(arg)
        return Bool
    raise NotImplementedError


def tc_bool_op(*args: Type) -> Type:
    return create_union(list(args))
