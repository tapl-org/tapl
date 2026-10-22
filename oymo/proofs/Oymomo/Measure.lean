-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Confluence

/-!
# Parallel reduction with a measure (for the guarantee, 6.4)

`ParM op t t' m` is `Par op t t'` together with a measure `m` (Takahashi): each redex the
parallel step contracts counts once, and a redex inside the argument of an `E-Beta` counts
once for every copy the substitution makes. Contracting one redex of a parallel step at the
start leaves a parallel step of a smaller measure (`Guarantee.lean`).

`occ μ t` counts the free variables of `t`, variable `n` weighing `μ n`.
-/

namespace Oymomo
open Term

/-- The weights under one more binder: the new variable `0` weighs nothing. -/
def shiftW (μ : Nat → Nat) : Nat → Nat
  | 0 => 0
  | n + 1 => μ n

/-- Weight `k` on variable `0`, nothing on the others. -/
def w0 (k : Nat) : Nat → Nat
  | 0 => k
  | _ + 1 => 0

/-- The free variables of `t`, variable `n` weighing `μ n`. -/
def occ (μ : Nat → Nat) : Term → Nat
  | var n => μ n
  | lam t => occ (shiftW μ) t
  | app a b => occ μ a + occ μ b
  | snil => 0
  | scons _ t r => occ μ t + occ μ r
  | proj t _ => occ μ t
  | bytes _ => 0
  | fix t => occ μ t

theorem occ_congr {μ ν : Nat → Nat} (h : ∀ n, μ n = ν n) (t : Term) : occ μ t = occ ν t := by
  have : μ = ν := funext h
  rw [this]

theorem occ_ren (μ : Nat → Nat) (ξ : Nat → Nat) (t : Term) :
    occ μ (ren ξ t) = occ (fun n => μ (ξ n)) t := by
  induction t generalizing μ ξ with
  | var n => rfl
  | lam t ih =>
    simp only [ren, occ, ih]
    apply occ_congr; intro n; cases n <;> rfl
  | app a b iha ihb => simp only [ren, occ, iha, ihb]
  | snil => rfl
  | scons l t r iht ihr => simp only [ren, occ, iht, ihr]
  | proj t l ih => simp only [ren, occ, ih]
  | bytes b => rfl
  | fix t ih => simp only [ren, occ, ih]

theorem occ_zero (t : Term) : occ (fun _ => 0) t = 0 := by
  induction t with
  | var n => rfl
  | lam t ih =>
    simp only [occ]
    rw [occ_congr (ν := fun _ => 0) (by intro n; cases n <;> rfl)]
    exact ih
  | app a b iha ihb => simp only [occ, iha, ihb]
  | snil => rfl
  | scons l t r iht ihr => simp only [occ, iht, ihr]
  | proj t l ih => simp only [occ, ih]
  | bytes b => rfl
  | fix t ih => simp only [occ, ih]

theorem occ_add (μ ν : Nat → Nat) (t : Term) :
    occ μ t + occ ν t = occ (fun n => μ n + ν n) t := by
  induction t generalizing μ ν with
  | var n => rfl
  | lam t ih =>
    simp only [occ]
    rw [ih]
    apply occ_congr; intro n; cases n <;> rfl
  | app a b iha ihb => simp only [occ]; rw [← iha, ← ihb]; omega
  | snil => rfl
  | scons l t r iht ihr => simp only [occ]; rw [← iht, ← ihr]; omega
  | proj t l ih => simp only [occ, ih]
  | bytes b => rfl
  | fix t ih => simp only [occ, ih]

theorem occ_subst (μ : Nat → Nat) (σ : Nat → Term) (t : Term) :
    occ μ (subst σ t) = occ (fun n => occ μ (σ n)) t := by
  induction t generalizing μ σ with
  | var n => rfl
  | lam t ih =>
    simp only [subst, occ, ih]
    apply occ_congr; intro n
    cases n with
    | zero => rfl
    | succ n => simp only [ups, shiftW]; rw [occ_ren]; rfl
  | app a b iha ihb => simp only [subst, occ, iha, ihb]
  | snil => rfl
  | scons l t r iht ihr => simp only [subst, occ, iht, ihr]
  | proj t l ih => simp only [subst, occ, ih]
  | bytes b => rfl
  | fix t ih => simp only [subst, occ, ih]

variable (op : Bytes → Term → Option Bytes)

/-- Parallel reduction with Takahashi's measure. -/
inductive ParM : Term → Term → Nat → Prop
  | var (n : Nat) : ParM (var n) (var n) 0
  | bytes (b : Bytes) : ParM (bytes b) (bytes b) 0
  | snil : ParM snil snil 0
  | lam {t t' : Term} {m : Nat} : ParM t t' m → ParM (lam t) (lam t') m
  | app {a a' b b' : Term} {m₁ m₂ : Nat} :
      ParM a a' m₁ → ParM b b' m₂ → ParM (app a b) (app a' b') (m₁ + m₂)
  | scons {l : String} {t t' r r' : Term} {m₁ m₂ : Nat} :
      ParM t t' m₁ → ParM r r' m₂ → ParM (scons l t r) (scons l t' r') (m₁ + m₂)
  | proj {t t' : Term} {l : String} {m : Nat} : ParM t t' m → ParM (proj t l) (proj t' l) m
  | beta {t t' u u' : Term} {m₁ m₂ : Nat} :
      isValue u = true → ParM t t' m₁ → ParM u u' m₂ →
      ParM (app (lam t) u) (subst (inst u') t') (1 + m₁ + occ (w0 m₂) t')
  | projR {s u u' : Term} {l : String} {m : Nat} :
      lookup s l = some u → ParM u u' m → ParM (proj s l) u' (m + 1)
  | indexR {s u u' : Term} {b : Bytes} {m : Nat} :
      select s b.toNat = some u → ParM u u' m → ParM (app s (bytes b)) u' (m + 1)
  | opcodeR {s : Term} {b b' : Bytes} :
      isStruct s = true → isData s = true → op b s = some b' → ParM (app (bytes b) s) (bytes b') 1
  | fix {t t' : Term} {m : Nat} : ParM t t' m → ParM (fix t) (fix t') m
  /-- Unfolding copies `fix (λx. t')` once per occurrence of `x`, with the steps inside it. -/
  | fixProjR {t t' : Term} {l : String} {m : Nat} :
      ParM t t' m →
      ParM (proj (fix (lam t)) l) (proj (subst (inst (fix (lam t'))) t') l) (1 + m + occ (w0 m) t')
  | fixAppR {t t' u u' : Term} {m₁ m₂ : Nat} :
      ParM t t' m₁ → ParM u u' m₂ →
      ParM (app (fix (lam t)) u) (app (subst (inst (fix (lam t'))) t') u')
        (1 + m₁ + occ (w0 m₁) t' + m₂)

variable {op}

theorem ParM.cast {t t' : Term} {m m' : Nat} (h : ParM op t t' m) (e : m = m') : ParM op t t' m' :=
  e ▸ h

theorem ParM.par {t t' : Term} {m : Nat} (h : ParM op t t' m) : Par op t t' := by
  induction h with
  | var n => exact .var n
  | bytes b => exact .bytes b
  | snil => exact .snil
  | lam _ ih => exact .lam ih
  | app _ _ iha ihb => exact .app iha ihb
  | scons _ _ iht ihr => exact .scons iht ihr
  | proj _ ih => exact .proj ih
  | beta hu _ _ iht ihu => exact .beta hu iht ihu
  | projR h _ ih => exact .projR h ih
  | indexR h _ ih => exact .indexR h ih
  | opcodeR h1 h2 h3 => exact .opcodeR h1 h2 h3
  | fix _ ih => exact .fix ih
  | fixProjR _ ih => exact .fixProjR ih
  | fixAppR _ _ iht ihu => exact .fixAppR iht ihu

theorem Par.parM {t t' : Term} (h : Par op t t') : ∃ m, ParM op t t' m := by
  induction h with
  | var n => exact ⟨_, .var n⟩
  | bytes b => exact ⟨_, .bytes b⟩
  | snil => exact ⟨_, .snil⟩
  | lam _ ih => obtain ⟨_, h⟩ := ih; exact ⟨_, .lam h⟩
  | app _ _ iha ihb => obtain ⟨_, ha⟩ := iha; obtain ⟨_, hb⟩ := ihb; exact ⟨_, .app ha hb⟩
  | scons _ _ iht ihr => obtain ⟨_, ht⟩ := iht; obtain ⟨_, hr⟩ := ihr; exact ⟨_, .scons ht hr⟩
  | proj _ ih => obtain ⟨_, h⟩ := ih; exact ⟨_, .proj h⟩
  | beta hu _ _ iht ihu =>
    obtain ⟨_, ht⟩ := iht; obtain ⟨_, hu'⟩ := ihu; exact ⟨_, .beta hu ht hu'⟩
  | projR h _ ih => obtain ⟨_, h'⟩ := ih; exact ⟨_, .projR h h'⟩
  | indexR h _ ih => obtain ⟨_, h'⟩ := ih; exact ⟨_, .indexR h h'⟩
  | opcodeR h1 h2 h3 => exact ⟨_, .opcodeR h1 h2 h3⟩
  | fix _ ih => obtain ⟨_, h⟩ := ih; exact ⟨_, .fix h⟩
  | fixProjR _ ih => obtain ⟨_, h⟩ := ih; exact ⟨_, .fixProjR h⟩
  | fixAppR _ _ iht ihu =>
    obtain ⟨_, ht⟩ := iht; obtain ⟨_, hu⟩ := ihu; exact ⟨_, .fixAppR ht hu⟩

theorem ParM.refl : ∀ t : Term, ParM op t t 0
  | .var n => .var n
  | .lam t => .lam (ParM.refl t)
  | .app a b => .app (ParM.refl a) (ParM.refl b)
  | .snil => .snil
  | .scons _ t r => .scons (ParM.refl t) (ParM.refl r)
  | .proj t _ => .proj (ParM.refl t)
  | .bytes b => .bytes b
  | .fix t => .fix (ParM.refl t)

/-- Renaming keeps the measure. -/
theorem ParM.ren {t t' : Term} {m : Nat} (h : ParM op t t' m) (ξ : Nat → Nat) :
    ParM op (Oymomo.ren ξ t) (Oymomo.ren ξ t') m := by
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
    have h := ParM.beta (isValue_ren ξ hu) (iht (upr ξ)) (ihu ξ)
    rwa [occ_ren, occ_congr (ν := w0 _) (by intro n; cases n <;> rfl)] at h
  | projR h _ ih => exact .projR (lookup_ren ξ h) (ih _)
  | indexR h _ ih => exact .indexR (select_ren ξ h) (ih _)
  | opcodeR h1 h2 h3 =>
    simp only [Oymomo.ren]
    rw [ren_data ξ h2]
    exact .opcodeR h1 h2 h3
  | fix _ ih => exact .fix (ih _)
  | @fixProjR t t' l m _ ih =>
    simp only [Oymomo.ren]
    rw [ren_inst]
    simp only [Oymomo.ren]
    have h := ParM.fixProjR (l := l) (ih (upr ξ))
    rwa [occ_ren, occ_congr (ν := w0 _) (by intro n; cases n <;> rfl)] at h
  | fixAppR _ _ iht ihu =>
    simp only [Oymomo.ren]
    rw [ren_inst]
    simp only [Oymomo.ren]
    have h := ParM.fixAppR (iht (upr ξ)) (ihu ξ)
    rwa [occ_ren, occ_congr (ν := w0 _) (by intro n; cases n <;> rfl)] at h

theorem ParM.ups {σ τ : Nat → Term} {μ : Nat → Nat} (h : ∀ n, ParM op (σ n) (τ n) (μ n)) :
    ∀ n, ParM op (Oymomo.ups σ n) (Oymomo.ups τ n) (shiftW μ n)
  | 0 => .var 0
  | n + 1 => (h n).ren Nat.succ

/-- Substitution adds the measure of each substituted step once per occurrence. -/
theorem ParM.subst {t t' : Term} {m : Nat} (h : ParM op t t' m) {σ τ : Nat → Term}
    {μ : Nat → Nat} (hσ : ∀ n, ParM op (σ n) (τ n) (μ n)) (hv : ValSub σ) :
    ParM op (Oymomo.subst σ t) (Oymomo.subst τ t') (m + occ μ t') := by
  induction h generalizing σ τ μ with
  | var n => exact (hσ n).cast (by simp [occ])
  | bytes b => exact (ParM.bytes b).cast (by simp [occ])
  | snil => exact ParM.snil.cast (by simp [occ])
  | lam _ ih => exact .lam (ih (ParM.ups hσ) hv.ups)
  | app _ _ iha ihb => exact (ParM.app (iha hσ hv) (ihb hσ hv)).cast (by simp only [occ]; omega)
  | scons _ _ iht ihr =>
    exact (ParM.scons (iht hσ hv) (ihr hσ hv)).cast (by simp only [occ]; omega)
  | proj _ ih => exact .proj (ih hσ hv)
  | @beta t t' u u' m₁ m₂ hu _ _ iht ihu =>
    simp only [Oymomo.subst]
    rw [subst_inst]
    have h := ParM.beta (isValue_subst hv hu) (iht (ParM.ups hσ) hv.ups) (ihu hσ hv)
    refine h.cast ?_
    have e1 : ∀ K, occ (w0 K) (Oymomo.subst (Oymomo.ups τ) t') = occ (w0 K) t' := by
      intro K
      rw [occ_subst]
      apply occ_congr; intro n
      cases n with
      | zero => rfl
      | succ n => simp only [Oymomo.ups]; rw [occ_ren]; exact occ_zero _
    have e2 : occ (shiftW μ) t' + occ (w0 (m₂ + occ μ u')) t' =
        occ (w0 m₂) t' + occ μ (Oymomo.subst (inst u') t') := by
      rw [occ_subst, occ_add, occ_add]
      apply occ_congr; intro n
      cases n with
      | zero => simp [shiftW, w0, inst]
      | succ n => simp [shiftW, w0, inst, occ]
    rw [e1]
    omega
  | projR h _ ih => exact (ParM.projR (lookup_subst _ h) (ih hσ hv)).cast (by omega)
  | indexR h _ ih => exact (ParM.indexR (select_subst _ h) (ih hσ hv)).cast (by omega)
  | opcodeR h1 h2 h3 =>
    simp only [Oymomo.subst]
    rw [subst_data _ h2]
    exact (ParM.opcodeR h1 h2 h3).cast (by simp [occ])
  | fix _ ih => exact (ParM.fix (ih hσ hv)).cast (by simp [occ])
  | @fixProjR t t' l M _ ih =>
    simp only [Oymomo.subst]
    rw [subst_inst]
    simp only [Oymomo.subst]
    have h := ParM.fixProjR (l := l) (ih (ParM.ups hσ) hv.ups)
    refine h.cast ?_
    have e1 : ∀ K, occ (w0 K) (Oymomo.subst (Oymomo.ups τ) t') = occ (w0 K) t' := by
      intro K
      rw [occ_subst]
      apply occ_congr; intro n
      cases n with
      | zero => rfl
      | succ n => simp only [Oymomo.ups]; rw [occ_ren]; exact occ_zero _
    have e2 : occ (shiftW μ) t' + occ (w0 (M + occ μ (Term.fix (Term.lam t')))) t' =
        occ (w0 M) t' + occ μ (Oymomo.subst (inst (Term.fix (Term.lam t'))) t') := by
      rw [occ_subst, occ_add, occ_add]
      apply occ_congr; intro n
      cases n with
      | zero => simp [shiftW, w0, inst]
      | succ n => simp [shiftW, w0, inst, occ]
    rw [e1]
    simp only [occ] at e2 ⊢
    omega
  | @fixAppR t t' u u' M m₂ _ _ iht ihu =>
    simp only [Oymomo.subst]
    rw [subst_inst]
    simp only [Oymomo.subst]
    have h := ParM.fixAppR (iht (ParM.ups hσ) hv.ups) (ihu hσ hv)
    refine h.cast ?_
    have e1 : ∀ K, occ (w0 K) (Oymomo.subst (Oymomo.ups τ) t') = occ (w0 K) t' := by
      intro K
      rw [occ_subst]
      apply occ_congr; intro n
      cases n with
      | zero => rfl
      | succ n => simp only [Oymomo.ups]; rw [occ_ren]; exact occ_zero _
    have e2 : occ (shiftW μ) t' + occ (w0 (M + occ μ (Term.fix (Term.lam t')))) t' =
        occ (w0 M) t' + occ μ (Oymomo.subst (inst (Term.fix (Term.lam t'))) t') := by
      rw [occ_subst, occ_add, occ_add]
      apply occ_congr; intro n
      cases n with
      | zero => simp [shiftW, w0, inst]
      | succ n => simp [shiftW, w0, inst, occ]
    rw [e1]
    simp only [occ] at e2 ⊢
    omega

theorem ParM.inst {u u' : Term} {m : Nat} (h : ParM op u u' m) :
    ∀ n, ParM op (Oymomo.inst u n) (Oymomo.inst u' n) (w0 m n)
  | 0 => h
  | n + 1 => .var n

end Oymomo
