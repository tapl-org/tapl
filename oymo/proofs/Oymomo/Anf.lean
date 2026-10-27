-- SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

import Oymomo.Reduction

/-!
# ANF terms are normal forms

ANF with de Bruijn indices. Every variable is a `var`: the grammar does not tell
the module, the arguments, a region and a value apart (the verifier does), and the
proof does not need to.

* `Path` `P ::= x | P.l`.
* `Operand` `Q ::= P | D`, `D` data; `Operands`: a struct of them.
* `Op`: an instruction `O {lᵢ = Qᵢ}`, `O ::= P | b`: a call, or an opcode call
  that E-Opcode does not compute.
* `Jump` `J ::= P Q₁ ⋯ Qₙ`; `Jumps`: a struct of them, the arms of a branch.
* `Terminal` `T ::= Q | J | {Jᵢ} P | R`.
* `Expr` `E ::= let x = O {lᵢ = Qᵢ} in E | T`, the `let` being `(λx. E) (O {…})`.
* `Block` `K ::= E | λx₁. ⋯ λxₙ. E`; `Blocks`: a struct of them.
* `Region` `R ::= x [] (λx. {lᵢ = Kᵢ})`, `0 < k`, field 0 an expression.

`anf_normal`: a term in ANF has no step, regions included.
-/

namespace Oymomo
open Term

variable {op : Bytes → Term → Option Bytes}

inductive Path : Term → Prop
  | var (n : Nat) : Path (var n)
  | proj {p : Term} (l : String) : Path p → Path (proj p l)

inductive Operand : Term → Prop
  | path {p : Term} : Path p → Operand p
  | data {d : Term} : isData d = true → Operand d

/-- A struct of operands. -/
inductive Operands : Term → Prop
  | snil : Operands snil
  | scons {l : String} {q r : Term} : Operand q → Operands r → Operands (scons l q r)

variable (op) in
/-- An instruction: an opcode call that E-Opcode does not compute, or a call. -/
inductive Op : Term → Prop
  | opcode {b : Bytes} {s : Term} :
      Operands s → (∀ b', isData s = true → op b s ≠ some b') → Op (app (bytes b) s)
  | call {g s : Term} : Path g → Operands s → Op (app g s)

/-- A path applied to operands, one by one. -/
inductive Jump : Term → Prop
  | head {p : Term} : Path p → Jump p
  | arg {j q : Term} : Jump j → Operand q → Jump (app j q)

/-- A struct of jumps: the arms of a branch. -/
inductive Jumps : Term → Prop
  | snil : Jumps snil
  | scons {l : String} {j s : Term} : Jump j → Jumps s → Jumps (scons l j s)

variable (op) in
mutual
  inductive Terminal : Term → Prop
    | ret {q : Term} : Operand q → Terminal q
    | jump {j : Term} : Jump j → Terminal j
    | branch {s c : Term} : Jumps s → Path c → Terminal (app s c)
    | region {r : Term} : Region r → Terminal r

  inductive Expr : Term → Prop
    | let_ {e o : Term} : Op op o → Expr e → Expr (app (lam e) o)
    | term {t : Term} : Terminal t → Expr t

  /-- An expression, or `λ`s taking the block's parameters. -/
  inductive Block : Term → Prop
    | expr {e : Term} : Expr e → Block e
    | lam {k : Term} : Block k → Block (lam k)

  /-- A struct of blocks. -/
  inductive Blocks : Term → Prop
    | snil : Blocks snil
    | scons {l : String} {k s : Term} : Block k → Blocks s → Blocks (scons l k s)

  /-- `x [] (λr. {l₀ = e, lᵢ = Kᵢ})`: field 0 is an expression. -/
  inductive Region : Term → Prop
    | mk {l : String} {e s : Term} (n : Nat) :
        Expr e → Blocks s → Region (app (app (var n) (bytes [])) (lam (scons l e s)))
end

/-! ## No step -/

theorem Path.lookup_none {p : Term} (hp : Path p) (l : String) : lookup p l = none := by
  cases hp <;> rfl

theorem Path.select_none {p : Term} (hp : Path p) (n : Nat) : select p n = none := by
  cases hp <;> rfl

theorem Path.normal {p t' : Term} (hp : Path p) : ¬ Step op p t' := by
  induction hp generalizing t' with
  | var n => intro h; cases h
  | proj l hp ih =>
    intro h
    cases h with
    | proj hl => rw [hp.lookup_none] at hl; cases hl
    | proj1 h => exact ih h
    | fixProj => cases hp

/-- Data has no step. -/
theorem data_normal {d t' : Term} (hd : isData d = true) : ¬ Step op d t' := by
  induction d generalizing t' with
  | snil => intro h; cases h
  | bytes b => intro h; cases h
  | scons l t r iht ihr =>
    simp only [isData, Bool.and_eq_true] at hd
    intro h
    cases h with
    | scons1 h => exact iht hd.1 h
    | scons2 h => exact ihr hd.2 h
  | _ => simp [isData] at hd

theorem Operand.normal {q t' : Term} : Operand q → ¬ Step op q t'
  | .path hp => hp.normal
  | .data hd => data_normal hd

theorem Operands.normal {s t' : Term} (hs : Operands s) : ¬ Step op s t' := by
  induction hs generalizing t' with
  | snil => intro h; cases h
  | scons hq _ ih =>
    intro h
    cases h with
    | scons1 h => exact hq.normal h
    | scons2 h => exact ih h

theorem Operands.not_bytes {s : Term} {b : Bytes} (hs : Operands s) : s ≠ bytes b := by
  cases hs <;> simp

theorem Op.normal {o t' : Term} (ho : Op op o) : ¬ Step op o t' := by
  cases ho with
  | opcode hs hn =>
    intro h
    cases h with
    | index _ => exact absurd rfl hs.not_bytes
    | opcode _ hd ho => exact hn _ hd ho
    | app1 h => cases h
    | app2 h => exact hs.normal h
  | call hg hs =>
    intro h
    cases h with
    | beta _ => cases hg
    | index _ => exact absurd rfl hs.not_bytes
    | opcode _ _ _ => cases hg
    | app1 h => exact hg.normal h
    | app2 h => exact hs.normal h
    | fixApp => cases hg

theorem Op.not_value {o : Term} (ho : Op op o) : isValue o = false := by
  cases ho <;> rfl

theorem Jump.select_none {j : Term} (hj : Jump j) (n : Nat) : select j n = none := by
  cases hj with
  | head hp => exact hp.select_none n
  | arg _ _ => rfl

theorem Jump.normal {j t' : Term} (hj : Jump j) : ¬ Step op j t' := by
  induction hj generalizing t' with
  | head hp => exact hp.normal
  | arg hj hq ih =>
    intro h
    cases h with
    | beta _ => cases hj with | head hp => cases hp
    | index hs => rw [hj.select_none] at hs; cases hs
    | opcode _ _ _ => cases hj with | head hp => cases hp
    | app1 h => exact ih h
    | app2 h => exact hq.normal h
    | fixApp => cases hj with | head hp => cases hp

theorem Jumps.normal {s t' : Term} (hs : Jumps s) : ¬ Step op s t' := by
  induction hs generalizing t' with
  | snil => intro h; cases h
  | scons hj _ ih =>
    intro h
    cases h with
    | scons1 h => exact hj.normal h
    | scons2 h => exact ih h

/-- The runner `x []` has no step. -/
theorem runner_normal {n : Nat} {t' : Term} : ¬ Step op (app (var n) (bytes [])) t' := by
  intro h
  cases h with
  | index hs => cases hs
  | app1 h => cases h
  | app2 h => cases h

mutual
  theorem Terminal.normal {t t' : Term} : Terminal op t → ¬ Step op t t'
    | .ret hq => hq.normal
    | .jump hj => hj.normal
    | .region hr => hr.normal
    | .branch hs hc => fun h => by
      cases h with
      | beta _ => cases hs
      | index _ => cases hc
      | opcode _ _ _ => cases hs
      | app1 h => exact hs.normal h
      | app2 h => exact hc.normal h
      | fixApp => cases hs

  /-- A term in ANF has no step: it is a normal form. -/
  theorem anf_normal {e t' : Term} : Expr op e → ¬ Step op e t'
    | .term ht => ht.normal
    | .let_ ho he => fun h => by
      cases h with
      | beta hv => rw [ho.not_value] at hv; cases hv
      | index _ => cases ho
      | app1 h =>
        cases h with
        | lam h => exact anf_normal he h
      | app2 h => exact ho.normal h

  theorem Block.normal {k t' : Term} : Block op k → ¬ Step op k t'
    | .expr he => anf_normal he
    | .lam hk => fun h => by
      cases h with
      | lam h => exact hk.normal h

  theorem Blocks.normal {s t' : Term} : Blocks op s → ¬ Step op s t'
    | .snil => fun h => by cases h
    | .scons hk hs => fun h => by
      cases h with
      | scons1 h => exact hk.normal h
      | scons2 h => exact hs.normal h

  theorem Region.normal {r t' : Term} : Region op r → ¬ Step op r t'
    | .mk _ he hs => fun h => by
      cases h with
      | app1 h => exact runner_normal h
      | app2 h =>
        cases h with
        | lam h =>
          cases h with
          | scons1 h => exact anf_normal he h
          | scons2 h => exact hs.normal h
end

end Oymomo
