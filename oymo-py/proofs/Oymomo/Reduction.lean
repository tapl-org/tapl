-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Substitution

/-!
# Reduction

`Step op t t'` is `t ⟶ t'`: a computation rule anywhere in `t` (reduction
anywhere). `op` is the opcode table, left abstract: `op b s = some t` when `op(b)` is
defined on the operand `s`. E-Opcode reads it only when `s` is an opcode operand
(`isOperand`): a byte array, a struct of operands, or a closed lambda in normal form. An
operand never steps (`isNF_sound`), so an opcode may move, copy, drop or read its lambdas.
The result is any closed term (`OpOK`); it may hold lambdas and reduce further. Normal
forms are a syntactic test here (`isNF`, exactly the terms with no step: `isNF_iff`),
since a rule cannot ask for the absence of steps. E-Beta substitutes only a value. E-FixProj and E-FixApp unfold a
fixed point `fix (λx. t)` once, where it is projected or applied.

`Par op t t'` is parallel reduction: any set of redexes of `t` at once. It is the tool for
confluence (Tait and Martin-Löf).
-/

namespace Oymomo
open Term

/-- Reflexive-transitive closure. -/
inductive Star (R : Term → Term → Prop) : Term → Term → Prop
  | refl (t : Term) : Star R t t
  | tail {a b c : Term} : Star R a b → R b c → Star R a c

namespace Star

variable {R : Term → Term → Prop}

theorem single {a b : Term} (h : R a b) : Star R a b := tail (refl a) h

theorem trans {a b c : Term} (hab : Star R a b) (hbc : Star R b c) : Star R a c := by
  induction hbc with
  | refl => exact hab
  | tail _ h ih => exact tail ih h

theorem head {a b c : Term} (hab : R a b) (hbc : Star R b c) : Star R a c :=
  trans (single hab) hbc

/-- A closure goes through any context `f` that preserves single steps. -/
theorem map {S : Term → Term → Prop} (f : Term → Term) (hf : ∀ {a b}, R a b → S (f a) (f b))
    {a b : Term} (h : Star R a b) : Star S (f a) (f b) := by
  induction h with
  | refl => exact refl _
  | tail _ h ih => exact tail ih (hf h)

end Star

variable (op : Bytes → Term → Option Term)

/-- The root of `a u` is a redex: E-Beta, E-FixApp, E-Opcode (`ok` says that `u` is an
opcode operand), or E-Index and E-Default. -/
def appRedex (a u : Term) (ok : Bool) : Bool :=
  match a, u with
  | lam _, u => isValue u
  | fix (lam _), _ => true
  | bytes b, u => ok && (op b u).isSome
  | a, bytes n => (select a n.toNat).isSome
  | _, _ => false

mutual
  /-- Normal forms, by their syntax: no computation rule fires anywhere in the term. -/
  def isNF : Term → Bool
    | var _ => true
    | lam t => isNF t
    | app a u => isNF a && isNF u && !appRedex op a u (isOperand u)
    | snil => true
    | scons _ t r => isNF t && isNF r
    | proj s l => isNF s && (lookup s l).isNone && !isFixLam s
    | bytes _ => true
    | fix t => isNF t

  /-- Opcode operands `A`: a byte array, a struct of operands, or a closed lambda in normal
  form. -/
  def isOperand : Term → Bool
    | lam t => isNF t && closedAt 1 t
    | snil => true
    | scons _ t r => isOperand t && isOperand r
    | bytes _ => true
    | _ => false
end

/-- What the strategy and the proofs ask of the opcode table: every result is closed, so
substituting it captures no variable, and its struct chains end in `snil`. -/
structure OpOK : Prop where
  closed : ∀ {b : Bytes} {s r : Term}, op b s = some r → Oymomo.closed r
  wf : ∀ {b : Bytes} {s r : Term}, op b s = some r → WF r

/-- One step, `t ⟶ t'`. -/
inductive Step : Term → Term → Prop
  /-- E-Beta. -/
  | beta {t u : Term} : isValue u = true → Step (app (lam t) u) (subst (inst u) t)
  /-- E-Proj. -/
  | proj {s u : Term} {l : String} : lookup s l = some u → Step (proj s l) u
  /-- E-Index and E-Default. -/
  | index {s u : Term} {b : Bytes} : select s b.toNat = some u → Step (app s (bytes b)) u
  /-- E-Opcode. -/
  | opcode {s r : Term} {b : Bytes} :
      isOperand op s = true → op b s = some r → Step (app (bytes b) s) r
  /-- E-Abs. -/
  | lam {t t' : Term} : Step t t' → Step (lam t) (lam t')
  /-- E-App1. -/
  | app1 {a a' b : Term} : Step a a' → Step (app a b) (app a' b)
  /-- E-App2. -/
  | app2 {a b b' : Term} : Step b b' → Step (app a b) (app a b')
  /-- E-Struct, the first field. -/
  | scons1 {l : String} {t t' r : Term} : Step t t' → Step (scons l t r) (scons l t' r)
  /-- E-Struct, a later field. -/
  | scons2 {l : String} {t r r' : Term} : Step r r' → Step (scons l t r) (scons l t r')
  /-- E-Proj1. -/
  | proj1 {t t' : Term} {l : String} : Step t t' → Step (proj t l) (proj t' l)
  /-- E-FixProj. -/
  | fixProj {t : Term} {l : String} :
      Step (proj (fix (lam t)) l) (proj (subst (inst (fix (lam t))) t) l)
  /-- E-FixApp. -/
  | fixApp {t u : Term} : Step (app (fix (lam t)) u) (app (subst (inst (fix (lam t))) t) u)
  /-- E-Fix1. -/
  | fix {t t' : Term} : Step t t' → Step (fix t) (fix t')

/-- Parallel reduction. -/
inductive Par : Term → Term → Prop
  | var (n : Nat) : Par (var n) (var n)
  | bytes (b : Bytes) : Par (bytes b) (bytes b)
  | snil : Par snil snil
  | lam {t t' : Term} : Par t t' → Par (lam t) (lam t')
  | app {a a' b b' : Term} : Par a a' → Par b b' → Par (app a b) (app a' b')
  | scons {l : String} {t t' r r' : Term} : Par t t' → Par r r' → Par (scons l t r) (scons l t' r')
  | proj {t t' : Term} {l : String} : Par t t' → Par (proj t l) (proj t' l)
  | beta {t t' u u' : Term} :
      isValue u = true → Par t t' → Par u u' → Par (app (lam t) u) (subst (inst u') t')
  | projR {s u u' : Term} {l : String} : lookup s l = some u → Par u u' → Par (proj s l) u'
  | indexR {s u u' : Term} {b : Bytes} :
      select s b.toNat = some u → Par u u' → Par (app s (bytes b)) u'
  | opcodeR {s r : Term} {b : Bytes} :
      isOperand op s = true → op b s = some r → Par (app (bytes b) s) r
  | fix {t t' : Term} : Par t t' → Par (fix t) (fix t')
  | fixProjR {t t' : Term} {l : String} :
      Par t t' → Par (proj (fix (lam t)) l) (proj (subst (inst (fix (lam t'))) t') l)
  | fixAppR {t t' u u' : Term} :
      Par t t' → Par u u' → Par (app (fix (lam t)) u) (app (subst (inst (fix (lam t'))) t') u')

variable {op}

/-! ## Facts about the helpers -/

theorem lookup_ren {s u : Term} {l : String} (ξ : Nat → Nat) (h : lookup s l = some u) :
    lookup (ren ξ s) l = some (ren ξ u) := by
  induction s with
  | scons l' t r _ ihr =>
    simp only [lookup] at h
    simp only [ren, lookup]
    split
    · simp_all
    · simp_all
  | _ => simp [lookup] at h

theorem lookup_subst {s u : Term} {l : String} (σ : Nat → Term) (h : lookup s l = some u) :
    lookup (subst σ s) l = some (subst σ u) := by
  induction s with
  | scons l' t r _ ihr =>
    simp only [lookup] at h
    simp only [subst, lookup]
    split
    · simp_all
    · simp_all
  | _ => simp [lookup] at h

theorem select_scons_zero (l : String) (t r : Term) : select (scons l t r) 0 = some t := by
  cases r <;> rfl

theorem select_ren {s u : Term} {n : Nat} (ξ : Nat → Nat) (h : select s n = some u) :
    select (ren ξ s) n = some (ren ξ u) := by
  induction s generalizing n with
  | scons l t r _ ihr =>
    cases n with
    | zero =>
      rw [select_scons_zero] at h
      cases h
      simp only [ren]
      exact select_scons_zero _ _ _
    | succ n =>
      cases r with
      | snil => simp_all [select, ren]
      | scons l' t' r' => simp only [select, ren] at h ⊢; exact ihr h
      | _ => simp [select] at h
  | _ => simp [select] at h

theorem select_subst {s u : Term} {n : Nat} (σ : Nat → Term) (h : select s n = some u) :
    select (subst σ s) n = some (subst σ u) := by
  induction s generalizing n with
  | scons l t r _ ihr =>
    cases n with
    | zero =>
      rw [select_scons_zero] at h
      cases h
      simp only [subst]
      exact select_scons_zero _ _ _
    | succ n =>
      cases r with
      | snil => simp_all [select, subst]
      | scons l' t' r' => simp only [select, subst] at h ⊢; exact ihr h
      | _ => simp [select] at h
  | _ => simp [select] at h

theorem isValue_ren {v : Term} (ξ : Nat → Nat) (h : isValue v = true) :
    isValue (ren ξ v) = true := by
  induction v generalizing ξ with
  | scons l t r iht ihr =>
    simp only [isValue, Bool.and_eq_true] at h
    simp [ren, isValue, iht _ h.1, ihr _ h.2]
  | fix x _ => cases x <;> simp_all [isValue, ren]
  | _ => simp_all [isValue, ren]

/-- A substitution of values. -/
def ValSub (σ : Nat → Term) : Prop := ∀ n, isValue (σ n) = true

theorem ValSub.ups {σ : Nat → Term} (h : ValSub σ) : ValSub (ups σ)
  | 0 => rfl
  | n + 1 => isValue_ren _ (h n)

theorem ValSub.inst {u : Term} (h : isValue u = true) : ValSub (inst u)
  | 0 => h
  | _ + 1 => rfl

/-- Substituting values into a value gives a value. -/
theorem isValue_subst {v : Term} {σ : Nat → Term} (hσ : ValSub σ) (h : isValue v = true) :
    isValue (subst σ v) = true := by
  induction v generalizing σ with
  | var n => exact hσ n
  | scons l t r iht ihr =>
    simp only [isValue, Bool.and_eq_true] at h
    simp [subst, isValue, iht hσ h.1, ihr hσ h.2]
  | fix x _ => cases x <;> simp_all [isValue, subst]
  | _ => simp_all [isValue, subst]

/-- Data has no variables. -/
theorem ren_data {s : Term} (ξ : Nat → Nat) (h : isData s = true) : ren ξ s = s := by
  induction s with
  | scons l t r iht ihr =>
    simp only [isData, Bool.and_eq_true] at h
    simp [ren, iht h.1, ihr h.2]
  | _ => simp_all [isData, ren]

theorem subst_data {s : Term} (σ : Nat → Term) (h : isData s = true) : subst σ s = s := by
  induction s with
  | scons l t r iht ihr =>
    simp only [isData, Bool.and_eq_true] at h
    simp [subst, iht h.1, ihr h.2]
  | _ => simp_all [isData, subst]

/-! ## Parallel reduction -/

theorem Par.refl : ∀ t : Term, Par op t t
  | .var n => .var n
  | .lam t => .lam (Par.refl t)
  | .app a b => .app (Par.refl a) (Par.refl b)
  | .snil => .snil
  | .scons _ t r => .scons (Par.refl t) (Par.refl r)
  | .proj t _ => .proj (Par.refl t)
  | .bytes b => .bytes b
  | .fix t => .fix (Par.refl t)

/-- Values stay values. -/
theorem Par.value {v v' : Term} (h : Par op v v') (hv : isValue v = true) : isValue v' = true := by
  induction h with
  | scons _ _ iht ihr =>
    simp only [isValue, Bool.and_eq_true] at hv ⊢
    exact ⟨iht hv.1, ihr hv.2⟩
  | fix h _ => cases h <;> first | rfl | simp [isValue] at hv
  | _ => first | rfl | exact absurd hv Bool.false_ne_true

theorem Step.par {t t' : Term} (h : Step op t t') : Par op t t' := by
  induction h with
  | beta hu => exact .beta hu (.refl _) (.refl _)
  | proj h => exact .projR h (.refl _)
  | index h => exact .indexR h (.refl _)
  | opcode h1 h2 => exact .opcodeR h1 h2
  | lam _ ih => exact .lam ih
  | app1 _ ih => exact .app ih (.refl _)
  | app2 _ ih => exact .app (.refl _) ih
  | scons1 _ ih => exact .scons ih (.refl _)
  | scons2 _ ih => exact .scons (.refl _) ih
  | proj1 _ ih => exact .proj ih
  | fixProj => exact .fixProjR (.refl _)
  | fixApp => exact .fixAppR (.refl _) (.refl _)
  | fix _ ih => exact .fix ih

theorem Par.star {t t' : Term} (h : Par op t t') : Star (Step op) t t' := by
  induction h with
  | var => exact .refl _
  | bytes => exact .refl _
  | snil => exact .refl _
  | lam _ ih => exact Star.map Term.lam (fun h => Step.lam h) ih
  | @app a a' b b' _ _ iha ihb =>
    exact (Star.map (fun x => Term.app x b) (fun h => Step.app1 h) iha).trans
      (Star.map (Term.app a') (fun h => Step.app2 h) ihb)
  | @scons l t t' r r' _ _ iht ihr =>
    exact (Star.map (fun x => Term.scons l x r) (fun h => Step.scons1 h) iht).trans
      (Star.map (Term.scons l t') (fun h => Step.scons2 h) ihr)
  | @proj t t' l _ ih => exact Star.map (fun x => Term.proj x l) (fun h => Step.proj1 h) ih
  | @beta t t' u u' hu _ huu iht ihu =>
    have h1 := Star.map (fun x => Term.app (Term.lam x) u) (fun h => Step.app1 (Step.lam h)) iht
    have h2 := Star.map (Term.app (Term.lam t')) (fun h => Step.app2 h) ihu
    exact (h1.trans h2).tail (Step.beta (huu.value hu))
  | projR h _ ih => exact Star.head (Step.proj h) ih
  | indexR h _ ih => exact Star.head (Step.index h) ih
  | opcodeR h1 h2 => exact Star.single (Step.opcode h1 h2)
  | fix _ ih => exact Star.map Term.fix (fun h => Step.fix h) ih
  | @fixProjR t t' l _ ih =>
    exact (Star.map (fun x => Term.proj (Term.fix (Term.lam x)) l)
      (fun h => Step.proj1 (Step.fix (Step.lam h))) ih).tail Step.fixProj
  | @fixAppR t t' u u' _ _ iht ihu =>
    have h1 := Star.map (fun x => Term.app (Term.fix (Term.lam x)) u)
      (fun h => Step.app1 (Step.fix (Step.lam h))) iht
    have h2 := Star.map (Term.app (Term.fix (Term.lam t'))) (fun h => Step.app2 h) ihu
    exact (h1.trans h2).tail Step.fixApp

/-- Data never steps. -/
theorem Par.data {s s' : Term} (h : Par op s s') (hd : isData s = true) : s' = s := by
  induction h with
  | bytes => rfl
  | snil => rfl
  | scons _ _ iht ihr =>
    simp only [isData, Bool.and_eq_true] at hd
    rw [iht hd.1, ihr hd.2]
  | _ => simp_all [isData]

theorem Par.isStruct {s s' : Term} (h : Par op s s') (hs : isStruct s = true) :
    isStruct s' = true := by
  cases h <;> first | rfl | exact absurd hs Bool.false_ne_true

theorem lookup_par {s s' u : Term} {l : String} (h : Par op s s') (hl : lookup s l = some u) :
    ∃ u', lookup s' l = some u' ∧ Par op u u' := by
  induction h generalizing u with
  | @scons l' t t' r r' ht _ _ ihr =>
    simp only [lookup] at hl ⊢
    split
    · simp_all
    · simp_all
  | _ => simp [lookup] at hl

theorem select_par {s s' u : Term} {n : Nat} (h : Par op s s') (hl : select s n = some u) :
    ∃ u', select s' n = some u' ∧ Par op u u' := by
  induction h generalizing u n with
  | @scons l t t' r r' ht hr _ ihr =>
    cases n with
    | zero =>
      rw [select_scons_zero] at hl
      cases hl
      exact ⟨t', select_scons_zero _ _ _, ht⟩
    | succ n =>
      cases hr with
      | snil =>
        simp only [select, Option.some.injEq] at hl ⊢
        subst hl
        exact ⟨t', rfl, ht⟩
      | scons _ _ => simp only [select] at hl ⊢; exact ihr hl
      | _ => simp [select] at hl
  | _ => simp [select] at hl

/-! ## Normal forms and operands -/

theorem isNF_app {a u : Term} :
    isNF op (app a u) = (isNF op a && isNF op u && !appRedex op a u (isOperand op u)) := by
  simp [isNF]

theorem isOperand_isNF {s : Term} (h : isOperand op s = true) : isNF op s = true := by
  induction s with
  | lam t _ => simp only [isOperand, Bool.and_eq_true] at h; simp [isNF, h.1]
  | scons l t r iht ihr =>
    simp only [isOperand, Bool.and_eq_true] at h
    simp [isNF, iht h.1, ihr h.2]
  | snil => simp [isNF]
  | bytes => simp [isNF]
  | _ => simp [isOperand] at h

/-- An operand is closed. -/
theorem isOperand_closed {s : Term} (h : isOperand op s = true) : closed s := by
  induction s with
  | lam t _ => simp only [isOperand, Bool.and_eq_true] at h; exact h.2
  | scons l t r iht ihr =>
    simp only [isOperand, Bool.and_eq_true] at h
    have h1 := iht h.1
    have h2 := ihr h.2
    simp only [closed, closedAt, Bool.and_eq_true] at h1 h2 ⊢
    exact ⟨h1, h2⟩
  | snil => rfl
  | bytes => rfl
  | _ => simp [isOperand] at h

/-- A redex at the root of an application is a step. -/
theorem appRedex_step {a u : Term} (h : appRedex op a u (isOperand op u) = true) :
    ∃ t', Step op (app a u) t' := by
  unfold appRedex at h
  split at h
  · exact ⟨_, .beta h⟩
  · exact ⟨_, .fixApp⟩
  · simp only [Bool.and_eq_true, Option.isSome_iff_exists] at h
    obtain ⟨h1, _, h2⟩ := h
    exact ⟨_, .opcode h1 h2⟩
  · obtain ⟨_, hs⟩ := Option.isSome_iff_exists.mp h
    exact ⟨_, .index hs⟩
  · cases h

/-- A normal form has no step. -/
theorem isNF_sound {t t' : Term} (h : isNF op t = true) : ¬ Step op t t' := by
  intro hs
  induction hs with
  | beta hu => simp [isNF_app, appRedex, hu] at h
  | proj hl => simp [isNF, hl] at h
  | @index s _ b hsel =>
    rw [isNF_app] at h
    cases s with
    | fix x => cases x <;> simp_all [select]
    | _ => simp_all [appRedex, select]
  | opcode h1 h2 => simp [isNF_app, appRedex, h1, h2] at h
  | lam _ ih => exact ih (by simpa [isNF] using h)
  | app1 _ ih => simp only [isNF_app, Bool.and_eq_true] at h; exact ih h.1.1
  | app2 _ ih => simp only [isNF_app, Bool.and_eq_true] at h; exact ih h.1.2
  | scons1 _ ih => simp only [isNF, Bool.and_eq_true] at h; exact ih h.1
  | scons2 _ ih => simp only [isNF, Bool.and_eq_true] at h; exact ih h.2
  | proj1 _ ih => simp only [isNF, Bool.and_eq_true] at h; exact ih h.1.1
  | fixProj => simp [isNF, isFixLam] at h
  | fixApp => simp [isNF_app, appRedex] at h
  | fix _ ih => exact ih (by simpa [isNF] using h)

/-- A term with no step is a normal form. -/
theorem isNF_complete : ∀ {t : Term}, (∀ t', ¬ Step op t t') → isNF op t = true
  | var _, _ => by simp [isNF]
  | snil, _ => by simp [isNF]
  | bytes _, _ => by simp [isNF]
  | lam t, h => by
    simp only [isNF]
    exact isNF_complete fun t' ht => h _ (.lam ht)
  | fix t, h => by
    simp only [isNF]
    exact isNF_complete fun t' ht => h _ (.fix ht)
  | scons l t r, h => by
    simp only [isNF, Bool.and_eq_true]
    exact ⟨isNF_complete fun t' ht => h _ (.scons1 ht),
      isNF_complete fun r' hr => h _ (.scons2 hr)⟩
  | proj s l, h => by
    simp only [isNF, Bool.and_eq_true, Bool.not_eq_true']
    refine ⟨⟨isNF_complete fun s' hs => h _ (.proj1 hs), ?_⟩, ?_⟩
    · cases hl : lookup s l with
      | none => rfl
      | some u => exact absurd (Step.proj hl) (h _)
    · cases s with
      | fix x =>
        cases x with
        | lam t => exact absurd Step.fixProj (h _)
        | _ => rfl
      | _ => rfl
  | app a u, h => by
    rw [isNF_app]
    simp only [Bool.and_eq_true, Bool.not_eq_true']
    refine ⟨⟨isNF_complete fun a' ha => h _ (.app1 ha),
      isNF_complete fun u' hu => h _ (.app2 hu)⟩, ?_⟩
    cases hr : appRedex op a u (isOperand op u) with
    | false => rfl
    | true =>
      obtain ⟨_, hs⟩ := appRedex_step hr
      exact absurd hs (h _)

/-- `isNF` is exactly the normal forms. -/
theorem isNF_iff {t : Term} : isNF op t = true ↔ ∀ t', ¬ Step op t t' :=
  ⟨fun h _ => isNF_sound h, isNF_complete⟩

/-- A normal form has no parallel step but itself. -/
theorem Par.nf_eq {t u : Term} (h : Par op t u) (hn : isNF op t = true) : u = t := by
  induction h with
  | var => rfl
  | bytes => rfl
  | snil => rfl
  | lam _ ih => rw [ih (by simpa [isNF] using hn)]
  | app _ _ iha ihb =>
    simp only [isNF_app, Bool.and_eq_true] at hn
    rw [iha hn.1.1, ihb hn.1.2]
  | scons _ _ iht ihr =>
    simp only [isNF, Bool.and_eq_true] at hn
    rw [iht hn.1, ihr hn.2]
  | proj _ ih =>
    simp only [isNF, Bool.and_eq_true] at hn
    rw [ih hn.1.1]
  | beta hu _ _ _ _ => exact absurd (Step.beta hu) (isNF_sound hn)
  | projR hl _ _ => exact absurd (Step.proj hl) (isNF_sound hn)
  | indexR hs _ _ => exact absurd (Step.index hs) (isNF_sound hn)
  | opcodeR h1 h2 => exact absurd (Step.opcode h1 h2) (isNF_sound hn)
  | fix _ ih => rw [ih (by simpa [isNF] using hn)]
  | fixProjR _ _ => exact absurd Step.fixProj (isNF_sound hn)
  | fixAppR _ _ _ _ => exact absurd Step.fixApp (isNF_sound hn)

/-- An operand never steps. -/
theorem Par.operand {s s' : Term} (h : Par op s s') (hs : isOperand op s = true) : s' = s :=
  h.nf_eq (isOperand_isNF hs)

end Oymomo
