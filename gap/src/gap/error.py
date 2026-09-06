# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


class GapError(Exception):
    pass


class ReadError(GapError):
    """A term the reader rejects: bad head, wrong arity, duplicate label, bits where a name belongs."""

    def __init__(self, message: str, position: int = -1):
        super().__init__(f'{message} at offset {position}' if position >= 0 else message)
        self.position = position
