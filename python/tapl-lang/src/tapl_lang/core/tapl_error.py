# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


class TaplError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class MismatchedLayerLengthError(TaplError):
    def __init__(self, message: str = 'Mismatched layer lengths'):
        super().__init__(message)


class UnhandledError(TaplError):
    def __init__(self, message: str = 'Unhandled error'):
        super().__init__(message)
