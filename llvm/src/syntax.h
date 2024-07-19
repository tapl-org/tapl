// Part of the TAPL project, under the Apache License v2.0 with LLVM
// Exceptions. See /LICENSE for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

#pragma once

#include <cctype>
#include <memory>
#include <sstream>
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

typedef int TermKind;
namespace term_kind {
constexpr TermKind kUnknown = 0;
constexpr TermKind kCode = 1;
constexpr TermKind kAbstraction = 2;
constexpr TermKind kLock = 3;
constexpr TermKind kApplication = 4;
constexpr TermKind kEquivalent = 5;
constexpr TermKind kExpressionAsTerm = 6;
constexpr TermKind kParameter = 7;
constexpr TermKind kMultiLevel = 8;
}  // namespace term_kind

using Lines = std::shared_ptr<std::vector<std::string>>;

struct TermBase;
using Term = std::shared_ptr<TermBase>;
struct TermBase {
  const TermKind kind{term_kind::kUnknown};
  Location location;
  explicit TermBase(TermKind kind, Location location)
      : kind(kind), location(location) {}
  virtual ~TermBase() = default;
  virtual void AppendToBody(Term term);
};

struct TermCode : TermBase {
  Lines lines;
  TermCode(Location location, Lines lines)
      : TermBase(term_kind::kCode, location), lines(lines) {}
};
Term CreateTermCode(Location location, Lines lines);

struct TermAbstraction : TermBase {
  Term parameter;
  std::vector<Term> body;
  TermAbstraction(Location location, Term parameter, std::vector<Term> body)
      : TermBase(term_kind::kAbstraction, location),
        parameter(parameter),
        body(body) {}
  void AppendToBody(Term term) override;
};
Term CreateTermAbstraction(Location location, Term parameter, std::vector<Term> body);

struct TermLock : TermBase {
  Term keyhole;
  std::vector<Term> body;
  TermLock(Location location, Term keyhole, std::vector<Term> body)
      : TermBase(term_kind::kLock, location), keyhole(keyhole), body(body) {}
  void AppendToBody(Term term) override;
};
Term CreateTermLock(Location location, Term guard, std::vector<Term> body);

struct TermApplication : TermBase {
  Term function;
  Term argument;
  TermApplication(Location location, Term function, Term argument)
      : TermBase(term_kind::kApplication, location),
        function(function),
        argument(argument) {}
};
Term CreateTermApplication(Location location, Term function, Term argument);

struct TermEquivalent : TermBase {
  Term left;
  Term right;
  TermEquivalent(Location location, Term left, Term right)
      : TermBase(term_kind::kApplication, location), left(left), right(right) {}
};
Term CreateTermEquivalent(Location location, Term left, Term right);

struct TermExpressionAsTerm : TermBase {
  Term expression;
  TermExpressionAsTerm(Location location, Term expression)
      : TermBase(term_kind::kExpressionAsTerm, location),
        expression(expression) {}
};
Term CreateExpressionAsTerm(Location location, Term expression);

struct TermParameter : TermBase {
  Term signature;
  explicit TermParameter(Location location, Term signature)
      : TermBase(term_kind::kParameter, location), signature(signature) {}
};
Term CreateTermParameter(Location location, Term signature);

struct TermMultiLevel : TermBase {
  Term high;
  Term low;
  TermMultiLevel(Location location, Term high, Term low)
      : TermBase(term_kind::kMultiLevel, location), high(high), low(low) {}
};
Term CreateTermMultiLevel(Location location, Term term, Term type);


}  // namespace tapl