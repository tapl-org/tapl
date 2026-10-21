-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Reduction

/-!
# The strategy (semantics.tex, Section 6)

`SStep op t t'` is the order of table 6.2: each constructor is one row, and its premises
say that the row's shape matches, that the chosen part has a step, and that no earlier row
of the same group applies. A chosen part takes its own `SStep`, carried by the rule of
Section 5 named in the table.

* `sstep_step`: every step of the order is a `⟶` step (it defines no rule of its own).
* `sstep_complete`: a term with a `⟶` step has a step of the order (completeness, 6.4).
* `sstep_det`: the order chooses at most one step (the first row that applies).
-/

namespace Oymomo
open Term

variable {op : Bytes → Term → Option Bytes}

variable (op) in
/-- `t` has a step. -/
def Red (t : Term) : Prop := ∃ t', Step op t t'

variable (op) in
/-- A rule of Section 4 fires at the root of `t`. -/
def RootRed : Term → Prop
  | app (lam _) u => isValue u = true
  | app (bytes b) s => isStruct s = true ∧ isData s = true ∧ ∃ b', op b s = some b'
  | app s (bytes b) => ∃ u, select s b.toNat = some u
  | proj s l => ∃ u, lookup s l = some u
  | _ => False

def isLam : Term → Bool
  | lam _ => true
  | _ => false

variable (op) in
/-- Some field of the struct is not a value and has a step (row 6.2k applies). -/
def NVRed : Term → Prop
  | scons _ t r => (isValue t = false ∧ Red op t) ∨ NVRed r
  | _ => False

variable (op) in
/-- One step of the order of table 6.2. -/
inductive SStep : Term → Term → Prop
  /-- Row a, E-Proj. -/
  | proj {s u : Term} {l : String} : lookup s l = some u → SStep (proj s l) u
  /-- Row b, E-Proj1 on `t`. -/
  | proj1 {t t' : Term} {l : String} :
      lookup t l = none → SStep t t' → SStep (proj t l) (proj t' l)
  /-- Row c, E-Beta. -/
  | beta {t u : Term} : isValue u = true → SStep (app (lam t) u) (subst (inst u) t)
  /-- Row d, E-App2 on the argument of a lambda. -/
  | arg {t u u' : Term} : isValue u = false → SStep u u' → SStep (app (lam t) u) (app (lam t) u')
  /-- Row e, E-Opcode. -/
  | opcode {s : Term} {b b' : Bytes} :
      isStruct s = true → isData s = true → op b s = some b' → SStep (app (bytes b) s) (bytes b')
  /-- Rows f and g, E-Index and E-Default. -/
  | index {s u : Term} {b : Bytes} : select s b.toNat = some u → SStep (app s (bytes b)) u
  /-- Row h, E-App2 on a branch's condition. -/
  | cond {s c c' : Term} : isStruct s = true → SStep c c' → SStep (app s c) (app s c')
  /-- Row i, E-App1. -/
  | app1 {a a' b : Term} :
      ¬ RootRed op (app a b) → ¬ (isLam a = true ∧ Red op b) → ¬ (isStruct a = true ∧ Red op b) →
      SStep a a' → SStep (app a b) (app a' b)
  /-- Row j, E-App2. -/
  | app2 {a b b' : Term} :
      ¬ RootRed op (app a b) → isLam a = false → isStruct a = false → ¬ Red op a →
      SStep b b' → SStep (app a b) (app a b')
  /-- Row k, E-Struct on the first field that is not a value and has a step: the head. -/
  | fieldNV {l : String} {t t' r : Term} :
      isValue t = false → SStep t t' → SStep (scons l t r) (scons l t' r)
  /-- Row k, a later field. -/
  | fieldNVTail {l : String} {t r r' : Term} :
      ¬ (isValue t = false ∧ Red op t) → NVRed op r → SStep r r' → SStep (scons l t r) (scons l t r')
  /-- Row l, E-Struct on the first field with a step: the head. -/
  | field {l : String} {t t' r : Term} :
      ¬ NVRed op (scons l t r) → SStep t t' → SStep (scons l t r) (scons l t' r)
  /-- Row l, a later field. -/
  | fieldTail {l : String} {t r r' : Term} :
      ¬ NVRed op (scons l t r) → ¬ Red op t → SStep r r' → SStep (scons l t r) (scons l t r')
  /-- Row m, E-Abs. -/
  | lam {t t' : Term} : SStep t t' → SStep (lam t) (lam t')

/-! ## Each step of the order is a `⟶` step -/

theorem sstep_step {t t' : Term} (h : SStep op t t') : Step op t t' := by
  induction h with
  | proj h => exact .proj h
  | proj1 _ _ ih => exact .proj1 ih
  | beta h => exact .beta h
  | arg _ _ ih => exact .app2 ih
  | opcode h1 h2 h3 => exact .opcode h1 h2 h3
  | index h => exact .index h
  | cond _ _ ih => exact .app2 ih
  | app1 _ _ _ _ ih => exact .app1 ih
  | app2 _ _ _ _ _ ih => exact .app2 ih
  | fieldNV _ _ ih => exact .scons1 ih
  | fieldNVTail _ _ _ ih => exact .scons2 ih
  | field _ _ ih => exact .scons1 ih
  | fieldTail _ _ _ ih => exact .scons2 ih
  | lam _ ih => exact .lam ih

theorem SStep.red {t t' : Term} (h : SStep op t t') : Red op t := ⟨t', sstep_step h⟩

/-! ## Completeness: a term with a step has a step of the order -/

theorem NVRed.red {r : Term} (h : NVRed op r) : Red op r := by
  induction r with
  | scons l t r _ ihr =>
    rcases h with ⟨_, t', ht⟩ | h
    · exact ⟨_, .scons1 ht⟩
    · obtain ⟨r', hr⟩ := ihr h
      exact ⟨_, .scons2 hr⟩
  | _ => exact h.elim

theorem Step.root_or_parts {a b t' : Term} (h : Step op (app a b) t') :
    RootRed op (app a b) ∨ Red op a ∨ Red op b := by
  cases h with
  | beta hv => exact .inl hv
  | index hs => cases a <;> first | exact .inl ⟨_, hs⟩ | (simp [RootRed]; exact .inl ⟨_, hs⟩) | simp [select] at hs
  | opcode h1 h2 h3 => exact .inl ⟨h1, h2, _, h3⟩
  | app1 h => exact .inr (.inl ⟨_, h⟩)
  | app2 h => exact .inr (.inr ⟨_, h⟩)

theorem RootRed.sstep {a b : Term} (h : RootRed op (app a b)) : ∃ t', SStep op (app a b) t' := by
  cases a with
  | lam t => exact ⟨_, .beta h⟩
  | bytes c =>
    cases b with
    | bytes d =>
      -- `app (bytes c) (bytes d)`: the opcode pattern comes first
      obtain ⟨h1, _⟩ := h
      exact absurd h1 (by simp [isStruct])
    | _ =>
      obtain ⟨h1, h2, b', h3⟩ := h
      exact ⟨_, .opcode h1 h2 h3⟩
  | _ =>
    cases b with
    | bytes d =>
      obtain ⟨u, hu⟩ := h
      exact ⟨_, .index hu⟩
    | _ => exact h.elim

/-- Completeness (6.4): when a term has a step, the order chooses one. -/
theorem sstep_complete : ∀ {t : Term}, Red op t → ∃ t', SStep op t t'
  | var _, ⟨_, h⟩ => by cases h
  | bytes _, ⟨_, h⟩ => by cases h
  | snil, ⟨_, h⟩ => by cases h
  | lam t, ⟨_, h⟩ => by
    cases h with
    | lam h =>
      obtain ⟨t', ht⟩ := sstep_complete ⟨_, h⟩
      exact ⟨_, .lam ht⟩
  | proj t l, ⟨_, h⟩ => by
    cases hl : lookup t l with
    | some u => exact ⟨_, .proj hl⟩
    | none =>
      cases h with
      | proj h => rw [hl] at h; cases h
      | proj1 h =>
        obtain ⟨t', ht⟩ := sstep_complete ⟨_, h⟩
        exact ⟨_, .proj1 hl ht⟩
  | scons l t r, ⟨_, h⟩ => by
    by_cases hnv : NVRed op (scons l t r)
    · by_cases hh : isValue t = false ∧ Red op t
      · obtain ⟨t', ht⟩ := sstep_complete hh.2
        exact ⟨_, .fieldNV hh.1 ht⟩
      · have hr : NVRed op r := by
          rcases hnv with h' | h'
          · exact absurd h' hh
          · exact h'
        obtain ⟨r', hr'⟩ := sstep_complete hr.red
        exact ⟨_, .fieldNVTail hh hr hr'⟩
    · by_cases ht : Red op t
      · obtain ⟨t', ht'⟩ := sstep_complete ht
        exact ⟨_, .field hnv ht'⟩
      · cases h with
        | scons1 h => exact absurd ⟨_, h⟩ ht
        | scons2 h =>
          obtain ⟨r', hr'⟩ := sstep_complete ⟨_, h⟩
          exact ⟨_, .fieldTail hnv ht hr'⟩
  | app a b, ⟨_, h⟩ => by
    by_cases hroot : RootRed op (app a b)
    · exact hroot.sstep
    · rcases h.root_or_parts with hr | ha | hb
      · exact absurd hr hroot
      · -- the head has a step
        cases hl : isLam a with
        | true =>
          cases a with
          | lam t =>
            by_cases hb : Red op b
            · have hv : isValue b = false := by
                cases hv : isValue b with
                | false => rfl
                | true => exact absurd hv hroot
              obtain ⟨b', hb'⟩ := sstep_complete hb
              exact ⟨_, .arg hv hb'⟩
            · obtain ⟨a', ha'⟩ := sstep_complete ha
              exact ⟨_, .app1 hroot (fun h => hb h.2) (fun h => hb h.2) ha'⟩
          | _ => simp [isLam] at hl
        | false =>
          by_cases hc : isStruct a = true ∧ Red op b
          · obtain ⟨b', hb'⟩ := sstep_complete hc.2
            exact ⟨_, .cond hc.1 hb'⟩
          · obtain ⟨a', ha'⟩ := sstep_complete ha
            exact ⟨_, .app1 hroot (fun h => by rw [hl] at h; exact Bool.false_ne_true h.1) hc ha'⟩
      · -- the argument has a step
        obtain ⟨b', hb'⟩ := sstep_complete hb
        cases hl : isLam a with
        | true =>
          cases a with
          | lam t =>
            have hv : isValue b = false := by
              cases hv : isValue b with
              | false => rfl
              | true => exact absurd hv hroot
            exact ⟨_, .arg hv hb'⟩
          | _ => simp [isLam] at hl
        | false =>
          cases hs : isStruct a with
          | true => exact ⟨_, .cond hs hb'⟩
          | false =>
            by_cases ha : Red op a
            · obtain ⟨a', ha'⟩ := sstep_complete ha
              exact ⟨_, .app1 hroot (fun h => by rw [hl] at h; exact Bool.false_ne_true h.1)
                (fun h => by rw [hs] at h; exact Bool.false_ne_true h.1) ha'⟩
            · exact ⟨_, .app2 hroot hl hs ha hb'⟩

/-! ## The order chooses at most one step -/

theorem not_red_bytes {b : Bytes} : ¬ Red op (bytes b) := fun ⟨_, h⟩ => by cases h

theorem index_root {s u : Term} {b : Bytes} (hs : select s b.toNat = some u) :
    RootRed op (app s (bytes b)) := by
  cases s with
  | scons l t r => exact ⟨u, hs⟩
  | _ => simp [select] at hs

/-- Determinism: the first row that applies is the only one. -/
theorem sstep_det {t a b : Term} (ha : SStep op t a) (hb : SStep op t b) : a = b := by
  induction ha generalizing b with
  | proj h =>
    cases hb with
    | proj h' => rw [h] at h'; cases h'; rfl
    | proj1 hn _ => rw [h] at hn; cases hn
  | proj1 hn _ ih =>
    cases hb with
    | proj h' => rw [hn] at h'; cases h'
    | proj1 _ h' => rw [ih h']
  | beta hv =>
    cases hb with
    | beta _ => rfl
    | arg hv' _ => rw [hv] at hv'; cases hv'
    | index hs => simp [select] at hs
    | cond hs _ => simp [isStruct] at hs
    | app1 hr _ _ _ => exact absurd hv hr
    | app2 hr _ _ _ _ => exact absurd hv hr
  | arg hv hs ih =>
    cases hb with
    | beta hv' => rw [hv] at hv'; cases hv'
    | arg _ h' => rw [ih h']
    | index hsel => simp [select] at hsel
    | cond hst _ => simp [isStruct] at hst
    | app1 _ hl _ _ => exact absurd ⟨rfl, hs.red⟩ hl
    | app2 _ hl _ _ _ => simp [isLam] at hl
  | opcode h1 h2 h3 =>
    cases hb with
    | opcode _ _ h3' => rw [h3] at h3'; cases h3'; rfl
    | index _ => simp [isStruct] at h1
    | cond hst _ => simp [isStruct] at hst
    | app1 hr _ _ _ => exact absurd ⟨h1, h2, _, h3⟩ hr
    | app2 hr _ _ _ _ => exact absurd ⟨h1, h2, _, h3⟩ hr
  | index hs =>
    cases hb with
    | beta _ => simp [select] at hs
    | arg _ h => exact absurd h.red not_red_bytes
    | opcode h1 _ _ => simp [isStruct] at h1
    | index hs' => rw [hs] at hs'; cases hs'; rfl
    | cond _ hc => exact absurd hc.red not_red_bytes
    | app1 hr _ _ _ => exact absurd (index_root hs) hr
    | app2 hr _ _ _ _ => exact absurd (index_root hs) hr
  | cond hst hc ih =>
    cases hb with
    | beta _ => simp [isStruct] at hst
    | arg _ _ => simp [isStruct] at hst
    | opcode _ _ _ => simp [isStruct] at hst
    | index _ => exact absurd hc.red not_red_bytes
    | cond _ h' => rw [ih h']
    | app1 _ _ hs _ => exact absurd ⟨hst, hc.red⟩ hs
    | app2 _ _ hs _ _ => rw [hst] at hs; cases hs
  | app1 hr hl hs ha ih =>
    cases hb with
    | beta hv => exact absurd hv hr
    | arg _ hb' => exact absurd ⟨rfl, hb'.red⟩ hl
    | opcode h1 h2 h3 => exact absurd ⟨h1, h2, _, h3⟩ hr
    | index hsel => exact absurd (index_root hsel) hr
    | cond hst hc => exact absurd ⟨hst, hc.red⟩ hs
    | app1 _ _ _ h' => rw [ih h']
    | app2 _ _ _ hna _ => exact absurd ha.red hna
  | app2 hr hl hs hna _ ih =>
    cases hb with
    | beta hv => exact absurd hv hr
    | arg _ _ => simp [isLam] at hl
    | opcode h1 h2 h3 => exact absurd ⟨h1, h2, _, h3⟩ hr
    | index hsel => exact absurd (index_root hsel) hr
    | cond hst _ => rw [hs] at hst; cases hst
    | app1 _ _ _ ha' => exact absurd ha'.red hna
    | app2 _ _ _ _ h' => rw [ih h']
  | fieldNV hv ht ih =>
    cases hb with
    | fieldNV _ h' => rw [ih h']
    | fieldNVTail hn _ _ => exact absurd ⟨hv, ht.red⟩ hn
    | field hn _ => exact absurd (Or.inl ⟨hv, ht.red⟩) hn
    | fieldTail hn _ _ => exact absurd (Or.inl ⟨hv, ht.red⟩) hn
  | fieldNVTail hn hnv _ ih =>
    cases hb with
    | fieldNV hv ht => exact absurd ⟨hv, ht.red⟩ hn
    | fieldNVTail _ _ h' => rw [ih h']
    | field hn' _ => exact absurd (Or.inr hnv) hn'
    | fieldTail hn' _ _ => exact absurd (Or.inr hnv) hn'
  | field hn ht ih =>
    cases hb with
    | fieldNV hv ht' => exact absurd (Or.inl ⟨hv, ht'.red⟩) hn
    | fieldNVTail _ hnv _ => exact absurd (Or.inr hnv) hn
    | field _ h' => rw [ih h']
    | fieldTail _ hnr _ => exact absurd ht.red hnr
  | fieldTail hn hnr _ ih =>
    cases hb with
    | fieldNV hv ht' => exact absurd (Or.inl ⟨hv, ht'.red⟩) hn
    | fieldNVTail _ hnv _ => exact absurd (Or.inr hnv) hn
    | field _ ht' => exact absurd ht'.red hnr
    | fieldTail _ _ h' => rw [ih h']
  | lam _ ih =>
    cases hb with
    | lam h' => rw [ih h']

end Oymomo
