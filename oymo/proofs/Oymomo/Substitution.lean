-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Syntax

/-!
# Renaming and substitution

`subst σ t` replaces every free index `n` of `t` with `σ n`. E-Beta's `[x ↦ t₂] t₁` is
`subst (inst t₂) t₁`.
-/

namespace Oymomo
open Term

/-- Lifts a renaming under one binder. -/
def upr (ξ : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => ξ n + 1

def ren (ξ : Nat → Nat) : Term → Term
  | var n => var (ξ n)
  | lam t => lam (ren (upr ξ) t)
  | app a b => app (ren ξ a) (ren ξ b)
  | snil => snil
  | scons l t r => scons l (ren ξ t) (ren ξ r)
  | proj t l => proj (ren ξ t) l
  | bytes b => bytes b
  | sapp a b => sapp (ren ξ a) (ren ξ b)

/-- Lifts a substitution under one binder. -/
def ups (σ : Nat → Term) : Nat → Term
  | 0 => var 0
  | n + 1 => ren Nat.succ (σ n)

def subst (σ : Nat → Term) : Term → Term
  | var n => σ n
  | lam t => lam (subst (ups σ) t)
  | app a b => app (subst σ a) (subst σ b)
  | snil => snil
  | scons l t r => scons l (subst σ t) (subst σ r)
  | proj t l => proj (subst σ t) l
  | bytes b => bytes b
  | sapp a b => sapp (subst σ a) (subst σ b)

/-- `inst u` puts `u` in for index 0 and lowers the others. -/
def inst (u : Term) : Nat → Term
  | 0 => u
  | n + 1 => var n

theorem upr_comp (ξ ζ : Nat → Nat) : upr (ξ ∘ ζ) = upr ξ ∘ upr ζ := by
  funext n; cases n <;> rfl

theorem ren_ren (ξ ζ : Nat → Nat) (t : Term) : ren ξ (ren ζ t) = ren (ξ ∘ ζ) t := by
  induction t generalizing ξ ζ with
  | var n => rfl
  | lam t ih => simp only [ren, ih, upr_comp]
  | app a b iha ihb => simp only [ren, iha, ihb]
  | snil => rfl
  | scons l t r iht ihr => simp only [ren, iht, ihr]
  | proj t l ih => simp only [ren, ih]
  | bytes b => rfl
  | sapp a b iha ihb => simp only [ren, iha, ihb]

theorem ren_ups (ξ : Nat → Nat) (σ : Nat → Term) :
    (fun n => ren (upr ξ) (ups σ n)) = ups (fun n => ren ξ (σ n)) := by
  funext n
  cases n with
  | zero => rfl
  | succ n =>
    simp only [ups, ren_ren]
    all_goals rfl

theorem ren_subst (ξ : Nat → Nat) (σ : Nat → Term) (t : Term) :
    ren ξ (subst σ t) = subst (fun n => ren ξ (σ n)) t := by
  induction t generalizing ξ σ with
  | var n => rfl
  | lam t ih => simp only [subst, ren, ih, ren_ups]
  | app a b iha ihb => simp only [subst, ren, iha, ihb]
  | snil => rfl
  | scons l t r iht ihr => simp only [subst, ren, iht, ihr]
  | proj t l ih => simp only [subst, ren, ih]
  | bytes b => rfl
  | sapp a b iha ihb => simp only [subst, ren, iha, ihb]

theorem ups_upr (σ : Nat → Term) (ξ : Nat → Nat) :
    (fun n => ups σ (upr ξ n)) = ups (fun n => σ (ξ n)) := by
  funext n; cases n <;> rfl

theorem subst_ren (σ : Nat → Term) (ξ : Nat → Nat) (t : Term) :
    subst σ (ren ξ t) = subst (fun n => σ (ξ n)) t := by
  induction t generalizing σ ξ with
  | var n => rfl
  | lam t ih => simp only [subst, ren, ih, ups_upr]
  | app a b iha ihb => simp only [subst, ren, iha, ihb]
  | snil => rfl
  | scons l t r iht ihr => simp only [subst, ren, iht, ihr]
  | proj t l ih => simp only [subst, ren, ih]
  | bytes b => rfl
  | sapp a b iha ihb => simp only [subst, ren, iha, ihb]

theorem subst_ups (τ σ : Nat → Term) :
    (fun n => subst (ups τ) (ups σ n)) = ups (fun n => subst τ (σ n)) := by
  funext n
  cases n with
  | zero => rfl
  | succ n =>
    simp only [ups, subst_ren, ren_subst]
    all_goals rfl

theorem subst_subst (τ σ : Nat → Term) (t : Term) :
    subst τ (subst σ t) = subst (fun n => subst τ (σ n)) t := by
  induction t generalizing τ σ with
  | var n => rfl
  | lam t ih => simp only [subst, ih, subst_ups]
  | app a b iha ihb => simp only [subst, iha, ihb]
  | snil => rfl
  | scons l t r iht ihr => simp only [subst, iht, ihr]
  | proj t l ih => simp only [subst, ih]
  | bytes b => rfl
  | sapp a b iha ihb => simp only [subst, iha, ihb]

theorem ups_var : ups var = var := by
  funext n; cases n <;> rfl

theorem subst_var (t : Term) : subst var t = t := by
  induction t with
  | var n => rfl
  | lam t ih => simp only [subst, ups_var, ih]
  | app a b iha ihb => simp only [subst, iha, ihb]
  | snil => rfl
  | scons l t r iht ihr => simp only [subst, iht, ihr]
  | proj t l ih => simp only [subst, ih]
  | bytes b => rfl
  | sapp a b iha ihb => simp only [subst, iha, ihb]

/-- Substitution goes through E-Beta's substitution. -/
theorem subst_inst (σ : Nat → Term) (u t : Term) :
    subst σ (subst (inst u) t) = subst (inst (subst σ u)) (subst (ups σ) t) := by
  rw [subst_subst, subst_subst]
  congr 1
  funext n
  cases n with
  | zero => rfl
  | succ n =>
    simp only [subst, inst, ups, subst_ren]
    exact (subst_var (σ n)).symm

/-- Renaming goes through E-Beta's substitution. -/
theorem ren_inst (ξ : Nat → Nat) (u t : Term) :
    ren ξ (subst (inst u) t) = subst (inst (ren ξ u)) (ren (upr ξ) t) := by
  rw [ren_subst, subst_ren]
  congr 1
  funext n
  cases n <;> rfl

end Oymomo
