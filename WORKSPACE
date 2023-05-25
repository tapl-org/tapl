# Part of the Tapl Language project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

workspace(name = "tapl")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

skylib_version = "1.4.1"

http_archive(
    name = "bazel_skylib",
    sha256 = "74d544d96f4a5bb630d465ca8bbcfe231e3594e5aae57e1edbf17a6eb3ca2506",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/bazel-skylib/releases/download/{0}/bazel-skylib-{0}.tar.gz".format(skylib_version),
        "https://github.com/bazelbuild/bazel-skylib/releases/download/{0}/bazel-skylib-{0}.tar.gz".format(skylib_version),
    ],
)

###############################################################################
# Abseil libraries
###############################################################################

# Head as of 2022-09-13.
abseil_version = "530cd52f585c9d31b2b28cea7e53915af7a878e3"

http_archive(
    name = "com_google_absl",
    sha256 = "f8a6789514a3b109111252af92da41d6e64f90efca9fb70515d86debee57dc24",
    strip_prefix = "abseil-cpp-{0}".format(abseil_version),
    urls = ["https://github.com/abseil/abseil-cpp/archive/{0}.tar.gz".format(abseil_version)],
)

###############################################################################
# GoogleTest libraries
###############################################################################

# Head as of 2022-09-14.
googletest_version = "1336c4b6d1a6f4bc6beebccb920e5ff858889292"

http_archive(
    name = "com_google_googletest",
    sha256 = "d701aaeb9a258afba27210d746d971042be96c371ddc5a49f1e8914d9ea17e3c",
    strip_prefix = "googletest-{0}".format(googletest_version),
    urls = ["https://github.com/google/googletest/archive/{0}.tar.gz".format(googletest_version)],
)

