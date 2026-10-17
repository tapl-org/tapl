# Plan: confluence, so reduction order doesn't change the result

**Status:** proposed, with open questions · 0 of 4 steps · oymo 0.2, its own release
· [roadmap › 0.2](roadmap.md#02--confluence-reduction-order-doesnt-change-the-result)

> [!IMPORTANT]
> BANF's removal (0.3) and Alcor (0.4) do not start before this plan is closed.

## Goal

**Any two reductions of a term can be joined again** (Church–Rosser), under *full* β:
any rule of [reduction_rules.md](reduction_rules.md), at any position (under `λ`, in
fields, arguments, forms).

- A term has **at most one normal form**, whatever the order.
- **`whnf`, `shape` and full β agree**: each strategy is a subset of full β.
- Today this fails: E-BetaForm strips the argument's form, and reducing the argument
  can create one (counterexample in [Background](#background-for-agents)).

## Steps

One commit each; each leaves `hatch run full-check` green.

- [ ] 1. A full-β reference reducer and a confluence test, test-only (`oymomo: test that reduction is confluent`)
- [ ] 2. A form on a form is replaced, and beta always wraps (`oymomo: a form replaces a form`)
- [ ] 3. A contract for built-in rules, checked by the test (`oymomo: built-in rules commute with reduction`)
- [ ] 4. `shape` keeps the meaning of its input, checked by the test (`oymomo: shape is a reduction`)

Step 1 adds the counterexample as `xfail`; step 2 fixes it. Steps 3–4 only add tests
and docs, unless the tests find a new problem.

## Decisions

### Rules

1. **New rule E-Reform:** `(t~G)~F → t~F`. Translation already does this. Fires at the
   root in `reduction.reduce`, so `whnf` uses it too.
2. **Beta always wraps; `strip` goes.** No beta rule looks at its argument:
   - E-Beta: `(λx. t1) t2 → [x ↦ t2] t1`
   - E-BetaForm: `(λx~F. t1) t2 → [x ↦ t2~F] t1`
3. **E-Select sees one form.** `index_value` accepts `[b]` and `[b]~F`; deeper nesting
   gets there by E-Reform first (the index is the head).
4. **Critical pairs.** The rules are left-linear; every overlap joins:

   | Overlap | Joins as |
   |---|---|
   | `((t~H)~G)~F`, inner and outer E-Reform | both give `t~F` |
   | E-BetaForm, then the argument reduces to `a~G` | `(a~G)~F` →E-Reform `a~F` |
   | E-Select on `{...} ([b]~F)` | no overlap: E-Formed can't step a byte array |
   | E-Proj, E-Fix, E-Beta | no overlap with each other |

   So the system is confluent. Step 1's test checks this; it doesn't prove it.

### Built-ins

5. **A built-in rule must commute with reduction of its argument.** Kept by each
   built-in's `reduce` case:
   > If `rule(call, a)` gives `r`, and `a →* a'`, then `rule(call, a')` gives some `r'`,
   > and `r` and `r'` can be joined. `None` on `a` and a result on `a'` is allowed, not
   > the reverse.
   - Read only what reduction can't change: the constructor once in whnf, labels, byte
     arrays.
6. **Step 3 tests each built-in in `BUILTINS`** on sample arguments, reducing the
   argument in every order. A plan that adds a rule adds samples.
   - `$seq` samples: `$seq {[01], x}`, `$seq {{a = [01]}.a, x}`, `$seq {s, x}`.

### `shape`

7. **`shape` is a reduction, with lets kept:** `normalize(shape(t)) == normalize(t)`
   whenever both terminate. Step 4 checks it on the `banf_reduce_test.py` and
   `banf_translate_test.py` programs.
8. **Confluence is about results, not termination.** `shape` may diverge where lazy
   reduction doesn't (e.g. `let x = $fix (s -> s) in args.n`). See open question 2.
9. **Effects aren't in the value.** Full β may drop an unused effect, copy a let used
   twice, or leave effects unordered; `shape` keeps every op let, once, in order
   (plan_memory decision 4). Decision 7 still holds. `$seq` puts an effect into the
   value, so every strategy keeps it. Samples (each checked under every strategy and
   with `shape`):

   | Program | `normalize(t)` |
   |---|---|
   | `hi`: `let q = putchar 'h' in let r = putchar {c = $seq {q, 'i'}} in r` | both calls |
   | `hi` without `$seq` | only `putchar 'i'`: the first call is dropped |
   | `let s = 'store' {n, p} in let v = 'load' {'i32', p} in v` | `'load' {'i32', p}`, no store |
   | the same with `$seq {s, p}` as the load's pointer | the store is kept |
   | `let v = 'load' {...} in let s = 'store' {...} in let w = 'add' {'i32', $seq {s, v}, v} in w` | two `'load'` subterms |
   | `let a = putchar 'h' in let b = putchar 'i' in $seq {a, b}` | `$seq {putchar 'h', putchar 'i'}`, no let |

   These tests land with whichever of this plan's step 4 and plan_memory's step 3
   comes second.

### Testing

10. **Full-β reference reducer, test-only:** `tests/oymomo/full_beta.py`.
    - `reducts(term)`: every term one full-β step away, at any position.
    - `normalize(term, fuel, choose)`: steps with `choose(reducts)` until none left;
      raises when out of fuel.
    - Strategies: leftmost-outermost, innermost, seeded random.
11. **Confluence test:** normalize each corpus term with each strategy; all that
    terminate must give the same term (`==`). Corpus:
    - the counterexample and one term per critical pair (decision 4)
    - every source in `banf_reduce_test.py` and `banf_translate_test.py`
    - the effect samples of decision 9
    - small seeded random terms (constructors, free variables, byte arrays, `$fix`)

### Docs to update

- [reduction_rules.md](reduction_rules.md): add E-Reform, drop `strip`, add a "Full β"
  section (congruence rules; `→`, `whnf`, `shape` as strategies).
- [notes.md › Forms](notes.md#forms): "`Formed` itself never reduces" → "a form on a
  form is replaced (E-Reform)".
- `reduction.beta` docstring: the form goes with the argument; E-Reform drops its own.
- [plan_struct_pack.md](implemented/plan_struct_pack.md),
  [plan_constant_folding.md](implemented/plan_constant_folding.md): each rule names
  its decision 5 samples.

### Risks

- **Nested forms in shaped terms**, e.g. in data definition fields. Step 2 checks that
  `convert` takes whnf before reading a form; otherwise `convert` uses the outer form.
- **Golden files** may gain a form level; step 2 updates them.

## Open questions

1. **E-Reform, or keep every form?** Leaning: **a**.
   - a. E-Reform, as above; matches translation
   - b. No E-Reform, no `strip`: `(a~G)~F` stays, translation reads the outermost form
2. **Should `shape` keep lazy termination?** Leaning: **a**.
   - a. No, decision 8 as written
   - b. `shape` drops a let whose binder is unused before reducing its value
3. **Random terms:** seeded hand-written generator, or `hypothesis`?
4. **Should `normalize` live in `src`** as `reduction.normalize`?

## Dependencies

- Blocks 0.3 (BANF's removal) and 0.4 (Alcor).
- Decision 9 uses [plan_memory.md](implemented/plan_memory.md)'s samples and `$seq`.
- Decision 5 applies to rules from [plan_struct_pack.md](implemented/plan_struct_pack.md)
  and [plan_constant_folding.md](implemented/plan_constant_folding.md).

## Background (for agents)

Context kept for reference; not needed to follow the plan.

### The counterexample

```
(x~'i16' -> x) ((y -> y~'i8') a)

beta first (whnf):          ((y -> y~'i8') a)~'i16'   →  (a~'i8')~'i16'
argument first (shape):     (x~'i16' -> x) (a~'i8')   →  a~'i16'
```

No rule takes `(a~'i8')~'i16'` to `a~'i16'`. Translation hides it, because the written
form replaces the atom's form ([notes.md › Forms](notes.md#forms)), but reduction
itself is not confluent.

### Notes on the decisions

- Goal: confluence is `t →* t1` and `t →* t2` ⇒ `t1 →* u` and `t2 →* u` for some `u`.
  `whnf` reduces lazily, at the root and head; `shape` also goes under the `module`,
  `f` and `args` lambdas and reduces a let's value before inlining it
  ([notes.md › Positions](notes.md#positions)).
- 2: a rule that checks its argument's shape is what breaks confluence.
- 4: E-Reform's self-overlap is the only overlap between left-hand sides. A left-linear
  system with all critical pairs joinable has the diamond property for parallel
  reduction.
- 5: today the only rule is `$fix`, which isn't strict and doesn't look at its
  argument. Strict rules (plan_struct_pack, plan_constant_folding) read it. Folding
  `$add_i32 {a = [01000000], b = [02000000]}` reads byte arrays (normal forms). A rule
  must not read a field not yet in normal form and return `None` for one shape of it and
  a result for another.
- 6: [plan_memory.md](implemented/plan_memory.md)'s `$seq {d1, ..., dn, x}` gives `x`
  once every `dᵢ` is a byte array; it only reads whether each is a byte array (a normal
  form), so it keeps the contract. `{a = [01]}.a` is not a redex until the field reduces.
- 7: each change `shape` makes is a full-β step at some position, or keeps a let that
  is a redex. `normalize` is step 1's reducer.
- 8: `shape` takes a let's value to whnf before deciding to keep the let, so
  `let x = $fix (s -> s) in args.n` runs out of fuel, while lazy reduction gives
  `args.n`. Confluence promises one normal form, not that every strategy reaches it.
- 9: with plan_memory, a term has effects: memory ops and calls to imports, which never
  reduce. Full β treats the let around one as any other redex: a load may run twice; a
  value has no order. `normalize(shape(t)) == normalize(t)` holds because the value
  doesn't record an effect nothing uses.
- 10: `reducts` uses `reduction.reduce` at the root and recurses into every child:
  `Lambda.body`, `Lambda.param_form`, struct fields, arguments and forms.
- 11: de Bruijn indices make `==` syntactic. `param_name` is compared too, which is fine
  because reduction never renames a binder.

### Notes on the open questions

- 1: both options are confluent. (b) keeps more information in the term, but every pass
  that reads a form must look through the nesting.
- 2: oymomo is strict once in BANF anyway. (b) covers the dead-let case but not
  `let x = loop in if c then x else [00]`.
- 3: hypothesis shrinks counterexamples but adds a dependency to `hatch-test`.
- 4: it could be a debugging and printing aid; test-only keeps `reduction` small.

### Out of scope

- **Termination** (strong normalization): `$fix` makes some terms diverge on purpose.
- **Transparent forms** for apply and projection (`(λx. t~F) a`, `({a = x}~F).a`): both
  are stuck in every order, so they don't affect confluence.
