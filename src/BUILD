# Part of the TAPL project, under the Apache License v2.0 with LLVM
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

cc_library(
    name = "chunk",
    srcs = ["chunk.cc"],
    hdrs = ["chunk.h"],
    deps = [
        "@abseil-cpp//absl/log",
        "@abseil-cpp//absl/log:check",
    ],

)
cc_library(
    name = "chunker",
    srcs = ["chunker.cc"],
    hdrs = ["chunker.h"],
    deps = [
        ":chunk",
        "@abseil-cpp//absl/log",
        "@abseil-cpp//absl/log:check",
    ],
)
cc_test(
    name = "chunker_test",
    srcs = ["chunker_test.cc"],
    deps = [
        ":chunker",
        "@googletest//:gtest_main",
    ]
)