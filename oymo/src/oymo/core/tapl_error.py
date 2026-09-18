# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception


class TaplError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class UnhandledError(TaplError):
    def __init__(self, message: str = 'Unhandled error'):
        super().__init__(message)
