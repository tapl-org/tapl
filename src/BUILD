# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

cc_binary(
    name = "main",
    srcs = ["main.cpp"],
    deps = [],
)

cc_library(
    name = "syntax",
    srcs = ["syntax.cc"],
    hdrs = ["syntax.h"],
    deps = [
        "@abseil-cpp//absl/log",
        "@abseil-cpp//absl/log:check",
    ],
)