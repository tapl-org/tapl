// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

#include <memory>
#include <string>
#include <string_view>
#include <sstream>
#include <vector>
#include <unordered_map>

#include "src/syntax.h"

namespace tapl {

/* A Chunk is a sequence of lines where the first line has less start whitespace
then others, and only last line ends with colon (:) or next line of the last
lines of the chunk has same start whitespace as chunk's first line. If a chunk ends
with colon, then that chunk must have a child chunk which consist of all next
lines have more start whitespace than parent.
Skip empty lines or a line with whitespace (only space)
*/

struct ChunkData;
using Chunk = std::shared_ptr<ChunkData>;

struct ChunkData {
  Position offset{0, 0};
  Lines lines{nullptr};
  std::vector<Chunk> children{};
  ChunkData() {}
};

class Parser;

struct ParserResult {
  Ast ast;
  std::shared_ptr<Parser> child_parser;
  std::shared_ptr<Parser> sibling_parser;
};

class Parser {
 public:
  virtual ParserResult Parse(Lines lines, Position offset);
};

class ChunkProcessor {
 public:
  ChunkProcessor(const std::string& text) : text_{text} {}
  void Split();
  std::string GetDump();
  Ast Parse(std::shared_ptr<Parser> parser);

 private:
  std::string text_;
  std::vector<std::string_view> lines_;
  std::vector<Chunk> chunks_{};

  void SplitLines();
  std::vector<std::size_t> GetChunkLineNumbers(std::size_t start, std::size_t end, std::size_t indent_level);
  std::size_t FindFirstPossibleIndent(std::size_t start, std::size_t end, std::size_t indent_level);
  Chunk DecodeChunk(std::size_t start, std::size_t end, std::size_t indent_level);
  void DecodeChunks(std::size_t start, std::size_t end, std::size_t indent_level, std::vector<Chunk>& container);

  void PrintDump(std::stringstream& ss, const Chunk& chunk, int index);
  void PrintDump(std::stringstream& ss, const std::vector<Chunk>& chunks);

};

}  // namespace tapl
