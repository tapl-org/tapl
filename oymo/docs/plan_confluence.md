# Plan: confluence, so reduction order doesn't change the result

Status: **proposed**, with open questions; 0 of 4 steps.

## Steps

One commit each. Each step leaves `hatch run full-check` green.

- [ ] 1. A full-β reference reducer and a confluence test, test-only (`oymomo: test that reduction is confluent`)
- [ ] 2. A form on a form is replaced, and beta always wraps (`oymomo: a form replaces a form`)
- [ ] 3. A contract for built-in rules, checked by the test (`oymomo: built-in rules commute with reduction`)
- [ ] 4. `shape` keeps the meaning of its input, checked by the test (`oymomo: shape is a reduction`)

Step 1 adds the known counterexample as an `xfail` test. Step 2 fixes it and removes the
`xfail`. Steps 3 and 4 only add tests and docs, unless the tests find a new problem.

## Goal

**Any two ways of reducing a term can be joined again** (Church–Rosser):

```
if  t →* t1  and  t →* t2,  then  t1 →* u  and  t2 →* u  for some u
```

where `→` is *full* β: any rule of [reduction_rules.md](reduction_rules.md), at any
position, under a `λ`, in a struct field, in an argument, or in a form. So:

- **A term has at most one normal form**, whatever order reaches it.
- **`whnf` and `shape` agree with each other and with full β.** `whnf` reduces lazily,
  at the root and the head. `shape` also goes under the `module`, `blocks` and `args`
  lambdas and reduces a let's value before it inlines it (see
  [notes.md › Positions](notes.md#positions)). Each strategy is a subset of full β, so
  with confluence they can never reach different results.

Today this fails. E-BetaForm strips the argument's form, and reducing the argument can
create a form:

```
(x: 'i16' -> x) ((y -> y: 'i8') a)

beta first (whnf):          ((y -> y: 'i8') a): 'i16'   →  (a: 'i8'): 'i16'
argument first (shape):     (x: 'i16' -> x) (a: 'i8')    →  a: 'i16'
```

No rule takes `(a: 'i8'): 'i16'` to `a: 'i16'`, so the two never meet. Translation
hides it, because the written form replaces the atom's form
([notes.md › Forms](notes.md#forms)), but the kernel itself is not confluent.

## Decisions

### Rules

1. **New rule E-Reform: a form on a form is replaced.** This is the rule translation
   already follows, made a reduction:

   ```
             (t : G) : F  →  t : F                        (E-Reform)
   ```

   It fires at the root, in `reduction.reduce`, so `whnf` uses it too.

2. **Beta always wraps; `strip` goes.** With E-Reform, `strip` is no longer needed.
   E-Beta and E-BetaForm become:

   ```
                 (λx. t1) t2  →  [x ↦ t2] t1               (E-Beta)
              (λx:F. t1) t2  →  [x ↦ t2 : F] t1            (E-BetaForm)
   ```

   A rule that checks what shape its argument has is what breaks confluence. After this,
   no beta rule looks at its argument.

3. **E-Select sees one form.** `index_value` keeps accepting `[b]` and `[b] : F`. A deeper
   nesting reaches that shape through E-Reform first, because the index is the head.

4. **Critical pairs.** After decisions 1 and 2, the rules are left-linear, and E-Reform's
   self-overlap is the only overlap between left-hand sides:

   | Overlap | Joins as |
   |---|---|
   | `((t : H) : G) : F`, inner and outer E-Reform | both give `t : F` |
   | E-BetaForm, then the argument reduces to `a : G` | `(a : G) : F` →E-Reform `a : F` |
   | E-Select on `{...} ([b] : F)` | no overlap: E-Formed can't step a byte array |
   | E-Proj, E-Fix, E-Beta | no overlap with each other |

   With every critical pair joinable, a left-linear system has the diamond property for
   parallel reduction, so it is confluent. Step 1's test checks this; it doesn't prove it.

### Built-ins

5. **A built-in rule must commute with reduction of its argument.** Today the only rule
   is `$fix`, which isn't strict and doesn't look at its argument. Strict rules
   ([plan_struct_pack.md](implemented/plan_struct_pack.md),
   [plan_constant_folding.md](implemented/plan_constant_folding.md)) read their argument, so they need
   a contract, in the `BuiltinRule` docstring:

   > If `rule(call, a)` gives `r`, and `a →* a'`, then `rule(call, a')` gives some `r'`, and
   > `r` and `r'` can be joined. A rule may give `None` on `a` and a result on `a'`, but not
   > the other way.

   In practice, the rule should read only parts of the argument that reduction can't
   change: the argument's constructor once it is in whnf, its labels, and byte arrays.
   Folding `$add_i32 {a = [01000000], b = [02000000]}` reads byte arrays, which are normal
   forms. A rule must not read a field that is not yet in normal form and then return
   `None` for one shape of that field and a result for another.

6. **Step 3's test checks each rule in `BUILTIN_RULES`**, on sample arguments, through
   step 1's harness: reduce the argument in every order and compare. A plan that adds a
   rule adds samples.

### `shape`

7. **`shape` is a reduction, with lets kept.** Each change `shape` makes is a step of
   full β at some position, or else it keeps a let that is a redex. So:

   ```
   normalize(shape(t)) == normalize(t)        whenever both terminate
   ```

   where `normalize` is step 1's full-β reducer. Step 4's test checks this on the
   existing `banf_reduce_test.py` and `banf_translate_test.py` programs.

8. **Confluence is about results, not termination.** `shape` takes a let's value to whnf
   before it decides whether to keep the let, so
   `let x = $fix (s -> s) in args.n` runs out of fuel, while lazy reduction gives
   `args.n`. Confluence promises one normal form; it doesn't promise that every
   strategy reaches it. See open question 2.

### Testing

9. **A full-β reference reducer, test-only.** `tests/oymomo/full_beta.py`:

   ```python
   def reducts(term) -> Iterator[Term]:
       """Every term one full-β step from `term`, at any position."""

   def normalize(term, fuel, choose) -> Term:
       """Steps with `choose(reducts)` until no reduct, or raises when out of fuel."""
   ```

   `reducts` uses `reduction.reduce` at the root and recurses into every child, including
   `Lambda.body`, `Lambda.param_form`, struct fields, arguments and forms. Strategies
   are `choose` functions: leftmost-outermost, innermost, and seeded random.

10. **The confluence test.** For each term in a corpus, normalize it with each strategy,
    with fuel. Every strategy that terminates must give the same term. The corpus is:
    - The counterexample above, and hand-written terms for each critical pair (decision 4).
    - Every source in `banf_reduce_test.py` and `banf_translate_test.py`.
    - Small random terms from a seeded generator over the term constructors, with a few
      free variables, byte arrays and `$fix`.

    Terms compare with `==`. De Bruijn indices make that syntactic. `param_name` is
    compared too, which is fine because a reduction never renames a binder.

## Docs

- [reduction_rules.md](reduction_rules.md): add E-Reform, drop `strip` from E-BetaForm,
  and add a "Full β" section: E-Abs and the other congruence rules, with a note that `→`,
  `whnf` and `shape` are strategies within it.
- [notes.md › Forms](notes.md#forms): "`Formed` itself never reduces" becomes "a form on
  a form is replaced (E-Reform)".
- `reduction.beta` docstring: the form goes with the argument, and E-Reform drops the
  argument's own form.
- [plan_struct_pack.md](implemented/plan_struct_pack.md), [plan_constant_folding.md](implemented/plan_constant_folding.md):
  each rule names its decision 5 samples.

## Risks

- **Nested forms in shaped terms.** Beta no longer strips, so `(a : G) : F` can appear
  where `shape` doesn't take whnf, for example in a data definition's fields. Step 2 checks
  that each position `convert` reads a form from takes whnf first. Otherwise `convert`
  has to accept nested forms and use the outer one.
- **Golden files.** Some printed terms may gain a form level before whnf removes it.
  Step 2 updates them.

## Open questions

1. **E-Reform, or keep every form?** Option (a), recommended: E-Reform, as above; it
   matches translation. Option (b): no E-Reform and no `strip`, so `(a : G) : F` stays, and
   translation reads the outermost form. Both are confluent. (b) keeps more information
   in the term, but every pass that reads a form must look through the nesting.
2. **Should `shape` keep lazy termination?** Option (a): no, decision 8 as written.
   Oymomo is strict once it is in BANF anyway. Option (b): `shape` drops a let whose
   binder its body doesn't use before reducing its value. That covers the dead-let case,
   but not `let x = loop in if c then x else [00]`.
3. **Random terms: a seeded hand-written generator, or `hypothesis`?** Hypothesis
   shrinks counterexamples, but it adds a dependency to `hatch-test`.
4. **Should `normalize` live in `src`, as `reduction.normalize`?** It could serve as a
   debugging and printing aid. Test-only keeps the kernel small.

## Out of scope

- **Termination** (strong normalization): `$fix` makes some terms diverge on purpose.
- **Making forms transparent** to apply and projection, as in `(λx. t : F) a` or
  `({a = x} : F).a`. Both are stuck in every order, so they don't affect confluence.
