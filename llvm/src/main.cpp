// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <iostream>

int main() {
  std::cout << "C++ version: " << __cplusplus << std::endl;
  int arr[5] = {1, 2, 3, 4, 5};
  std::cout << 3[arr] << std::endl;
  return 0;
}