// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include <memory>
#include <string_view>
#include <vector>

#include "src/chunk.h"

namespace tapl {

Position Location::start() const { return start_; }

Position Location::end() const { return end_; }

Chunk::Chunk(Location location, std::string_view text,
             std::vector<std::shared_ptr<Chunk>> children)
    : location_(location), text_(text), children_(children) {}

Location Chunk::location() const { return location_; }

std::string_view Chunk::text() const { return text_; }

const std::vector<std::shared_ptr<Chunk>>& Chunk::children() const {
  return children_;
}

}  // namespace tapl