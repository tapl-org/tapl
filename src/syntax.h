// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

#include <cctype>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace tapl::syntax {

typedef std::string::size_type Position;

struct Location {
  const Position start{0};
  const Position end{0};
};

typedef int AstKind;
namespace ast_kind {
constexpr AstKind kSyntaxError = 1;
constexpr AstKind kSymbolicName = 2;
constexpr AstKind kBytes = 3;
constexpr AstKind kTypeOfFunction = 4;
constexpr AstKind kTermVariable = 5;
constexpr AstKind kNativeCall = 6;
constexpr AstKind kAbstraction = 7;
constexpr AstKind kApplication = 8;
constexpr AstKind kRuntimeError = 9;
constexpr AstKind kExpressionVariable = 10;
constexpr AstKind kTypedTerm = 11;
constexpr AstKind kLock = 12;
constexpr AstKind kUnlock = 13;
constexpr AstKind kLetBinding = 14;
}  // namespace ast_kind

struct AstBase {
  const AstKind kind{0};
  const Location location;

  explicit AstBase(int kind, Location location)
      : kind(kind), location(location) {}
  virtual ~AstBase() = default;
};
using Ast = std::shared_ptr<AstBase>;

struct AstSyntaxError : AstBase {
  const int tag;
  const std::string message;
  explicit AstSyntaxError(Location location, int tag, std::string_view message)
      : AstBase(ast_kind::kSyntaxError, location), tag(tag), message(message) {}
};
Ast CreateAstSyntaxError(Location location, int tag, std::string_view message);

struct AstSymbolicName : AstBase {
  const std::string name;
  AstSymbolicName(const Location location, std::string_view name)
      : AstBase(ast_kind::kSymbolicName, location), name(name) {}
};
Ast CreateAstSymbolicName(Location location, std::string_view name);

struct AstBytes : AstBase {
  const std::string bytes;
  AstBytes(const Location location, std::string& bytes)
      : AstBase(ast_kind::kBytes, location), bytes(bytes) {}
};
Ast CreateAstBytes(Location location, std::vector<std::byte> bytes);

struct AstTypeOfFunction : AstBase {
  const Ast argument_type;
  const Ast result_type;
  AstTypeOfFunction(const Location location, Ast argument_type, Ast result_type)
      : AstBase(ast_kind::kTypeOfFunction, location),
        argument_type(argument_type),
        result_type(result_type) {}
};
Ast CreateAstTypeOfFunction(Location location, Ast argument_type,
                            Ast result_type);

struct AstTermVariable : AstBase {
  const int bruijn_index;
  AstTermVariable(const Location location, int bruijn_index)
      : AstBase(ast_kind::kTermVariable, location),
        bruijn_index(bruijn_index) {}
};
Ast CreateAstTermVariable(Location location, int bruijn_index);

struct AstNativeCall : AstBase {
  const std::vector<Ast> arguments;
  AstNativeCall(const Location location, std::vector<Ast> arguments)
      : AstBase(ast_kind::kNativeCall, location), arguments(arguments) {}
};
Ast CreateAstNativeCall(Location location, std::vector<Ast> arguments);

struct AstAbstraction : AstBase {
  const Ast variable_origin;
  const Ast body;
  AstAbstraction(const Location location, Ast variable_origin, Ast body)
      : AstBase(ast_kind::kAbstraction, location),
        variable_origin(variable_origin),
        body(body) {}
};
Ast CreateAstAbstraction(Location location, Ast variable_origin, Ast body);

struct AstApplication : AstBase {
  const Ast function;
  const Ast argument;
  AstApplication(const Location location, Ast function, Ast argument)
      : AstBase(ast_kind::kApplication, location),
        function(function),
        argument(argument) {}
};
Ast CreateAstApplication(Location location, Ast function, Ast argument);

struct AstRuntimeError : AstBase {
  AstRuntimeError(const Location location)
      : AstBase(ast_kind::kRuntimeError, location) {}
};
Ast CreateAstRuntimeError(Location location);

struct AstTypedTerm : AstBase {
  const Ast term;
  const Ast type;
  AstTypedTerm(const Location location, Ast term, Ast type)
      : AstBase(ast_kind::kTypedTerm, location), term(term), type(type) {}
};
Ast CreateAstTypedTerm(Location location, Ast term, Ast type);

struct AstLock : AstBase {
  const Ast variable_origin;
  const Ast argument_type;
  const Ast body;
  AstLock(const Location location, Ast variable_origin, Ast argument_type,
          Ast body)
      : AstBase(ast_kind::kLock, location),
        variable_origin(variable_origin),
        argument_type(argument_type),
        body(body) {}
};
Ast CreateAstLock(Location location, std::string_view variable_name_hint,
                  Ast argument_type, Ast body);

struct AstUnlock : AstBase {
  const Ast function;
  const Ast argument;
  AstUnlock(const Location location, Ast function, Ast argument)
      : AstBase(ast_kind::kUnlock, location),
        function(function),
        argument(argument) {}
};
Ast CreateUnlock(Location location, Ast function, Ast argument);

struct AstLetBinding : AstBase {
  const Ast variable_origin;
  const Ast bound_expression;
  const Ast body;
  AstLetBinding(const Location location, Ast variable_origin,
                Ast bound_expression, Ast body)
      : AstBase(ast_kind::kLetBinding, location),
        variable_origin(variable_origin),
        bound_expression(bound_expression),
        body(body) {}
};
Ast CreateLetBinding(Location location, Ast variable_origin,
                     Ast bound_expression, Ast body);

std::shared_ptr<AstSyntaxError> CastToSyntaxError(Ast ast);
bool WellFormed(Ast ast);
bool WellFormed_LogIfNot(Ast ast);

}  // namespace tapl::syntax