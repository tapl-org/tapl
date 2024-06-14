// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include "src/syntax.h"

#include <memory>
#include <stdexcept>

#include "absl/log/check.h"
#include "absl/log/log.h"

#include "absl/strings/substitute.h"

namespace tapl {

void AstBase::AppendToBody(Ast ast) {
  throw std::runtime_error(absl::Substitute("Ast kind=$0 does not support AppendToBody.", kind));
}

Lines AstBase::GeneratePythonCode() {
  throw std::runtime_error(absl::Substitute("Python code generation is not supported. kind=$0", kind));
}

void AstAbstraction::AppendToBody(Ast ast) {
  body->AppendToBody(ast);
}

void AstLock::AppendToBody(Ast ast) {
  body->AppendToBody(ast);
}

Ast CreateAstAbstraction(Location location, Ast parameter, Ast body) {
  return std::make_shared<AstAbstraction>(location, parameter, body);
}

Ast CreateAstLock(Location location, Ast guard,
                            Ast body) {
  return std::make_shared<AstLock>(location, guard, body);
}

Ast CreateAstApplication(Location location, Ast function, Ast argument) {
  return std::make_shared<AstApplication>(location, function, argument);
}

Ast CreateAstEquivalent(Location location, Ast left, Ast right) {
  return std::make_shared<AstApplication>(location, left, right);
}

Ast CreateAstExpressionAsTerm(Location location, Ast expression) {
  return std::make_shared<AstExpressionAsTerm>(location, expression);
}

Ast CreateAstParameter(Location location, Ast signature) {
  return std::make_shared<AstParameter>(location, signature);
}

Ast CreateAstTypedTerm(Location location, Ast term, Ast type) {
  return std::make_shared<AstTypedTerm>(location, term, type);
}

Ast CreateAstCollection(Location location) {
  return std::make_shared<AstCollection>(location);
}

void AstCollection::AppendToBody(Ast ast) {
  ast_list.push_back(ast);
}

Ast CreateAstPyhonCode(Location location, Lines lines) {
  return std::make_shared<AstPythonCode>(location, lines);
}

}  // namespace tapl