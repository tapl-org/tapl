// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include "src/syntax.h"

#include <memory>

#include "absl/log/check.h"
#include "absl/log/log.h"

namespace tapl::syntax {

Ast CreateAstParameter(Location location, Ast signature) {
  return std::make_shared<AstParameter>(location, signature);
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

Ast CreateAstTypedTerm(Location location, Ast term, Ast type) {
  return std::make_shared<AstTypedTerm>(location, term, type);
}

}  // namespace tapl::syntax