-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Reduction

/-!
# Classification of normal forms (semantics.tex, 1/20 and 1/21)

A normal form (a term with no step) is exactly one of: a value (row 8), a neutral term
(it waits for a free variable or a run-time operation, 1/21), or a stuck term (no rule will
ever reduce it, 1/20).

The classes look at the root and at the positions a rule must read there: the head of an
application or projection, the argument a value head consumes, the inside of `!t`, and the
fields of a struct. A lambda's body is not read: `x → t` is a value whatever `t` is.
-/

namespace Oymomo
open Term

variable (op : Bytes → Term → Option Bytes)

/-- No step: `t` is a normal form. -/
def Normal (t : Term) : Prop := ∀ t', ¬ Step op t t'

/-- Neutral terms: they wait for a free variable or for a run-time operation. -/
inductive Neutral : Term → Prop
  /-- A free variable. -/
  | var (n : Nat) : Neutral (var n)
  /-- A neutral term applied. -/
  | app {a u : Term} : Neutral a → Neutral (app a u)
  /-- A projection from a neutral term. -/
  | proj {a : Term} {l : String} : Neutral a → Neutral (proj a l)
  /-- `v !n`: a strict application waits for its argument. -/
  | sappV {a u : Term} : isValue a = true → Neutral u → Neutral (sapp a u)
  /-- `n !n`. -/
  | sappN {a u : Term} : Neutral a → Neutral u → Neutral (sapp a u)
  /-- A branch whose condition is not known yet. -/
  | branch {l : String} {t r u : Term} :
      isValue (scons l t r) = true → Neutral u → Neutral (app (scons l t r) u)
  /-- An opcode call whose operand is not known yet. -/
  | opcodeArg {b : Bytes} {u : Term} : Neutral u → Neutral (app (bytes b) u)
  /-- A run-time operation: `op(b)` is undefined (an effect, undefined behavior, or an
  unknown opcode). -/
  | runtime {b : Bytes} {s : Term} :
      isStruct s = true → isData s = true → op b s = none → Neutral (app (bytes b) s)
  /-- A struct with a neutral field and no stuck field: the first field is neutral. -/
  | scons1 {l : String} {t r : Term} : Neutral t → isValue r = true → Neutral (scons l t r)
  /-- A later field is neutral. -/
  | scons2 {l : String} {t r : Term} : isValue t = true → Neutral r → Neutral (scons l t r)
  /-- Both are neutral. -/
  | scons12 {l : String} {t r : Term} : Neutral t → Neutral r → Neutral (scons l t r)

/-- Stuck terms: no rule will ever reduce them. -/
inductive Stuck : Term → Prop
  /-- A stuck term applied. -/
  | app {a u : Term} : Stuck a → Stuck (app a u)
  /-- A projection from a stuck term. -/
  | proj {a : Term} {l : String} : Stuck a → Stuck (proj a l)
  /-- A stuck term applied strictly. -/
  | sapp1 {a u : Term} : Stuck a → Stuck (sapp a u)
  /-- A strict application to a stuck term. -/
  | sapp2 {a u : Term} : Stuck u → Stuck (sapp a u)
  /-- A value applied to a stuck term. -/
  | arg {a u : Term} : isValue a = true → Stuck u → Stuck (app a u)
  /-- A struct with a stuck field. -/
  | scons1 {l : String} {t r : Term} : Stuck t → Stuck (scons l t r)
  /-- A struct with a stuck later field. -/
  | scons2 {l : String} {t r : Term} : Stuck r → Stuck (scons l t r)
  /-- `v.l` where `v` is a lambda, a byte array or a struct with no field `l`. -/
  | projValue {v : Term} {l : String} : isValue v = true → lookup v l = none → Stuck (proj v l)
  /-- The empty struct applied to anything. -/
  | emptyApp (u : Term) : Stuck (app snil u)
  /-- A struct applied to a value that is not a byte array. -/
  | structApp {l : String} {t r u : Term} :
      isValue (scons l t r) = true → isValue u = true → (∀ b, u ≠ bytes b) →
      Stuck (app (scons l t r) u)
  /-- A struct value that `select` can't read (its tail is not a struct). -/
  | selectNone {l : String} {t r : Term} {b : Bytes} :
      isValue (scons l t r) = true → select (scons l t r) b.toNat = none →
      Stuck (app (scons l t r) (bytes b))
  /-- A byte array applied to a value that is not a struct. -/
  | opcodeNotStruct {b : Bytes} {u : Term} :
      isValue u = true → isStruct u = false → Stuck (app (bytes b) u)
  /-- An opcode call whose operand is a value that is not data. -/
  | opcodeNotData {b : Bytes} {u : Term} :
      isValue u = true → isStruct u = true → isData u = false → Stuck (app (bytes b) u)

variable {op}

/-! ## Subterms of a normal form are normal -/

theorem Normal.app_left {a u : Term} (h : Normal op (app a u)) : Normal op a :=
  fun _ hs => h _ (.app1 hs)

theorem Normal.app_right {a u : Term} (h : Normal op (app a u)) : Normal op u :=
  fun _ hs => h _ (.app2 hs)

theorem Normal.proj_inner {a : Term} {l : String} (h : Normal op (proj a l)) : Normal op a :=
  fun _ hs => h _ (.proj1 hs)

theorem Normal.sapp_left {a u : Term} (h : Normal op (sapp a u)) : Normal op a :=
  fun _ hs => h _ (.sapp1 hs)

theorem Normal.sapp_right {a u : Term} (h : Normal op (sapp a u)) : Normal op u :=
  fun _ hs => h _ (.sapp2 hs)

theorem Normal.scons_left {l : String} {t r : Term} (h : Normal op (scons l t r)) :
    Normal op t :=
  fun _ hs => h _ (.scons1 hs)

theorem Normal.scons_right {l : String} {t r : Term} (h : Normal op (scons l t r)) :
    Normal op r :=
  fun _ hs => h _ (.scons2 hs)

/-! ## Every normal form is a value, neutral or stuck -/

theorem classification {t : Term} (h : Normal op t) :
    isValue t = true ∨ Neutral op t ∨ Stuck t := by
  induction t with
  | var n => exact .inr (.inl (.var n))
  | lam t _ => exact .inl rfl
  | snil => exact .inl rfl
  | bytes b => exact .inl rfl
  | sapp a u iha ihu =>
    rcases ihu h.sapp_right with hu | hu | hu
    · exact absurd (Step.strict hu) (h _)
    · rcases iha h.sapp_left with ha | ha | ha
      · exact .inr (.inl (.sappV ha hu))
      · exact .inr (.inl (.sappN ha hu))
      · exact .inr (.inr (.sapp1 ha))
    · exact .inr (.inr (.sapp2 hu))
  | scons l t r iht ihr =>
    rcases iht h.scons_left with ht | ht | ht
    · rcases ihr h.scons_right with hr | hr | hr
      · exact .inl (by simp [isValue, ht, hr])
      · exact .inr (.inl (.scons2 ht hr))
      · exact .inr (.inr (.scons2 hr))
    · rcases ihr h.scons_right with hr | hr | hr
      · exact .inr (.inl (.scons1 ht hr))
      · exact .inr (.inl (.scons12 ht hr))
      · exact .inr (.inr (.scons2 hr))
    · exact .inr (.inr (.scons1 ht))
  | proj s l ihs =>
    rcases ihs h.proj_inner with hs | hs | hs
    · cases hl : lookup s l with
      | none => exact .inr (.inr (.projValue hs hl))
      | some u => exact absurd (Step.proj hl) (h u)
    · exact .inr (.inl (.proj hs))
    · exact .inr (.inr (.proj hs))
  | app a u iha ihu =>
    rcases iha h.app_left with ha | ha | ha
    · cases a with
      | lam t => exact absurd (Step.beta t u) (h _)
      | bytes b =>
        rcases ihu h.app_right with hu | hu | hu
        · cases hs : isStruct u with
          | false => exact .inr (.inr (.opcodeNotStruct hu hs))
          | true =>
            cases hd : isData u with
            | false => exact .inr (.inr (.opcodeNotData hu hs hd))
            | true =>
              cases ho : op b u with
              | none => exact .inr (.inl (.runtime hs hd ho))
              | some b' => exact absurd (Step.opcode hs hd ho) (h _)
        · exact .inr (.inl (.opcodeArg hu))
        · exact .inr (.inr (.arg ha hu))
      | snil => exact .inr (.inr (.emptyApp u))
      | scons l t r =>
        rcases ihu h.app_right with hu | hu | hu
        · cases u with
          | bytes b =>
            cases hsel : select (scons l t r) b.toNat with
            | none => exact .inr (.inr (.selectNone ha hsel))
            | some w => exact absurd (Step.index hsel) (h _)
          | _ => exact .inr (.inr (.structApp ha hu (by intro b hb; cases hb)))
        · exact .inr (.inl (.branch ha hu))
        · exact .inr (.inr (.arg ha hu))
      | _ => exact absurd ha Bool.false_ne_true
    · exact .inr (.inl (.app ha))
    · exact .inr (.inr (.app ha))

/-! ## The three classes are disjoint -/

theorem Neutral.not_value {t : Term} (h : Neutral op t) : isValue t = false := by
  induction h with
  | scons1 _ _ ih => simp [isValue, ih]
  | scons2 _ _ ih => simp [isValue, ih]
  | scons12 _ _ ih => simp [isValue, ih]
  | _ => rfl

theorem Stuck.not_value {t : Term} (h : Stuck t) : isValue t = false := by
  induction h with
  | scons1 _ ih => simp [isValue, ih]
  | scons2 _ ih => simp [isValue, ih]
  | _ => rfl

theorem isValue_of_isData {s : Term} (h : isData s = true) : isValue s = true := by
  induction s with
  | scons l t r iht ihr =>
    simp only [isData, Bool.and_eq_true] at h
    simp [isValue, iht h.1, ihr h.2]
  | _ => simp_all [isData, isValue]

theorem Stuck.not_bytes {b : Bytes} (h : Stuck (bytes b)) : False := by cases h

theorem Neutral.not_stuck {t : Term} (hn : Neutral op t) (hs : Stuck t) : False := by
  induction hn with
  | var n => cases hs
  | @app a u ha ih =>
    have hv := ha.not_value
    cases hs with
    | app hs => exact ih hs
    | arg h _ => simp_all
    | emptyApp => simp [isValue] at hv
    | structApp h _ _ => simp_all
    | selectNone h _ => simp_all
    | opcodeNotStruct _ _ => simp [isValue] at hv
    | opcodeNotData _ _ _ => simp [isValue] at hv
  | @proj a l ha ih =>
    cases hs with
    | proj hs => exact ih hs
    | projValue h _ => simp [ha.not_value] at h
  | @sappV a u ha hu ih =>
    cases hs with
    | sapp1 hs => simp [hs.not_value] at ha
    | sapp2 hs => exact ih hs
  | @sappN a u ha hu iha ihu =>
    cases hs with
    | sapp1 hs => exact iha hs
    | sapp2 hs => exact ihu hs
  | @branch l t r u hv hu ih =>
    cases hs with
    | app hs => simp [hs.not_value] at hv
    | arg _ hs => exact ih hs
    | structApp _ h _ => simp [hu.not_value] at h
    | selectNone _ _ => have := hu.not_value; simp [isValue] at this
  | @opcodeArg b u hu ih =>
    cases hs with
    | app hs => exact hs.not_bytes
    | arg _ hs => exact ih hs
    | opcodeNotStruct h _ => simp [hu.not_value] at h
    | opcodeNotData h _ _ => simp [hu.not_value] at h
  | @runtime b s h1 h2 h3 =>
    cases hs with
    | app hs => exact hs.not_bytes
    | arg _ hs => have := isValue_of_isData h2; simp [hs.not_value] at this
    | opcodeNotStruct _ h => simp [h1] at h
    | opcodeNotData _ _ h => simp [h2] at h
  | scons1 _ hr ih =>
    cases hs with
    | scons1 hs => exact ih hs
    | scons2 hs => simp [hs.not_value] at hr
  | scons2 ht _ ih =>
    cases hs with
    | scons1 hs => simp [hs.not_value] at ht
    | scons2 hs => exact ih hs
  | scons12 _ _ ih1 ih2 =>
    cases hs with
    | scons1 hs => exact ih1 hs
    | scons2 hs => exact ih2 hs

/-- A normal form is exactly one of: a value, a neutral term, a stuck term. -/
theorem classification_unique {t : Term} :
    ¬ (isValue t = true ∧ Neutral op t) ∧ ¬ (isValue t = true ∧ Stuck t) ∧
      ¬ (Neutral op t ∧ Stuck t) :=
  ⟨fun ⟨hv, hn⟩ => by simp [hn.not_value] at hv,
   fun ⟨hv, hs⟩ => by simp [hs.not_value] at hv,
   fun ⟨hn, hs⟩ => hn.not_stuck hs⟩

end Oymomo
