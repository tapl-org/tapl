-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

/-!
# Oymomo terms (semantics.tex, Section 2)

Variables are de Bruijn indices here; the document uses names (terms are equal up to
α-equivalence, 4.2).

A struct `{l₁ = t₁, …, lₙ = tₙ}` is the chain `scons l₁ t₁ (… (scons lₙ tₙ snil))`.
E-Struct steps any field: here it steps the head field or the tail. A chain whose tail is
not `snil` or `scons` is not a struct of the document; no rule treats it as one.
-/

namespace Oymomo

/-- A byte array. -/
abbrev Bytes := List UInt8

/-- A byte array read as an unsigned, little-endian number; the empty one is `0` (2.4a). -/
def Bytes.toNat : Bytes → Nat
  | [] => 0
  | b :: bs => b.toNat + 256 * Bytes.toNat bs

inductive Term where
  | var : Nat → Term
  | lam : Term → Term                     -- `λx. t`
  | app : Term → Term → Term              -- `t t`
  | snil : Term                           -- `{}`
  | scons : String → Term → Term → Term   -- a field `l = t` in front of the rest
  | proj : Term → String → Term           -- `t.l`
  | bytes : Bytes → Term                  -- `b`
  | fix : Term → Term                     -- `fix t`
  deriving Inhabited

open Term

/-- Values `v` (row 2.1h): `x`, `λx. t`, `b`, a struct of values, `fix (λx. t)`. -/
def isValue : Term → Bool
  | var _ => true
  | lam _ => true
  | snil => true
  | scons _ t r => isValue t && isValue r
  | bytes _ => true
  | fix (lam _) => true
  | _ => false

/-- A fixed point of a lambda, `fix (λx. t)`, which E-FixProj and E-FixApp unfold (4.8). -/
def isFixLam : Term → Bool
  | fix (lam _) => true
  | _ => false

/-- Data `d` (row 2.1i): a byte array or a struct of data. -/
def isData : Term → Bool
  | snil => true
  | scons _ t r => isData t && isData r
  | bytes _ => true
  | _ => false

/-- A struct at the root (`snil` or `scons`). -/
def isStruct : Term → Bool
  | snil => true
  | scons _ _ _ => true
  | _ => false

/-- The field labeled `l` (labels are unique, so the first one). -/
def lookup : Term → String → Option Term
  | scons l' t r, l => if l' = l then some t else lookup r l
  | _, _ => none

/-- The field at position `n`; past the last field, the last one (E-Index, E-Default). -/
def select : Term → Nat → Option Term
  | scons _ t snil, _ => some t
  | scons _ t _, 0 => some t
  | scons _ _ r, n + 1 => select r n
  | _, _ => none

end Oymomo
