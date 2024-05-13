// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include "src/chunk.h"

#include <iomanip>
#include <stdexcept>

#include "absl/strings/substitute.h"

namespace tapl {

void ChunkParser::SplitLines() {
  std::string_view sv = std::string_view(text_);
  std::size_t pos = 0;
  std::size_t nextPos;

  while ((nextPos = sv.find('\n', pos)) != std::string::npos) {
    // TODO: strip out trailing spaces
    lines_.emplace_back(sv.substr(pos, nextPos - pos));
    pos = nextPos + 1;
  }
  // Handle the last line if it doesn't end with a newline
  if (pos < sv.size()) {
    lines_.emplace_back(sv.substr(pos));
  }
}

std::size_t GetIndentLevel(std::string_view line) {
  for (std::size_t i = 0; i < line.length(); i++) {
    if (line[i] != ' ') {
      return i;
    }
  }
  return line.length();
}

std::vector<std::size_t> ChunkParser::GetChunkLineNumbers(
    std::size_t start, std::size_t end, std::size_t indent_level) {
  std::vector<std::size_t> indices;
  for (std::size_t i = start; i < end; i++) {
    std::size_t level = GetIndentLevel(lines_[i]);
    // If line is empty or just contains space, then continue
    if (level == lines_[i].length()) continue;
    if (level == indent_level) {
      indices.push_back(i);
    } else if (level < indent_level) {
      throw std::runtime_error(
          absl::Substitute("Line indent is smaller then expected indent level. "
                           "line=$0,level=$1,expected=$2",
                           i, level, indent_level));
    } else if (level > indent_level && indices.empty()) {
      throw std::runtime_error("First line must be at the given indent level.");
    }
  }
  if (indices.empty()) {
    throw std::runtime_error("No chunk found at the given indent level.");
  }
  return indices;
}

std::size_t ChunkParser::FindFirstPossibleIndent(std::size_t start,
                                                 std::size_t end,
                                                 std::size_t indent_level) {
  for (std::size_t j = start; j < end; j++) {
    std::size_t level = GetIndentLevel(lines_[j]);
    // If line is empty or just contains space, then continue
    if (level == lines_[j].length()) continue;
    if (level < indent_level) {
      throw std::runtime_error(
          "Child indent must be greater than parent indent.");
    }
    return level;
  }
  throw std::runtime_error("First possible indent could not be found.");
}

Chunk ChunkParser::ParseChunk(std::size_t start, std::size_t end,
                              std::size_t indent_level) {
  Chunk chunk{indent_level, start, end - start, {}};
  for (std::size_t i = start; i < end; i++) {
    std::string_view line = lines_[i];
    if (line.empty()) continue;
    // If line ends with colon, then this chunk may have children
    if (line[line.length() - 1] == ':') {
      std::size_t children_start = i + 1;
      std::size_t child_indent =
          FindFirstPossibleIndent(children_start, end, indent_level + 1);
      chunk.line_count = children_start - start;
      chunk.children = ParseChunks(children_start, end, child_indent);
      // All children are found
      break;
    }
  }
  return chunk;
}

std::vector<Chunk> ChunkParser::ParseChunks(std::size_t start, std::size_t end,
                                            std::size_t indent_level) {
  std::vector<std::size_t> indices =
      GetChunkLineNumbers(start, end, indent_level);
  std::vector<Chunk> result;
  for (std::size_t i = 0; i < indices.size(); i++) {
    std::size_t next = (i + 1) < indices.size() ? indices[i + 1] : end;
    result.push_back(ParseChunk(indices[i], next, indent_level));
  }
  return result;
}

void ChunkParser::Init() {
  SplitLines();
  chunks_ = ParseChunks(0, lines_.size(), 0);
}

void ChunkParser::PrintDump(std::stringstream& ss, const Chunk& chunk,
                            int index) {
  for (std::size_t i = 0; i < chunk.line_count; i++) {
    std::size_t k = chunk.start_line + i;
    ss << std::setw(10) << std::left;
    if (i == 0) {
      ss << absl::Substitute("$0:$1-$2", k, chunk.indent_level, index);
    } else {
      ss << k;
    }
    ss << "|" << lines_[k] << "\n";
  }
  PrintDump(ss, chunk.children);
}

void ChunkParser::PrintDump(std::stringstream& ss,
                            const std::vector<Chunk>& chunks) {
  for (std::size_t i = 0; i < chunks.size(); i++) {
    PrintDump(ss, chunks[i], i);
  }
}

std::string ChunkParser::GetDump() {
  std::stringstream ss;
  ss << "\n";
  PrintDump(ss, chunks_);
  return ss.str();
}

}  // namespace tapl