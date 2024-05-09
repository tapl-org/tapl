// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <memory>
#include <string_view>
#include <vector>

#include "src/chunk.h"

namespace tapl {

class Chunker {
 public:
  std::vector<ChunkPtr> devide_text(std::string_view text) const;
};

}  // namespace tapl