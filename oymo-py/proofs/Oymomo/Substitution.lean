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
  | fix t => fix (ren ξ t)

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
  | fix t => fix (subst σ t)

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
  | fix t ih => simp only [ren, ih]

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
  | fix t ih => simp only [subst, ren, ih]

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
  | fix t ih => simp only [subst, ren, ih]

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
  | fix t ih => simp only [subst, ih]

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
  | fix t ih => simp only [subst, ih]

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

/-! ## Closed terms -/

/-- Every free index of `t` is below `k`. -/
def closedAt : Nat → Term → Bool
  | k, var n => decide (n < k)
  | k, lam t => closedAt (k + 1) t
  | k, app a b => closedAt k a && closedAt k b
  | _, snil => true
  | k, scons _ t r => closedAt k t && closedAt k r
  | k, proj t _ => closedAt k t
  | _, bytes _ => true
  | k, fix t => closedAt k t

/-- `t` has no free variable. -/
def closed (t : Term) : Prop := closedAt 0 t = true

/-- A renaming that fixes the free indices of `t` leaves `t` alone. -/
theorem ren_closedAt {k : Nat} {t : Term} (h : closedAt k t = true) (ξ : Nat → Nat)
    (hξ : ∀ n, n < k → ξ n = n) : ren ξ t = t := by
  induction t generalizing k ξ with
  | var n =>
    simp only [closedAt, decide_eq_true_eq] at h
    simp only [ren, hξ n h]
  | lam t ih =>
    simp only [closedAt] at h
    simp only [ren]
    rw [ih h]
    intro n hn
    cases n with
    | zero => rfl
    | succ n => simp only [upr]; rw [hξ n (by omega)]
  | app a b iha ihb =>
    simp only [closedAt, Bool.and_eq_true] at h
    simp only [ren, iha h.1 ξ hξ, ihb h.2 ξ hξ]
  | snil => rfl
  | scons l t r iht ihr =>
    simp only [closedAt, Bool.and_eq_true] at h
    simp only [ren, iht h.1 ξ hξ, ihr h.2 ξ hξ]
  | proj t l ih => simp only [closedAt] at h; simp only [ren, ih h ξ hξ]
  | bytes b => rfl
  | fix t ih => simp only [closedAt] at h; simp only [ren, ih h ξ hξ]

/-- A substitution that fixes the free indices of `t` leaves `t` alone. -/
theorem subst_closedAt {k : Nat} {t : Term} (h : closedAt k t = true) (σ : Nat → Term)
    (hσ : ∀ n, n < k → σ n = var n) : subst σ t = t := by
  induction t generalizing k σ with
  | var n =>
    simp only [closedAt, decide_eq_true_eq] at h
    simp only [subst, hσ n h]
  | lam t ih =>
    simp only [closedAt] at h
    simp only [subst]
    rw [ih h]
    intro n hn
    cases n with
    | zero => rfl
    | succ n => simp only [ups]; rw [hσ n (by omega)]; rfl
  | app a b iha ihb =>
    simp only [closedAt, Bool.and_eq_true] at h
    simp only [subst, iha h.1 σ hσ, ihb h.2 σ hσ]
  | snil => rfl
  | scons l t r iht ihr =>
    simp only [closedAt, Bool.and_eq_true] at h
    simp only [subst, iht h.1 σ hσ, ihr h.2 σ hσ]
  | proj t l ih => simp only [closedAt] at h; simp only [subst, ih h σ hσ]
  | bytes b => rfl
  | fix t ih => simp only [closedAt] at h; simp only [subst, ih h σ hσ]

/-- A closed term has no variable to rename. -/
theorem ren_closed {t : Term} (h : closed t) (ξ : Nat → Nat) : ren ξ t = t :=
  ren_closedAt h ξ (fun _ hn => absurd hn (Nat.not_lt_zero _))

/-- A closed term has no variable to substitute. -/
theorem subst_closed {t : Term} (h : closed t) (σ : Nat → Term) : subst σ t = t :=
  subst_closedAt h σ (fun _ hn => absurd hn (Nat.not_lt_zero _))

end Oymomo
