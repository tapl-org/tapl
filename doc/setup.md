<? Part of the TAPL project, under the Apache License v2.0 with LLVM
   Exceptions. See /LICENSE for license information.
   SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception ?>

## Tools

1. [adr](https://github.com/npryce/adr-tools/blob/master/INSTALL.md)

## Set up the build environment

1. Install bazel - [ref](https://stackoverflow.com/a/67538831/22663977)
```
dpkg --print-architecture
wget https://github.com/bazelbuild/bazelisk/releases/download/v1.18.0/bazelisk-linux-amd64
chmod +x bazelisk-linux-amd64
sudo mv bazelisk-linux-amd64 /usr/local/bin/bazel
which bazel
bazel --version
```
2. Install bazel buildifier optional - [ref](https://github.com/bazelbuild/buildtools/releases)
```
wget https://github.com/bazelbuild/buildtools/releases/download/v6.3.3/buildifier-linux-amd64
chmod +x buildifier-linux-amd64
sudo mv buildifier-linux-amd64 /usr/local/bin/buildifier
which buildifier
```
3. Install clang - [ref](https://apt.llvm.org/)
```
sudo bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)"
sudo update-alternatives --install /usr/bin/cc cc /usr/bin/clang-18 100
echo "export CC=/usr/bin/cc" >> ~/.bash_aliases
```
4. Download absl
```
bazel build @abseil-cpp//...
```
5. Refresh Hedron
```
bazel run @hedron_compile_commands//:refresh_all
```
6. Clean bazel cache
```
bazel clean --expunge
```
