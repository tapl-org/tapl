-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Reduction

/-!
# ANF terms are normal forms (semantics.tex, 7.1 and 7.3)

ANF (7.1) with de Bruijn indices. A let variable and a free variable are both variables
here, so a free path `g` and a path from a let variable are both a `Path`; the proof does
not need to tell them apart.

* `Path`: `x | p.l` (a let variable, a free path, or a field of one).
* `Atom`: a path or a byte array (row 7.1b).
* `Atoms`: a struct of atoms.
* `Call`: `g {lᵢ = aᵢ}` (row 7.1c).
* `Op`: an opcode call that E-Opcode does not compute, or a call (row 7.1d).
* `Ret`: an atom or a call (row 7.1e).
* `Terminal`: a return or jump, or a branch of them on a path (row 7.1f).
* `Expr`: `let x = o in e`, that is `(λx. e) o`, or a terminal (row 7.1g).

`anf_normal`: a term in ANF has no step (7.3, Goal 1.4).
-/

namespace Oymomo
open Term

variable {op : Bytes → Term → Option Bytes}

inductive Path : Term → Prop
  | var (n : Nat) : Path (var n)
  | proj {p : Term} (l : String) : Path p → Path (proj p l)

inductive Atom : Term → Prop
  | path {p : Term} : Path p → Atom p
  | bytes (b : Bytes) : Atom (bytes b)

/-- A struct of atoms. -/
inductive Atoms : Term → Prop
  | snil : Atoms snil
  | scons {l : String} {a r : Term} : Atom a → Atoms r → Atoms (scons l a r)

inductive Call : Term → Prop
  | mk {g s : Term} : Path g → Atoms s → Call (app g s)

variable (op) in
inductive Op : Term → Prop
  | opcode {b : Bytes} {s : Term} :
      Atoms s → (∀ b', isData s = true → op b s ≠ some b') → Op (app (bytes b) s)
  | call {u : Term} : Call u → Op u

inductive Ret : Term → Prop
  | atom {a : Term} : Atom a → Ret a
  | call {u : Term} : Call u → Ret u

/-- A struct of returns and jumps: the arms of a branch. -/
inductive Rets : Term → Prop
  | snil : Rets snil
  | scons {l : String} {r s : Term} : Ret r → Rets s → Rets (scons l r s)

inductive Terminal : Term → Prop
  | ret {r : Term} : Ret r → Terminal r
  | branch {s c : Term} : Rets s → Path c → Terminal (app s c)

variable (op) in
inductive Expr : Term → Prop
  | let_ {e o : Term} : Op op o → Expr e → Expr (app (lam e) o)
  | term {t : Term} : Terminal t → Expr t

/-! ## No step -/

theorem Path.lookup_none {p : Term} (hp : Path p) (l : String) : lookup p l = none := by
  cases hp <;> rfl

theorem Path.normal {p t' : Term} (hp : Path p) : ¬ Step op p t' := by
  induction hp generalizing t' with
  | var n => intro h; cases h
  | proj l hp ih =>
    intro h
    cases h with
    | proj hl => rw [hp.lookup_none] at hl; cases hl
    | proj1 h => exact ih h

theorem Atom.normal {a t' : Term} (ha : Atom a) : ¬ Step op a t' := by
  cases ha with
  | path hp => exact hp.normal
  | bytes b => intro h; cases h

theorem Atoms.normal {s t' : Term} (hs : Atoms s) : ¬ Step op s t' := by
  induction hs generalizing t' with
  | snil => intro h; cases h
  | scons ha _ ih =>
    intro h
    cases h with
    | scons1 h => exact ha.normal h
    | scons2 h => exact ih h

theorem Call.normal {u t' : Term} (hu : Call u) : ¬ Step op u t' := by
  cases hu with
  | mk hg hs =>
    intro h
    cases h with
    | beta _ => cases hg
    | index _ => cases hs
    | opcode _ _ _ => cases hg
    | app1 h => exact hg.normal h
    | app2 h => exact hs.normal h

theorem Op.normal {o t' : Term} (ho : Op op o) : ¬ Step op o t' := by
  cases ho with
  | opcode hs hn =>
    intro h
    cases h with
    | index _ => cases hs
    | opcode _ hd ho => exact hn _ hd ho
    | app1 h => cases h
    | app2 h => exact hs.normal h
  | call hu => exact hu.normal

theorem Ret.normal {r t' : Term} (hr : Ret r) : ¬ Step op r t' := by
  cases hr with
  | atom ha => exact ha.normal
  | call hu => exact hu.normal

theorem Rets.normal {s t' : Term} (hs : Rets s) : ¬ Step op s t' := by
  induction hs generalizing t' with
  | snil => intro h; cases h
  | scons hr _ ih =>
    intro h
    cases h with
    | scons1 h => exact hr.normal h
    | scons2 h => exact ih h

theorem Terminal.normal {t t' : Term} (ht : Terminal t) : ¬ Step op t t' := by
  cases ht with
  | ret hr => exact hr.normal
  | branch hs hc =>
    intro h
    cases h with
    | beta _ => cases hs
    | index _ => cases hc
    | opcode _ _ _ => cases hs
    | app1 h => exact hs.normal h
    | app2 h => exact hc.normal h

theorem Op.not_value {o : Term} (ho : Op op o) : isValue o = false := by
  cases ho with
  | opcode _ _ => rfl
  | call hu => cases hu; rfl

/-- A term in ANF has no step: it is a normal form (7.3, Goal 1.4). -/
theorem anf_normal {e t' : Term} (he : Expr op e) : ¬ Step op e t' := by
  induction he generalizing t' with
  | let_ ho _ ih =>
    intro h
    cases h with
    | beta hv => rw [ho.not_value] at hv; cases hv
    | index _ => cases ho with | call hu => cases hu
    | app1 h =>
      cases h with
      | lam h => exact ih h
    | app2 h => exact ho.normal h
  | term ht => exact ht.normal

end Oymomo
