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

void TermBase::AppendToBody(Term term) {
  throw std::runtime_error(
      absl::Substitute("Term kind=$0 does not support AppendToBody.", kind));
}

Term CreateTermCode(Location location, Lines lines) {
  return std::make_shared<TermCode>(location, lines);
}

void TermAbstraction::AppendToBody(Term term) { body.push_back(term); }

Term CreateTermAbstraction(Location location, Term parameter,
                         std::vector<Term> body) {
  return std::make_shared<TermAbstraction>(location, parameter, body);
}

void TermLock::AppendToBody(Term term) { body.push_back(term); }

Term CreateTermLock(Location location, Term keyhole, std::vector<Term> body) {
  return std::make_shared<TermLock>(location, keyhole, body);
}

Term CreateTermApplication(Location location, Term function, Term argument) {
  return std::make_shared<TermApplication>(location, function, argument);
}

Term CreateTermEquivalent(Location location, Term left, Term right) {
  return std::make_shared<TermApplication>(location, left, right);
}

Term CreateTermExpressionAsTerm(Location location, Term expression) {
  return std::make_shared<TermExpressionAsTerm>(location, expression);
}

Term CreateTermParameter(Location location, Term signature) {
  return std::make_shared<TermParameter>(location, signature);
}

Term CreateTermMultiLevel(Location location, Term high, Term low) {
  return std::make_shared<TermMultiLevel>(location, high, low);
}

}  // namespace tapl