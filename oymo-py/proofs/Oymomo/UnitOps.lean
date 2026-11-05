-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Guarantee

/-!
# The unit tools

`'unit.merge'`, `'unit.rebase'` and `'unit.make_reducible'` as functions on `Term`, written
to match the Python ones (`oymo.oymomo.unit_ops`) case by case. The generated
`UnitOpsCases.lean` checks both on the same cases.

* `merge_closed`, `merge_wf`, `rebase_closed`, `rebase_wf`, `makeReducible_closed`,
  `makeReducible_wf`: each tool gives a closed, well-formed result for a closed,
  well-formed operand.
* `unitOps_ok`, `withUnitOps_ok`: so a table of the unit tools, alone or added to any table
  that satisfies `OpOK`, satisfies `OpOK`; confluence and the guarantee hold for it.
* `rebaseBody_subst`: rebasing a body `λg. b` under the prefix `P` is substituting
  `g := g.P` in `b`.
* `rebase_call`, `rebase_call_nf`: so calling the rebased body with an instance `G'` whose
  `G'.P` reduces to `G` reaches what calling the original body with `G` reaches.

A struct is a `scons` chain; Python's structs always end in `snil`. The tools here walk a
chain without looking at its tail; the theorems ask for a well-formed operand, and the
table only calls the tools on one (and on a closed one, as E-Opcode does).
-/

namespace Oymomo
open Term

deriving instance DecidableEq for Term

/-! ## Helpers -/

/-- The labels of a struct, in order. -/
def labels : Term → List String
  | scons l _ r => l :: labels r
  | _ => []

/-- No λ and no fixed point anywhere. -/
def lamFree : Term → Bool
  | var _ => true
  | lam _ => false
  | app a b => lamFree a && lamFree b
  | snil => true
  | scons _ t r => lamFree t && lamFree r
  | proj t _ => lamFree t
  | bytes _ => true
  | fix _ => false

/-- Some field labeled `l` holds `v`. -/
def hasField : Term → String → Term → Bool
  | scons l' t r, l, v => (l' == l && t == v) || hasField r l v
  | _, _, _ => false

/-- An entry: a struct with a `type` field. -/
def isEntry (t : Term) : Bool := (lookup t "type").isSome

/-- The fields of a struct being built, the last one first. -/
abbrev Fields := List (String × Term)

/-- `acc` with the fields of the struct `s` pushed on, in order. -/
def revFields (acc : Fields) : Term → Fields
  | scons l t r => revFields ((l, t) :: acc) r
  | _ => acc

/-- The struct of the fields `acc` (the last one first) in front of `r`. -/
def ofRev : Fields → Term → Term
  | [], r => r
  | (l, t) :: acc, r => ofRev acc (scons l t r)

/-- The value of the last field labeled `l`. -/
def findRev : Fields → String → Option Term
  | (l', t) :: acc, l => if l' = l then some t else findRev acc l
  | [], _ => none

/-- The last field labeled `l` set to `v`. -/
def setRev : Fields → String → Term → Fields
  | (l', t) :: acc, l, v => if l' = l then (l', v) :: acc else (l', t) :: setRev acc l v
  | [], _, _ => []

/-! ## `'unit.merge'` -/

/-- A hole: an entry with only a `type`. -/
def isHole (e : Term) : Bool := labels e == ["type"]

/-- An entry that may fill a hole: it brings a `body`, `init`, `value` or `link`. -/
def fills (e : Term) : Bool :=
  (labels e).any fun l => l == "body" || l == "init" || l == "value" || l == "link"

/-- A declaration: an entry with only a `type` and a `link`. -/
def isDecl (e : Term) : Bool :=
  labels e == ["type", "link"] || labels e == ["link", "type"]

/-- `e` defines what the declaration `d` declares: it brings a `body`, `init` or `value`,
and has `d`'s `link`. -/
def defines (e d : Term) : Bool :=
  (labels e).any (fun l => l == "body" || l == "init" || l == "value") &&
    match lookup d "link" with
    | some k => hasField e "link" k
    | none => false

/-- Two equal λ-free values give one. -/
def same (a b : Term) : Option Term := if a == b && lamFree a then some a else none

/-- Two values with the same label merged, given `ns`: their fields merged, as namespaces. -/
def mergeWith (a b : Term) (ns : Option Fields) : Option Term :=
  if isStruct a && isStruct b then
    match lookup a "type", lookup b "type" with
    | none, none => ns.map (ofRev · snil)
    | some x, some y =>
      if x == y then
        if isHole a && (isHole b || fills b) then some b
        else if isHole b && fills a then some a
        else if isDecl a && defines b a then some b
        else if isDecl b && defines a b then some a
        else same a b
      else same a b
    | _, _ => same a b
  else same a b

/-- The fields `acc` with the fields of the struct `s` merged in: an unlabeled field or a
new label is appended; a label already there is merged with the last field that has it. -/
def mergeInto (acc : Fields) : Term → Option Fields
  | scons l t r =>
    match (if l = "" then none else findRev acc l) with
    | none => mergeInto ((l, t) :: acc) r
    | some v =>
      match mergeWith v t (mergeInto (revFields [] v) t) with
      | none => none
      | some w => mergeInto (setRev acc l w) r
  | _ => some acc

/-- The fields `acc` with every part of the struct `s` merged in, in order. -/
def mergeParts (acc : Fields) : Term → Option Fields
  | scons _ p r =>
    if isStruct p then
      match mergeInto acc p with
      | none => none
      | some acc' => mergeParts acc' r
    else none
  | _ => some acc

/-- `'unit.merge' {X₁, X₂, …}`: the structs `Xᵢ` merged into one, or none. -/
def merge (s : Term) : Option Term :=
  if isStruct s then (mergeParts [] s).map (ofRev · snil) else none

/-! ## `'unit.rebase'` -/

/-- `t.p₁.….pₙ` for `P = [p₁, …, pₙ]`. -/
def path (P : List String) (t : Term) : Term := P.foldl proj t

/-- `t` is a path `x.l₁.….lₙ` (`n ≥ 0`) from the variable `d`. -/
def rootedAt (d : Nat) : Term → Bool
  | var n => n == d
  | proj t _ => rootedAt d t
  | _ => false

/-- A path `x.l₁.….lₙ` with `P` put in after its root: `x.P.l₁.….lₙ`. -/
def ins (P : List String) : Term → Term
  | proj t l => proj (ins P t) l
  | t => path P t

/-- `t`, `d` binders inside `λg`, with every path from `g` (the index `d`) prefixed by `P`,
or none where `g` is used another way. -/
def rebaseTerm (P : List String) (d : Nat) : Term → Option Term
  | var n => if n = d then none else some (var n)
  | lam t => (rebaseTerm P (d + 1) t).map lam
  | app a b =>
    match rebaseTerm P d a, rebaseTerm P d b with
    | some a', some b' => some (app a' b')
    | _, _ => none
  | snil => some snil
  | scons l t r =>
    match rebaseTerm P d t, rebaseTerm P d r with
    | some t', some r' => some (scons l t' r')
    | _, _ => none
  | proj t l =>
    if rootedAt d t then some (proj (ins P t) l) else (rebaseTerm P d t).map (proj · l)
  | bytes b => some (bytes b)
  | fix t => (rebaseTerm P d t).map fix

/-- An entry's body `λg. b` with every path from `g` in `b` prefixed by `P`, or none. -/
def rebaseBody (P : List String) : Term → Option Term
  | lam t => (rebaseTerm P 0 t).map lam
  | _ => none

/-- An entry's field that `λg` binds: its `body`, or an `init` or `value` that is a λ
(`λg. C`). -/
def bindsUnit (l : String) (v : Term) : Bool :=
  l == "body" || ((l == "init" || l == "value") && isLam v)

/-- A struct with its entries' bodies, and `init`s and `value`s `λg. C`, rebased, or none:
`entry` says the struct is an entry. λ-free data is copied; a λ elsewhere gives none. -/
def rebaseNs (P : List String) (entry : Bool) : Term → Option Term
  | scons l v r =>
    let v' :=
      if entry && bindsUnit l v then rebaseBody P v
      else if isStruct v then rebaseNs P (isEntry v) v
      else if lamFree v then some v else none
    match v', rebaseNs P entry r with
    | some v', some r' => some (scons l v' r')
    | _, _ => none
  | snil => some snil
  | _ => none

/-- The label a byte array spells: nonempty UTF-8 text, else none. -/
def labelOf : Term → Option String
  | bytes b =>
    match String.fromUTF8? ⟨b.toArray⟩ with
    | some s => if s = "" then none else some s
    | none => none
  | _ => none

/-- The labels of a prefix `{'p₁', …, 'pₙ'}`, or none. -/
def prefixOf : Term → Option (List String)
  | scons _ t r =>
    match labelOf t, prefixOf r with
    | some l, some ls => some (l :: ls)
    | _, _ => none
  | snil => some []
  | _ => none

/-- `{p₁ = {p₂ = … t}}` for `P = [p₁, p₂, …]`. -/
def nest (P : List String) (t : Term) : Term := P.foldr (fun l t => scons l t snil) t

/-- `'unit.rebase' {P, X}`: `X` under the prefix `P`, with the paths in its entries' bodies
(and `init`s and `value`s `λg. C`) prefixed, or none. -/
def rebase : Term → Option Term
  | scons _ p (scons _ x snil) =>
    if isStruct p && isStruct x then
      match prefixOf p with
      | some P => (rebaseNs P (isEntry x) x).map (nest P)
      | none => none
    else none
  | _ => none

/-! ## `'unit.make_reducible'` -/

/-- Every region `'R' (λr. u)` turned into `(fix (λr. u)) [00]`. -/
def runRegions : Term → Term
  | var n => var n
  | lam t => lam (runRegions t)
  | app (bytes c) (lam u) =>
    if c = [0x52] then app (fix (lam (runRegions u))) (bytes [0])
    else app (bytes c) (lam (runRegions u))
  | app a b => app (runRegions a) (runRegions b)
  | snil => snil
  | scons l t r => scons l (runRegions t) (runRegions r)
  | proj t l => proj (runRegions t) l
  | bytes b => bytes b
  | fix t => fix (runRegions t)

/-- An entry's field with its `λg` moved out: an `init` or `value` `λg. C` becomes `C`. -/
def hoistPart (l : String) : Term → Term
  | lam c => if l = "init" ∨ l = "value" then c else lam c
  | t => t

/-- An entry with each `init` or `value` `λg. C` turned into `C`. -/
def hoistInits : Term → Term
  | scons l t r => scons l (hoistPart l t) (hoistInits r)
  | t => t

/-- A struct with each definition `{…, body = λg. λp. R, …}` turned into `λp. R'` (`R`
with its regions run), and each `init` or `value` `λg. C` of another entry turned into `C`,
or none. Other entry parts and λ-free data stay; any other λ, or a body not shaped
`λg. λp. …`, gives none. -/
def reducibleNs : Term → Option Term
  | scons l v r =>
    let v' :=
      if isEntry v then
        match lookup v "body" with
        | none => if lamFree (hoistInits v) then some (hoistInits v) else none
        | some (lam (lam R)) => some (runRegions (lam R))
        | some _ => none
      else if isStruct v then reducibleNs v
      else if lamFree v then some v else none
    match v', reducibleNs r with
    | some v', some r' => some (scons l v' r')
    | _, _ => none
  | snil => some snil
  | _ => none

/-- `'unit.make_reducible' I`: the ingot `I` as `λg. N`, or none. -/
def makeReducible (s : Term) : Option Term :=
  if isStruct s then (reducibleNs s).map lam else none

/-! ## Facts about the helpers -/

theorem closedAt_mono {k m : Nat} {t : Term} (h : closedAt k t = true) (hkm : k ≤ m) :
    closedAt m t = true := by
  induction t generalizing k m with
  | var n => simp only [closedAt, decide_eq_true_eq] at h ⊢; omega
  | lam t ih => exact ih h (by omega)
  | app a b iha ihb =>
    simp only [closedAt, Bool.and_eq_true] at h ⊢; exact ⟨iha h.1 hkm, ihb h.2 hkm⟩
  | snil => rfl
  | scons l t r iht ihr =>
    simp only [closedAt, Bool.and_eq_true] at h ⊢; exact ⟨iht h.1 hkm, ihr h.2 hkm⟩
  | proj t l ih => exact ih h hkm
  | bytes b => rfl
  | fix t ih => exact ih h hkm

/-- A property that building a struct out of fields keeps, and taking one apart keeps:
being closed under `k` binders, or well formed. -/
structure StructClosed (Q : Term → Prop) : Prop where
  nil : Q snil
  cons : ∀ {l t r}, Q t → Q r → isStruct r = true → Q (scons l t r)
  head : ∀ {l t r}, Q (scons l t r) → Q t
  tail : ∀ {l t r}, Q (scons l t r) → Q r

theorem StructClosed.closedAt (k : Nat) : StructClosed (fun t => closedAt k t = true) where
  nil := rfl
  cons h1 h2 _ := by simp only [Oymomo.closedAt, Bool.and_eq_true]; exact ⟨h1, h2⟩
  head h := by simp only [Oymomo.closedAt, Bool.and_eq_true] at h; exact h.1
  tail h := by simp only [Oymomo.closedAt, Bool.and_eq_true] at h; exact h.2

theorem StructClosed.wf : StructClosed WF where
  nil := trivial
  cons h1 h2 h3 := ⟨h1, h2, h3⟩
  head h := h.1
  tail h := h.2.1

section Merge

variable {Q : Term → Prop} (hQ : StructClosed Q)
include hQ

theorem StructClosed.lookup {s u : Term} {l : String} (hs : Q s) (h : lookup s l = some u) :
    Q u := by
  induction s with
  | scons l' t r _ ihr =>
    simp only [Oymomo.lookup] at h
    split at h
    · cases h; exact hQ.head hs
    · exact ihr (hQ.tail hs) h
  | _ => simp [Oymomo.lookup] at h

theorem revFields_all {acc : Fields} {s : Term} (ha : ∀ p ∈ acc, Q p.2) (hs : Q s) :
    ∀ p ∈ revFields acc s, Q p.2 := by
  induction s generalizing acc with
  | scons l t r _ ihr =>
    refine ihr ?_ (hQ.tail hs)
    intro p hp
    rcases List.mem_cons.mp hp with rfl | hp
    · exact hQ.head hs
    · exact ha p hp
  | _ => exact ha

theorem ofRev_q {acc : Fields} {r : Term} (ha : ∀ p ∈ acc, Q p.2) (hr : Q r)
    (hs : isStruct r = true) : Q (ofRev acc r) ∧ isStruct (ofRev acc r) = true := by
  induction acc generalizing r with
  | nil => exact ⟨hr, hs⟩
  | cons p acc ih =>
    obtain ⟨l, t⟩ := p
    exact ih (fun q hq => ha q (List.mem_cons_of_mem _ hq))
      (hQ.cons (ha _ List.mem_cons_self) hr hs) rfl

omit hQ in
theorem findRev_q {acc : Fields} {l : String} {v : Term} (ha : ∀ p ∈ acc, Q p.2)
    (h : findRev acc l = some v) : Q v := by
  induction acc with
  | nil => simp [findRev] at h
  | cons p acc ih =>
    obtain ⟨l', t⟩ := p
    simp only [findRev] at h
    split at h
    · cases h; exact ha _ List.mem_cons_self
    · exact ih (fun q hq => ha q (List.mem_cons_of_mem _ hq)) h

omit hQ in
theorem setRev_all {acc : Fields} {l : String} {w : Term} (ha : ∀ p ∈ acc, Q p.2) (hw : Q w) :
    ∀ p ∈ setRev acc l w, Q p.2 := by
  induction acc with
  | nil => simp [setRev]
  | cons p acc ih =>
    obtain ⟨l', t⟩ := p
    simp only [setRev]
    split
    · intro q hq
      rcases List.mem_cons.mp hq with rfl | hq
      · exact hw
      · exact ha q (List.mem_cons_of_mem _ hq)
    · intro q hq
      rcases List.mem_cons.mp hq with rfl | hq
      · exact ha _ List.mem_cons_self
      · exact ih (fun q hq => ha q (List.mem_cons_of_mem _ hq)) q hq

omit hQ in
theorem same_q {a b w : Term} (ha : Q a) (h : same a b = some w) : Q w := by
  simp only [same] at h
  split at h
  · cases h; exact ha
  · cases h

theorem mergeWith_q {a b w : Term} {ns : Option Fields} (ha : Q a) (hb : Q b)
    (hns : ∀ f, ns = some f → ∀ p ∈ f, Q p.2) (h : mergeWith a b ns = some w) : Q w := by
  simp only [mergeWith] at h
  split at h
  · split at h
    · cases ns with
      | none => cases h
      | some f =>
        simp only [Option.map_some, Option.some.injEq] at h
        subst h
        exact (ofRev_q hQ (hns f rfl) hQ.nil rfl).1
    · split at h
      · split at h
        · cases h; exact hb
        · split at h
          · cases h; exact ha
          · split at h
            · cases h; exact hb
            · split at h
              · cases h; exact ha
              · exact same_q ha h
      · exact same_q ha h
    · exact same_q ha h
  · exact same_q ha h

theorem mergeInto_all {acc f : Fields} {s : Term} (ha : ∀ p ∈ acc, Q p.2) (hs : Q s)
    (h : mergeInto acc s = some f) : ∀ p ∈ f, Q p.2 := by
  induction s generalizing acc f with
  | scons l t r iht ihr =>
    simp only [mergeInto] at h
    split at h
    · refine ihr ?_ (hQ.tail hs) h
      intro p hp
      rcases List.mem_cons.mp hp with rfl | hp
      · exact hQ.head hs
      · exact ha p hp
    · rename_i v hv
      have hqv : Q v := by
        split at hv
        · cases hv
        · exact findRev_q ha hv
      split at h
      · cases h
      · rename_i w hw
        have hqw : Q w :=
          mergeWith_q hQ hqv (hQ.head hs)
            (fun f' hf' => iht (revFields_all hQ (by simp) hqv) (hQ.head hs) hf') hw
        exact ihr (setRev_all ha hqw) (hQ.tail hs) h
  | _ => simp only [mergeInto, Option.some.injEq] at h; subst h; exact ha

theorem mergeParts_all {acc f : Fields} {s : Term} (ha : ∀ p ∈ acc, Q p.2) (hs : Q s)
    (h : mergeParts acc s = some f) : ∀ p ∈ f, Q p.2 := by
  induction s generalizing acc f with
  | scons l p r _ ihr =>
    simp only [mergeParts] at h
    split at h
    · split at h
      · cases h
      · rename_i acc' hacc
        exact ihr (mergeInto_all hQ ha (hQ.head hs) hacc) (hQ.tail hs) h
    · cases h
  | _ => simp only [mergeParts, Option.some.injEq] at h; subst h; exact ha

theorem merge_q {s r : Term} (hs : Q s) (h : merge s = some r) : Q r := by
  simp only [merge] at h
  split at h
  · cases hf : mergeParts [] s with
    | none => simp [hf] at h
    | some f =>
      simp only [hf, Option.map_some, Option.some.injEq] at h
      subst h
      exact (ofRev_q hQ (mergeParts_all hQ (by simp) hs hf) hQ.nil rfl).1
  · cases h

end Merge

/-- `'unit.merge'` gives a closed result for a closed operand. -/
theorem merge_closed {s r : Term} (hs : closed s) (h : merge s = some r) : closed r :=
  merge_q (StructClosed.closedAt 0) hs h

/-- `'unit.merge'` gives a well-formed result for a well-formed operand. -/
theorem merge_wf {s r : Term} (hs : WF s) (h : merge s = some r) : WF r :=
  merge_q StructClosed.wf hs h

/-! ## `'unit.rebase'` gives closed, well-formed results -/

theorem closedAt_path {k : Nat} (P : List String) (t : Term) :
    closedAt k (path P t) = closedAt k t := by
  induction P generalizing t with
  | nil => rfl
  | cons l P ih => exact (ih (proj t l)).trans rfl

theorem wf_path (P : List String) (t : Term) : WF (path P t) ↔ WF t := by
  induction P generalizing t with
  | nil => exact Iff.rfl
  | cons l P ih => exact ih (proj t l)

theorem closedAt_ins {k : Nat} (P : List String) (t : Term) :
    closedAt k (ins P t) = closedAt k t := by
  induction t with
  | proj t l ih => simp only [ins, closedAt, ih]
  | _ => simp only [ins, closedAt_path]

theorem wf_ins (P : List String) (t : Term) : WF (ins P t) ↔ WF t := by
  induction t with
  | proj t l ih => simp only [ins, WF, ih]
  | _ => simp only [ins, wf_path]

theorem rebaseTerm_closedAt {P : List String} {d k : Nat} {t t' : Term}
    (h : rebaseTerm P d t = some t') (ht : closedAt k t = true) : closedAt k t' = true := by
  induction t generalizing d k t' with
  | var n =>
    simp only [rebaseTerm] at h
    split at h
    · cases h
    · cases h; exact ht
  | lam t ih =>
    simp only [rebaseTerm, Option.map_eq_some_iff] at h
    obtain ⟨t₁, h1, rfl⟩ := h
    exact ih (t' := t₁) h1 ht
  | app a b iha ihb =>
    simp only [rebaseTerm] at h
    split at h
    · rename_i a' b' ha hb
      cases h
      simp only [closedAt, Bool.and_eq_true] at ht ⊢
      exact ⟨iha ha ht.1, ihb hb ht.2⟩
    · cases h
  | snil => simp only [rebaseTerm, Option.some.injEq] at h; subst h; rfl
  | scons l t r iht ihr =>
    simp only [rebaseTerm] at h
    split at h
    · rename_i t₁ r₁ h1 h2
      cases h
      simp only [closedAt, Bool.and_eq_true] at ht ⊢
      exact ⟨iht h1 ht.1, ihr h2 ht.2⟩
    · cases h
  | proj t l ih =>
    simp only [rebaseTerm] at h
    split at h
    · cases h; simp only [closedAt, closedAt_ins]; exact ht
    · simp only [Option.map_eq_some_iff] at h
      obtain ⟨t₁, h1, rfl⟩ := h
      exact ih (t' := t₁) h1 ht
  | bytes b => simp only [rebaseTerm, Option.some.injEq] at h; subst h; rfl
  | fix t ih =>
    simp only [rebaseTerm, Option.map_eq_some_iff] at h
    obtain ⟨t₁, h1, rfl⟩ := h
    exact ih (t' := t₁) h1 ht

theorem rebaseTerm_isStruct {P : List String} {d : Nat} {r r' : Term}
    (h : rebaseTerm P d r = some r') (hr : isStruct r = true) : isStruct r' = true := by
  cases r <;> simp only [isStruct, Bool.false_eq_true] at hr <;>
    simp only [rebaseTerm, Option.some.injEq] at h
  · subst h; rfl
  · split at h
    · cases h; rfl
    · cases h

theorem rebaseTerm_wf {P : List String} {d : Nat} {t t' : Term}
    (h : rebaseTerm P d t = some t') (ht : WF t) : WF t' := by
  induction t generalizing d t' with
  | var n =>
    simp only [rebaseTerm] at h
    split at h
    · cases h
    · cases h; exact ht
  | lam t ih =>
    simp only [rebaseTerm, Option.map_eq_some_iff] at h
    obtain ⟨t₁, h1, rfl⟩ := h
    exact ih (t' := t₁) h1 ht
  | app a b iha ihb =>
    simp only [rebaseTerm] at h
    split at h
    · rename_i a' b' ha hb
      cases h
      exact ⟨iha ha ht.1, ihb hb ht.2⟩
    · cases h
  | snil => simp only [rebaseTerm, Option.some.injEq] at h; subst h; trivial
  | scons l t r iht ihr =>
    simp only [rebaseTerm] at h
    split at h
    · rename_i t₁ r₁ h1 h2
      cases h
      exact ⟨iht h1 ht.1, ihr h2 ht.2.1, rebaseTerm_isStruct h2 ht.2.2⟩
    · cases h
  | proj t l ih =>
    simp only [rebaseTerm] at h
    split at h
    · cases h; exact (wf_ins P t).mpr ht
    · simp only [Option.map_eq_some_iff] at h
      obtain ⟨t₁, h1, rfl⟩ := h
      exact ih (t' := t₁) h1 ht
  | bytes b => simp only [rebaseTerm, Option.some.injEq] at h; subst h; trivial
  | fix t ih =>
    simp only [rebaseTerm, Option.map_eq_some_iff] at h
    obtain ⟨t₁, h1, rfl⟩ := h
    exact ih (t' := t₁) h1 ht

theorem rebaseBody_closedAt {P : List String} {k : Nat} {b b' : Term}
    (h : rebaseBody P b = some b') (hb : closedAt k b = true) : closedAt k b' = true := by
  cases b <;> simp only [rebaseBody, reduceCtorEq] at h
  simp only [Option.map_eq_some_iff] at h
  obtain ⟨t₁, h1, rfl⟩ := h
  exact rebaseTerm_closedAt (t' := t₁) h1 hb

theorem rebaseBody_wf {P : List String} {b b' : Term} (h : rebaseBody P b = some b') (hb : WF b) :
    WF b' := by
  cases b <;> simp only [rebaseBody, reduceCtorEq] at h
  simp only [Option.map_eq_some_iff] at h
  obtain ⟨t₁, h1, rfl⟩ := h
  exact rebaseTerm_wf (t' := t₁) h1 hb

theorem rebaseNs_closedAt {P : List String} {k : Nat} {e : Bool} {s s' : Term}
    (h : rebaseNs P e s = some s') (hc : closedAt k s = true) : closedAt k s' = true := by
  induction s generalizing e s' with
  | scons l v r ihv ihr =>
    simp only [rebaseNs] at h
    split at h
    · rename_i v₁ r₁ hv hr
      cases h
      simp only [closedAt, Bool.and_eq_true] at hc ⊢
      refine ⟨?_, ihr hr hc.2⟩
      split at hv
      · exact rebaseBody_closedAt hv hc.1
      · split at hv
        · exact ihv hv hc.1
        · split at hv
          · cases hv; exact hc.1
          · cases hv
    · cases h
  | snil => simp only [rebaseNs, Option.some.injEq] at h; subst h; rfl
  | _ => simp [rebaseNs] at h

theorem rebaseNs_wf {P : List String} {e : Bool} {s s' : Term}
    (h : rebaseNs P e s = some s') (hw : WF s) : WF s' ∧ isStruct s' = true := by
  induction s generalizing e s' with
  | scons l v r ihv ihr =>
    simp only [rebaseNs] at h
    split at h
    · rename_i v₁ r₁ hv hr
      cases h
      obtain ⟨hr1, hr2⟩ := ihr hr hw.2.1
      refine ⟨⟨?_, hr1, hr2⟩, rfl⟩
      split at hv
      · exact rebaseBody_wf hv hw.1
      · split at hv
        · exact (ihv hv hw.1).1
        · split at hv
          · cases hv; exact hw.1
          · cases hv
    · cases h
  | snil => simp only [rebaseNs, Option.some.injEq] at h; subst h; exact ⟨trivial, rfl⟩
  | _ => simp [rebaseNs] at h

theorem closedAt_nest {k : Nat} (P : List String) {t : Term} (hc : closedAt k t = true) :
    closedAt k (nest P t) = true := by
  induction P with
  | nil => exact hc
  | cons l P ih =>
    simp only [nest, List.foldr] at ih ⊢
    simp [closedAt, ih]

theorem wf_nest (P : List String) {t : Term} (hw : WF t) : WF (nest P t) := by
  induction P with
  | nil => exact hw
  | cons l P ih =>
    simp only [nest, List.foldr] at ih ⊢
    exact ⟨ih, trivial, rfl⟩

/-- `rebase` gives `nest P x'` with `x'` the rebased `X`. -/
theorem rebase_inv {s r : Term} (h : rebase s = some r) :
    ∃ l₁ l₂ p x P x', s = scons l₁ p (scons l₂ x snil) ∧ rebaseNs P (isEntry x) x = some x' ∧
      r = nest P x' := by
  match s, h with
  | scons _ p (scons _ x snil), h =>
    simp only [rebase] at h
    split at h
    · split at h
      · rename_i P _
        simp only [Option.map_eq_some_iff] at h
        obtain ⟨x', hx, rfl⟩ := h
        exact ⟨_, _, _, _, _, _, rfl, hx, rfl⟩
      · cases h
    · cases h

/-- `'unit.rebase'` gives a closed result for a closed operand. -/
theorem rebase_closed {s r : Term} (hs : closed s) (h : rebase s = some r) : closed r := by
  obtain ⟨_, _, _, _, P, _, rfl, hx, rfl⟩ := rebase_inv h
  simp only [closed, closedAt, Bool.and_eq_true] at hs
  exact closedAt_nest P (rebaseNs_closedAt hx hs.2.1)

/-- `'unit.rebase'` gives a well-formed result for a well-formed operand. -/
theorem rebase_wf {s r : Term} (hw : WF s) (h : rebase s = some r) : WF r := by
  obtain ⟨_, _, _, _, P, _, rfl, hx, rfl⟩ := rebase_inv h
  exact wf_nest P (rebaseNs_wf hx hw.2.1.1).1

/-! ## `'unit.make_reducible'` gives closed, well-formed results -/

theorem isStruct_runRegions (t : Term) : isStruct (runRegions t) = isStruct t := by
  cases t with
  | app a b => cases a <;> cases b <;> simp only [runRegions] <;> (try split) <;> rfl
  | _ => rfl

theorem runRegions_closedAt {k : Nat} {t : Term} (h : closedAt k t = true) :
    closedAt k (runRegions t) = true := by
  induction t generalizing k with
  | app a b iha ihb =>
    simp only [closedAt, Bool.and_eq_true] at h
    have h1 := iha h.1
    have h2 := ihb h.2
    cases a <;> cases b <;> simp only [runRegions] at h1 h2 ⊢ <;> (try split) <;>
      simp_all [closedAt]
  | lam t ih => exact ih h
  | scons l t r iht ihr =>
    simp only [runRegions, closedAt, Bool.and_eq_true] at h ⊢; exact ⟨iht h.1, ihr h.2⟩
  | proj t l ih => exact ih h
  | fix t ih => exact ih h
  | _ => exact h

theorem runRegions_wf {t : Term} (h : WF t) : WF (runRegions t) := by
  induction t with
  | app a b iha ihb =>
    have h1 := iha h.1
    have h2 := ihb h.2
    cases a <;> cases b <;> simp only [runRegions] at h1 h2 ⊢ <;> (try split) <;>
      simp_all [WF]
  | lam t ih => exact ih h
  | scons l t r iht ihr => exact ⟨iht h.1, ihr h.2.1, by rw [isStruct_runRegions]; exact h.2.2⟩
  | proj t l ih => exact ih h
  | fix t ih => exact ih h
  | _ => exact h

theorem closedAt_lookup {k : Nat} {s u : Term} {l : String} (hs : closedAt k s = true)
    (h : lookup s l = some u) : closedAt k u = true :=
  (StructClosed.closedAt k).lookup hs h

theorem hoistPart_closedAt {k : Nat} (l : String) {t : Term} (h : closedAt k t = true) :
    closedAt (k + 1) (hoistPart l t) = true := by
  cases t with
  | lam c =>
    simp only [hoistPart]
    split
    · exact h
    · exact closedAt_mono (t := lam c) h (by omega)
  | _ => exact closedAt_mono h (by omega)

theorem hoistInits_closedAt {k : Nat} {t : Term} (h : closedAt k t = true) :
    closedAt (k + 1) (hoistInits t) = true := by
  induction t with
  | scons l t r _ ihr =>
    simp only [hoistInits, closedAt, Bool.and_eq_true] at h ⊢
    exact ⟨hoistPart_closedAt l h.1, ihr h.2⟩
  | _ => exact closedAt_mono h (by omega)

theorem hoistPart_wf (l : String) {t : Term} (h : WF t) : WF (hoistPart l t) := by
  cases t with
  | lam c =>
    simp only [hoistPart]
    split
    · exact h
    · exact h
  | _ => exact h

theorem isStruct_hoistInits (t : Term) : isStruct (hoistInits t) = isStruct t := by
  cases t <;> rfl

theorem hoistInits_wf {t : Term} (h : WF t) : WF (hoistInits t) := by
  induction t with
  | scons l t r _ ihr =>
    exact ⟨hoistPart_wf l h.1, ihr h.2.1, by rw [isStruct_hoistInits]; exact h.2.2⟩
  | _ => simpa only [hoistInits] using h

theorem reducibleNs_closedAt {k : Nat} {s s' : Term} (h : reducibleNs s = some s')
    (hc : closedAt k s = true) : closedAt (k + 1) s' = true := by
  induction s generalizing s' with
  | scons l v r ihv ihr =>
    simp only [reducibleNs] at h
    split at h
    · rename_i v₁ r₁ hv hr
      cases h
      simp only [closedAt, Bool.and_eq_true] at hc ⊢
      refine ⟨?_, ihr hr hc.2⟩
      split at hv
      · split at hv
        · split at hv
          · cases hv; exact hoistInits_closedAt hc.1
          · cases hv
        · rename_i R hb
          cases hv
          have := closedAt_lookup hc.1 hb
          exact runRegions_closedAt (t := lam R) this
        · cases hv
      · split at hv
        · exact ihv hv hc.1
        · split at hv
          · cases hv; exact closedAt_mono hc.1 (by omega)
          · cases hv
    · cases h
  | snil => simp only [reducibleNs, Option.some.injEq] at h; subst h; rfl
  | _ => simp [reducibleNs] at h

theorem reducibleNs_wf {s s' : Term} (h : reducibleNs s = some s') (hw : WF s) :
    WF s' ∧ isStruct s' = true := by
  induction s generalizing s' with
  | scons l v r ihv ihr =>
    simp only [reducibleNs] at h
    split at h
    · rename_i v₁ r₁ hv hr
      cases h
      obtain ⟨hr1, hr2⟩ := ihr hr hw.2.1
      refine ⟨⟨?_, hr1, hr2⟩, rfl⟩
      split at hv
      · split at hv
        · split at hv
          · cases hv; exact hoistInits_wf hw.1
          · cases hv
        · rename_i R hb
          cases hv
          have := WF.lookup hw.1 hb
          exact runRegions_wf (t := lam R) this
        · cases hv
      · split at hv
        · exact (ihv hv hw.1).1
        · split at hv
          · cases hv; exact hw.1
          · cases hv
    · cases h
  | snil => simp only [reducibleNs, Option.some.injEq] at h; subst h; exact ⟨trivial, rfl⟩
  | _ => simp [reducibleNs] at h

/-- `'unit.make_reducible'` gives a closed result for a closed operand. -/
theorem makeReducible_closed {s r : Term} (hs : closed s) (h : makeReducible s = some r) :
    closed r := by
  simp only [makeReducible] at h
  split at h
  · simp only [Option.map_eq_some_iff] at h
    obtain ⟨N, hN, rfl⟩ := h
    exact reducibleNs_closedAt hN hs
  · cases h

/-- `'unit.make_reducible'` gives a well-formed result for a well-formed operand. -/
theorem makeReducible_wf {s r : Term} (hw : WF s) (h : makeReducible s = some r) : WF r := by
  simp only [makeReducible] at h
  split at h
  · simp only [Option.map_eq_some_iff] at h
    obtain ⟨N, hN, rfl⟩ := h
    exact (reducibleNs_wf hN hw).1
  · cases h

/-! ## The table of the unit tools -/

/-- `WF`, as a test. -/
def isWF : Term → Bool
  | lam t => isWF t
  | app a b => isWF a && isWF b
  | scons _ t r => isWF t && isWF r && isStruct r
  | proj t _ => isWF t
  | fix t => isWF t
  | _ => true

theorem isWF_iff (t : Term) : isWF t = true ↔ WF t := by
  induction t <;> simp_all [isWF, WF, and_assoc]

/-- The opcode names, as byte arrays. -/
def mergeName : Bytes := "unit.merge".toUTF8.data.toList
def rebaseName : Bytes := "unit.rebase".toUTF8.data.toList
def makeReducibleName : Bytes := "unit.make_reducible".toUTF8.data.toList

/-- The unit tools as an opcode table. E-Opcode only reads closed operands, and Python's
structs always end in `snil`; the table reads only such operands. -/
def unitOps (b : Bytes) (s : Term) : Option Term :=
  if closedAt 0 s && isWF s then
    if b = mergeName then merge s
    else if b = rebaseName then rebase s
    else if b = makeReducibleName then makeReducible s
    else none
  else none

/-- The unit tools give closed, well-formed results. -/
theorem unitOps_ok : OpOK unitOps := by
  have key : ∀ {b s r}, unitOps b s = some r → closed r ∧ WF r := by
    intro b s r h
    simp only [unitOps] at h
    split at h
    · rename_i hs
      simp only [Bool.and_eq_true] at hs
      have hc : closed s := hs.1
      have hw : WF s := (isWF_iff s).mp hs.2
      split at h
      · exact ⟨merge_closed hc h, merge_wf hw h⟩
      · split at h
        · exact ⟨rebase_closed hc h, rebase_wf hw h⟩
        · split at h
          · exact ⟨makeReducible_closed hc h, makeReducible_wf hw h⟩
          · cases h
    · cases h
  exact ⟨fun h => (key h).1, fun h => (key h).2⟩

/-- The names of the unit tools. -/
def isUnitName (b : Bytes) : Bool := b == mergeName || b == rebaseName || b == makeReducibleName

/-- A table with the unit tools added. -/
def withUnitOps (op : Bytes → Term → Option Term) (b : Bytes) (s : Term) : Option Term :=
  if isUnitName b then unitOps b s else op b s

/-- Adding the unit tools to a table that satisfies `OpOK` gives one that does. -/
theorem withUnitOps_ok {op : Bytes → Term → Option Term} (hop : OpOK op) :
    OpOK (withUnitOps op) := by
  constructor
  · intro b s r h
    simp only [withUnitOps] at h
    split at h
    · exact unitOps_ok.closed h
    · exact hop.closed h
  · intro b s r h
    simp only [withUnitOps] at h
    split at h
    · exact unitOps_ok.wf h
    · exact hop.wf h

/-! ## Rebasing is substituting `g := g.P` -/

/-- `g := g.P` for `g` the index `d`. -/
def prefixAt (P : List String) (d : Nat) (n : Nat) : Term :=
  if n = d then path P (var d) else var n

theorem ren_path (ξ : Nat → Nat) (P : List String) (t : Term) :
    ren ξ (path P t) = path P (ren ξ t) := by
  induction P generalizing t with
  | nil => rfl
  | cons l P ih => exact ih (proj t l)

theorem subst_path (σ : Nat → Term) (P : List String) (t : Term) :
    subst σ (path P t) = path P (subst σ t) := by
  induction P generalizing t with
  | nil => rfl
  | cons l P ih => exact ih (proj t l)

theorem ups_prefixAt (P : List String) (d : Nat) : ups (prefixAt P d) = prefixAt P (d + 1) := by
  funext n
  cases n with
  | zero => simp [ups, prefixAt]
  | succ n =>
    simp only [ups, prefixAt]
    by_cases hn : n = d
    · subst hn; simp [ren_path, ren]
    · simp [hn, ren]

theorem subst_ins {P : List String} {d : Nat} {t : Term} (h : rootedAt d t = true) :
    subst (prefixAt P d) t = ins P t := by
  induction t with
  | var n =>
    simp only [rootedAt, beq_iff_eq] at h
    subst h
    simp [subst, prefixAt, ins]
  | proj t l ih => simp only [rootedAt] at h; simp only [subst, ins, ih h]
  | _ => simp [rootedAt] at h

/-- Where `rebaseTerm` gives a result, it is the substitution `g := g.P`. -/
theorem rebaseTerm_subst {P : List String} {d : Nat} {t t' : Term}
    (h : rebaseTerm P d t = some t') : t' = subst (prefixAt P d) t := by
  induction t generalizing d t' with
  | var n =>
    simp only [rebaseTerm] at h
    split at h
    · cases h
    · rename_i hn; cases h; simp [subst, prefixAt, hn]
  | lam t ih =>
    simp only [rebaseTerm, Option.map_eq_some_iff] at h
    obtain ⟨t₁, h1, rfl⟩ := h
    simp only [subst, ups_prefixAt, ih h1]
  | app a b iha ihb =>
    simp only [rebaseTerm] at h
    split at h
    · rename_i a' b' ha hb
      cases h
      simp only [subst, iha ha, ihb hb]
    · cases h
  | snil => simp only [rebaseTerm, Option.some.injEq] at h; subst h; rfl
  | scons l t r iht ihr =>
    simp only [rebaseTerm] at h
    split at h
    · rename_i t₁ r₁ h1 h2
      cases h
      simp only [subst, iht h1, ihr h2]
    · cases h
  | proj t l ih =>
    simp only [rebaseTerm] at h
    split at h
    · rename_i hr; cases h; simp only [subst, subst_ins hr]
    · simp only [Option.map_eq_some_iff] at h
      obtain ⟨t₁, h1, rfl⟩ := h
      simp only [subst, ih h1]
  | bytes b => simp only [rebaseTerm, Option.some.injEq] at h; subst h; rfl
  | fix t ih =>
    simp only [rebaseTerm, Option.map_eq_some_iff] at h
    obtain ⟨t₁, h1, rfl⟩ := h
    simp only [subst, ih h1]

/-- Rebasing a body `λg. b` under `P` gives `λg. b[g := g.P]`. -/
theorem rebaseBody_subst {P : List String} {b b' : Term} (h : rebaseBody P (lam b) = some b') :
    b' = lam (subst (prefixAt P 0) b) := by
  simp only [rebaseBody, Option.map_eq_some_iff] at h
  obtain ⟨t₁, h1, rfl⟩ := h
  rw [rebaseTerm_subst h1]

/-! ## Rebasing keeps the meaning of a call -/

section Semantics

variable {op : Bytes → Term → Option Term}

/-- Substitution goes through parallel steps of the substituted terms. -/
theorem Par.subst_congr (hop : OpOK op) {σ τ : Nat → Term} (h : ∀ n, Par op (σ n) (τ n))
    (t : Term) : Par op (Oymomo.subst σ t) (Oymomo.subst τ t) := by
  induction t generalizing σ τ with
  | var n => exact h n
  | lam t ih => exact .lam (ih (Par.ups hop h))
  | app a b iha ihb => exact .app (iha h) (ihb h)
  | snil => exact .snil
  | scons l t r iht ihr => exact .scons (iht h) (ihr h)
  | proj t l ih => exact .proj (ih h)
  | bytes b => exact .bytes b
  | fix t ih => exact .fix (ih h)

/-- E-Beta's substitution goes through steps of the substituted term. -/
theorem Star.subst_inst (hop : OpOK op) {u u' : Term} (h : Star (Step op) u u') (t : Term) :
    Star (Step op) (Oymomo.subst (inst u) t) (Oymomo.subst (inst u') t) := by
  induction h with
  | refl => exact .refl _
  | tail _ hs ih => exact ih.trans (Par.subst_congr hop (Par.inst hs.par) t).star

/-- A normal form reduces only to itself. -/
theorem Star.nf_eq {n c : Term} (h : Star (Step op) n c) (hn : isNF op n = true) : c = n := by
  induction h with
  | refl => rfl
  | tail _ hs ih => subst ih; exact absurd hs (isNF_sound hn)

/-- Calling the rebased body `b'` with an instance `G'` whose `G'.P` reduces to `G`, and
calling the original body `λg. b` with `G`, both reduce to `b[g := G]`. -/
theorem rebase_call (hop : OpOK op) {P : List String} {b b' G G' : Term}
    (h : rebaseBody P (lam b) = some b') (hG' : isValue G' = true) (hG : isValue G = true)
    (hP : Star (Step op) (path P G') G) :
    Star (Step op) (app b' G') (subst (inst G) b) ∧
      Star (Step op) (app (lam b) G) (subst (inst G) b) := by
  refine ⟨?_, .single (.beta hG)⟩
  rw [rebaseBody_subst h]
  refine Star.head (.beta hG') ?_
  have : subst (inst G') (subst (prefixAt P 0) b) = subst (inst (path P G')) b := by
    rw [subst_subst]
    congr 1
    funext n
    cases n with
    | zero => simp [prefixAt, subst_path, subst, inst]
    | succ n => simp [prefixAt, subst, inst]
  rw [this]
  exact Star.subst_inst hop hP b

/-- So a call `b' G' u` of the rebased entry reaches every normal form that the call
`(λg. b) G u` of the original entry reaches. -/
theorem rebase_call_nf (hop : OpOK op) {P : List String} {b b' G G' u N : Term}
    (h : rebaseBody P (lam b) = some b') (hG' : isValue G' = true) (hG : isValue G = true)
    (hP : Star (Step op) (path P G') G) (hN : Star (Step op) (app (app (lam b) G) u) N)
    (hn : isNF op N = true) : Star (Step op) (app (app b' G') u) N := by
  obtain ⟨h1, _⟩ := rebase_call hop h hG' hG hP
  have h1u := Star.map (fun x => app x u) (fun hs => Step.app1 hs) h1
  have h2u : Star (Step op) (app (app (lam b) G) u) (app (subst (inst G) b) u) :=
    .single (.app1 (.beta hG))
  obtain ⟨c, hNc, hc⟩ := confluence hop hN h2u
  rw [Star.nf_eq hNc hn] at hc
  exact h1u.trans hc

end Semantics

end Oymomo
