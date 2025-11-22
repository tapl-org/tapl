# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

EVALATE_LAYER_INDEX = 1
TYPECHECK_LAYER_INDEX = 2


class TaplDev:
    def __init__(self, layer_index: int) -> None:
        self.layer_index = layer_index
        self.print = print

    def print_type(self, type_) -> None:
        if self.layer_index == TYPECHECK_LAYER_INDEX:
            self.print(repr(type_))
