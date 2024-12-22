# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _Bool:
    def __repr__(self) -> str:
        return 'Bool'


Bool = _Bool()


@dataclass(frozen=True)
class _Int:
    def __repr__(self) -> str:
        return 'Int'


Int = _Int()


@dataclass(frozen=True)
class Union:
    types: set[Any]

    def __post_init__(self) -> None:
        for el in self.types:
            if isinstance(el, Union):
                raise TypeError('Union type should be flattened, and does not contain another Union type.')

    def __repr__(self) -> str:
        return '|'.join(repr(v) for v in self.types)


def create_union(*args: Any) -> Any:
    result: set[Any] = set()
    for arg in args:
        # Union of unions are flattened
        if isinstance(arg, Union):
            result.update(arg.types)
        else:
            result.add(arg)
    # Unions of a single argument vanish
    if len(result) == 1:
        return next(iter(result))
    return Union(result)
