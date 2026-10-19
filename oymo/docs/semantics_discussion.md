# Semantics discussion: term classes, `stuck t`, effects

Notes from the review of `semantics.tex` (roadmap: `review-rules`, `term-classes`), so
nothing is lost between sessions. We continue the discussion here.

## Where we are

- `semantics.tex` is fully accepted through D37 (6 pages; `make -C oymo/docs` builds it).
  See "State of semantics.tex" below.
- Lean 4 (`oymo/proofs/`, no `sorry`): `Oymomo.confluence` (full β, D27) and
  `Oymomo.classification` / `classification_unique` (D28), both on strict application (D29).
- D1–D10 and Rebuild steps 1–6 are history; the current decisions are D11–D37 (newest first,
  after "Rebuild").

## Open

1. Evaluation strategy `⟶w`: postponed (D18). Not in the doc or in Lean.
2. Shapes of type terms (`{'array', n, 'i32'}`, …): postponed (D23).
3. Built-ins `$fix`, `$struct_to_fields`, `$fields_to_struct`: postponed (D24; maybe dropped).
4. Literal widths: the LLVM width of a literal that no opcode types (e.g. passed straight
   to a block parameter) is not stated.
5. Code, after the Lean proofs (D18): refactor the Python implementation to semantics.tex —
   blocks/modules/declarations/constants/globals (D19, D20, D23, D33), `takes`/`gives` (D35),
   strict application `t !u` and `let x =! t in …` instead of `$seq` (D29), default arm and
   empty byte array = 0 (D23), no forms and no `form_of` (D23), reject duplicate labels (D16).
6. Goldens and tests move to the new syntax with 5.

## Goal

Like the θ-calculus, split all terms into classes so that each class is either
reducible by exactly one rule of the evaluation step `⟶w`, or a value, neutral, or
stuck (`stuck t`). Every class is defined by a grammar (extensionally), not in
words. Then prove in Lean 4 that nothing is missed.

## Rebuild (D11)

**Evaluation strategy dropped for now** (the user): `⟶w` comes back once the full syntax and full β are settled. Until then the classes say "a rule of Section 2 applies at its head".

The user: "becomes so complex. lets simplify. i want simple full beta rule." Then:
"we will gradually add new syntax. so we are start from scratch."

**Names revised again (the user): solo / duet.** A solo has no `~` anywhere; a duet has one somewhere; both are terms. Letters: `t` term, `s` solo, `d` duet (a letter for duets because more duet syntax will come). A duet stands for the pair of its halves; one rule E-Split `d ⟶ term(d)~form(d)` (when `d` is not `s₁~s₂`) replaces the split rules and E-Reclad; E-Duet1/2 step each side of a pair. In `t₁~t₂`, `t₂` is still the form of `t₁`.

The user then restricted the pair to `s~s` (both sides solo), so `~` never nests; closed under reduction because E-Beta only substitutes solos into solos and a duet only splits. Halves: `term(s₁~s₂) = s₁`, `form(s₁~s₂) = s₂`. Syntax is defined once under `t`; `s` and `d` are classes.

Superseded: **formless / formed** (naked/clad dropped; considered matter/substance, strand/duplex). The user's analogy: a formed term is two concurrent computations, each side computed separately, stored as a pair; a formed term can come from a formless one, never back. **Constraint (agreed):** `t ::= formless`, formed = `t₁~t₂` with both sides formless, only at the top. A term written with `~` inside stands for `term(t)~form(t)` (the halves become a definition); the split rules and E-Reclad leave the computation; E-Clad1/2 become E-Formed1/2; confluence carries over from the formless calculus.

Earlier names: a **naked** term has no `~` at its root; a **clad** term is
`naked~naked`. ("Formed" already names the node `t~F` in the code; "form" clashes
with "normal form".) Variables: `t`, `s` (and `F`, `G` as forms) for naked terms;
`p`, `q` for clad terms.

### Step 1: naked terms — variable, abstraction, application — agreed

```
t, s ::= x | λx. t | t s
```

Full β (`⟶`):

```
(λx. t) s ⟶ t[x := s]                         E-Beta
t ⟶ t'  ⟹  t s ⟶ t' s                         E-App1
s ⟶ s'  ⟹  t s ⟶ t s'                         E-App2
t ⟶ t'  ⟹  λx. t ⟶ λx. t'                     E-Abs
```

Substitution is capture-avoiding; terms are equal up to renaming bound variables.

Evaluation step `⟶w` (weak head, normal order): E-Beta and E-App1 only.

Classes for `⟶w` (each term is in exactly one):

```
r  ::= (λx. t) s | r s        reducible (E-Beta at the root, or E-App1)
v  ::= λx. t                  value
ne ::= x | ne t               neutral
```

No stuck class yet: in this fragment no term is wrong. Normal forms of full β:
`nf ::= λx. nf | nn`, `nn ::= x | nn nf`.

Known results: confluence (Church–Rosser; Tait–Martin-Löf parallel reduction);
normal order finds a normal form when one exists; no termination (`(λx. x x)
(λx. x x)`).

### Step 2: signature `s ⇒ t` — agreed

The name is **signature** (the wiki already says "import signature `{...} => R`";
"arrow" is a grammar rule name in the parser).

```
t, s ::= x | λx. t | t s | s ⇒ t
```

```
s ⟶ s'  ⟹  s ⇒ t ⟶ s' ⇒ t                     E-Sig1
t ⟶ t'  ⟹  s ⇒ t ⟶ s ⇒ t'                     E-Sig2
(s ⇒ t) u ⟶ t                                 E-SigApp (option A; step 3 adds drops)
```

(Revised by the user: a signature is a value only when both sides are values, `v ::= λx. t | v ⇒ v`. `⟶w` reduces both sides, left first (W-Sig1/2); E-SigApp fires on `(v₁ ⇒ v₂) t`.) Earlier: `⟶w` does not reduce inside `⇒`, so `s ⇒ t` is a value. D3's
full normalization of forms waits for clad terms. Rejected: no rule for
`(s ⇒ t) u` (it would need the stuck class now).

### Step 3: linearity by default — agreed

Names: **`dup`/`drop` kept** (the user; considered `copy`/`discard` and `clone`/`drop`). Koka's Perceus uses the same pair for compiler-inserted reference counting, the closest match; Oymo is mostly generated, so the jargon is fine.

The user: "lets enable linearity by default too".

```
t, s, k ::= x | λx. t | t s | s ⇒ t | dup s k | drop s t
```

- **Check (local, at each binder):** `t` is linear when, for every subterm
  `λx. u` of `t`, `x` occurs exactly once in `u` (occurrences inside inner `λ`s
  count). The user: free variables are checked before entering an abstraction
  body, so inside the body they are trusted and not checked again. A free variable
  of a body belongs to an outer binder, whose check already counted it, or to the
  environment (`args`/`module` later), which is trusted. `dup` and `drop` are
  ordinary terms (no binders); `k` receives the two copies through its own linear
  binders, e.g. `dup x (λa. λb. a b)`.
- **Rules:**

  ```
  dup v k   ⟶ k v v      (v a closed value)        E-Dup
  drop v t  ⟶ t          (v a closed value)        E-Drop
  (s ⇒ t) u ⟶ drop s (drop u t)                    E-SigApp (revised)
  ```

  plus congruence on every position (E-Dup1/2, E-Drop1/2).
- **Why "closed value":**
  - *value*: never copy or drop work that is not done (later: run-time
    operations);
  - *closed*: copying or dropping a value with a free variable would make that
    variable occur twice or zero times, so the check would not survive reduction
    (linear logic's promotion condition).
  - In a linear calculus free variables never appear or disappear under reduction,
    so "closed value" is stable under reduction and confluence holds.
  - `dup`/`drop` of an open value or a neutral term wait for run time (translation:
    reuse / ignore, like SSA and reference counting).
- **The check survives reduction:** β puts `s` where the single `x` was; E-Dup and
  E-Drop only copy or drop closed terms.
- **Classes for `⟶w`** (`cv` closed value, `ov` open value; "closed" is a side
  condition, like label membership later):

  ```
  r  ::= (λx. t) s | (s ⇒ t) u | dup cv k | drop cv t | r s | dup r k | drop r t
  v  ::= λx. t | s ⇒ t
  ne ::= x | ne t | dup ne k | drop ne t | dup ov k | drop ov t
  ```

  `dup ov k` and `drop ov t` are **neutral** (agreed): like `x t`, they wait for a
  free variable; once the enclosing binder is applied, the value may become closed
  and the term reducible. In a closed program they appear at the head only through
  environment variables, so they are run-time copies/drops.
- **Lean:** if `t` is linear and `t ⟶ t'`, then `t'` is linear. Key lemma: if
  `λx. u` and `s` are linear, then `u[x := s]` is linear.

### Step 4: clad terms — agreed (superseded by D12: no forms)

```
t, s, k, F, G ::= … | t~F          (a clad term p, q; naked = no ~ at the root)
```

**The user's rule (first rule):** when an application has a clad term on one side,
the naked side is read as clad by itself (`t` as `t~t`), and application acts
on each side:

```
(t~F) (s~G) ⟶ (t s)~(F G)
(t~F) s     ⟶ (t s)~(F s)        (= D2's E-AppForm)
t (s~G)     ⟶ (t s)~(t G)                                   E-CladApp
```

- Linearity (the user): form sides are checked too. After splitting each side is
  a naked term, and each must be linear. Formally: a term is linear when both of
  its halves are. Consequence: `λx. x~F` needs `x` once in `F` (its form half
  is `λx. F`).
- Critical pair with E-Beta when the argument is clad:
  `(λx. λz. x) (s~G)` gives `λz. (s~G)` by E-Beta, and `(λz. s)~(λz. G)` by
  E-CladApp. Fix **(a) agreed**: the same rule for every construct. Rejected:
  (b) E-Beta may not fire on a clad argument (a side condition on β).

**Rules of step 4** (halves are deep: `term(t~F) = term(t)`, `form(t~F) =
term(F)`, and part by part through every other construct; both halves have no
`~` inside. Shallow halves were wrong: `(λz. z~F) (s~G)` gives `s~F` by E-Beta
but `s~G` by a shallow split):

```
C[…, p, …] ⟶ C[term of each child] ~ C[form of each child]        E-Split
    (C is λ, application, ⇒, dup or drop; at least one child is clad)
p~q ⟶ term(p) ~ term(q)      (p or q clad)                          E-Reclad
(E-Collapse `t~t ⟶ t` was removed by the user: not needed.)
```

- E-Split instances: `(t~F) (s~G) ⟶ (t s)~(F G)` (E-CladApp),
  `λz. (s~G) ⟶ (λz. s)~(λz. G)`, `(s~G) ⇒ t ⟶ (s ⇒ t)~(G ⇒ t)`,
  `dup (s~G) k ⟶ (dup s k)~(dup G k)`, `drop (s~G) t ⟶ (drop s t)~(drop G t)`.
- E-Reclad: `~` can't split like the others (`(t~F)~G` would give `(t~G)~(F~G)`,
  clad again, forever). A written form replaces the old one, and a form's own
  form is discarded: `(t~F)~(G~H) ⟶ t~G` (old E-Reform and E-FormOfForm).
- E-Collapse was proposed for `drop (s~G) c`, but E-Drop never fires there (a clad
  term is not a value); removed by the user.
- After these rules every clad term is `naked~naked`, at every depth.
- Proof idea for confluence: the halves `h₁`, `h₂` map each term to a naked term;
  a step `t ⟶ t'` gives `hᵢ t ⟶* hᵢ t'`, and E-Split, E-Reclad and E-Collapse
  leave the halves unchanged. Confluence then comes from confluence of the naked
  calculus.

Earlier proposal for this step (superseded by the user's rule): E-Unform,
`E[t~F] ⟶ E[t]`, forms disappear where a term is consumed.

### Step 5: abstraction with a form `λx~s. t` — agreed (accepted)

- A duet. Halves: `term(λx~s. t) = λx. term(t)`, `form(λx~s. t) = s ⇒ [x ↦ s] form(t)` (the form side has no `x`; a function's form is a signature).
- Examples (agreed): `(λx~i32. x) (3~i8) ⟶ 3~i32` (the parameter's form replaces the argument's); `(λx~i32. x) y ⟶ y~(drop y i32)` (the user: this is the right result; the drop waits until `y` is a closed value).
- Linearity stays on both sides. `λx. x~i32` alone is not linear (form side `λx. i32`), but `λx. y (x~i32) (a~(drop x i32))` is: term side `λx. y x a`, form side `λx. y i32 (drop x i32)`.
- Recalled for the user: linearity exists because full β can copy/drop effects (D8); full β is how the semantics says the reduction order doesn't change the result.

### D12: no form syntax — agreed (accepted)

The user: "forget ~ sigil syntax". An opcode like `'add'` takes a struct whose first operand is the type and returns a byte array, which other opcodes use as operands; so every SSA value's type comes from the instruction that defines it, and a type is an ordinary term (it can still be computed at compile time). The only place that needs a type outside an instruction is a declaration without a definition; it gets its own shape: a signature `t ⇒ t` is declaration data (nothing applies it).

- Removed: `~`, `λx~s. t`, solo/duet, halves, E-Split, E-Duet1/2, E-SigApp. Steps 4–5 are superseded.
- `(v ⇒ v) t` matches no rule; it joins the stuck class when that comes (with numbers).
- Linearity is for one world again.
- Why splitting failed (the user's point): after E-Split, a let the shaper keeps (`(λq. …) (sext a)`) has no form next to `q`, so it cannot become an SSA instruction with a type.
- Block parameter (phi) types: settled (declared, D20/D35 `takes`). Literal widths: still open (Open 4).

### Step 6: signature removed; struct, projection, byte arrays, case — agreed (accepted)

- The user: a function form is not needed; a declaration can be a tagged struct (like `{'array', count, element}`), e.g. `{'function', {a = 'i32'}, 'i32'}` and `{'function', 'i32'}` (defined function). Removed: `t ⇒ t`, E-Sig1/2, `v ⇒ v`.
- Struct `{l₁ = t₁, …, lₙ = tₙ}` (ordered, labels may be empty or repeat; data only: never applied) and projection `t.l`.
- E-Proj: `{l₁ = t₁, …, lₙ = tₙ}.l ⟶ drop t₁ (⋯ (drop tₙ tₖ))`, `k` the first field labeled `l`, every other field dropped (linearity). Congruence E-Struct, E-Proj1.
- Values: `λx. t | {…}`. Linearity: fields share out the variables (⊗).
- Wrong terms with no rule (stuck later): a struct applied; `v.l` with `v` an abstraction or a struct without `l`.
- Byte arrays `b` (values; `num(b)` unsigned little-endian). The user: a struct applied to a byte array is allowed only when the struct is a value (all fields values), so it can't act as an `if`; branching is `case`. E-Index: `{l₁ = v₁, …, lₙ = vₙ} b ⟶ drop v₁ (⋯ (drop vₙ vₖ))` with `num(b) = k − 1 < n`, like LLVM `extractvalue`. Class `sv` (struct value). Numbers `n` removed (the user): a byte array can be seen as an unsigned, little-endian number at any time; `case` arms are byte-array literals, E-Index uses `b = k − 1 < n`.
- Numbers `n` (values) and `case t when n₁ then t₁ ⋯ when nₖ then tₖ else t₀` (D9) added: E-Case (`n = nᵢ` → `tᵢ`), E-CaseElse (no match → `t₀`), congruence E-Case1 (scrutinee) and E-CaseArm (any arm, default included). Arms share variables (&): each arm uses the same variables once; discarded arms need no drop. `case ne …` is neutral; a `case` on an abstraction or a struct, a number applied, `n.l` are wrong (stuck later).

### D37: 5/9 as a monospace listing — agreed (accepted)

- The user asked why some text looked bold in 5/9 (Computer Modern Typewriter for byte arrays and keywords next to thin math italic); chose "4d": show 5/9 as plain monospace source, like the draft. `fancyvrb` `Verbatim` (commandchars `@<>`, `@vto` = `\mbox{$\to$}` for →), `upquote` for straight quotes. On accept: drop `formatcom=\color{blue}` from the `Verbatim` options.

### D36: gcd example with sugars, user's layout; entry label back — agreed (accepted)

- The user: "5/9 use sugars in Euclid's gcd" (`let`, `if`), then "format the code so it is easy to read", then gave "my intentional format" (each block `l = {takes = …, body = p →` on one line, the body indented below, `if … then` / `else` on their own lines). Also: "i guess we should return back entry label. and mention that translation just takes first field as an entry, so any label can work there." 5/2 drops "l₀ is empty"; 5/3(3): the translation takes the first field as the entry, any label works; no block jumps to it; full β may reach it by label or position; only the translation rejects such a jump. The user's draft wrote `'icmp eq'`; the user: "keep 'icmp_eq'".

### D35: labels `takes` and `gives` — agreed (accepted)

- The user: "better shorter label names for result_type and param_type". Options: takes/gives, from/to, ptype/rtype, params/returns, dom/cod (`in` is reserved; `ret` is an LLVM instruction). The user weighed from/to (LLVM-like) against takes/gives; agent: LLVM has no keyword for either, `to` is LLVM's cast word and `from` on a block reads as phi predecessors. Chosen: `takes` (parameter types) and `gives` (result type) throughout Section 5.

### D34: effects run as steps at run time; output may depend on the path — agreed (accepted)

- The user (resolving D32's open question): "(x -> {x,x}) (print 'h') can be evaluated to 2 expression: (x->{x,x}) void (output=h) or {print 'h', print 'h'}. then they can evaluate to {void, void} (output=h) or {void, void} (output=hh). … even though they reached same normal form, but their output can be different"; "if you want effect called once, use strict application, which guarantees the first evaluation path".
- Section 4 rewritten: 4/1 "At compile time, reduction never runs an effect"; 4/2 at run time an effect is a step (`p` steps to its result `r`, writing `'h'`), order is free, the normal form doesn't show the output, two paths give `'h'` or `'hh'`; 4/3 strict application forces path 4/2(1), exactly once; any other order and the count of a copied effect are free; 4/4 the translation may follow any path: `{p, p}` may become one or two prints. 1/15(3) now refers to 4/3. Replaces D13's "each effect in the normal form runs once".

### D33: the first block is the entry — agreed (accepted)

- The user: "5/2/2 the parameters and their types are those of the first block (at zero index)". A definition's body is `f → {lᵢ = tᵢ'}_{i<n}` with `0 < n` blocks; the first block (position 0) runs first and gives the parameters; its label is free (`entry` in 5/9 is just a name). 5/7: `m.l` is the body of the first block.
- The user: "should we remove entry label, since entry cannot be reachable from other blocks?" then "yes. but a jump to the first block is not allowed is only for translation. but full-beta can do this." Now `l₀` is empty (the first block has no label); 5/3(3): no block jumps to it (LLVM's entry block has no predecessors); full β may still reach it by position, `(f [00]).body {…}`; only the translation rejects such a jump. 5/9 drops `entry =`.

### D32: struct indices from 0; dropped terms; E-SApp order — agreed (accepted; 4/2 settled in D34)

- The user: "index struct labels starting with 0" — every `{l₁ = t₁, …, lₙ = tₙ}` is now `{l₀ = t₀, …, lₙ₋₁ = tₙ₋₁}` (also `v`, `d`, `x` in Section 5); E-Index `b < n ⟹ {…} b ▷ t_b`; E-Default `… ▷ tₙ₋₁`; E-Opcode `op(b)(d₀, …, dₙ₋₁)`.
- 2/8(1): "full β may reduce e or not, but e is not in the normal form: it is dropped" (was "never runs e"). 2/9: a discarded arm "does not contribute to the normal form" (was "never runs").
- E-SApp1/2 moved after E-App2 (3/4, 3/5).
- The user: "why n-1 in struct fields. use just n. so struct length then becomes n+1". Now `{l₀ = t₀, …, lₙ = tₙ}` (n + 1 fields); `{}` added to rows 5, 8, 9 and 1/14(1); E-Index `b ≤ n ⟹ … ▷ t_b`; E-Default `n < b ⟹ … ▷ tₙ`; E-Opcode `op(b)(d₀, …, dₙ)`.
- The user needed `{}` in the same form ("i want to show this mixed with {l=t} syntax"); chose TAPL-style `{lᵢ = tᵢ}_{i<n}` (n fields, `{}` when n = 0). Rows 5, 8, 9 one form each; 1/14(1) explains; E-Proj `l_j = l ⟹ … ▷ t_j`; E-Index `b < n ⟹ … ▷ t_b`; E-Default `0 < n ≤ b ⟹ … ▷ tₙ₋₁`; E-Opcode `op(b)(dᵢ)_{i<n} = b'`; Section 5 uses `{xᵢ = tᵢ}_{i<n}`. E-Strict moved to after E-Beta (2/2) (user).
- Settled by D34 (was open): the user wants 4/2(1) to say `'h'` may be printed once or twice (the effect isn't observable from the normal form) and 4/2(2) that strict application guarantees once — conflicts with 4/2 "each one runs exactly once" and 4/3 "{p, p} becomes two print instructions, never one"; asked.

### D31: numbered sub-bullets; split points — agreed (accepted)

- The user: "some bullets sentences feels like can be bulleted. sub-bullet with numbers or split if their meanings are different". New list `subpoints`, labels (1), (2), …, referred to as e.g. 1/14(2). Points with several parts got sub-bullets (byte array, struct, opcode call, positions, branch, strict application, `let`, stuck shapes, E-Proj, E-Opcode, E-Strict, definition, block, `m`/`f`; Section 4's examples). Split: the lambda sentences out of 1/10 (now 1/11); "rejected at compile time" out of the stuck point (now 1/24). Section 1 references renumbered.
- On accept: in the preamble, change the `subpoints` label from `{\color{blue}(\arabic*)}` to `(\arabic*)`.

### D30: keep the arrow for abstraction — agreed (accepted)

- The user asked about `\x.t` (doc and source). Agent: `.` is projection, and bodies often start with one (`\p.f.loop.body`); suggested keeping `x → t` (or `\x → t`). The user: "keep arrow. 1/2 comment abstraction instead of lambda. also add a note saying that we used arrow syntax so . dont clash with projection". Row 2's comment is now "abstraction"; 1/10 explains the arrow. The prose still says "lambda" (D22).

### D29: strict application `t !t` replaces the strict term `!t` — agreed (accepted)

- The user: "what if i move the strictness to argument, like: t !t"; after a pros/cons comparison (C strict constructor, A strict application, C′ strict binder `!x → t`): "I choose A. and also ! groupping works same as applciation and let". Keep `=` in `let` and `!` as the sigil (walrus `:=`, `←`, other characters discussed and declined).
- Grammar row 7 `t !t`; values row 8 lose `!v`; E-Strict `t !v ▷ t v`; E-Strict1 replaced by E-SApp1/E-SApp2. Sugar `let x = !t₁ in t₂` is `(x → t₂) !t₁` (`let!` removed). `!` does not change grouping: `f !x y` is `(f !x) y`, `f !(g y)`; in `let`, `t₁` extends to `in`. `!` is not a term on its own.
- Also D28's 1/20 fix 1 applied ("a byte array applied to a value that is not a struct"); gap 2 (`(!v).l`) disappears with A.
- Lean updated: constructor `sapp` (strict application), Step E-Strict `sapp t v ▷ app t v`, E-SApp1/2; Neutral `v !n`, `n !n`; Stuck `s !t`, `t !s`. Both theorems rebuilt, no `sorry`.
- The user: "let x= !t1 in t2, t1 extends to in. but t3 !t1, t1 does not extend. so let one is confusing. maybe ! sigil merge to = sigil like this let x =! t1 in t2". Now `let x =! t₁ in t₂` is `(x → t₂) !(t₁)`; `=!` is one sign (strictness on the binding), so `t₁` extends to `in` as in a plain `let`. Strict application row moved to row 4, after application (user).
- Infix `f ! x` discussed (tight like application, or loose like Haskell's `$!` but left-associative); the user: "lets keep it as it is. t !t".

### D28: Lean classification of normal forms — done (accepted)

- The user: "implement classification theorem". `proofs/Oymomo/Classification.lean`: `Normal op t` (no step); inductive `Neutral op` and `Stuck`; `classification`: a normal form is a value, neutral or stuck; `classification_unique`: the three are pairwise disjoint (for all terms). Axioms: `propext` only; no `sorry`.
- Neutral: a variable; a neutral term applied, projected, or under `!`; `(!v) n`; a struct value applied to a neutral condition; `b n`; a run-time operation `b d` with `op` undefined; a struct with a neutral field and no stuck field.
- Stuck: a stuck term applied, projected, or under `!`; a value head (not a lambda) applied to a stuck term; a struct with a stuck field; `v.l` with no field `l`; `{}` applied to anything; a struct applied to a value that is not a byte array; `b v` with `v` a value that is not a struct, or a struct that is not data.
- A lambda body and a neutral head's argument are not read: `x ({}.a)` is neutral (the program is still rejected, 1/20, since it contains a stuck term).
- Doc differences found (settled: the first fixed in 1/23(3), the second gone with D29): 1/20 says "a byte array applied to a term that is not a struct" — the proof needs "a value" (`b x` waits, neutral); 1/20's `v.l` list misses `!v`.

### D27: Lean 4 proof of confluence — done (accepted)

- The user: "start lean 4 proof". Project `oymo/proofs/` (Lean 4.35.0 via elan, Lake, no Mathlib). Files: `Oymomo/Syntax.lean` (terms, values, data, `lookup`, `select`), `Substitution.lean` (de Bruijn renaming/substitution, composition lemmas), `Reduction.lean` (`Step` = ▷ with every rule of Sections 2–3, `Par` parallel reduction), `Confluence.lean` (Takahashi complete development `cd`, triangle, diamond, `confluence`).
- Theorem `Oymomo.confluence`: `Star (Step op) t a → Star (Step op) t b → ∃ c, Star (Step op) a c ∧ Star (Step op) b c`, for every opcode table `op` (abstract). Axioms: `propext`, `Quot.sound` only; no `sorry`.
- Modelling choices: names are de Bruijn indices (doc: α-equivalence); a struct is a chain `scons l t (… snil)`, E-Struct steps the head field or the tail; labels are not checked for uniqueness (`lookup` takes the first). E-Opcode needs a struct of data (D26), so `op` needs no extra assumption.
- Not in the proof: `⟶w`, stuck/neutral classification, `$fix` and the struct built-ins (postponed, D24).

### D26: opcode operands must be data — agreed (accepted)

- Agent: E-Opcode fired on any values, but a value can still step inside (a lambda body), so `op` could see two different operands for one call and break confluence. The user: "op code can only fire when its body struct or bytearray recursively".
- New class row 9 `d ::= b | {l₁ = d₁, …, lₙ = dₙ}` (data); E-Opcode premise `op(b)(d₁, …, dₙ) = b'`. 2/10 explains; 1/21 adds the stuck term "an opcode call whose operand is a value that is not data". 1/13 drops "A struct is data" (data is now the class name). Point references renumbered (+1).

### D25: struct fields keep commas — agreed (accepted)

- From the user's todo ("wy we need a comma in struct. instead we can use whitespace."). Application is juxtaposition, so whitespace-separated fields would need parentheses around every application, lambda and call in a field (as in Nix lists). The user: "keep commas, and accepted". Surface syntax only; semantics.tex unchanged.

### D24: stuck terms are compile errors — agreed (accepted)

- Stuck today (1/21): a struct applied to a non-byte-array value; the empty struct applied to anything; a byte array applied to a non-struct value; `v.l` on a lambda, byte array, `!v` or struct without `l`.
- Options were (a) compile error, (b) LLVM `unreachable`/poison, (c) an `error` term. The user: "compile error". 1/21: "wrong" renamed "stuck"; a program whose normal form contains a stuck term, anywhere, is rejected at compile time. No stuck class or rule in the doc (D21); Lean will have value/neutral/stuck for the classification theorem.
- The user: "unknown opcode and divizion by zero stay neutral" (run-time operations, not stuck); 1/13 now says `op(b)` is undefined for an opcode it doesn't know.
- Not needed in the Lean proof now: `⟶w`, type-term shapes, `$fix` (Y combinator, or a non-overlapping rule later). `$struct_to_fields`/`$fields_to_struct` would be new rules; the user: "can we add them later. I'm not sure I will keep them in the future or not". Postponed.
- Settled by D26 (was open): Lean needs `op` to be a function whose result doesn't change when an operand steps inside (e.g. defined only on byte arrays and structs of byte arrays).

### D23: gaps against the Python implementation — agreed (accepted)

Agent compared semantics.tex with `src/oymo/oymomo/` and the goldens. The user's answers:
- `let x = t₁ in t₂` is sugar for `(x → t₂) t₁`; `let! x = t₁ in t₂` for `!(x → t₂) t₁` (new). `if c then t₁ else t₂` is sugar for `{t₂, t₁} c`. Both in Section 1.
- `$fix`, `$struct_to_fields`, `$fields_to_struct`: "no need to mention them now".
- Constants `{type, value}` (LLVM `constant`; `m.l` is the value) and global variables `{type, init}` (LLVM `global`; `m.l` is its address, a `ptr`) added to Section 5 (label names are the agent's pick).
- Type shapes (tagged forms `{'array', n, 'i32'}` etc.): postponed.
- Memory: said explicitly; wording "reduction cannot reduce" (not "no result"): `op(b)` is undefined for effects (printing, `alloca`, `load`, `store`) and undefined behavior; reduction has no memory.
- Opcode results are plain byte arrays (the doc is right); the code's `form_of` will be dropped.
- Right ones (the code changes): past-the-end index selects the last field (default arm; new rule E-Default `1 ≤ n ≤ b ⟹ {…} b ▷ tₙ`; a branch takes `then` when `c ≠ 0`); empty byte array reads as 0; no duplicate labels; no forms; `!t` (not `$seq`). Code will be refactored to semantics.tex for blocks, module, declarations.
- The user: "5/9 result and param labels are ambigues. they don't mention that the hold type or value". Renamed `param` → `param_type` (singular: the parameter struct is one struct type, as the body takes one struct) and `result` → `result_type` throughout Section 5.

### D22: lambda written `x → t`; "abstraction" renamed "lambda" — agreed (accepted)

- The user: "to match oymomo syntax, should we use -> sigil for abstraction. and may be rename abstraction to function"; then "yes, but for the arrow use →". Agent advised "lambda", not "function" (function = module definition/declaration, Section 5); applied "lambda".
- `\lam{x}{t}` renders `x → t`; `→` extends as far right as possible (1/9). The macro is blue while under review: on accept, change it in the preamble to `\newcommand{\lam}[2]{#1 \to #2}`.
- Step arrow: the user chose `▷` (`\triangleright`), replacing `⟶`. Macro `\step` is `\mathrel{\new{\triangleright}}` while under review: on accept, change it to `\newcommand{\step}{\mathrel{\triangleright}}`. Substitution `[x ↦ t₂] t₁` unchanged.

### D21: keep only classes used in rules; no num(b), no k — agreed (accepted)

- The user: "v, ne, r keep them if they used in formulas". `v` is used (E-Opcode, E-Strict) and kept; `ne` and `r` are used by no rule and are struck, with the classes point (1/21 now defines only wrong terms), the premises point (1/22) and the struct sentence in 1/17. "Neutral" stays as a prose word (1/23: no rule reduces it yet; waits for a free variable or a run-time operation).
- The user: "dont use num(b). just say that when b is used where number is expected. that bytearray is considered as unsigned and little-endian encoded number". 1/11 says so (`[0100]` is 1); E-Index premise `b = k < n`; other `num(b)` uses become `b`.
- Points "x ranges over…" and "A byte array…" swapped (user); example `[0201]` is 258 (user). `k` dropped: E-Index is `b < n ⟹ {…} b ⟶ t_{b+1}`.

### D20: blocks; m stays free; struct applied to a byte array replaces `if` and `.k` — agreed (accepted)

- The user: "definition labels order: param, result, body"; "m maybe replaced if user wants. see programs_test.py. test_gcd_blocks"; "Yes, m stays free, and so calls are neutral".
- The user: "a block is {param, body} and body is a recursive function. like \f.{entry=...., join=..}". Written: a definition's `body = λf.{entry = block, l = block, …}`; a block `{param, body = λx₁…λxₙ. t}`, param = phi types; jump `f.l.body t…` (LLVM `br`); call `m.l.body.entry.body t…` (m stands for the module with bodies tied). Example: gcd from `tests/oymomo/programs_test.py::test_gcd_blocks`.
- The user: "yes" to the struct form. E-Index `{l₁ = t₁, …, lₙ = tₙ} b ⟶ t_{k+1}` (num(b) = k < n) replaces `if` (E-IfTrue/False, E-If1/2/3) and `.k` (E-ProjPos, E-ProjPos1). Branch `{false = t₂, true = t₁} c`; more fields = LLVM `switch`. Classes: `r` gets `{…} b`, `{…} r`; `ne` gets `{…} ne`. The user's criterion: "my only interest is full-beta confluence with support of manual effect order".
- The definition's `param` repeated the entry block's; the user: "yes" to dropping it. A definition is `{result, body}`; a declaration `{param, result}`.
- Call form: the user wants it "shorter". Now `m.l t₁ … tₙ`: `m.l` stands for the function itself (for a definition, its entry block's body with `f` tied). Example `main` calls `m.gcd [30000000] [12000000]`.
- The user: "block body takes only one struct argument and its form is same as its param value, not a curried one". Now `body = λp. t`, read as `p.xᵢ`; jump `f.l.body {x₁ = t₁, …}`; call `m.l {x₁ = t₁, …}`.

### D19: modules, definitions, declarations — agreed (accepted)

- The user: "definition: {fn = \a.t, param={...}, result=...}. if fn does not exist then decleration, and calling fn is also stuck"; "calling is directly lambda application"; "module: a struct of labeled declerations and definitions. labels act as global names. they refer each other by \m. {...} ---> m.puts.fn"; "find a better label for fn".
- Written as Section 5 "Modules": label `fn` renamed `body` (agent's pick); a definition `{body = λx₁…λxₙ. t, param = {x₁ = t₁, …}, result = t'}` → LLVM `define`; a declaration has no `body` → `declare`; a call is `m.l.body t`.
- Agent's proposal, flagged to the user: the module is never applied, so `m` stays free and calls are neutral (no unfolding, so recursion doesn't loop); the translation emits `call`. If `m` were substituted, a call to a definition reduces (E-Proj, E-Beta) and a call to a declaration is stuck.
- Phi types: the user chose "declare it"; struct form to be proposed.
- `if` vs struct applied to a byte array: the user's only criterion is full-β confluence with manual effect order.

### D18: projection drops effects; postponements — agreed (accepted)

- E-Proj and E-ProjPos discard the other fields even when they hold effects; the user: "this is up to user. if user wants to keep they can use strict mode." Note added to 2/9 with `!(λx.{a = x, b = [01]}.b) e`.
- Stuck class: postponed ("we will discuss about it later").
- Evaluation strategy `⟶w`: postponed.
- All code implementations come after the Lean 4 proof.
- Next: declarations as tagged structs; block parameter (phi) types; the user asks whether to go back to struct-applied-to-byte-array for `if`.

### D17: opcode call `b {…}` — agreed (accepted)

- The user: "lets add application of: b {...} this is a opcode call. and it can be evaluated, or not if undefined behavior, or may be effect".
- `b` names the opcode, the struct holds the operands (`'add' {'i32', a, b}`). `op(b)` is a partial function from operand values to a byte array.
- E-Opcode `b {l₁ = v₁, …, lₙ = vₙ} ⟶ b'` when `op(b)(v₁, …, vₙ) = b'` (compile-time evaluation). No result (effect, undefined behavior) → the call is neutral, a run-time operation; the translation to LLVM emits it as an instruction.
- Classes: `r` gets `b {l=v} (op gives a result) | b r`; `ne` gets `b {l=v} (op gives none) | b ne`. No new congruence rule: E-App2 and E-Struct step the operands.
- Wrong terms: a struct applied to anything; a byte array applied to a non-struct value.

### D16: projection by position; unique labels — agreed (accepted)

- E-Index and struct application removed (`if` branches now; a run-time index into a struct is not valid LLVM anyway). Added `t.k`: positions count every field from 0, labeled or not; a label names one position. E-ProjPos `{l₁ = t₁, …, lₙ = tₙ}.k ⟶ tₖ₊₁` (`k < n`), congruence E-ProjPos1. Both projections become `extractvalue` with a constant index.
- Labels: empty (no label) allowed any number of times; other labels unique (the user; no reason for repeats was found: the wiki only records "labels may repeat, s.a picks the first", likely because labels were optional names on LLVM tuples and `$fields_to_struct` kept duplicates). Code later: reject duplicate labels in the parser and in `$fields_to_struct`.

### D15: strict term `!t` replaces `seq` — agreed (accepted)


### D14: `if` replaces `case` — agreed (accepted)

Without linearity a chain of `if`s can reuse the tested value freely (no `dup`), so `case` (D9) goes. `if t then t₁ else t₂`: E-IfTrue (`[01]` → `t₁`), E-IfFalse (`[00]` → `t₂`), like LLVM `br i1`; congruence E-If1/2/3; any other condition is wrong (stuck later). LLVM's SimplifyCFG recovers `switch` from chains.

### D13: no linearity; `seq` — agreed (accepted)

The user: "dup and drop is too cumbersome. I do not want to restrict user. I believe user is 100% proficient... what i want is full beta confluence, and order where user wants. like i used $seq."

- Removed: `dup`, `drop`, `cv`/`ov`, the linearity section (D8 option D undone); E-Proj and E-Index just return the field.
- Meaning is read from the normal form: reduction never runs an effect (effectful operations are neutral at compile time); full β is confluent, so the normal form is unique; each effect in it runs once, ordered by `seq` and data dependencies. An effect written twice runs twice (the user's choice).
- `seq t₁ t₂`: run `t₁`, pass its result to `t₂`. E-Seq `seq v t ⟶ t v` (only on a value); congruence E-Seq1/2. A `seq` on a run-time operation waits; translation emits it first, the result as an SSA value. It is the only way to order effects and to share one result.
- Translation must not share two occurrences of an effect (it may share pure operations); `shape`'s let sharing must not apply to effects.

## Decisions

### D1: neutral vs stuck — agreed

- A **neutral** term waits for run time; it is not wrong. Examples: `x`, `x t`,
  `args.n`, `{e, t} c` with `c` unknown.
- A **stuck** term is wrong forever. Examples: `5 t`, `{a = t}.b`, `{} 5`.
  (D7 replaces "stuck" with an `error` term.)
- Neutral is about the position of the variable: `(λx. x) y` is reducible
  (E-Beta), not neutral; `y (λx. x)` is neutral.
- Exception named by the user: `n {l = n} ⟶ n`, a number applied to a struct of
  numbers steps (opcodes), so `n t` is not always wrong.

### D1a: the opcode rule — agreed

1. For abstraction, every number is an opcode.
2. `n₀ {lᵢ = oᵢ} ⟶ m~F`; a field is `n` or `n~F`.
3. `op(n₀)` is partial (option B). Where it gives no result (no defined result such
   as division by zero; an effect such as `alloca`, `store`; a layout field) the call
   is a **run-time operation**: a normal form that translation emits, as the code
   does today. Neutral therefore means "waits for run time": a free variable or a
   run-time operation. A constant division by zero stays run-time.
4. Neutral fields make the call neutral (a run-time operation).
5. A non-struct argument is wrong.

### D1b: operand fields — agreed

- `operand ::= n | n~F | {lᵢ = operandᵢ} | ne`; any other field (a `λ`, a function
  form) makes the call wrong.
- `F ⇒ G` is not an operand: in LLVM a function type is not a value (you hold a
  `ptr`); in Oymo function forms only declare external symbols in the `module` form.

### D2: eliminating through a form — agreed (the user's general rule)

- **E-AppForm** `(t~F) s ⟶ (t s)~(F s)`: the result's form is the form applied to
  the argument (`F = λy. G` gives a dependent result form; with a struct form,
  selecting carries the field's form).
- **E-ProjForm** `(t~F).l ⟶ (t.l)~(F.l)`, replacing the old E-ProjForm.
- **E-FuncFormApp** `(F ⇒ G) t ⟶ G`: a declared function's result form flows to its
  calls; the parameter form is dropped (translation reads it from the declaration).
- Checked: confluent with E-Reform.

### D3: forms as terms that compute — agreed

- a. Forms are fully normalized (strong reduction, normal order, also under `λ`).
- b. **E-FormOfForm** `t~(G~F) ⟶ t~G`: the form of a form says nothing about the
  term (keeps two layers). The user chose it over `t~F`. When E-Reform also applies,
  `(s~G)~(H~K)`, E-Reform goes first; both give `s~H`.
- c. A form on an opcode number is accepted (`F {…}` is an opcode call at the form
  level).
- Not decided: should `~` group to the left in the parser? Today `x~'i16'~'i8'`
  means `x~('i16'~'i8') ⟶ x~'i16'`.
- Later (user's correction): a form is never under a binder, so `⟶w` also
  normalizes the form of `λx~F. t` (W-AbsForm) and both sides of `F ⇒ G`
  (W-FuncForm1/2).

### D4: which relation the classes describe — agreed

- The classes, progress and determinism are about `⟶w`.
- Full β is needed eventually: confluence, and later its own normal forms.
- Values are weak: `⟶w` never reduces a `λ`'s body or a struct field, so
  `λx. (λy. y) a` is a value. Forms are reduced (D3).

### D5: Lean project — agreed

- `oymo/proofs/`, a `lake` project; latest stable Lean 4 via `elan`; no Mathlib to
  start. Lean is not installed yet.
- Round one: `Term` (de Bruijn indices, struct fields as a list, `Nat` numbers,
  `String` labels), substitution, every computation rule (`op` a parameter), `⟶w`
  with full normalization of forms, the classes, and proofs of progress,
  exclusivity and determinism.
- Not in round one: confluence, `shape`, translation.

### D6: roadmap — done

- Node `term-classes` under `foundations`: `classes-doc`, `classes-lean`,
  🚫 `classes-check`, 🚫 `classes-code`; 🚫 `conf-lean` under `confluence`.

### D7 (revised): a `stuck t` term — superseded by D24 (stuck terms are compile errors)

The user: "i will introduce `stuck t` syntax instead of error. it works same as
error but when bubbling up, it also keeps the term. main thing is outer term can
know about stuck term existence".

- `stuck t` replaces `error`; users can write it. It keeps the wrong term.
- **Creation (the only new rule kind):** each wrong shape wraps itself, only on
  values (the wrong-shape list of the first version below):
  `{a = t}.b ⟶ stuck ({a = t}.b)`, `5 s ⟶ stuck (5 s)` (non-struct argument),
  `{} c ⟶ stuck ({} c)`.
- **`stuck t` marks the origin.** Full β goes into the parts of `t`, never into
  `t`'s root: `stuck` has congruence rules into `t`'s immediate subterms only. So
  the wrong-shape rule can't fire twice. Context-free: no rule asks "am I inside
  `stuck`"; it is a choice of congruence rules, like reducing under `λ`.
- **Bubbling is a class, not a rule** (like neutral: `x t` has no wrapper). There is
  no bubbling rule; `(stuck u) s` matches no rule (its head is not a `λ`, struct or
  number), so it is a normal form, stuck by its shape:

  ```
  st ::= stuck t | st t | st.l | {lᵢ = tᵢ} st | n₀ {…, l = st, …}
       | st~F | t~st | st ⇒ F | F ⇒ st | λx~st. t
  ```

  The strict positions are the ones of the first version (plus `dup`/`drop` if D8
  option D is chosen). An outer term knows a stuck term exists by this grammar.
- **Not strict** (so not in `st`): a `λ`'s argument, a neutral head's argument, a
  struct field, a `λ` body. `(λx. 5) (stuck u) ⟶ 5`;
  `(λx. x s) (stuck u) ⟶ (stuck u) s`, which is in `st`.
- `st` terms are not values, so a stuck field never fires a wrong-shape rule on the
  outer term (e.g. an opcode call with a stuck field is in `st`, not re-created).
- Classes: **reducible, value, neutral, stuck**, all by grammar. `⟶w` never looks
  inside `stuck t`; `st` terms are `⟶w` normal forms.

1. **What reduces inside `stuck t` — agreed:** the parts of `t`, not its root (the
   user's middle ground between B and E). Options considered:
   - A. Frozen (nothing inside): breaks confluence. In
     `n₀ {a = {x = 1}.y, b = (λz. z) 3}`, `b` is recorded as `(λz. z) 3` or `3`
     depending on the order.
   - B. All rules inside: the wrong-shape rule fires again on the kept term,
     `stuck u ⟶ stuck (stuck u) ⟶ stuck u ⟶ …` (with flattening).
   - C. Ordinary rules inside, but no wrong-shape/bubbling rules: rejected, the
     rules become context dependent.
   - E. Frozen twins of each strict construct (`t ! s`, `t.!l`, `t ~! F`, …) on the
     path from the root to the failure, with a bubbling rule: works, but needs a
     twin per construct. Freezing only the root of `stuck t` together with a
     bubbling rule loops (bubbling moves the old root down).
   - Check: `n₀ {a = {x = 1}.y, b = (λz. z) 3}` ends in either order as
     `n₀ {a = stuck ({x = 1}.y), b = 3}`, in `st`.
   - Termination: creation fires once per node (the wrapped root is skipped).
2. **The marker stays at the origin — agreed** (reverses the earlier "strip inner
   markers"). Nothing is moved or stripped; no flattening rule. A user-written
   `stuck (stuck t)` just stays.
3. **Stuck inside a run-time branch — deferred** until the branching-syntax change.
   Idea: a stuck arm becomes LLVM `unreachable` / a trap.
4. **Surface syntax — deferred** until the branching issue is resolved; use
   `stuck t` for now. Rejected so far: `!t` (clashes with linear logic's `!`;
   `!t s` reads ambiguously), `#(t)` and `<t>` (the user: "none works for me").

### D7 (first version): an `error` term instead of a stuck class — superseded

Kept for the strict positions and the wrong-shape list, which `stuck t` reuses.

- `error` is a term users can write.
- It propagates only from **strict positions**: function position
  (`error s ⟶ error`), projected term (`error.l ⟶ error`), select index
  (`{lᵢ = tᵢ} error ⟶ error`), opcode argument and operand fields, every form
  position (`error~F`, `t~error`, `error ⇒ G`, `F ⇒ error`, `λx~error. t`).
- Never from a `λ`'s argument, a neutral head's argument, a struct field, or a `λ`
  body: otherwise `(λx. 5) error` gives `5` or `error`, and full β is not
  confluent.
- Each wrong shape gets a rule to `error`:
  - `{lᵢ = tᵢ}.l ⟶ error` when `l` is not a label; `v.l ⟶ error` when `v` is a
    `λ`, a number or `F ⇒ G`
  - `{} s ⟶ error`; `{lᵢ = tᵢ} v ⟶ error` (at least one field) when `v` is a value
    but not a number
  - `n₀ v ⟶ error` when `v` is a value but not a struct; `n₀ {…, l = v, …} ⟶ error`
    when `v` is not an operand
- Classes become: **reducible, value, neutral, `error`**. The `error` class is the
  single term `error`, so every class is easy to define by a grammar.
- Two side conditions can't be grammar (they depend on data): label membership,
  and "`op(n₀)` gives no result".

### D8: effects under full β (`$seq`) — superseded by D13, D15, D29, D34

Problem: lets are β-redexes, so full β can **drop** an unused effect, **copy** one
used twice, and leave effects unordered. Today `shape` keeps every op let once, in
order, and `$seq {s, x}` puts an effect into a value.

Agreed so far:

- No new syntax: a "sequence" opcode replaces `$seq` (every number is an opcode).
  Using an effect's result as an operand of any opcode counts as using it and orders
  it.
- Every opcode, effects too, returns `n~F` (the code is fixed later).
- No `effect(n₀)` predicate: if the user wants to wait on an effect, they use the
  sequence technique; an effect nobody waits on carries no guarantee (dropping is the
  user's choice).

Open: **copying**. `let q = putchar 'h' in seq {q, seq {q, 0}}` runs `putchar` twice
under full β. Also through a captured `λ`:
`let q = putchar 'h' in (λg. seq {g 0, g 0}) (λy. q)`. (An opcode inside a `λ` that
is called twice should run twice; that is code, not a copied effect.)

Options discussed:

- **A. Linearity (a static check):** every opcode result used at most once; a `λ`
  that captures one is linear too (like Rust `FnOnce`). Rejects programs. The user
  first leaned towards A.
- **B. Call-by-need `let` (sharing):** E-Beta substitutes only values
  (`λ`, number, struct, function form); otherwise the redex stays a shared
  `let x = s in t` (reduce inside `s` and `t`, never copy or drop `s`). A run-time
  operation is never a value, so it is never copied or dropped; captured copies refer
  to the one binding. This is the call-by-need λ-calculus (Ariola, Felleisen,
  Maraist, Odersky, Wadler), known to be confluent, and it is what `shape` does
  today. Costs: `let` becomes a core term (or E-Beta gets "the argument is a
  value"); two let-moving rules, `(let x = s in t) u ⟶ let x = s in (t u)` and
  `(let x = s in t).l ⟶ let x = s in t.l`; an unused non-value binding stays
  (`let x = $fix (s -> s) in args.n` keeps the let; `⟶w` never runs it; translation
  must drop it, safe only without effects, or reject it).
- Variants of the check without an effect predicate: every opcode result at most
  once; only results waited on by the sequence opcode at most once; no check.

Why Oymo is lazy (no recorded decision; inferred from the wiki): `if` arms and
struct fields must not be evaluated; recursion (`$fix`) must not loop on unused
work; compile time does only what is needed; normal order finds a normal form when
one exists. All of this needs *not evaluating* arguments, not *copying* them, so
call-by-need keeps it.

Next question for the user: record D8 as call-by-need (B), with the unused-binding
trade-off open, or as linearity (A)?

**C. Linear logic, opt-in (raised by the user):**

- Linear binders `λ°x. t`, `let° x = s in t`: `x` is used exactly once (once per
  `if` path). Ordinary binders `λx. t` stay unrestricted.
- A `λ` whose body has a free linear variable is itself linear (the `!` promotion
  condition: only terms without free linear variables may be copied).
- Both are checks on variable occurrences, not types, so they work in untyped Oymo;
  forms stay unchecked.
- Full β is unchanged; on a linear binder substitution can't copy or drop.
  Linearity is preserved by reduction and the linear λ-calculus is confluent
  (Simpson 2005; Benton, Bierman, Wadler, de Paiva). Lean: if `t` passes the check
  and `t ⟶ t'`, then `t'` passes, with the same linear effects.
- Opt-in matches "the user decides": bind an effect with `let°` for the guarantee.
- Fits the roadmap: `alcor-safety-syntax` plans substructural types.
- Examples: `let° q = putchar 'h' in seq {q, 'i'}` passes;
  `let° q = putchar 'h' in 'i'` (dropped) and `… in seq {q, seq {q, 0}}` (copied)
  fail; `let° q = putchar 'h' in (λg. seq {g 0, g 0}) (λy. q)` fails (`λy. q` is
  linear, `g` used twice).

Open questions on C: opt-in (`λ°`, `let°`) or linear by default with `!` for
copyable values? Syntax: `λ°x. t`, or a marker like `x~lin` (but forms are
unchecked)? Does C replace B as the D8 answer?

**D. Every binder linear, explicit `dup` and `drop` (the user's proposal; leaning):**

- Every `λ` binder is linear: its variable occurs exactly once (once per `if` path).
  `dup` and `drop` are the only ways to copy or discard. Like HVM's interaction
  calculus, Lean 4 IR (`inc`/`dec`), Koka's Perceus, Rust MIR `drop`. Oymo is mostly
  generated, so verbosity is acceptable; Alcor would insert them.
- Full β unchanged; substitution never copies or drops. The check is syntactic
  (occurrence counting). Lean: the check is preserved by reduction; confluence.
- Proposed rules: `dup s k ⟶ k s s` and `drop s t ⟶ t`, both only when `s` is a
  value (number, `λ`, struct, function form). On a neutral `s` (a run-time
  operation) neither steps: translation emits the operation once and uses its result
  twice (`dup`) or ignores it (`drop`), like SSA. So `drop` also orders effects and
  replaces `$seq` (`drop q t` = `seq {q, t}`); `dup` copies an effect's result, never
  the operation.
- Open:
  1. `dup` of a closure that captured an effect (`dup (λy. q) k`) copies the code;
     each call runs it. Consistent, since the user wrote `dup`?
  2. Projection drops the other fields. Proposal: E-Proj
     `{lᵢ = tᵢ}.l ⟶ drop t₁ (… (drop tₙ tₖ))` over the other fields, so pure fields
     vanish and effectful ones stay as run-time drops. Select is different: its arms
     are alternatives (the other arm must not run), checked per path. How does the
     check tell a selected struct from a data struct when the struct is a variable?
  3. Pure code gets verbose (`dup x (λa. λb. 'add' {'i32', a, b})`); OK for
     generated code?

**Problems with option D under full β** (the user: "lets say i choose Option D.
then what kind of problem I will face during full-beta"):

1. **Structs play two roles.** Branch arms are alternatives (one runs); data fields
   are consumed together. The check needs separate constructs. The user is changing
   the branching syntax; continue after that.
2. **Forms copy and drop terms.** E-AppForm copies `s`; E-FuncFormApp drops `t`;
   E-Reform and E-FormOfForm drop forms. Fix: form positions count as 0 uses
   (QTT, Atkey / McBride); E-FuncFormApp becomes `(F ⇒ G) t ⟶ drop t G`.
3. **Projection drops the other fields.** Fix: E-Proj
   `{lᵢ = tᵢ}.l ⟶ drop t₁ (… drop tₙ tₖ)` over the other fields.
4. **`args` and `module` need `dup` at every use**, and those `dup`s never reduce
   (the variables are never substituted). Translation must treat `dup`/`drop` of a
   neutral term as "reuse the SSA value" / "ignore it". Maybe an unrestricted
   marker for such variables.
5. **Dropping an error** loses it: solved by `stuck t`, which keeps the term.
6. **`dup`/`drop` must be strict in `stuck`**, or confluence breaks (a value such as
   `F ⇒ G` whose form steps to stuck: one order drops it, the other gets stuck).
7. **More classes:** `dup ne k` and `drop ne t` are neutral; `dup` of a `λ` copies
   its code, so work can be done twice (by the user's choice).

### D9: branching — `case`, agreed (superseded by D14, then D20)

The user: "struct is only used as operand. so there is no E-select rule, and E-Proj
is not a branching." So a struct is data only (linear logic's ⊗: fields split the
resources) and branching is its own construct (&: arms share the resources).

Agreed:

- One n-ary construct, not a chain of `if` (a chain uses the scrutinee once per
  test, so it needs a `dup` each time; one construct maps to LLVM `switch`).
- Each arm has an explicit number (sparse, like LLVM `switch` cases); no `->`.
- A default arm is required. It comes **last** (`case when then else`, the user's
  choice after the dangling-`when` problem): `else d` ends the `case`, so nesting
  is unambiguous, as with `if then else` today. (Default first was considered:
  nothing would end a `case`, so a `case` in the last arm would take every
  following `when`.)
- Keyword syntax (option A):

  ```
  case n
  when [00] then a
  when [05] then b
  else d
  ```

- **No `if` sugar**: `if` goes away; `case` is the only branching. A test against
  zero is `case c when [00] then e else t` (nonzero takes `else`, as in C/LLVM).
- Rules (draft):

  ```
  case nᵢ when n₁ then t₁ … when nₖ then tₖ else d  ⟶  tᵢ          E-Case
  case m  when n₁ then t₁ … when nₖ then tₖ else d  ⟶  d  (m ∉ {nᵢ}) E-CaseElse
  ```

- Arm numbers are distinct literals (a repeated one is an error). The scrutinee is
  strict (`case st …` is in `st`, `case ne …` is neutral); the arms and the default
  are not strict, and all share the same linear variables. A stuck arm becomes
  LLVM `unreachable` (D7 point 3).

- Arm-number width: matching compares numbers by value; LLVM translation or BANF
  `convert` checks that each arm number has the scrutinee's width (not the
  semantics, not a form check).
- At least one `when` arm: `case n else d` is a syntax error.

Open:

1. Code later: the parser's `if` (today `{e, t} c`), E-Select in `reduction`,
   `shape`, translation of select, and the `if` reserved word.

### D10: two worlds in lockstep — agreed in principle (superseded by D11/D12)

The user: "the reason why I introduce Form instead of Type of theta-calculus is I
want beta-reduction without separation. term and form world has a different
computation, they are mutually exclusive, but go together." Then: "rules for term
and form world are same. they are just separated".

Agreed:

- Every term is a pair `t ~ T`: `t` in the term world, `T` in the form world;
  neither side contains `~`. A term written without a form is `t ~ Empty`.
- **One calculus, two copies.** Both worlds use the same rules; they never
  interact. A step on a pair is a step on exactly one half. Constructs act per
  half: `(t~T) (s~S)` is `t s ~ T S`; a variable stands for a pair (its term half
  in the term world, its form half in the form world); β is
  `(λx. b~B) (s~S) ⟶ b[x := s] ~ B[x := S]`, without separation.
- **Normal forms are `φ ~ φ`** (the user: "normal form can be Formed only. but each
  side can have single layer normal form").
- **Confluence is proved once**, for the formless calculus; pairs follow from the
  lemma "stepping either half of a pair is confluent if the relation is".
  Classes are defined once, on the formless calculus. Only the strategy differs:
  `⟶w` is weak on the term half, strong on the form half (D3a).
- **The form world is linear too** (same rules): each world uses `x` exactly once,
  with its own `dup`/`drop`.
- **Opcodes are formless** (revises D1a): `n₀ {oᵢ} ⟶ m`, one `op` table. A result
  form is written by the user: `('add' {'i32', a, b})~'i32'`.
- Surface syntax is split into pairs: `t s` ↦ `t₁ s₁ ~ t₂ s₂`, `t~F` ↦ `t₁ ~ F₁`,
  `{l = t}` ↦ `{l = t₁} ~ {l = t₂}`, `λx. b` ↦ `λx. b₁ ~ λx. b₂`, `n` ↦ `n ~ Empty`.
  E-AppForm and E-ProjForm become facts about splitting, not rules; E-Reform and
  E-FormOfForm disappear (no nested `~`). D8 problem 2 disappears.

Open:

1. `t~F` splits to `t₁ ~ F₁` and throws away `t₂`. With a linear form world,
   variables used in `t₂` must be dropped: should splitting insert the `drop`s
   (`t₁ ~ drop t₂ F₁`), or must the user write them?
2. Binder forms `λx~F. b` (and `let x~F = s in b`): what do they mean in pairs?
   Proposal: the binder re-forms the argument, so in the form half `x` means `F`
   and the argument's form half is dropped.
3. Syntax for a result form: `(n {…})~'i32'`, or `let q~'i32' = n {…} in …`
   (existing binder syntax, if 2 is agreed).
4. `F ⇒ G` and E-FuncFormApp: in the form world, `F ⇒ G` is the form of a function;
   with the same rules, is it just a form-world `λ` (`λ_. G`), or a construct of
   its own?

## Classes (draft, before D7 and D8)

The user wants every class defined by a grammar, without subscripts. Agreed count:
four classes that split all terms (reducible, value, neutral, stuck after D7) and
two helpers (operands in normal form; forms in normal form `φ`).

`φ` is not `v | on`: `v` and `on` only describe the root and may contain redexes
(`λx. (λy. y) a`, `{a = (λy. y) 2}`, `x ((λy. y) 2)`). `φ` has no full-β step
anywhere; it is the strong copy of value, neutral and stuck, with every part in
normal form.

Draft grammar shown to the user (to redo without subscripts, with `stuck t` and `st`):

```
v   ::= λx. t | λx~φ. t | {lᵢ = tᵢ} | n | φ ⇒ φ | v~φ
ne  ::= x | ne t | ne.l | {lᵢ = tᵢ} ne | n₀ {lᵢ = onᵢ} (op gives no result) | ne~φ
on  ::= n | n~φ | {lᵢ = onᵢ} | ne
φ   ::= the same shapes as v and ne (and st), with every part a φ
```

## Notation agreed during the review

- One letter per class: every term, forms included, is `t`; several terms in one
  rule are `t₁`, `t₂`, … (replaces `F`, `G` and `s`).
- Numbers `n` (0, 1, 2, …), no byte arrays in the doc; the doc ignores byte length.
- Function forms are `F ⇒ G`.
- Points are numbered `1)`, `2)`, … per section; subsections are `4a`, `4b`, …
- Rules (and section 4 cases) are rows: number left, term centered, name right
  (a rule, or Value / Neutral / Stuck).
- Every change is marked blue (new) / red struck (removed) until the user accepts.

## State of semantics.tex (accepted)

Latest accepted (after D37):
- Syntax (rows 1–9): `x | x → t | t t | t !t | {lᵢ = tᵢ}_{i<n} | t.l | b`; values
  `v ::= x → t | {lᵢ = vᵢ}_{i<n} | b`; data `d ::= b | {lᵢ = dᵢ}_{i<n}`. Sugar: `let x = t₁ in t₂`,
  `let x =! t₁ in t₂`, `if c then t₁ else t₂`. No type checking (1/13).
- Rules: E-Beta, E-Strict `t !v ▷ t v`, E-Proj, E-Index `b < n`, E-Default `0 < n ≤ b ⟹ tₙ₋₁`,
  E-Opcode `op(b)(dᵢ)_{i<n} = b'`. Full β: E-Abs, E-App1/2, E-SApp1/2, E-Struct, E-Proj1.
  `▷` is confluent (Lean). Stuck terms are compile errors; unknown opcodes and UB are run-time.
- Section 4: compile time never runs effects; at run time an effect is a step, output may
  depend on the path; strict application runs an effect exactly once; the translation may
  merge copies.
- Section 5: module `m → {…}`; definition `{gives, body = f → {blocks}}`, first block is the
  entry (any label); block `{takes, body = p → t}`; declaration `{takes, gives}`; constant
  `{type, value}`; global `{type, init}`; jump `f.l.body {…}`; call `m.l {…}`; `m`, `f` free;
  gcd example as a monospace listing.

Older states (history):

Latest accepted (after D20): terms `x | λx. t | t t | {l = t, …} | t.l | b | !t`; rules E-Beta, E-Proj, E-Index (`{…} b`, branch/switch), E-Opcode (`b {…}`), E-Strict; full β E-Abs, E-App1/2, E-Struct, E-Proj1, E-Strict1; Section 4 "What Runs"; Section 5 "Modules": module `λm.{…}`, definition `{result, body = λf.{entry = block, …}}`, block `{param, body = λp. t}`, declaration `{param, result}`, jump `f.l.body {…}`, call `m.l {…}`; `m`, `f` stay free.

Latest accepted (after D17): terms `x | λx. t | t t | {l = t, …} | t.l | t.k | b | if t then t else t | !t`; opcode call `b {l = v, …}` via E-Opcode (`op(b)` partial; no result → neutral run-time operation); rules E-Beta, E-Proj, E-ProjPos, E-IfTrue, E-IfFalse, E-Opcode, E-Strict; full β congruence; Section 4 "What Runs".

Latest accepted (after D12 and step 6): terms `x | λx. t | t t | dup t t | drop t t | {l = t, …} | t.l | b | case t when b then t ⋯ else t`; a struct is a value only when its fields are values; rules E-Beta, E-Dup, E-Drop, E-Proj, E-Index, E-Case, E-CaseElse; `case` syntax kept as is (shorter options declined).

Latest accepted: solo/duet (`t` term, `s` solo, `d` duet; syntax once under `t`, `s`/`d` as classes), pair `s~s` only, one rule E-Split, E-Duet1/2, E-Collapse removed, evaluation strategy dropped for now, α-equivalence wording.

Rewritten from scratch (the user: "clear up semantics.tex and add what we build so
far"); accepted by the user. It holds rebuild steps 1–4:
syntax (naked, signature, dup/drop, clad), computation (E-Beta, E-SigApp, E-Dup,
E-Drop; clad: E-Split{App,Abs,Sig,Dup,Drop}, E-Reclad, E-Collapse), full β
congruence, linearity, `⟶w` for naked terms, classes for naked terms. Not yet:
`⟶w` and classes for clad terms. The previous draft is in git.

Accepted later: classes `cv ::= v where FV(v) = ∅` and `ov ::= v where FV(v) ≠ ∅` (E-Dup/E-Drop use `cv`; `ne` has `dup ov t`, `drop ov t`); `FV` defined; class order v, cv, ov, ne, r; signature value `v ⇒ v` with W-Sig1/2. Also: point 1/8 shortened; the term classes moved from
Section 6 into Section 1 (Syntax); every term is written `t` (`t₁`, `t₂`, …).

## Roadmap

- Done: `review-rules`, `classes-doc`, `classes-lean` (D28), `conf-lean` (D27).
- Next: the code refactor (Open 5), then `classes-check` / `classes-code`. `conf-form`
  (E-Reform, `strip`) is moot without forms (D12).
- Leaf details list what to do; decisions and reasons are in the agent wiki.
