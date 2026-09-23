# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

from dataclasses import dataclass

from oymo.oymomo.terms import Form


@dataclass
class Integer:
    value: int
    form: Form


@dataclass
class Function:
    name: str
    param_form: Form
    body: Integer


@dataclass
class Module:
    name: str
    functions: list[Function]
