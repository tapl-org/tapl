-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Reduction

/-!
# Sharing normal order (semantics.tex, Section 6)

`StepS op t t'` is `t ▷ₛ t'`. Each constructor is one row of the table (rows 5 to 20). A row
holds only when no earlier row's shape matches, so each constructor also says that the
earlier rows don't apply; the document gets this from "rows are tried top to bottom" (6/21).

The four forms of 6/1 to 6/4:

* `isAtom a`: `a ::= d | x.l₁⋯lₙ` (form 1); `isPath` is `x.l₁⋯lₙ`, an atom that is not data.
* `isRunTime op r` (form 2): a run-time operation `b {lᵢ = aᵢ}` (E-Opcode does not fire), a
  run-time branch `{lᵢ = aᵢ} a` (`0 < k`, `a` not data), or a call `a {lᵢ = aᵢ}` (`a` not
  data).
* A shared `let` (form 3) is `(λx. t) r`.
* `W t`: every redex in `t` is a shared `let` (form 4). A redex that is not a shared `let`
  is a step of `UStep`: a rule of Section 2 anywhere, with E-Beta only on an argument that
  is not a run-time term. So `W t` says `t` has no `UStep` step.

A struct is a `scons` chain (see `Syntax.lean`): row 20, "the first field not in `w`", is
the head field when it is not in `W`, otherwise a step in the tail.

Results:

* `StepS.step`: each `▷ₛ` step is a `▷` step (6/26).
* `StepS.det`: `▷ₛ` is deterministic (6/26).
* `StepS.not_W`: a term in `w` has no `▷ₛ` step, and `progress`: every term is in `w` or
  has a `▷ₛ` step (6/21).
-/

namespace Oymomo
open Term

/-- A path `x.l₁⋯lₙ`. -/
def isPath : Term → Bool
  | var _ => true
  | proj p _ => isPath p
  | _ => false

/-- An atom `a ::= d | x.l₁⋯lₙ` (form 1). -/
def isAtom (t : Term) : Bool := isData t || isPath t

/-- A struct whose fields are atoms, `{lᵢ = aᵢ}`. -/
def atomFields : Term → Bool
  | snil => true
  | scons _ t r => isAtom t && atomFields r
  | _ => false

/-- A struct with at least one field. -/
def isCons : Term → Bool
  | scons _ _ _ => true
  | _ => false

/-- An abstraction. -/
def isLam : Term → Bool
  | lam _ => true
  | _ => false

/-- E-Opcode fires on `b u`. -/
def opFires (op : Bytes → Term → Option Bytes) (b : Bytes) (u : Term) : Bool :=
  isStruct u && isData u && (op b u).isSome

/-- E-Index or E-Default fires on `s u`. -/
def indexFires (s : Term) : Term → Bool
  | bytes b => (select s b.toNat).isSome
  | _ => false

/-- A head that is not an abstraction, a struct or a byte array: rows 17 and 18 are the
only rows for an application with this head. -/
def isPlain : Term → Bool
  | var _ => true
  | app _ _ => true
  | proj _ _ => true
  | sapp _ _ => true
  | _ => false

variable (op : Bytes → Term → Option Bytes)

/-- A run-time term `r` (form 2). -/
def isRunTime : Term → Bool
  | app (bytes b) s => atomFields s && !opFires op b s
  | app f c => (isCons f && atomFields f && isPath c) || (isPath f && atomFields c)
  | _ => false

/-- A step of a redex that is not a shared `let`: `Step` with E-Beta only on an argument
that is not a run-time term. -/
inductive UStep : Term → Term → Prop
  | beta (t u : Term) : isRunTime op u = false → UStep (app (lam t) u) (subst (inst u) t)
  | proj {s u : Term} {l : String} : lookup s l = some u → UStep (proj s l) u
  | index {s u : Term} {b : Bytes} : select s b.toNat = some u → UStep (app s (bytes b)) u
  | opcode {s : Term} {b b' : Bytes} :
      isStruct s = true → isData s = true → op b s = some b' → UStep (app (bytes b) s) (bytes b')
  | strict {t v : Term} : isValue v = true → UStep (sapp t v) (app t v)
  | lam {t t' : Term} : UStep t t' → UStep (lam t) (lam t')
  | app1 {a a' b : Term} : UStep a a' → UStep (app a b) (app a' b)
  | app2 {a b b' : Term} : UStep b b' → UStep (app a b) (app a b')
  | scons1 {l : String} {t t' r : Term} : UStep t t' → UStep (scons l t r) (scons l t' r)
  | scons2 {l : String} {t r r' : Term} : UStep r r' → UStep (scons l t r) (scons l t r')
  | proj1 {t t' : Term} {l : String} : UStep t t' → UStep (proj t l) (proj t' l)
  | sapp1 {a a' b : Term} : UStep a a' → UStep (sapp a b) (sapp a' b)
  | sapp2 {a b b' : Term} : UStep b b' → UStep (sapp a b) (sapp a b')

/-- `w` (form 4): every redex is a shared `let`. -/
def W (t : Term) : Prop := ∀ t', ¬ UStep op t t'

/-- `t ▷ₛ t'`, one constructor per row. -/
inductive StepS : Term → Term → Prop
  /-- Row 5: `(λx. t₁) r`, the body of a shared `let`. -/
  | letBody {t t' u : Term} : isRunTime op u = true → StepS t t' →
      StepS (app (lam t) u) (app (lam t') u)
  /-- Row 6: `(λx. t₁) t₂`, E-Beta. -/
  | beta (t u : Term) : isRunTime op u = false → StepS (app (lam t) u) (subst (inst u) t)
  /-- Row 7: `t !v`, E-Strict. -/
  | strict {t v : Term} : isValue v = true → StepS (sapp t v) (app t v)
  /-- Row 8: `t₁ !w`, the head. -/
  | sappHead {a a' u : Term} : isValue u = false → W op u → StepS a a' →
      StepS (sapp a u) (sapp a' u)
  /-- Row 9: `t₁ !t₂`, the argument. -/
  | sappArg {a u u' : Term} : isValue u = false → ¬ W op u → StepS u u' →
      StepS (sapp a u) (sapp a u')
  /-- Row 10: `{…}.l`, E-Proj. -/
  | proj {s u : Term} {l : String} : lookup s l = some u → StepS (proj s l) u
  /-- Row 11: `t.l`, the struct. -/
  | projIn {s s' : Term} {l : String} : lookup s l = none → StepS s s' →
      StepS (proj s l) (proj s' l)
  /-- Rows 12 and 13: `{…} b`, E-Index and E-Default. -/
  | index {s u : Term} {b : Bytes} : select s b.toNat = some u → StepS (app s (bytes b)) u
  /-- Row 14: `b {lᵢ = dᵢ}`, E-Opcode. -/
  | opcode {s : Term} {b b' : Bytes} :
      isStruct s = true → isData s = true → op b s = some b' → StepS (app (bytes b) s) (bytes b')
  /-- Row 15: `{…} w`, the arms. -/
  | arms {s s' u : Term} : isStruct s = true → indexFires s u = false → W op u → StepS s s' →
      StepS (app s u) (app s' u)
  /-- Row 16: `{…} t₂`, the condition. -/
  | cond {s u u' : Term} : isStruct s = true → ¬ W op u → StepS u u' →
      StepS (app s u) (app s u')
  /-- Row 17 with a byte array head: `b t₂`, the operands. -/
  | operands {u u' : Term} {b : Bytes} : opFires op b u = false → StepS u u' →
      StepS (app (bytes b) u) (app (bytes b) u')
  /-- Row 17: `w t₂`, the argument. -/
  | arg {a u u' : Term} : isPlain a = true → W op a → StepS u u' → StepS (app a u) (app a u')
  /-- Row 18: `t₁ t₂`, the head. -/
  | head {a a' u : Term} : isPlain a = true → ¬ W op a → StepS a a' →
      StepS (app a u) (app a' u)
  /-- Row 19: `λx. t`, the body. -/
  | lam {t t' : Term} : StepS t t' → StepS (lam t) (lam t')
  /-- Row 20: a struct, its first field when that is not in `w`. -/
  | field {l : String} {t t' r : Term} : ¬ W op t → StepS t t' →
      StepS (scons l t r) (scons l t' r)
  /-- Row 20: a later field, when the first is in `w`. -/
  | rest {l : String} {t r r' : Term} : W op t → StepS r r' →
      StepS (scons l t r) (scons l t r')

variable {op}

/-! ## Each `▷ₛ` step is a `▷` step -/

theorem UStep.step {t t' : Term} (h : UStep op t t') : Step op t t' := by
  induction h with
  | beta t u _ => exact .beta t u
  | proj h => exact .proj h
  | index h => exact .index h
  | opcode h1 h2 h3 => exact .opcode h1 h2 h3
  | strict h => exact .strict h
  | lam _ ih => exact .lam ih
  | app1 _ ih => exact .app1 ih
  | app2 _ ih => exact .app2 ih
  | scons1 _ ih => exact .scons1 ih
  | scons2 _ ih => exact .scons2 ih
  | proj1 _ ih => exact .proj1 ih
  | sapp1 _ ih => exact .sapp1 ih
  | sapp2 _ ih => exact .sapp2 ih

/-- A `▷ₛ` step never contracts a shared `let`. -/
theorem StepS.ustep {t t' : Term} (h : StepS op t t') : UStep op t t' := by
  induction h with
  | beta t u hu => exact .beta t u hu
  | letBody _ _ ih => exact .app1 (.lam ih)
  | strict h => exact .strict h
  | sappHead _ _ _ ih => exact .sapp1 ih
  | sappArg _ _ _ ih => exact .sapp2 ih
  | proj h => exact .proj h
  | projIn _ _ ih => exact .proj1 ih
  | index h => exact .index h
  | opcode h1 h2 h3 => exact .opcode h1 h2 h3
  | arms _ _ _ _ ih => exact .app1 ih
  | cond _ _ _ ih => exact .app2 ih
  | operands _ _ ih => exact .app2 ih
  | arg _ _ _ ih => exact .app2 ih
  | head _ _ _ ih => exact .app1 ih
  | lam _ ih => exact .lam ih
  | field _ _ ih => exact .scons1 ih
  | rest _ _ ih => exact .scons2 ih

/-- 6/26: each `▷ₛ` step is a `▷` step. -/
theorem StepS.step {t t' : Term} (h : StepS op t t') : Step op t t' := h.ustep.step

/-- 6/21: a term in `w` has no `▷ₛ` step. -/
theorem StepS.not_W {t t' : Term} (h : StepS op t t') : ¬ W op t := fun hw => hw _ h.ustep

/-! ## Determinism -/

theorem W_bytes (b : Bytes) : W op (bytes b) := fun _ h => nomatch h

theorem plain_not_struct {s : Term} (hp : isPlain s = true) (hs : isStruct s = true) : False := by
  cases s <;> simp_all [isPlain, isStruct]

theorem select_isStruct {s u : Term} {n : Nat} (h : select s n = some u) : isStruct s = true := by
  cases s <;> simp_all [select, isStruct]

/-- 6/26: `▷ₛ` is deterministic. -/
theorem StepS.det {t t₁ t₂ : Term} (h₁ : StepS op t t₁) (h₂ : StepS op t t₂) : t₁ = t₂ := by
  induction h₁ generalizing t₂ with
  | beta t u hu =>
    cases h₂ with
    | beta => rfl
    | letBody hu' => simp_all
    | arms hs => simp [isStruct] at hs
    | cond hs => simp [isStruct] at hs
    | arg hp => simp [isPlain] at hp
    | head hp => simp [isPlain] at hp
    | index h => simp [select] at h
  | letBody hu _ ih =>
    cases h₂ with
    | beta _ _ hu' => simp_all
    | letBody _ h => rw [ih h]
    | arms hs => simp [isStruct] at hs
    | cond hs => simp [isStruct] at hs
    | arg hp => simp [isPlain] at hp
    | head hp => simp [isPlain] at hp
    | index h => simp [select] at h
  | strict hv =>
    cases h₂ with
    | strict => rfl
    | sappHead hv' => simp_all
    | sappArg hv' => simp_all
  | sappHead hv hw _ ih =>
    cases h₂ with
    | strict hv' => simp_all
    | sappHead _ _ h => rw [ih h]
    | sappArg _ hw' => exact absurd hw hw'
  | sappArg hv hw _ ih =>
    cases h₂ with
    | strict hv' => simp_all
    | sappHead _ hw' => exact absurd hw' hw
    | sappArg _ _ h => rw [ih h]
  | proj h =>
    cases h₂ with
    | proj h' => simp_all
    | projIn h' => simp_all
  | projIn h _ ih =>
    cases h₂ with
    | proj h' => simp_all
    | projIn _ h' => rw [ih h']
  | index h =>
    cases h₂ with
    | index h' => simp_all
    | beta => simp [select] at h
    | letBody => simp [select] at h
    | arms _ hi => simp_all [indexFires]
    | cond _ hw => exact absurd (W_bytes _) hw
    | operands => simp [select] at h
    | arg hp => exact (plain_not_struct hp (select_isStruct h)).elim
    | head hp => exact (plain_not_struct hp (select_isStruct h)).elim
    | opcode => simp [select] at h
  | opcode h1 h2 h3 =>
    cases h₂ with
    | opcode _ _ h3' => simp_all
    | operands hf => simp_all [opFires]
    | index h => simp [select] at h
    | arms hs => simp [isStruct] at hs
    | cond hs => simp [isStruct] at hs
    | arg hp => simp [isPlain] at hp
    | head hp => simp [isPlain] at hp
  | arms hs hi hw _ ih =>
    cases h₂ with
    | arms _ _ _ h => rw [ih h]
    | cond _ hw' => exact absurd hw hw'
    | index h => simp_all [indexFires]
    | beta => simp [isStruct] at hs
    | letBody => simp [isStruct] at hs
    | opcode => simp [isStruct] at hs
    | operands => simp [isStruct] at hs
    | arg hp => exact (plain_not_struct hp hs).elim
    | head hp => exact (plain_not_struct hp hs).elim
  | cond hs hw _ ih =>
    cases h₂ with
    | cond _ _ h => rw [ih h]
    | arms _ _ hw' => exact absurd hw' hw
    | index => exact absurd (W_bytes _) hw
    | beta => simp [isStruct] at hs
    | letBody => simp [isStruct] at hs
    | opcode => simp [isStruct] at hs
    | operands => simp [isStruct] at hs
    | arg hp => exact (plain_not_struct hp hs).elim
    | head hp => exact (plain_not_struct hp hs).elim
  | operands hf _ ih =>
    cases h₂ with
    | operands _ h => rw [ih h]
    | opcode h1 h2 h3 => simp_all [opFires]
    | index h => simp [select] at h
    | arms hs => simp [isStruct] at hs
    | cond hs => simp [isStruct] at hs
    | arg hp => simp [isPlain] at hp
    | head hp => simp [isPlain] at hp
  | arg hp hw _ ih =>
    cases h₂ with
    | arg _ _ h => rw [ih h]
    | head _ hw' => exact absurd hw hw'
    | beta => simp [isPlain] at hp
    | letBody => simp [isPlain] at hp
    | opcode => simp [isPlain] at hp
    | operands => simp [isPlain] at hp
    | index h => exact (plain_not_struct hp (select_isStruct h)).elim
    | arms hs => exact (plain_not_struct hp hs).elim
    | cond hs => exact (plain_not_struct hp hs).elim
  | head hp hw _ ih =>
    cases h₂ with
    | head _ _ h => rw [ih h]
    | arg _ hw' => exact absurd hw' hw
    | beta => simp [isPlain] at hp
    | letBody => simp [isPlain] at hp
    | opcode => simp [isPlain] at hp
    | operands => simp [isPlain] at hp
    | index h => exact (plain_not_struct hp (select_isStruct h)).elim
    | arms hs => exact (plain_not_struct hp hs).elim
    | cond hs => exact (plain_not_struct hp hs).elim
  | lam _ ih =>
    cases h₂ with
    | lam h => rw [ih h]
  | field hw _ ih =>
    cases h₂ with
    | field _ h => rw [ih h]
    | rest hw' => exact absurd hw' hw
  | rest hw _ ih =>
    cases h₂ with
    | field hw' => exact absurd hw hw'
    | rest _ h => rw [ih h]

/-! ## Progress: every term is in `w` or has a `▷ₛ` step -/

theorem data_W {s : Term} (h : isData s = true) : W op s := by
  induction s with
  | scons l t r iht ihr =>
    simp only [isData, Bool.and_eq_true] at h
    intro _ hs
    cases hs with
    | scons1 hs => exact iht h.1 _ hs
    | scons2 hs => exact ihr h.2 _ hs
  | bytes b => exact W_bytes b
  | snil => exact fun _ h => nomatch h
  | _ => simp [isData] at h

theorem path_W {p : Term} (h : isPath p = true) : W op p := by
  induction p with
  | var n => exact fun _ h => nomatch h
  | proj p l ih =>
    simp only [isPath] at h
    intro _ hs
    cases hs with
    | proj hl => cases p <;> simp_all [lookup, isPath]
    | proj1 hs => exact ih h _ hs
  | _ => simp [isPath] at h

theorem atom_W {a : Term} (h : isAtom a = true) : W op a := by
  simp only [isAtom, Bool.or_eq_true] at h
  rcases h with h | h
  · exact data_W h
  · exact path_W h

theorem atomFields_W {s : Term} (h : atomFields s = true) : W op s := by
  induction s with
  | snil => exact fun _ h => nomatch h
  | scons l t r _ ihr =>
    simp only [atomFields, Bool.and_eq_true] at h
    intro _ hs
    cases hs with
    | scons1 hs => exact atom_W h.1 _ hs
    | scons2 hs => exact ihr h.2 _ hs
  | _ => simp [atomFields] at h

theorem path_not_bytes {p : Term} {b : Bytes} (h : isPath p = true) : p ≠ bytes b := by
  rintro rfl; simp [isPath] at h

/-- A run-time term is in `w`: substituting it is never needed for a step inside it. -/
theorem runTime_W {u : Term} (h : isRunTime op u = true) : W op u := by
  cases u with
  | app f c =>
    cases f with
    | bytes b =>
      simp only [isRunTime, Bool.and_eq_true, Bool.not_eq_true'] at h
      intro _ hs
      cases hs with
      | opcode h1 h2 h3 => simp_all [opFires]
      | app1 hs => exact nomatch hs
      | app2 hs => exact atomFields_W h.1 _ hs
      | index hs => simp [select] at hs
    | scons l t r =>
      have h' : atomFields (scons l t r) = true ∧ isPath c = true := by
        simpa [isRunTime, isCons, isPath] using h
      intro _ hs
      cases hs with
      | index hs => simp [isPath] at h'
      | app1 hs => exact atomFields_W h'.1 _ hs
      | app2 hs => exact path_W h'.2 _ hs
    | var n =>
      simp only [isRunTime, isCons, Bool.false_and, isPath, Bool.true_and, Bool.false_or] at h
      intro _ hs
      cases hs with
      | index hs => simp [select] at hs
      | app1 hs => exact nomatch hs
      | app2 hs => exact atomFields_W h _ hs
    | proj p l =>
      simp only [isRunTime, isCons, Bool.false_and, Bool.false_or, Bool.and_eq_true] at h
      intro _ hs
      cases hs with
      | index hs => simp [select] at hs
      | app1 hs => exact path_W (p := proj p l) h.1 _ hs
      | app2 hs => exact atomFields_W h.2 _ hs
    | _ => simp [isRunTime, isCons, isPath] at h
  | _ => simp [isRunTime] at h

/-- 6/21: every term not in `w` has a `▷ₛ` step. -/
theorem progress (t : Term) : W op t ∨ ∃ t', StepS op t t' := by
  induction t with
  | var n => exact .inl fun _ h => nomatch h
  | bytes b => exact .inl (W_bytes b)
  | snil => exact .inl fun _ h => nomatch h
  | lam t ih =>
    rcases ih with hw | ⟨t', h⟩
    · exact .inl fun _ h => by cases h with | lam h => exact hw _ h
    · exact .inr ⟨_, .lam h⟩
  | scons l t r iht ihr =>
    rcases iht with hwt | ⟨t', ht⟩
    · rcases ihr with hwr | ⟨r', hr⟩
      · exact .inl fun _ h => by
          cases h with
          | scons1 h => exact hwt _ h
          | scons2 h => exact hwr _ h
      · exact .inr ⟨_, .rest hwt hr⟩
    · exact .inr ⟨_, .field ht.not_W ht⟩
  | proj s l ih =>
    cases hl : lookup s l with
    | some u => exact .inr ⟨_, .proj hl⟩
    | none =>
      rcases ih with hw | ⟨s', h⟩
      · exact .inl fun _ h => by
          cases h with
          | proj h => simp_all
          | proj1 h => exact hw _ h
      · exact .inr ⟨_, .projIn hl h⟩
  | sapp a u iha ihu =>
    cases hv : isValue u with
    | true => exact .inr ⟨_, .strict hv⟩
    | false =>
      rcases ihu with hwu | ⟨u', hu⟩
      · rcases iha with hwa | ⟨a', ha⟩
        · exact .inl fun _ h => by
            cases h with
            | strict h => simp_all
            | sapp1 h => exact hwa _ h
            | sapp2 h => exact hwu _ h
        · exact .inr ⟨_, .sappHead hv hwu ha⟩
      · exact .inr ⟨_, .sappArg hv hu.not_W hu⟩
  | app a u iha ihu =>
    cases a with
    | lam t =>
      cases hc : isRunTime op u with
      | false => exact .inr ⟨_, .beta t u hc⟩
      | true =>
        rcases iha with hwa | ⟨a', ha⟩
        · exact .inl fun _ h => by
            cases h with
            | beta _ _ h => simp_all
            | app1 h => exact hwa _ h
            | app2 h => exact runTime_W hc _ h
            | index h => simp [select] at h
        · cases ha with
          | lam ht => exact .inr ⟨_, .letBody hc ht⟩
    | bytes b =>
      cases hf : opFires op b u with
      | true =>
        simp only [opFires, Bool.and_eq_true, Option.isSome_iff_exists] at hf
        obtain ⟨⟨hs, hd⟩, b', hb⟩ := hf
        exact .inr ⟨_, .opcode hs hd hb⟩
      | false =>
        rcases ihu with hwu | ⟨u', hu⟩
        · exact .inl fun _ h => by
            cases h with
            | opcode h1 h2 h3 => simp_all [opFires]
            | app1 h => exact nomatch h
            | app2 h => exact hwu _ h
            | index h => simp [select] at h
        · exact .inr ⟨_, .operands hf hu⟩
    | snil =>
      rcases ihu with hwu | ⟨u', hu⟩
      · rcases iha with hwa | ⟨a', ha⟩
        · exact .inl fun _ h => by
            cases h with
            | index h => simp [select] at h
            | app1 h => exact hwa _ h
            | app2 h => exact hwu _ h
        · exact .inr ⟨_, .arms rfl (by cases u <;> simp [indexFires, select]) hwu ha⟩
      · exact .inr ⟨_, .cond rfl hu.not_W hu⟩
    | scons l t r =>
      cases hi : indexFires (scons l t r) u with
      | true =>
        cases u with
        | bytes b =>
          simp only [indexFires, Option.isSome_iff_exists] at hi
          obtain ⟨v, hv⟩ := hi
          exact .inr ⟨_, .index hv⟩
        | _ => simp [indexFires] at hi
      | false =>
        rcases ihu with hwu | ⟨u', hu⟩
        · rcases iha with hwa | ⟨a', ha⟩
          · exact .inl fun _ h => by
              cases h with
              | index h => simp_all [indexFires]
              | app1 h => exact hwa _ h
              | app2 h => exact hwu _ h
          · exact .inr ⟨_, .arms rfl hi hwu ha⟩
        · exact .inr ⟨_, .cond rfl hu.not_W hu⟩
    | var n =>
      rcases iha with hwa | ⟨a', ha⟩
      · rcases ihu with hwu | ⟨u', hu⟩
        · exact .inl fun _ h => by
            cases h with
            | index h => simp [select] at h
            | app1 h => exact hwa _ h
            | app2 h => exact hwu _ h
        · exact .inr ⟨_, .arg rfl hwa hu⟩
      · exact .inr ⟨_, .head rfl ha.not_W ha⟩
    | app a₁ a₂ =>
      rcases iha with hwa | ⟨a', ha⟩
      · rcases ihu with hwu | ⟨u', hu⟩
        · exact .inl fun _ h => by
            cases h with
            | index h => simp [select] at h
            | app1 h => exact hwa _ h
            | app2 h => exact hwu _ h
        · exact .inr ⟨_, .arg rfl hwa hu⟩
      · exact .inr ⟨_, .head rfl ha.not_W ha⟩
    | proj s l =>
      rcases iha with hwa | ⟨a', ha⟩
      · rcases ihu with hwu | ⟨u', hu⟩
        · exact .inl fun _ h => by
            cases h with
            | index h => simp [select] at h
            | app1 h => exact hwa _ h
            | app2 h => exact hwu _ h
        · exact .inr ⟨_, .arg rfl hwa hu⟩
      · exact .inr ⟨_, .head rfl ha.not_W ha⟩
    | sapp a₁ a₂ =>
      rcases iha with hwa | ⟨a', ha⟩
      · rcases ihu with hwu | ⟨u', hu⟩
        · exact .inl fun _ h => by
            cases h with
            | index h => simp [select] at h
            | app1 h => exact hwa _ h
            | app2 h => exact hwu _ h
        · exact .inr ⟨_, .arg rfl hwa hu⟩
      · exact .inr ⟨_, .head rfl ha.not_W ha⟩

/-- 6/21: `t` is in `w` exactly when it has no `▷ₛ` step. -/
theorem W_iff (t : Term) : W op t ↔ ∀ t', ¬ StepS op t t' := by
  constructor
  · exact fun hw t' h => h.not_W hw
  · intro h
    rcases progress t with hw | ⟨t', ht⟩
    · exact hw
    · exact absurd ht (h t')

/-! ## Reaching `w` (6/26)

If no reduction of `t` is infinite, `▷ₛ` reaches a term in `w`. -/

/-- `t` is strongly normalizing: every reduction from `t` is finite. -/
def SN (op : Bytes → Term → Option Bytes) (t : Term) : Prop := Acc (fun a b => Step op b a) t

/-- 6/26(1): from a strongly normalizing term, `▷ₛ` reaches a term in `w`. -/
theorem SN.reaches_W {t : Term} (h : SN op t) : ∃ s, Star (StepS op) t s ∧ W op s := by
  induction h with
  | intro t _ ih =>
    rcases progress t with hw | ⟨t', ht⟩
    · exact ⟨t, .refl t, hw⟩
    · obtain ⟨s, hs, hw⟩ := ih t' ht.step
      exact ⟨s, Star.head ht hs, hw⟩

/-- `ω = λy. y y`. -/
def omega : Term := lam (app (var 0) (var 0))

/-- `Ω = ω ω`. -/
def Omega : Term := app omega omega

/-- 6/26(2): `(λx. []) Ω ▷ₛ []` (row 6). -/
theorem dropOmega_stepS : StepS op (app (lam (bytes [])) Omega) (bytes []) :=
  .beta (bytes []) Omega (by simp [isRunTime, Omega, omega, isCons, isPath])

end Oymomo
