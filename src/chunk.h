// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

#include <memory>
#include <string>
#include <string_view>
#include <sstream>
#include <vector>

namespace tapl {

/* A Chunk is a sequence of lines where the first line has less start whitespace
then others, and only last line ends with colon (:) or next line of the last
lines of chunk has same start whitespace as chunk's first line. If a chunk ends
with colon, then that chunk must have a child chunk which consist of all next
lines which have more start whitespace than parent.
Skip empty lines or a line with whitespace (only space)
*/

struct Chunk {
  std::size_t indent_level;
  std::size_t start_line;
  std::size_t line_count;
  std::vector<Chunk> children;
};

class ChunkParser {
 public:
  ChunkParser(const std::string& text) : text_{text} {}
  void Init();
  std::string GetDump();

 private:
  std::string text_;
  std::vector<std::string_view> lines_;
  std::vector<Chunk> chunks_;

  void SplitLines();
  Chunk ParseChunk(std::size_t start, std::size_t end, std::size_t indent_level);
  std::vector<std::size_t> GetChunkLineNumbers(std::size_t start, std::size_t end, std::size_t indent_level);
  std::size_t FindFirstPossibleIndent(std::size_t start, std::size_t end, std::size_t indent_level);
  std::vector<Chunk> ParseChunks(std::size_t start, std::size_t end, std::size_t indent_level);

  void PrintDump(std::stringstream& ss, const Chunk& chunk, int index);
  void PrintDump(std::stringstream& ss, const std::vector<Chunk>& chunks);

};

}  // namespace tapl
