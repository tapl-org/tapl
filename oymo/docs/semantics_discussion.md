# Semantics discussion: term classes, `stuck t`, effects

Notes from the review of `semantics.tex` (roadmap: `review-rules`, `term-classes`), so
nothing is lost between sessions. We continue the discussion here.

## Where we are

- **Restart from scratch (D11):** the calculus is rebuilt step by step, adding
  syntax gradually. See "Rebuild" below; D1–D10 are input, not the current state.
- `semantics.tex` was rewritten from scratch with the rebuild, steps 1–4 (accepted);
  see "State of semantics.tex" below.
- Decisions D1–D6 are agreed. D7 is revised to `stuck t` (points 1 and 2
  agreed, point 3 deferred). D8 (effects under full β) leans to option D. D9
  (`case`) agreed. D10 (pairs) was replaced by a simpler idea (one β, E-Unform),
  then by the rebuild.
- `make -C oymo/docs` builds `semantics.pdf`.

## Goal

Like the θ-calculus, split all terms into classes so that each class is either
reducible by exactly one rule of the evaluation step `⟶w`, or a value, neutral, or
stuck (`stuck t`). Every class is defined by a grammar (extensionally), not in
words. Then prove in Lean 4 that nothing is missed.

## Rebuild (D11)

**Evaluation strategy dropped for now** (the user): `⟶w` comes back once the full syntax and full β are settled. Until then the classes say "a rule of Section 2 applies at its head".

The user: "becomes so complex. lets simplify. i want simple full beta rule." Then:
"we will gradually add new syntax. so we are start from scratch."

Names (agreed): a **naked** term has no `~` at its root; a **clad** term is
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

### Step 4: clad terms — agreed (⟶w and classes for clad terms still to do)

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

### D7 (revised): a `stuck t` term — points 1 and 2 agreed, 3 deferred

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

### D8: effects under full β (`$seq`) — open, resume here

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

### D9: branching — `case`, agreed (code changes later)

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

### D10: two worlds in lockstep — agreed in principle (revises D1a, D2, D3, D8 problem 2)

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

Rewritten from scratch (the user: "clear up semantics.tex and add what we build so
far"); accepted by the user. It holds rebuild steps 1–4:
syntax (naked, signature, dup/drop, clad), computation (E-Beta, E-SigApp, E-Dup,
E-Drop; clad: E-Split{App,Abs,Sig,Dup,Drop}, E-Reclad, E-Collapse), full β
congruence, linearity, `⟶w` for naked terms, classes for naked terms. Not yet:
`⟶w` and classes for clad terms. The previous draft is in git.

Accepted later: classes `cv ::= v where FV(v) = ∅` and `ov ::= v where FV(v) ≠ ∅` (E-Dup/E-Drop use `cv`; `ne` has `dup ov t`, `drop ov t`); `FV` defined; class order v, cv, ov, ne, r; signature value `v ⇒ v` with W-Sig1/2. Also: point 1/8 shortened; the term classes moved from
Section 6 into Section 1 (Syntax); every term is written `t` (`t₁`, `t₂`, …).

## Roadmap

- `review-rules`, `term-classes` (`classes-doc`, `classes-lean`, `classes-check`,
  `classes-code`), `conf-lean`, `conf-form` (E-Reform, drop `strip` in the code).
- Leaf details list what to do; decisions and reasons are in the agent wiki.
