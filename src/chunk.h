// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace tapl {

typedef std::string::size_type Position;

class Location {
 public:
  Position start() const;
  Position end() const;

 private:
  Position start_;
  Position end_;
};

class Chunk {
 public:
  Chunk(Location location, std::string_view text,
        std::vector<std::shared_ptr<Chunk>> children);
  Location location() const;
  std::string_view text() const;
  const std::vector<std::shared_ptr<Chunk>>& children() const;

 private:
  Location location_;
  std::string_view text_;
  std::vector<std::shared_ptr<Chunk>> children_;
};
using ChunkPtr = std::shared_ptr<Chunk>;

}  // namespace tapl
