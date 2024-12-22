# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass
from typing import Any, Self


@dataclass(frozen=True)
class _Bool:
    pass

Bool = _Bool()


@dataclass(frozen=True)
class Union:
    types: set[Any]

    def __post_init__(self) -> None:
        for el in self.types:
            if isinstance(el, 'Union'):
                raise ValueError('Union type should be flattened, and does not contain another Union type.')


def simplify_union(union: Union) -> Any:
    """Simplify union

    - Union of unions are flattened: Union(Union(Int, Str), Float) -> Union(Int, Str, Float)
    - Unions of a single argument vanish: Union(Int) == Int
    - Reduntant arguments are skipped: Union(Int, Str, Int) == Union(Int, Str)
    - When comparing unions, argument order ignored: Union[int, str] == Union[str, int]
    """
    pass


def create_union(*args: Any) -> Any:
    result: set[Any] = set()
    for arg in args:
        if isinstance(arg, Union):
            result.update(arg.types)
        else:
            result.add(arg)
    if len(result) == 1:
        return next(iter(result))
    return Union(result)