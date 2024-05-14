// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

#include <cctype>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace tapl {

struct Position {
  std::size_t line{0};
  std::size_t column{0};
};

struct Location {
  Position start;
  Position end;
};

typedef int AstKind;
namespace ast_kind {
constexpr AstKind kData = 1;
constexpr AstKind kCode = 2;
constexpr AstKind kParameter = 3;
constexpr AstKind kAbstraction = 4;
constexpr AstKind kLock = 5;
constexpr AstKind kApplication = 6;
constexpr AstKind kEquivalent = 7;
constexpr AstKind kExpressionAsTerm = 8;
constexpr AstKind kTypedTerm = 9;
}  // namespace ast_kind

struct AstBase {
  AstKind kind{0};
  Location location;

  explicit AstBase(int kind, Location location)
      : kind(kind), location(location) {}
  virtual ~AstBase() = default;
};
using Ast = std::shared_ptr<AstBase>;

struct AstParameter : AstBase {
  Ast signature;
  explicit AstParameter(Location location, Ast signature)
      : AstBase(ast_kind::kParameter, location), signature(signature) {}
};
Ast CreateAstParameter(Location location, Ast code);

struct AstAbstraction : AstBase {
  Ast parameter;
  Ast body;
  AstAbstraction(Location location, Ast parameter, Ast body)
      : AstBase(ast_kind::kAbstraction, location), parameter(parameter), body(body) {}
};
Ast CreateAstAbstraction(Location location, Ast parameter, Ast body);

struct AstLock : AstBase {
  Ast guard;
  Ast body;
  AstLock(Location location, Ast guard, Ast body)
      : AstBase(ast_kind::kLock, location), guard(guard), body(body) {}
};
Ast CreateAstLock(Location location, Ast guard, Ast body);

struct AstApplication : AstBase {
  const Ast function;
  const Ast argument;
  AstApplication(Location location, Ast function, Ast argument)
      : AstBase(ast_kind::kApplication, location),
        function(function),
        argument(argument) {}
};
Ast CreateAstApplication(Location location, Ast function, Ast argument);

struct AstEquivalent : AstBase {
  const Ast left;
  const Ast right;
  AstEquivalent(Location location, Ast left, Ast right)
      : AstBase(ast_kind::kApplication, location),
        left(left), right(right) {}
};
Ast CreateAstEquivalent(Location location, Ast left, Ast right);

struct AstExpressionAsTerm : AstBase {
  Ast expression;
  AstExpressionAsTerm(Location location, Ast expression)
      : AstBase(ast_kind::kExpressionAsTerm, location), expression(expression) {}
};
Ast CreateAstRuntimeError(Location location, Ast expression);

struct AstTypedTerm : AstBase {
  const Ast term;
  const Ast type;
  AstTypedTerm(const Location location, Ast term, Ast type)
      : AstBase(ast_kind::kTypedTerm, location), term(term), type(type) {}
};
Ast CreateAstTypedTerm(Location location, Ast term, Ast type);

}  // namespace tapl