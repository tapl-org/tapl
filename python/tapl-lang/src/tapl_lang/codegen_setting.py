# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import enum
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


class VariableHandling(enum.Enum):
    NATIVE = 1  # Variables are handled natively
    MANUAL = 2  # Variables are managed manually (e.g., in a scope)


@dataclass
class CodegenSetting:
    variable_handling: VariableHandling = VariableHandling.NATIVE
    scope_level: int = 0


current: ContextVar[CodegenSetting] = ContextVar('codegen_setting', default=CodegenSetting())


def get_current() -> CodegenSetting:
    return current.get()


@contextmanager
def set_current(setting: CodegenSetting) -> Generator[None, None, None]:
    old_setting = current.get()
    current.set(setting)
    try:
        yield
    finally:
        current.set(old_setting)


@contextmanager
def new_inner_scope() -> Generator[None, None, None]:
    old_setting = current.get()
    current.set(
        CodegenSetting(variable_handling=old_setting.variable_handling, scope_level=old_setting.scope_level + 1)
    )
    try:
        yield
    finally:
        current.set(old_setting)


def get_scope_name() -> str:
    return f'scope{current.get().scope_level}'
