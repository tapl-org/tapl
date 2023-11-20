// Part of the Tapl Language project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#include "src/syntax.h"

#include <memory>

#include "absl/log/check.h"
#include "absl/log/log.h"

namespace tapl::syntax {

Ast CreateAstSyntaxError(Location location, int tag, std::string_view message) {
  return std::make_shared<AstSyntaxError>(location, tag, message);
}
Ast CreateAstSymbolicName(Location location, std::string_view name) {
  return std::make_shared<AstSymbolicName>(location, name);
}
Ast CreateAstBytes(Location location, std::string bytes) {
  return std::make_shared<AstBytes>(location, bytes);
}
Ast CreateAstTypeOfFunction(Location location, Ast argument_type,
                            Ast result_type) {
  return std::make_shared<AstTypeOfFunction>(location, argument_type,
                                             result_type);
}
Ast CreateAstTermVariable(Location location, int bruijn_index) {
  return std::make_shared<AstTermVariable>(location, bruijn_index);
}
Ast CreateAstNativeCall(Location location, std::vector<Ast> arguments) {
  return std::make_shared<AstNativeCall>(location, arguments);
}
Ast CreateAstAbstraction(Location location, Ast variable_origin, Ast body,
                         std::string_view variable_name_hint) {
  return std::make_shared<AstAbstraction>(location, variable_origin, body);
}
Ast CreateAstApplication(Location location, Ast function, Ast argument) {
  return std::make_shared<AstApplication>(location, function, argument);
}
Ast CreateAstRuntimeError(Location location) {
  return std::make_shared<AstRuntimeError>(location);
}
Ast CreateAstTypedTerm(Location location, Ast term, Ast type) {
  return std::make_shared<AstTypedTerm>(location, term, type);
}
Ast CreateAstLock(Location location, Ast variable_origin, Ast argument_type,
                  Ast body) {
  return std::make_shared<AstLock>(location, variable_origin, argument_type,
                                   body);
}
Ast CreateAstUnlock(Location location, Ast function, Ast argument) {
  return std::make_shared<AstUnlock>(location, function, argument);
}
Ast CreateLetBinding(Location location, Ast variable_origin,
                     Ast bound_expression, Ast body) {
  return std::make_shared<AstLetBinding>(location, variable_origin,
                                         bound_expression, body);
}

std::shared_ptr<AstSyntaxError> CastToSyntaxError(Ast ast) {
  QCHECK(ast != nullptr && ast->kind == ast_kind::kSyntaxError)
      << "ast_error::CastToSyntaxError: Not Syntax Error AST.";
  return std::dynamic_pointer_cast<AstSyntaxError>(ast);
}

bool WellFormed(Ast ast) {
  return ast != nullptr && ast->kind != ast_kind::kSyntaxError;
}

bool WellFormed_LogIfNot(Ast ast) {
  if (WellFormed(ast)) {
    return true;
  }
  if (ast == nullptr) {
    LOG(WARNING) << "WellFormed_LogIfNot: input is nullptr";
  } else {
    LOG(WARNING) << "SuccessfulAst_LogIfNot: "
                 << CastToSyntaxError(ast)->message;
  }
  return false;
}

}  // namespace tapl::syntax