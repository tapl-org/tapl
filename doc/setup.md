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
sudo update-alternatives --install /usr/bin/cc cc /usr/bin/clang-17 100
```

