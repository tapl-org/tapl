# oymomo reduction rules

The rules implemented by [`bruijn.reduce`](../src/oymo/oymomo/bruijn.py) (computation)
and [`banf_shape.step`](../src/oymo/oymomo/banf_shape.py) (congruence), in the style of
TAPL. See [notes.md › Blockers](notes.md#blockers) for the prose version.

## Syntax

```
t ::=                                   terms
      x                                 variable (a de Bruijn index after resolve)
      λx:t. t                           abstraction (the form may be empty: λx. t)
      t t                               application
      {l1 = t1, ..., ln = tn}           struct (labels may be empty)
      t.l                               projection
      [b]                               byte array
      $name                             built-in
      t:t                               formed term
      t -> t                            function form
```

Forms are terms. Below, `F` and `G` are metavariables for terms used as forms.

## Where `reduce_until_top_stable` stops

Evaluation is **weak** (never under `λ`) and **lazy** (an ordinary argument is never
reduced). `reduce_until_top_stable` stops at:

```
w ::=   λx:t. t  |  {l1 = t1, ...}  |  [b]  |  x  |  $name  |  t -> t  |  stuck terms
```

Stuck terms include `$add_i32 {a = args.n, ...}`, `args.n`, `blocks.done {...}` and `{e, t} c` where `c`
is not a byte array.

## Evaluation  `t → t'`

### Computation (at the root)

```
                 (λx. t1) t2  →  [x ↦ t2] t1                              (E-Beta)

              (λx:F. t1) t2  →  [x ↦ (strip t2) : F] t1                  (E-BetaForm)
                 where strip (t : G) = t,  strip t = t otherwise

                 $fix t  →  t ($fix t)                                    (E-Fix)

      $op is folded    vi literal operands of op's params    eval(op, v1..vn) = v
   ─────────────────────────────────────────────────────                 (E-Opcode)
            $op {l1 = v1, ..., ln = vn}  →  v : R
                 (li are op's params, in order; R is op's result form;
                  no rule where eval is undefined: x / 0, x % 0, signed min / -1,
                  signed min % -1, a shift by the width or more)

         {li = ti  i∈1..n}.lj  →  tj                                      (E-Proj)
                 (the first field labeled lj)

               le(b) = j      j < n      b ≠ ''
   ─────────────────────────────────────────────────────                 (E-Select)
     {f0 = t0, ..., f(n-1) = t(n-1)} [b]  →  tj
                 ([b] : F counts as [b]; labels are ignored;
                  `if c then t else e` is `{e, t} c`)
```

`le(b)` reads `b` as an unsigned little-endian integer.

### Congruence (reduce the blocker)

These apply only when no computation rule applies at the root.

```
                       t1 → t1'      t1 is not a struct
   ─────────────────────────────────────────────────────                 (E-App1)
                        t1 t2  →  t1' t2

                              t2 → t2'
   ─────────────────────────────────────────────────────                 (E-SelectArg)
                {f1 = t1, ...} t2  →  {f1 = t1, ...} t2'

                               t → t'
   ─────────────────────────────────────────────────────                 (E-Proj1)
                             t.l  →  t'.l

                               t → t'
   ─────────────────────────────────────────────────────                 (E-Formed)
                           t : F  →  t' : F

                 p is a part of t that the rule of $name reads      p → p'
   ─────────────────────────────────────────────────────                 (E-Builtin)
                          $name t  →  $name t[p ↦ p']
```

E-Builtin is the rule's own `reduce`, given `reduce_until_top_stable` as `reduce_part`:
each built-in says which parts it reads (`$fix` reads none). There are no rules for
`λx:F. t`, struct fields, ordinary arguments, or forms: those positions are never
reduced by `→`. So `$fix t` never reduces `t`.

## Under binders: `shape`

[`banf_shape.shape`](../src/oymo/oymomo/banf_shape.py) is the only place that goes under
a `λ` or into a struct field, and only along BANF's skeleton. Writing `⇓` for `reduce_until_top_stable`:

```
   module position:   t ⇓ λm. b        ⟹  shape t = λm. body(b)
   body(b):           b ⇓ {li = fi}     ⟹  {li = func(fi)}
   func(f):           f ⇓ λk. g, g ⇓ {li = bi}  ⟹  λk. {li = block(bi)}
   block(b):          b ⇓ λa. t         ⟹  λa. block_body(t)

   block_body((λx. t) v):
        v ⇓ op          ⟹  keep the let, shape op's atoms, continue in t   (S-Let)
        v ⇓ w, not op   ⟹  continue in [x ↦ w] t                          (S-Inline)
   block_body(t):  step t, else shape the terminal's jumps / atoms
```

Anything a position doesn't name (a let-bound `λ`, a lambda passed as an argument, a
non-structural struct field, a form) is left unreduced.
