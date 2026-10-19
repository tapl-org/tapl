-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Reduction

/-!
# Confluence of full β (semantics.tex, 3/8)

Takahashi's proof: `cd t`, the complete development of `t`, contracts every redex of `t`
at once. Every parallel step from `t` can be completed to `cd t` in one more parallel step
(the triangle), so parallel reduction has the diamond property, and its closure, which is
the closure of `▷`, is confluent.
-/

namespace Oymomo
open Term

variable {op : Bytes → Term → Option Bytes}

/-! ## Parallel reduction goes through renaming and substitution -/

theorem Par.ren {t t' : Term} (h : Par op t t') (ξ : Nat → Nat) :
    Par op (Oymomo.ren ξ t) (Oymomo.ren ξ t') := by
  induction h generalizing ξ with
  | var n => exact .var _
  | bytes b => exact .bytes b
  | snil => exact .snil
  | lam _ ih => exact .lam (ih _)
  | app _ _ iha ihb => exact .app (iha _) (ihb _)
  | scons _ _ iht ihr => exact .scons (iht _) (ihr _)
  | proj _ ih => exact .proj (ih _)
  | sapp _ _ iha ihb => exact .sapp (iha _) (ihb _)
  | beta _ _ iht ihu =>
    simp only [Oymomo.ren]
    rw [ren_inst]
    exact .beta (iht _) (ihu _)
  | projR h _ ih => exact .projR (lookup_ren ξ h) (ih _)
  | indexR h _ ih => exact .indexR (select_ren ξ h) (ih _)
  | opcodeR h1 h2 h3 =>
    simp only [Oymomo.ren]
    rw [ren_data ξ h2]
    exact .opcodeR h1 h2 h3
  | strictR hv _ _ iht ihv => exact .strictR (isValue_ren ξ hv) (iht _) (ihv _)

theorem Par.ups {σ τ : Nat → Term} (h : ∀ n, Par op (σ n) (τ n)) :
    ∀ n, Par op (Oymomo.ups σ n) (Oymomo.ups τ n)
  | 0 => .var 0
  | n + 1 => (h n).ren Nat.succ

theorem Par.subst {t t' : Term} (h : Par op t t') {σ τ : Nat → Term}
    (hσ : ∀ n, Par op (σ n) (τ n)) : Par op (Oymomo.subst σ t) (Oymomo.subst τ t') := by
  induction h generalizing σ τ with
  | var n => exact hσ n
  | bytes b => exact .bytes b
  | snil => exact .snil
  | lam _ ih => exact .lam (ih (Par.ups hσ))
  | app _ _ iha ihb => exact .app (iha hσ) (ihb hσ)
  | scons _ _ iht ihr => exact .scons (iht hσ) (ihr hσ)
  | proj _ ih => exact .proj (ih hσ)
  | sapp _ _ iha ihb => exact .sapp (iha hσ) (ihb hσ)
  | beta _ _ iht ihu =>
    simp only [Oymomo.subst]
    rw [subst_inst]
    exact .beta (iht (Par.ups hσ)) (ihu hσ)
  | projR h _ ih => exact .projR (lookup_subst _ h) (ih hσ)
  | indexR h _ ih => exact .indexR (select_subst _ h) (ih hσ)
  | opcodeR h1 h2 h3 =>
    simp only [Oymomo.subst]
    rw [subst_data _ h2]
    exact .opcodeR h1 h2 h3
  | strictR hv _ _ iht ihv => exact .strictR (isValue_subst _ hv) (iht hσ) (ihv hσ)

theorem Par.inst {u u' : Term} (h : Par op u u') :
    ∀ n, Par op (Oymomo.inst u n) (Oymomo.inst u' n)
  | 0 => h
  | n + 1 => .var n

/-! ## Complete development -/

variable (op) in
/-- Contracts every redex of `t` at once. -/
def cd : Term → Term
  | var n => var n
  | lam t => lam (cd t)
  | snil => snil
  | scons l t r => scons l (cd t) (cd r)
  | bytes b => bytes b
  | sapp t v => if isValue v then app (cd t) (cd v) else sapp (cd t) (cd v)
  | proj s l => if (lookup s l).isSome then (lookup (cd s) l).getD snil else proj (cd s) l
  | app (lam t) u => subst (inst (cd u)) (cd t)
  | app (bytes b) s =>
    match isStruct s && isData s, op b s with
    | true, some b' => bytes b'
    | _, _ => app (bytes b) (cd s)
  | app s (bytes b) =>
    if (select s b.toNat).isSome then (select (cd s) b.toNat).getD snil
    else app (cd s) (bytes b)
  | app a u => app (cd a) (cd u)

/-- Heads that `cd` treats on their own when applied. -/
def isHead : Term → Bool
  | lam _ => true
  | bytes _ => true
  | _ => false

theorem cd_app_bytes {a : Term} (d : Bytes) (ha : isHead a = false) :
    cd op (app a (bytes d)) =
      if (select a d.toNat).isSome then (select (cd op a) d.toNat).getD snil
      else app (cd op a) (bytes d) := by
  cases a <;> first | rfl | exact absurd ha (by simp [isHead])

theorem cd_app_other {a u : Term} (ha : isHead a = false) (hu : ∀ d, u ≠ bytes d) :
    cd op (app a u) = app (cd op a) (cd op u) := by
  cases a <;> cases u <;> first | rfl | exact (hu _ rfl).elim | exact absurd ha (by simp [isHead])

theorem lookup_cd {s u : Term} {l : String} (h : lookup s l = some u) :
    lookup (cd op s) l = some (cd op u) := by
  induction s with
  | scons l' t r _ ihr =>
    simp only [lookup] at h
    simp only [cd, lookup]
    split
    · simp_all
    · simp_all
  | _ => simp [lookup] at h

theorem select_cd {s u : Term} {n : Nat} (h : select s n = some u) :
    select (cd op s) n = some (cd op u) := by
  induction s generalizing n with
  | scons l t r _ ihr =>
    cases n with
    | zero =>
      rw [select_scons_zero] at h
      cases h
      simp only [cd]
      exact select_scons_zero _ _ _
    | succ n =>
      cases r with
      | snil => simp_all [select, cd]
      | scons l' t' r' =>
        simp only [select] at h
        have := ihr h
        simp only [cd] at this ⊢
        simp only [select]
        exact this
      | _ => simp [select] at h
  | _ => simp [select] at h

/-! ## The triangle -/

theorem Par.lam_inv {t s : Term} (h : Par op (Term.lam t) s) :
    ∃ t', s = Term.lam t' ∧ Par op t t' := by
  cases h with
  | lam h => exact ⟨_, rfl, h⟩

theorem Par.bytes_inv {b : Bytes} {s : Term} (h : Par op (Term.bytes b) s) : s = Term.bytes b := by
  cases h; rfl

/-- Every parallel step from `t` reaches `cd t` in one more. -/
theorem Par.triangle {t s : Term} (h : Par op t s) : Par op s (cd op t) := by
  induction h with
  | var n => exact .var n
  | bytes b => exact .bytes b
  | snil => exact .snil
  | lam _ ih => exact .lam ih
  | scons _ _ iht ihr => exact .scons iht ihr
  | @sapp a a' b b' _ hbb iha ihb =>
    simp only [cd]
    cases hv : isValue b with
    | true =>
      simp only [ite_true]
      exact .strictR (hbb.value hv) iha ihb
    | false =>
      simp only [Bool.false_eq_true, ite_false]
      exact .sapp iha ihb
  | @proj t t' l htt ih =>
    simp only [cd]
    cases hl : lookup t l with
    | none => simpa using Par.proj ih
    | some u =>
      simp only [Option.isSome_some, ite_true]
      rw [lookup_cd hl, Option.getD_some]
      obtain ⟨w, hw, huw⟩ := lookup_par htt hl
      obtain ⟨w', hw', hww'⟩ := lookup_par ih hw
      rw [lookup_cd hl, Option.some.injEq] at hw'
      subst hw'
      exact .projR hw hww'
  | @projR s u u' l hl _ ih =>
    simp only [cd, hl, Option.isSome_some, ite_true]
    rw [lookup_cd hl, Option.getD_some]
    exact ih
  | @app a a' b b' hab hbb iha ihb =>
    cases hh : isHead a with
    | false =>
      cases b with
      | bytes d =>
        rw [cd_app_bytes d hh]
        rw [hbb.bytes_inv]
        cases hsel : select a d.toNat with
        | none => simpa using Par.app iha (.bytes d)
        | some u =>
          simp only [Option.isSome_some, ite_true]
          rw [select_cd hsel, Option.getD_some]
          obtain ⟨w, hw, huw⟩ := select_par hab hsel
          obtain ⟨w', hw', hww'⟩ := select_par iha hw
          rw [select_cd hsel, Option.some.injEq] at hw'
          subst hw'
          exact .indexR hw hww'
      | _ =>
        rw [cd_app_other hh (by intro d h; cases h)]
        exact .app iha ihb
    | true =>
      cases a with
      | lam t =>
        obtain ⟨t', rfl, _⟩ := hab.lam_inv
        obtain ⟨_, he, ht⟩ := iha.lam_inv
        cases he
        exact .beta ht ihb
      | bytes c =>
        rw [hab.bytes_inv]
        simp only [cd]
        split
        next b'' hc ho =>
          simp only [Bool.and_eq_true] at hc
          rw [hbb.data hc.2]
          exact .opcodeR hc.1 hc.2 ho
        next => exact .app (.bytes c) ihb
      | _ => exact absurd hh Bool.false_ne_true
  | @beta t t' u u' _ _ iht ihu =>
    simp only [cd]
    exact iht.subst ihu.inst
  | @indexR s u u' b hsel _ ih =>
    cases s with
    | scons l t r =>
      rw [cd_app_bytes b rfl]
      simp only [hsel, Option.isSome_some, ite_true]
      rw [select_cd hsel, Option.getD_some]
      exact ih
    | _ => simp [select] at hsel
  | @opcodeR s b b' h1 h2 h3 =>
    simp only [cd, h1, h2, h3, Bool.and_self]
    exact .bytes b'
  | @strictR t t' v v' hv _ _ iht ihv =>
    simp only [cd, hv, ite_true]
    exact .app iht ihv

/-! ## Confluence -/

theorem Par.diamond {t a b : Term} (ha : Par op t a) (hb : Par op t b) :
    ∃ c, Par op a c ∧ Par op b c :=
  ⟨cd op t, ha.triangle, hb.triangle⟩

theorem Par.strip {t a b : Term} (ha : Par op t a) (hb : Star (Par op) t b) :
    ∃ c, Star (Par op) a c ∧ Par op b c := by
  induction hb generalizing a with
  | refl => exact ⟨a, .refl a, ha⟩
  | tail _ hbc ih =>
    obtain ⟨c, hac, hbc'⟩ := ih ha
    obtain ⟨d, hcd, hd⟩ := Par.diamond hbc' hbc
    exact ⟨d, hac.tail hcd, hd⟩

theorem Par.confluent {t a e : Term} (ha : Star (Par op) t a) (hb : Star (Par op) t e) :
    ∃ c, Star (Par op) a c ∧ Star (Par op) e c := by
  induction ha generalizing e with
  | refl => exact ⟨e, hb, .refl e⟩
  | tail _ hac ih =>
    obtain ⟨c, hbc, hc⟩ := ih hb
    obtain ⟨d, had, hcd⟩ := Par.strip hac hbc
    exact ⟨d, had, hc.tail hcd⟩

theorem star_par_iff {t s : Term} : Star (Par op) t s ↔ Star (Step op) t s := by
  constructor
  · intro h
    induction h with
    | refl => exact .refl _
    | tail _ h ih => exact ih.trans h.star
  · intro h
    exact Star.map id (fun h => h.par) h

/-- Full β is confluent: two reduction sequences from one term meet again. -/
theorem confluence {t a b : Term} (ha : Star (Step op) t a) (hb : Star (Step op) t b) :
    ∃ c, Star (Step op) a c ∧ Star (Step op) b c := by
  obtain ⟨c, hac, hbc⟩ := Par.confluent (star_par_iff.mpr ha) (star_par_iff.mpr hb)
  exact ⟨c, star_par_iff.mp hac, star_par_iff.mp hbc⟩

end Oymomo
