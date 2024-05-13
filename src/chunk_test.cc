// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include "src/chunk.h"

#include "gtest/gtest.h"

namespace tapl {

void Assert(std::string text, std::string dump) {
  ChunkParser parser(text);
  parser.Init();
  ASSERT_STREQ(parser.GetDump().c_str(), dump.c_str());
}

TEST(ChunkTest, Parse1) {
  Assert(R"(
Hello
World
)", R"(
1:0-0     |Hello
2:0-1     |World
)");
}

TEST(ChunkTest, Parse2) {
  Assert(R"(
Hello
 World
)", R"(
1:0-0     |Hello
2         | World
)");
}

TEST(ChunkTest, Parse3) {
  Assert(R"(

Hello
 World
One
    two
  three

)", R"(
2:0-0     |Hello
3         | World
4:0-1     |One
5         |    two
6         |  three
7         |
)");
}

TEST(ChunkTest, Parse4) {
  Assert(R"(
Hello:
 World
)", R"(
1:0-0     |Hello:
2:1-0     | World
)");
}

TEST(ChunkTest, Parse5) {
  Assert(R"(
def compute_next(n):
  if n % 2 == 0:
    print('even')
    return n / 2
  else:
    print('odd')
    return 3 * n + 1
)", R"(
1:0-0     |def compute_next(n):
2:2-0     |  if n % 2 == 0:
3:4-0     |    print('even')
4:4-1     |    return n / 2
5:2-1     |  else:
6:4-0     |    print('odd')
7:4-1     |    return 3 * n + 1
)");
}



}  // namespace tapl