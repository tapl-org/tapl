-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Measure
import Oymomo.Strategy

/-!
# The guarantee of the strategy (semantics.tex, 6.4)

`guarantee`: when `t ⟶* n` and `n` is a normal form, the order of table 6.2 reaches `n`.

The proof follows Takahashi's factorization:

* `IPar op t u` is an internal parallel step: a parallel step that leaves alone the redex
  the order would contract in `t`, and every redex on the path to it. It keeps the choice
  the order makes (`IPar.merge`), and a term with a step keeps one (`IPar.red`).
* `Par.split`: a parallel step is some steps of the order followed by an internal one. Each
  step of the order lowers Takahashi's measure (`ParM`).
* `IPar.merge`: after an internal step, the step the order takes can be taken first.

The terms are well formed (`WF`): every struct chain ends in `snil`. Steps keep that.
-/

namespace Oymomo
open Term

variable {op : Bytes → Term → Option Bytes}

/-! ## Well-formed chains -/

/-- Every struct chain ends in `snil` (a tail is a struct). -/
def WF : Term → Prop
  | lam t => WF t
  | app a b => WF a ∧ WF b
  | scons _ t r => WF t ∧ WF r ∧ Oymomo.isStruct r = true
  | proj t _ => WF t
  | _ => True

theorem isStruct_ren (ξ : Nat → Nat) (r : Term) : Oymomo.isStruct (ren ξ r) = Oymomo.isStruct r := by
  cases r <;> rfl

theorem isStruct_subst (σ : Nat → Term) {r : Term} (h : Oymomo.isStruct r = true) :
    Oymomo.isStruct (subst σ r) = true := by
  cases r <;> simp_all [Oymomo.isStruct, subst]

theorem WF.ren (ξ : Nat → Nat) {t : Term} (h : WF t) : WF (ren ξ t) := by
  induction t generalizing ξ with
  | var n => trivial
  | lam t ih => exact ih _ h
  | app a b iha ihb => exact ⟨iha _ h.1, ihb _ h.2⟩
  | snil => trivial
  | scons l t r iht ihr => exact ⟨iht _ h.1, ihr _ h.2.1, by rw [isStruct_ren]; exact h.2.2⟩
  | proj t l ih => exact ih _ h
  | bytes b => trivial

theorem WF.subst {σ : Nat → Term} (hσ : ∀ n, WF (σ n)) {t : Term} (h : WF t) :
    WF (subst σ t) := by
  induction t generalizing σ with
  | var n => exact hσ n
  | lam t ih =>
    refine ih (σ := ups σ) ?_ h
    intro n; cases n with
    | zero => trivial
    | succ n => exact (hσ n).ren _
  | app a b iha ihb => exact ⟨iha hσ h.1, ihb hσ h.2⟩
  | snil => trivial
  | scons l t r iht ihr => exact ⟨iht hσ h.1, ihr hσ h.2.1, isStruct_subst σ h.2.2⟩
  | proj t l ih => exact ih hσ h
  | bytes b => trivial

theorem WF.lookup {s u : Term} {l : String} (h : WF s) (hl : lookup s l = some u) : WF u := by
  induction s with
  | scons l' t r _ ihr =>
    simp only [Oymomo.lookup] at hl
    split at hl
    · cases hl; exact h.1
    · exact ihr h.2.1 hl
  | _ => simp [Oymomo.lookup] at hl

theorem WF.select {s u : Term} {n : Nat} (h : WF s) (hs : select s n = some u) : WF u := by
  induction s generalizing n with
  | scons l t r _ ihr =>
    cases n with
    | zero =>
      rw [select_scons_zero] at hs
      cases hs; exact h.1
    | succ n =>
      cases r with
      | snil => simp only [Oymomo.select, Option.some.injEq] at hs; subst hs; exact h.1
      | scons _ _ _ => simp only [Oymomo.select] at hs; exact ihr h.2.1 hs
      | _ => simp [Oymomo.select] at hs
  | _ => simp [Oymomo.select] at hs

theorem Step.isStruct {r r' : Term} (h : Step op r r') (hr : Oymomo.isStruct r = true) :
    Oymomo.isStruct r' = true := by
  cases h <;> simp_all [Oymomo.isStruct]

theorem Step.wf {t t' : Term} (h : Step op t t') : WF t → WF t' := by
  induction h with
  | beta _ =>
    intro hw
    exact WF.subst (fun n => by cases n with | zero => exact hw.2 | succ n => trivial) hw.1
  | @proj s _ _ hl => intro hw; exact WF.lookup (s := s) hw hl
  | index hs => intro hw; exact hw.1.select hs
  | opcode _ _ _ => intro _; trivial
  | lam _ ih => exact ih
  | app1 _ ih => intro hw; exact ⟨ih hw.1, hw.2⟩
  | app2 _ ih => intro hw; exact ⟨hw.1, ih hw.2⟩
  | scons1 _ ih => intro hw; exact ⟨ih hw.1, hw.2.1, hw.2.2⟩
  | scons2 hr ih => intro hw; exact ⟨hw.1, ih hw.2.1, hr.isStruct hw.2.2⟩
  | proj1 _ ih => exact ih

theorem SStep.wf {t t' : Term} (h : SStep op t t') (hw : WF t) : WF t' := (sstep_step h).wf hw

theorem Star.sstep_wf {t t' : Term} (h : Star (SStep op) t t') (hw : WF t) : WF t' := by
  induction h with
  | refl => exact hw
  | tail _ h ih => exact h.wf ih

/-- A nonempty well-formed struct always has a field at any position (E-Index, E-Default). -/
theorem select_some {l : String} {t r : Term} (n : Nat) (h : WF (scons l t r)) :
    ∃ u, select (scons l t r) n = some u := by
  induction r generalizing l t n with
  | snil => exact ⟨t, by cases n <;> rfl⟩
  | scons l' t' r' _ ihr =>
    cases n with
    | zero => exact ⟨t, select_scons_zero _ _ _⟩
    | succ n => simp only [Oymomo.select]; exact ihr n h.2.1
  | _ => exact absurd h.2.2 (by simp [Oymomo.isStruct])

/-! ## Facts about steps and parallel steps -/

theorem Step.not_data {s s' : Term} (h : Step op s s') : isData s = false := by
  induction h <;> simp_all [isData]

theorem not_red_data {s : Term} (h : isData s = true) : ¬ Red op s := fun ⟨_, hs⟩ => by
  rw [hs.not_data] at h; cases h

theorem NVRed.nv {r : Term} (h : NVRed op r) : isValue r = false := by
  induction r with
  | scons l t r _ ihr =>
    rcases h with ⟨hv, _⟩ | h
    · simp [isValue, hv]
    · simp [isValue, ihr h]
  | _ => exact h.elim

theorem RootRed.red {t : Term} (h : RootRed op t) : Red op t := by
  cases t with
  | app a b => obtain ⟨_, hs⟩ := h.sstep; exact hs.red
  | proj s l => obtain ⟨_, hl⟩ := h; exact ⟨_, .proj hl⟩
  | _ => exact h.elim

/-- A normal form has no parallel step but itself (6.4d, step D). -/
theorem Par.normal_eq {t u : Term} (h : Par op t u) (hn : ¬ Red op t) : u = t := by
  induction h with
  | var => rfl
  | bytes => rfl
  | snil => rfl
  | lam _ ih => rw [ih (fun ⟨_, h⟩ => hn ⟨_, .lam h⟩)]
  | app _ _ iha ihb =>
    rw [iha (fun ⟨_, h⟩ => hn ⟨_, .app1 h⟩), ihb (fun ⟨_, h⟩ => hn ⟨_, .app2 h⟩)]
  | scons _ _ iht ihr =>
    rw [iht (fun ⟨_, h⟩ => hn ⟨_, .scons1 h⟩), ihr (fun ⟨_, h⟩ => hn ⟨_, .scons2 h⟩)]
  | proj _ ih => rw [ih (fun ⟨_, h⟩ => hn ⟨_, .proj1 h⟩)]
  | beta hu _ _ _ _ => exact absurd ⟨_, .beta hu⟩ hn
  | projR hl _ _ => exact absurd ⟨_, .proj hl⟩ hn
  | indexR hs _ _ => exact absurd ⟨_, .index hs⟩ hn
  | opcodeR h1 h2 h3 => exact absurd ⟨_, .opcode h1 h2 h3⟩ hn

/-- On a well-formed struct whose fields that are not values are normal, a parallel step
keeps some field not a value. -/
theorem Par.nv_of_not_nvred {r r' : Term} (h : Par op r r') :
    WF r → Oymomo.isStruct r = true → ¬ NVRed op r → isValue r = false → isValue r' = false := by
  induction h with
  | @scons l t t' r r' ht _ _ ihr =>
    intro hw _ hn hv
    cases htv : isValue t with
    | false =>
      have hnt : ¬ Red op t := fun h => hn (Or.inl ⟨htv, h⟩)
      rw [ht.normal_eq hnt]
      simp [isValue, htv]
    | true =>
      have hrv : isValue r = false := by simpa [isValue, htv] using hv
      simp [isValue, ihr hw.2.1 hw.2.2 (fun h => hn (Or.inr h)) hrv]
  | _ => intro _ hs _ hv; simp_all [Oymomo.isStruct, isValue]

/-- On a well-formed struct, a parallel step keeps the fields that are not values normal. -/
theorem Par.not_nvred {r r' : Term} (h : Par op r r') :
    WF r → Oymomo.isStruct r = true → ¬ NVRed op r → ¬ NVRed op r' := by
  induction h with
  | snil => intro _ _ _ h; exact h
  | @scons l t t' r r' ht _ _ ihr =>
    intro hw _ hn
    rintro (⟨hv', hr'⟩ | h')
    · have htv : isValue t = false := by
        cases htv : isValue t with
        | false => rfl
        | true => rw [ht.value htv] at hv'; cases hv'
      have hnt : ¬ Red op t := fun h => hn (Or.inl ⟨htv, h⟩)
      rw [ht.normal_eq hnt] at hr'
      exact hnt hr'
    · exact ihr hw.2.1 hw.2.2 (fun h => hn (Or.inr h)) h'
  | _ => intro _ hs; simp_all [Oymomo.isStruct]

/-- On a well-formed struct, a parallel step keeps a label missing. -/
theorem Par.lookup_none {s s' : Term} {l : String} (h : Par op s s') :
    WF s → Oymomo.isStruct s = true → lookup s l = none → lookup s' l = none := by
  induction h with
  | snil => intro _ _ h; exact h
  | @scons l' t t' r r' _ _ _ ihr =>
    intro hw _ hl
    simp only [Oymomo.lookup] at hl ⊢
    split at hl
    · cases hl
    · rename_i hne
      simp only [hne, ↓reduceIte]
      exact ihr hw.2.1 hw.2.2 hl
  | _ => intro _ hs; simp_all [Oymomo.isStruct]

theorem RootRed.par {a a' b b' : Term} (hr : RootRed op (app a b)) (ha : Par op a a')
    (hb : Par op b b') : RootRed op (app a' b') := by
  cases a with
  | lam t =>
    obtain ⟨t', rfl, _⟩ := Par.lam_inv ha
    exact hb.value hr
  | bytes c =>
    rw [Par.bytes_inv ha]
    obtain ⟨h1, h2, h3⟩ := hr
    rw [hb.data h2]
    exact ⟨h1, h2, h3⟩
  | _ =>
    cases b with
    | bytes d =>
      rw [Par.bytes_inv hb]
      obtain ⟨u, hu⟩ := hr
      obtain ⟨u', hu', _⟩ := select_par ha hu
      cases a' <;> first | exact ⟨u', hu'⟩ | simp [Oymomo.select] at hu' | rfl
    | _ => exact hr.elim

/-! ## Internal parallel steps -/

variable (op) in
/-- A parallel step that leaves alone the redex the order chooses and the path to it. Each
constructor is a row of table 6.2: the chosen part takes an internal step, the other parts
any parallel step. -/
inductive IPar : Term → Term → Prop
  /-- A normal form. -/
  | normal {t : Term} : ¬ Red op t → IPar t t
  /-- Rows c, e, f, g: the root is chosen, and stays. -/
  | rootApp {a a' b b' : Term} :
      RootRed op (app a b) → Par op a a' → Par op b b' → IPar (app a b) (app a' b')
  /-- Row a. -/
  | rootProj {s s' : Term} {l : String} :
      (∃ u, lookup s l = some u) → Par op s s' → IPar (proj s l) (proj s' l)
  /-- Row b. -/
  | proj1 {s s' : Term} {l : String} :
      lookup s l = none → Red op s → IPar s s' → IPar (proj s l) (proj s' l)
  /-- Row d. -/
  | arg {t t' u u' : Term} :
      isValue u = false → Red op u → Par op t t' → IPar u u' →
      IPar (app (lam t) u) (app (lam t') u')
  /-- Row h. -/
  | cond {s s' c c' : Term} :
      Oymomo.isStruct s = true → Red op c → Par op s s' → IPar c c' → IPar (app s c) (app s' c')
  /-- Row i. -/
  | app1 {a a' b b' : Term} :
      ¬ RootRed op (app a b) → ¬ (isLam a = true ∧ Red op b) →
      ¬ (Oymomo.isStruct a = true ∧ Red op b) → Red op a → IPar a a' → Par op b b' →
      IPar (app a b) (app a' b')
  /-- Row j. -/
  | app2 {a b b' : Term} :
      ¬ RootRed op (app a b) → isLam a = false → Oymomo.isStruct a = false → ¬ Red op a →
      Red op b → IPar b b' → IPar (app a b) (app a b')
  /-- Row k, the head. -/
  | fieldNV {l : String} {t t' r r' : Term} :
      isValue t = false → Red op t → IPar t t' → Par op r r' →
      IPar (scons l t r) (scons l t' r')
  /-- Row k, a later field. -/
  | fieldNVTail {l : String} {t t' r r' : Term} :
      ¬ (isValue t = false ∧ Red op t) → NVRed op r → Par op t t' → IPar r r' →
      IPar (scons l t r) (scons l t' r')
  /-- Row l, the head. -/
  | field {l : String} {t t' r r' : Term} :
      ¬ NVRed op (scons l t r) → Red op t → IPar t t' → Par op r r' →
      IPar (scons l t r) (scons l t' r')
  /-- Row l, a later field. -/
  | fieldTail {l : String} {t r r' : Term} :
      ¬ NVRed op (scons l t r) → ¬ Red op t → IPar r r' → IPar (scons l t r) (scons l t r')
  /-- Row m. -/
  | lam {t t' : Term} : IPar t t' → IPar (lam t) (lam t')

theorem IPar.par {t u : Term} (h : IPar op t u) : Par op t u := by
  induction h with
  | normal _ => exact .refl _
  | rootApp _ ha hb => exact .app ha hb
  | rootProj _ hs => exact .proj hs
  | proj1 _ _ _ ih => exact .proj ih
  | arg _ _ ht _ ih => exact .app (.lam ht) ih
  | cond _ _ hs _ ih => exact .app hs ih
  | app1 _ _ _ _ _ hb ih => exact .app ih hb
  | app2 _ _ _ _ _ _ ih => exact .app (.refl _) ih
  | fieldNV _ _ _ hr ih => exact .scons ih hr
  | fieldNVTail _ _ ht _ ih => exact .scons ht ih
  | field _ _ _ hr ih => exact .scons ih hr
  | fieldTail _ _ _ ih => exact .scons (.refl _) ih
  | lam _ ih => exact .lam ih

theorem IPar.isLam_eq {t u : Term} (h : IPar op t u) : isLam u = isLam t := by
  cases h <;> rfl

theorem IPar.isStruct_eq {t u : Term} (h : IPar op t u) : Oymomo.isStruct u = Oymomo.isStruct t := by
  cases h <;> rfl

theorem IPar.bytes_eq {t : Term} {d : Bytes} (h : IPar op t (bytes d)) : t = bytes d := by
  cases h; rfl

/-- Persistence: an internal step keeps a step (6.4d, step C). -/
theorem IPar.red {t u : Term} (h : IPar op t u) (ht : Red op t) : Red op u := by
  induction h with
  | normal hn => exact absurd ht hn
  | rootApp hr ha hb => exact (hr.par ha hb).red
  | rootProj hl hs =>
    obtain ⟨_, hl⟩ := hl
    obtain ⟨_, hl', _⟩ := lookup_par hs hl
    exact ⟨_, .proj hl'⟩
  | proj1 _ hs _ ih => obtain ⟨_, h⟩ := ih hs; exact ⟨_, .proj1 h⟩
  | arg _ hu _ _ ih => obtain ⟨_, h⟩ := ih hu; exact ⟨_, .app2 h⟩
  | cond _ hc _ _ ih => obtain ⟨_, h⟩ := ih hc; exact ⟨_, .app2 h⟩
  | app1 _ _ _ ha _ _ ih => obtain ⟨_, h⟩ := ih ha; exact ⟨_, .app1 h⟩
  | app2 _ _ _ _ hb _ ih => obtain ⟨_, h⟩ := ih hb; exact ⟨_, .app2 h⟩
  | fieldNV _ hr _ _ ih => obtain ⟨_, h⟩ := ih hr; exact ⟨_, .scons1 h⟩
  | fieldNVTail _ hnv _ _ ih => obtain ⟨_, h⟩ := ih hnv.red; exact ⟨_, .scons2 h⟩
  | field _ hr _ _ ih => obtain ⟨_, h⟩ := ih hr; exact ⟨_, .scons1 h⟩
  | @fieldTail l t r r' _ hnt _ ih =>
    have hr : Red op r := by
      obtain ⟨_, h⟩ := ht
      cases h with
      | scons1 h => exact absurd ⟨_, h⟩ hnt
      | scons2 h => exact ⟨_, h⟩
    obtain ⟨_, h⟩ := ih hr; exact ⟨_, .scons2 h⟩
  | lam _ ih =>
    obtain ⟨_, h⟩ := ht
    cases h with
    | lam h => obtain ⟨_, h'⟩ := ih ⟨_, h⟩; exact ⟨_, .lam h'⟩

/-- An internal step never makes a value of a term that is not one. -/
theorem IPar.nv {t u : Term} (h : IPar op t u) : WF t → isValue t = false → isValue u = false := by
  induction h with
  | normal _ => intro _ h; exact h
  | rootApp _ _ _ => intro _ _; rfl
  | rootProj _ _ => intro _ _; rfl
  | proj1 _ _ _ _ => intro _ _; rfl
  | arg _ _ _ _ _ => intro _ _; rfl
  | cond _ _ _ _ _ => intro _ _; rfl
  | app1 _ _ _ _ _ _ _ => intro _ _; rfl
  | app2 _ _ _ _ _ _ _ => intro _ _; rfl
  | fieldNV hv _ _ _ ih => intro hw _; simp [isValue, ih hw.1 hv]
  | fieldNVTail _ hnv _ _ ih => intro hw _; simp [isValue, ih hw.2.1 hnv.nv]
  | @field l t t' r r' hn hr _ hrr _ =>
    intro hw hv
    have htv : isValue t = true := by
      cases htv : isValue t with
      | false => exact absurd (Or.inl ⟨htv, hr⟩) hn
      | true => rfl
    have hrv : isValue r = false := by simpa [isValue, htv] using hv
    simp [isValue, hrr.nv_of_not_nvred hw.2.1 hw.2.2 (fun h => hn (Or.inr h)) hrv]
  | @fieldTail l t r r' hn _ _ ih =>
    intro hw hv
    cases htv : isValue t with
    | false => simp [isValue, htv]
    | true =>
      have hrv : isValue r = false := by simpa [isValue, htv] using hv
      simp [isValue, ih hw.2.1 hrv]
  | lam _ _ => intro _ h; cases h

/-- An internal step keeps row k applicable. -/
theorem IPar.nvred {r r' : Term} (h : IPar op r r') : WF r → NVRed op r → NVRed op r' := by
  induction h with
  | normal _ => intro _ h; exact h
  | fieldNV hv hr hip _ _ =>
    intro hw _
    exact Or.inl ⟨hip.nv hw.1 hv, hip.red hr⟩
  | fieldNVTail _ hnv _ _ ih => intro hw _; exact Or.inr (ih hw.2.1 hnv)
  | field hn _ _ _ _ => intro _ h; exact absurd h hn
  | fieldTail hn _ _ _ => intro _ h; exact absurd h hn
  | _ => intro _ h; exact h.elim

/-! ## Split: a parallel step is steps of the order, then an internal step -/

theorem not_red_var {n : Nat} : ¬ Red op (var n) := fun ⟨_, h⟩ => by cases h
theorem not_red_snil : ¬ Red op snil := fun ⟨_, h⟩ => by cases h

/-- One step of the split: either the parallel step is internal, or the order takes a step
and a parallel step of a smaller measure is left. -/
theorem ParM.split1 {t u : Term} {m : Nat} (h : ParM op t u m) :
    IPar op t u ∨ ∃ t₁ m₁, SStep op t t₁ ∧ ParM op t₁ u m₁ ∧ m₁ < m := by
  induction h with
  | var n => exact .inl (.normal not_red_var)
  | bytes b => exact .inl (.normal not_red_bytes)
  | snil => exact .inl (.normal not_red_snil)
  | lam h ih =>
    rcases ih with h' | ⟨t₁, m₁, hs, hm, hlt⟩
    · exact .inl (.lam h')
    · exact .inr ⟨_, _, .lam hs, .lam hm, hlt⟩
  | @app a a' b b' m₁ m₂ ha hb iha ihb =>
    by_cases hroot : RootRed op (Term.app a b)
    · exact .inl (.rootApp hroot ha.par hb.par)
    by_cases hlb : isLam a = true ∧ Red op b
    · cases a with
      | lam t₀ =>
        have hv : isValue b = false := by
          cases hv : isValue b with
          | false => rfl
          | true => exact absurd hv hroot
        cases ha with
        | lam ht₀ =>
          rcases ihb with h' | ⟨b₁, m₂', hs, hm, hlt⟩
          · exact .inl (.arg hv hlb.2 ht₀.par h')
          · exact .inr ⟨_, _, .arg hv hs, .app (.lam ht₀) hm, by omega⟩
      | _ => simp [isLam] at hlb
    by_cases hsb : Oymomo.isStruct a = true ∧ Red op b
    · rcases ihb with h' | ⟨b₁, m₂', hs, hm, hlt⟩
      · exact .inl (.cond hsb.1 hsb.2 ha.par h')
      · exact .inr ⟨_, _, .cond hsb.1 hs, .app ha hm, by omega⟩
    by_cases hra : Red op a
    · rcases iha with h' | ⟨a₁, m₁', hs, hm, hlt⟩
      · exact .inl (.app1 hroot hlb hsb hra h' hb.par)
      · exact .inr ⟨_, _, .app1 hroot hlb hsb hs, .app hm hb, by omega⟩
    have ha' : a' = a := ha.par.normal_eq hra
    subst a'
    by_cases hrb : Red op b
    · have hl : isLam a = false := by
        cases hl : isLam a with
        | false => rfl
        | true => exact absurd ⟨hl, hrb⟩ hlb
      have hs : Oymomo.isStruct a = false := by
        cases hs : Oymomo.isStruct a with
        | false => rfl
        | true => exact absurd ⟨hs, hrb⟩ hsb
      rcases ihb with h' | ⟨b₁, m₂', hs', hm, hlt⟩
      · exact .inl (.app2 hroot hl hs hra hrb h')
      · exact .inr ⟨_, _, .app2 hroot hl hs hra hs', .app ha hm, by omega⟩
    · have hb' : b' = b := hb.par.normal_eq hrb
      subst b'
      refine .inl (.normal fun ⟨_, hst⟩ => ?_)
      rcases hst.root_or_parts with h | h | h
      · exact hroot h
      · exact hra h
      · exact hrb h
  | @scons l t t' r r' m₁ m₂ ht hr iht ihr =>
    by_cases h1 : isValue t = false ∧ Red op t
    · rcases iht with h' | ⟨t₁, m₁', hs, hm, hlt⟩
      · exact .inl (.fieldNV h1.1 h1.2 h' hr.par)
      · exact .inr ⟨_, _, .fieldNV h1.1 hs, .scons hm hr, by omega⟩
    by_cases hnv : NVRed op r
    · rcases ihr with h' | ⟨r₁, m₂', hs, hm, hlt⟩
      · exact .inl (.fieldNVTail h1 hnv ht.par h')
      · exact .inr ⟨_, _, .fieldNVTail h1 hnv hs, .scons ht hm, by omega⟩
    have hn : ¬ NVRed op (Term.scons l t r) := by
      rintro (h | h)
      · exact h1 h
      · exact hnv h
    by_cases hrt : Red op t
    · rcases iht with h' | ⟨t₁, m₁', hs, hm, hlt⟩
      · exact .inl (.field hn hrt h' hr.par)
      · exact .inr ⟨_, _, .field hn hs, .scons hm hr, by omega⟩
    have ht' : t' = t := ht.par.normal_eq hrt
    subst t'
    by_cases hrr : Red op r
    · rcases ihr with h' | ⟨r₁, m₂', hs, hm, hlt⟩
      · exact .inl (.fieldTail hn hrt h')
      · exact .inr ⟨_, _, .fieldTail hn hrt hs, .scons ht hm, by omega⟩
    · have hr' : r' = r := hr.par.normal_eq hrr
      subst r'
      refine .inl (.normal fun ⟨_, hst⟩ => ?_)
      cases hst with
      | scons1 h => exact hrt ⟨_, h⟩
      | scons2 h => exact hrr ⟨_, h⟩
  | @proj s s' l m hs ih =>
    by_cases hl : ∃ u, lookup s l = some u
    · exact .inl (.rootProj hl hs.par)
    have hn : lookup s l = none := by
      cases h : lookup s l with
      | none => rfl
      | some u => exact absurd ⟨u, h⟩ hl
    by_cases hrs : Red op s
    · rcases ih with h' | ⟨s₁, m', hst, hm, hlt⟩
      · exact .inl (.proj1 hn hrs h')
      · exact .inr ⟨_, _, .proj1 hn hst, .proj hm, hlt⟩
    · have hs' : s' = s := hs.par.normal_eq hrs
      subst s'
      refine .inl (.normal fun ⟨_, hst⟩ => ?_)
      cases hst with
      | proj h => rw [hn] at h; cases h
      | proj1 h => exact hrs ⟨_, h⟩
  | @beta t t' u u' m₁ m₂ hu ht hu' _ _ =>
    exact .inr ⟨_, _, .beta hu, ht.subst (ParM.inst hu') (ValSub.inst hu), by omega⟩
  | projR hl hu _ => exact .inr ⟨_, _, .proj hl, hu, by omega⟩
  | indexR hs hu _ => exact .inr ⟨_, _, .index hs, hu, by omega⟩
  | opcodeR h1 h2 h3 => exact .inr ⟨_, _, .opcode h1 h2 h3, .bytes _, by omega⟩

/-- Split (6.4d, step A): a parallel step is some steps of the order, then an internal
step. -/
theorem Par.split {t u : Term} (h : Par op t u) : ∃ t', Star (SStep op) t t' ∧ IPar op t' u := by
  obtain ⟨m, hm⟩ := h.parM
  induction m using Nat.strongRecOn generalizing t with
  | _ m ih =>
    rcases hm.split1 with h' | ⟨t₁, m₁, hs, hm₁, hlt⟩
    · exact ⟨t, .refl _, h'⟩
    · obtain ⟨t', hst, hip⟩ := ih m₁ hlt hm₁.par hm₁
      exact ⟨t', Star.head hs hst, hip⟩

/-! ## Merge: after an internal step, the order's step can come first -/

theorem rootApp_merge {a a' b b' u₁ : Term} (hr : RootRed op (app a b)) (ha : Par op a a')
    (hb : Par op b b') (hu : SStep op (app a' b') u₁) :
    ∃ t₂, SStep op (app a b) t₂ ∧ Par op t₂ u₁ := by
  cases a with
  | lam t =>
    obtain ⟨t', rfl, ht⟩ := Par.lam_inv ha
    have hv' : isValue b' = true := hb.value hr
    rw [sstep_det hu (.beta hv')]
    exact ⟨_, .beta hr, ht.subst (Par.inst hb) (ValSub.inst hr)⟩
  | bytes c =>
    rw [Par.bytes_inv ha] at hu
    obtain ⟨h1, h2, b'', h3⟩ := hr
    rw [hb.data h2] at hu
    rw [sstep_det hu (.opcode h1 h2 h3)]
    exact ⟨_, .opcode h1 h2 h3, .refl _⟩
  | _ =>
    cases b with
    | bytes d =>
      rw [Par.bytes_inv hb] at hu
      obtain ⟨w, hw⟩ := hr
      obtain ⟨w', hw', hp⟩ := select_par ha hw
      rw [sstep_det hu (.index hw')]
      exact ⟨_, .index hw, hp⟩
    | _ => exact hr.elim

/-- Merge (6.4d, step B). -/
theorem IPar.merge {t u : Term} (h : IPar op t u) :
    WF t → ∀ {u₁}, SStep op u u₁ → ∃ t₂, SStep op t t₂ ∧ Par op t₂ u₁ := by
  induction h with
  | normal hn => intro _ _ hu; exact absurd hu.red hn
  | rootApp hr ha hb => intro _ _ hu; exact rootApp_merge hr ha hb hu
  | rootProj hl hs =>
    intro _ _ hu
    obtain ⟨w, hw⟩ := hl
    obtain ⟨w', hw', hp⟩ := lookup_par hs hw
    rw [sstep_det hu (.proj hw')]
    exact ⟨_, .proj hw, hp⟩
  | @proj1 s s' l hn hrs hip ih =>
    intro hw _ hu
    have hn' : lookup s' l = none := by
      cases hip with
      | normal _ => exact hn
      | fieldNV _ _ _ hr =>
        simp only [Oymomo.lookup] at hn ⊢
        split at hn
        · cases hn
        · rename_i hne; simp only [hne, ↓reduceIte]; exact hr.lookup_none hw.2.1 hw.2.2 hn
      | fieldNVTail _ _ _ hr =>
        simp only [Oymomo.lookup] at hn ⊢
        split at hn
        · cases hn
        · rename_i hne; simp only [hne, ↓reduceIte]; exact hr.par.lookup_none hw.2.1 hw.2.2 hn
      | field _ _ _ hr =>
        simp only [Oymomo.lookup] at hn ⊢
        split at hn
        · cases hn
        · rename_i hne; simp only [hne, ↓reduceIte]; exact hr.lookup_none hw.2.1 hw.2.2 hn
      | fieldTail _ _ hr =>
        simp only [Oymomo.lookup] at hn ⊢
        split at hn
        · cases hn
        · rename_i hne; simp only [hne, ↓reduceIte]; exact hr.par.lookup_none hw.2.1 hw.2.2 hn
      | _ => rfl
    cases hu with
    | proj h' => rw [hn'] at h'; cases h'
    | proj1 _ h' =>
      obtain ⟨s₂, hs₂, hp⟩ := ih hw h'
      exact ⟨_, .proj1 hn hs₂, .proj hp⟩
  | @arg t t' u u' hv hru ht hip ih =>
    intro hw _ hu
    have hv' : isValue u' = false := hip.nv hw.2 hv
    have hru' : Red op u' := hip.red hru
    cases hu with
    | beta hv'' => rw [hv'] at hv''; cases hv''
    | arg _ h' =>
      obtain ⟨u₂, hu₂, hp⟩ := ih hw.2 h'
      exact ⟨_, .arg hv hu₂, .app (.lam ht) hp⟩
    | index hs => simp [select] at hs
    | cond hst _ => simp [Oymomo.isStruct] at hst
    | app1 _ hl _ _ => exact absurd ⟨rfl, hru'⟩ hl
    | app2 _ hl _ _ _ => simp [isLam] at hl
  | @cond s s' c c' hst hrc hs hip ih =>
    intro hw _ hu
    have hst' : Oymomo.isStruct s' = true := hs.isStruct hst
    have hrc' : Red op c' := hip.red hrc
    cases hu with
    | beta _ => simp [Oymomo.isStruct] at hst'
    | arg _ _ => simp [Oymomo.isStruct] at hst'
    | opcode _ _ _ => simp [Oymomo.isStruct] at hst'
    | index _ => rw [hip.bytes_eq] at hrc; exact absurd hrc not_red_bytes
    | cond _ h' =>
      obtain ⟨c₂, hc₂, hp⟩ := ih hw.2 h'
      exact ⟨_, .cond hst hc₂, .app hs hp⟩
    | app1 _ _ hns _ => exact absurd ⟨hst', hrc'⟩ hns
    | app2 _ _ hns _ _ => rw [hst'] at hns; cases hns
  | @app1 a a' b b' hr hl hs hra hip hb ih =>
    intro hw _ hu
    have hra' : Red op a' := hip.red hra
    cases hu with
    | beta hv =>
      have hla : isLam a = true := by rw [← hip.isLam_eq]; rfl
      have hnb : ¬ Red op b := fun h => hl ⟨hla, h⟩
      rw [hb.normal_eq hnb] at hv
      cases a with
      | lam _ => exact absurd hv hr
      | _ => simp [isLam] at hla
    | arg _ h' =>
      have hla : isLam a = true := by rw [← hip.isLam_eq]; rfl
      have hnb : ¬ Red op b := fun h => hl ⟨hla, h⟩
      rw [hb.normal_eq hnb] at h'
      exact absurd h'.red hnb
    | opcode _ _ _ => rw [hip.bytes_eq] at hra; exact absurd hra not_red_bytes
    | index hsel =>
      have hsa' : Oymomo.isStruct a' = true := by
        revert hsel; cases a' <;> simp [Oymomo.select, Oymomo.isStruct]
      have hsa : Oymomo.isStruct a = true := by rw [← hip.isStruct_eq]; exact hsa'
      have hnb : ¬ Red op b := fun h => hs ⟨hsa, h⟩
      have hbe := hb.normal_eq hnb
      subst hbe
      cases a with
      | scons l t r => exact absurd (select_some _ hw.1) hr
      | snil => exact absurd hra not_red_snil
      | _ => simp [Oymomo.isStruct] at hsa
    | cond hst h' =>
      have hsa : Oymomo.isStruct a = true := by rw [← hip.isStruct_eq]; exact hst
      have hnb : ¬ Red op b := fun h => hs ⟨hsa, h⟩
      rw [hb.normal_eq hnb] at h'
      exact absurd h'.red hnb
    | app1 _ _ _ h' =>
      obtain ⟨a₂, ha₂, hp⟩ := ih hw.1 h'
      exact ⟨_, .app1 hr hl hs ha₂, .app hp hb⟩
    | app2 _ _ _ hna _ => exact absurd hra' hna
  | @app2 a b b' hr hl hs hna hrb hip ih =>
    intro hw _ hu
    have hrb' : Red op b' := hip.red hrb
    cases hu with
    | beta _ => simp [isLam] at hl
    | arg _ _ => simp [isLam] at hl
    | opcode _ h2 _ => exact absurd hrb' (not_red_data h2)
    | index _ => exact absurd hrb' not_red_bytes
    | cond hst _ => rw [hs] at hst; cases hst
    | app1 _ _ _ h' => exact absurd h'.red hna
    | app2 _ _ _ _ h' =>
      obtain ⟨b₂, hb₂, hp⟩ := ih hw.2 h'
      exact ⟨_, .app2 hr hl hs hna hb₂, .app (.refl _) hp⟩
  | @fieldNV l t t' r r' hv hrt hip hr ih =>
    intro hw _ hu
    have hv' : isValue t' = false := hip.nv hw.1 hv
    have hrt' : Red op t' := hip.red hrt
    cases hu with
    | fieldNV _ h' =>
      obtain ⟨t₂, ht₂, hp⟩ := ih hw.1 h'
      exact ⟨_, .fieldNV hv ht₂, .scons hp hr⟩
    | fieldNVTail hn _ _ => exact absurd ⟨hv', hrt'⟩ hn
    | field hn _ => exact absurd (Or.inl ⟨hv', hrt'⟩) hn
    | fieldTail hn _ _ => exact absurd (Or.inl ⟨hv', hrt'⟩) hn
  | @fieldNVTail l t t' r r' hn hnv ht hip ih =>
    intro hw _ hu
    have hnv' : NVRed op r' := hip.nvred hw.2.1 hnv
    have hn' : ¬ (isValue t' = false ∧ Red op t') := by
      rintro ⟨hv', hrt'⟩
      have htv : isValue t = false := by
        cases htv : isValue t with
        | false => rfl
        | true => rw [ht.value htv] at hv'; cases hv'
      have hnt : ¬ Red op t := fun h => hn ⟨htv, h⟩
      rw [ht.normal_eq hnt] at hrt'
      exact hnt hrt'
    cases hu with
    | fieldNV hv' ht' => exact absurd ⟨hv', ht'.red⟩ hn'
    | fieldNVTail _ _ h' =>
      obtain ⟨r₂, hr₂, hp⟩ := ih hw.2.1 h'
      exact ⟨_, .fieldNVTail hn hnv hr₂, .scons ht hp⟩
    | field hn'' _ => exact absurd (Or.inr hnv') hn''
    | fieldTail hn'' _ _ => exact absurd (Or.inr hnv') hn''
  | @field l t t' r r' hn hrt hip hr ih =>
    intro hw _ hu
    have hrt' : Red op t' := hip.red hrt
    have htv : isValue t = true := by
      cases htv : isValue t with
      | false => exact absurd (Or.inl ⟨htv, hrt⟩) hn
      | true => rfl
    have htv' : isValue t' = true := hip.par.value htv
    have hnr' : ¬ NVRed op r' := hr.not_nvred hw.2.1 hw.2.2 (fun h => hn (Or.inr h))
    cases hu with
    | fieldNV hv' _ => rw [htv'] at hv'; cases hv'
    | fieldNVTail _ hnv _ => exact absurd hnv hnr'
    | field _ h' =>
      obtain ⟨t₂, ht₂, hp⟩ := ih hw.1 h'
      exact ⟨_, .field hn ht₂, .scons hp hr⟩
    | fieldTail _ hnt _ => exact absurd hrt' hnt
  | @fieldTail l t r r' hn hnt hip ih =>
    intro hw _ hu
    have hnr' : ¬ NVRed op r' := hip.par.not_nvred hw.2.1 hw.2.2 (fun h => hn (Or.inr h))
    cases hu with
    | fieldNV _ ht' => exact absurd ht'.red hnt
    | fieldNVTail _ hnv _ => exact absurd hnv hnr'
    | field _ ht' => exact absurd ht'.red hnt
    | fieldTail _ _ h' =>
      obtain ⟨r₂, hr₂, hp⟩ := ih hw.2.1 h'
      exact ⟨_, .fieldTail hn hnt hr₂, .scons (.refl _) hp⟩
  | lam _ ih =>
    intro hw _ hu
    cases hu with
    | lam h' =>
      obtain ⟨t₂, ht₂, hp⟩ := ih hw h'
      exact ⟨_, .lam ht₂, .lam hp⟩

/-! ## The guarantee -/

/-- Induction from the end of a closure. -/
theorem Star.head_induction {R : Term → Term → Prop} {b : Term} {P : Term → Prop}
    (hb : P b) (hstep : ∀ {a c}, R a c → Star R c b → P c → P a) {a : Term}
    (h : Star R a b) : P a := by
  revert hb hstep
  induction h with
  | refl => intro hb _; exact hb
  | @tail m b' _ hmb ih =>
    intro hb hstep
    exact ih (hstep hmb (.refl _) hb) (fun hac hcm hc => hstep hac (hcm.tail hmb) hc)

/-- A parallel step into a term from which the order reaches a normal form. -/
theorem par_sstar {n : Term} (hn : ¬ Red op n) {u : Term} (hu : Star (SStep op) u n) :
    ∀ {t}, WF t → Par op t u → Star (SStep op) t n := by
  refine Star.head_induction (P := fun u => ∀ {t}, WF t → Par op t u → Star (SStep op) t n)
    ?_ ?_ hu
  · intro t _ hp
    obtain ⟨t', hst, hip⟩ := hp.split
    have hnt : ¬ Red op t' := fun h => hn (hip.red h)
    rw [← hip.par.normal_eq hnt] at hst
    exact hst
  · intro u u₁ hs _ ih t hw hp
    obtain ⟨t', hst, hip⟩ := hp.split
    obtain ⟨t₂, hs₂, hp₂⟩ := hip.merge (hst.sstep_wf hw) hs
    exact hst.trans (Star.head hs₂ (ih ((hs₂.wf (hst.sstep_wf hw))) hp₂))

/-- The guarantee (6.4d): when a well-formed term reaches a normal form, the order reaches
it. -/
theorem guarantee {t n : Term} (hw : WF t) (h : Star (Step op) t n) (hn : ¬ Red op n) :
    Star (SStep op) t n := by
  refine Star.head_induction (P := fun t => WF t → Star (SStep op) t n) (fun _ => .refl _)
    ?_ h hw
  intro a c hac _ ih hwa
  exact par_sstar hn (ih (hac.wf hwa)) hwa hac.par

end Oymomo
