-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Reduction

/-!
# Confluence

Takahashi's proof: `cd t`, the complete development of `t`, contracts every redex of `t`
at once. Every parallel step from `t` can be completed to `cd t` in one more parallel step
(the triangle), so parallel reduction has the diamond property, and its closure, which is
the closure of `⟶`, is confluent.

E-Beta substitutes only values, so the substitution lemma asks the substitution to map
every variable to a value (`ValSub`); values are closed under substitution of values and
under parallel reduction (`isValue_subst`, `Par.value`).
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
  | beta hu _ _ iht ihu =>
    simp only [Oymomo.ren]
    rw [ren_inst]
    exact .beta (isValue_ren _ hu) (iht _) (ihu _)
  | projR h _ ih => exact .projR (lookup_ren ξ h) (ih _)
  | indexR h _ ih => exact .indexR (select_ren ξ h) (ih _)
  | opcodeR h1 h2 h3 =>
    simp only [Oymomo.ren]
    rw [ren_data ξ h2]
    exact .opcodeR h1 h2 h3
  | fix _ ih => exact .fix (ih _)
  | fixProjR _ ih =>
    simp only [Oymomo.ren]
    rw [ren_inst]
    simp only [Oymomo.ren]
    exact .fixProjR (ih _)
  | fixAppR _ _ iht ihu =>
    simp only [Oymomo.ren]
    rw [ren_inst]
    simp only [Oymomo.ren]
    exact .fixAppR (iht _) (ihu _)

theorem Par.ups {σ τ : Nat → Term} (h : ∀ n, Par op (σ n) (τ n)) :
    ∀ n, Par op (Oymomo.ups σ n) (Oymomo.ups τ n)
  | 0 => .var 0
  | n + 1 => (h n).ren Nat.succ

theorem Par.subst {t t' : Term} (h : Par op t t') {σ τ : Nat → Term}
    (hσ : ∀ n, Par op (σ n) (τ n)) (hv : ValSub σ) :
    Par op (Oymomo.subst σ t) (Oymomo.subst τ t') := by
  induction h generalizing σ τ with
  | var n => exact hσ n
  | bytes b => exact .bytes b
  | snil => exact .snil
  | lam _ ih => exact .lam (ih (Par.ups hσ) hv.ups)
  | app _ _ iha ihb => exact .app (iha hσ hv) (ihb hσ hv)
  | scons _ _ iht ihr => exact .scons (iht hσ hv) (ihr hσ hv)
  | proj _ ih => exact .proj (ih hσ hv)
  | beta hu _ _ iht ihu =>
    simp only [Oymomo.subst]
    rw [subst_inst]
    exact .beta (isValue_subst hv hu) (iht (Par.ups hσ) hv.ups) (ihu hσ hv)
  | projR h _ ih => exact .projR (lookup_subst _ h) (ih hσ hv)
  | indexR h _ ih => exact .indexR (select_subst _ h) (ih hσ hv)
  | opcodeR h1 h2 h3 =>
    simp only [Oymomo.subst]
    rw [subst_data _ h2]
    exact .opcodeR h1 h2 h3
  | fix _ ih => exact .fix (ih hσ hv)
  | fixProjR _ ih =>
    simp only [Oymomo.subst]
    rw [subst_inst]
    simp only [Oymomo.subst]
    exact .fixProjR (ih (Par.ups hσ) hv.ups)
  | fixAppR _ _ iht ihu =>
    simp only [Oymomo.subst]
    rw [subst_inst]
    simp only [Oymomo.subst]
    exact .fixAppR (iht (Par.ups hσ) hv.ups) (ihu hσ hv)

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
  | fix t => fix (cd t)
  | proj (fix (lam t)) l => proj (subst (inst (fix (lam (cd t)))) (cd t)) l
  | proj s l => if (lookup s l).isSome then (lookup (cd s) l).getD snil else proj (cd s) l
  | app (lam t) u => if isValue u then subst (inst (cd u)) (cd t) else app (lam (cd t)) (cd u)
  | app (bytes b) s =>
    match isStruct s && isData s, op b s with
    | true, some b' => bytes b'
    | _, _ => app (bytes b) (cd s)
  | app (fix (lam t)) u => app (subst (inst (fix (lam (cd t)))) (cd t)) (cd u)
  | app s (bytes b) =>
    if (select s b.toNat).isSome then (select (cd s) b.toNat).getD snil
    else app (cd s) (bytes b)
  | app a u => app (cd a) (cd u)

/-- Heads that `cd` treats on their own when applied. -/
def isHead : Term → Bool
  | lam _ => true
  | bytes _ => true
  | fix (lam _) => true
  | _ => false

theorem cd_app_bytes {a : Term} (d : Bytes) (ha : isHead a = false) :
    cd op (app a (bytes d)) =
      if (select a d.toNat).isSome then (select (cd op a) d.toNat).getD snil
      else app (cd op a) (bytes d) := by
  cases a with
  | fix x => cases x <;> first | rfl | exact absurd ha (by simp [isHead])
  | _ => first | rfl | exact absurd ha (by simp [isHead])

theorem cd_app_other {a u : Term} (ha : isHead a = false) (hu : ∀ d, u ≠ bytes d) :
    cd op (app a u) = app (cd op a) (cd op u) := by
  cases a with
  | fix x =>
    cases x <;> cases u <;>
      first | rfl | exact (hu _ rfl).elim | exact absurd ha (by simp [isHead])
  | _ => cases u <;> first | rfl | exact (hu _ rfl).elim | exact absurd ha (by simp [isHead])

theorem cd_proj_other {s : Term} (l : String) (hs : isFixLam s = false) :
    cd op (proj s l) =
      if (lookup s l).isSome then (lookup (cd op s) l).getD snil else proj (cd op s) l := by
  cases s with
  | fix x => cases x <;> first | rfl | exact absurd hs (by simp [isFixLam])
  | _ => rfl

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

theorem Par.fix_lam_inv {t s : Term} (h : Par op (Term.fix (Term.lam t)) s) :
    ∃ t', s = Term.fix (Term.lam t') ∧ Par op t t' := by
  cases h with
  | fix h => cases h with | lam h => exact ⟨_, rfl, h⟩

theorem ValSub.inst_fix (t : Term) : ValSub (Oymomo.inst (Term.fix (Term.lam t))) :=
  ValSub.inst (u := Term.fix (Term.lam t)) rfl

/-- Every parallel step from `t` reaches `cd t` in one more. -/
theorem Par.triangle {t s : Term} (h : Par op t s) : Par op s (cd op t) := by
  induction h with
  | var n => exact .var n
  | bytes b => exact .bytes b
  | snil => exact .snil
  | lam _ ih => exact .lam ih
  | scons _ _ iht ihr => exact .scons iht ihr
  | fix _ ih => exact .fix ih
  | @fixProjR t t' l _ ih =>
    simp only [cd]
    exact .proj (ih.subst (Par.inst (.fix (.lam ih))) (ValSub.inst_fix _))
  | @fixAppR t t' u u' _ _ iht ihu =>
    simp only [cd]
    exact .app (iht.subst (Par.inst (.fix (.lam iht))) (ValSub.inst_fix _)) ihu
  | @proj t t' l htt ih =>
    cases hf : isFixLam t with
    | true =>
      cases t with
      | fix x =>
        cases x with
        | lam a =>
          obtain ⟨a', rfl, _⟩ := htt.fix_lam_inv
          simp only [cd] at ih ⊢
          obtain ⟨_, he, ha⟩ := ih.fix_lam_inv
          cases he
          exact .fixProjR ha
        | _ => simp [isFixLam] at hf
      | _ => simp [isFixLam] at hf
    | false =>
    rw [cd_proj_other l hf]
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
    have hf : isFixLam s = false := by
      cases s with
      | fix x => simp [lookup] at hl
      | _ => rfl
    rw [cd_proj_other l hf]
    simp only [hl, Option.isSome_some, ite_true]
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
        cases hv : isValue b with
        | true =>
          simp only [cd, hv, ite_true]
          exact .beta (hbb.value hv) ht ihb
        | false =>
          simp only [cd, hv, Bool.false_eq_true, ite_false]
          exact .app (.lam ht) ihb
      | bytes c =>
        rw [hab.bytes_inv]
        simp only [cd]
        split
        next b'' hc ho =>
          simp only [Bool.and_eq_true] at hc
          rw [hbb.data hc.2]
          exact .opcodeR hc.1 hc.2 ho
        next => exact .app (.bytes c) ihb
      | fix x =>
        cases x with
        | lam t =>
          obtain ⟨t', rfl, _⟩ := hab.fix_lam_inv
          simp only [cd] at iha ⊢
          obtain ⟨_, he, ht⟩ := iha.fix_lam_inv
          cases he
          exact .fixAppR ht ihb
        | _ => exact absurd hh (by simp [isHead])
      | _ => exact absurd hh Bool.false_ne_true
  | @beta t t' u u' hu _ huu iht ihu =>
    simp only [cd, hu, ite_true]
    exact iht.subst ihu.inst (ValSub.inst (huu.value hu))
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

/-- `⟶` is confluent: two reduction sequences from one term meet again. -/
theorem confluence {t a b : Term} (ha : Star (Step op) t a) (hb : Star (Step op) t b) :
    ∃ c, Star (Step op) a c ∧ Star (Step op) b c := by
  obtain ⟨c, hac, hbc⟩ := Par.confluent (star_par_iff.mpr ha) (star_par_iff.mpr hb)
  exact ⟨c, star_par_iff.mp hac, star_par_iff.mp hbc⟩

end Oymomo
