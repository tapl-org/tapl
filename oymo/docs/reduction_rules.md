# oymomo reduction rules

TAPL-style rules for oymomo evaluation:

- `t → t'` (one step) is [`banf_shape.step`](../src/oymo/oymomo/banf_shape.py): the
  computation rules come from [`reduction.reduce`](../src/oymo/oymomo/reduction.py), and the
  congruence rules from `banf_shape.unblock`.
- `t ⇓ w` is `reduce_until_top_stable`: apply `→` until no rule applies.
- `shape` goes under binders, but only along BANF's skeleton.

For the prose version, see [notes.md › Blockers](notes.md#blockers).

## Syntax

```
t, F ::=                         terms (forms are terms too, written F, G)
      x                          variable (a de Bruijn index after resolve)
      λx~F. t  |  λx. t          abstraction, with or without a form
      t t                        application
      {l1 = t1, ..., ln = tn}    struct (a label may be empty)
      t.l                        projection
      [b]                        byte array ('l' is the UTF-8 bytes of l)
      $name                      built-in
      t~F                        formed term
      F -> F                     function form

if c then t else e   ≡   {e, t} c
```

## Evaluation strategy

Evaluation is **weak** (it never goes under a `λ` or into a struct field) and
**lazy** (it never reduces an ordinary argument). `⇓` stops at:

```
w ::= λx~F. t | {l1 = t1, ...} | [b] | x | $name | F -> G | stuck terms
```

Here are some stuck terms: `args.n`, `blocks.done {...}`, `'add' {'i32', args.n, ...}`,
`{e, t} c` when `c` is not a byte array, `s.l` when `s` has no field `l`, `{} [b]`,
`$unknown t`.

## Computation (at the root)

```
(λx. t1) t2          →  [x ↦ t2] t1                            (E-Beta)
(λx~F. t1) t2        →  [x ↦ strip(t2)~F] t1                   (E-BetaForm)
                         strip(t~G) = t;  strip(t) = t otherwise

{li = ti}.lj         →  tk     tk is the first field labeled lj         (E-Proj)

{f0 = t0, ..., f(n-1) = t(n-1)} [b]  →  t(min(le(b), n-1))
                         n ≥ 1, b ≠ '', labels ignored, [b]~F counts as [b]
                         le(b) = b read as an unsigned little-endian integer   (E-Select)
```

E-Select means that the last field works as a default. So `if [02] then a else b`
and `if [0100] then a else b` both give `a`.

### Built-ins

A built-in fires only when the parts it reads are already reduced (see E-Builtin).

```
$fix t               →  t ($fix t)                              (E-Fix)

$struct_to_fields {l1 = t1, ..., ln = tn}  →  fl(l1 = t1, ..., ln = tn)   (E-ToFields)
$fields_to_struct fl(l1 = t1, ..., ln = tn)  →  {l1 = t1, ..., ln = tn}   (E-FromFields)
    fl()                = {more = [00]}
    fl(l1 = t1, rest)   = {more = [01], label = 'l1', value = t1, rest = fl(rest)}
    (When E-FromFields reads a field list, it ignores extra fields and any
     form on more or label. Each label must be valid UTF-8.)

'op' {v1, ..., vn}  →  [r]~R                                    (E-Opcode)
    'op' is a pure opcode with params p1 ... pn, in this order; labels on
    the fields are ignored. Each form param's vi is a literal form the
    opcode accepts, and each value param's vi is [b] or [b]~iN, where iN
    is the form its form param got, |b| = ceil(N / 8) and le(b) < 2^N.
    R is the result form: a form param's vi, or fixed (i1).
    r = the bytes LLVM computes. There is no rule where LLVM leaves the
    result undefined: x / 0, x % 0, signed-min / -1, signed-min % -1, and
    shifts by the width or more.
```

## Congruence (reduce the blocker)

These rules apply only when no computation rule applies at the root.

```
         t2 → t2'
───────────────────────────────                    (E-SelectArg)
{fi = ti} t2  →  {fi = ti} t2'

   t1 → t1'     t1 is not a struct or a built-in that has a rule
───────────────────────────────                    (E-App1)
      t1 t2  →  t1' t2

     t → t'
───────────────                                    (E-Proj1)
  t.l → t'.l

     t → t'
───────────────                                    (E-Formed; the form F is never reduced)
   t~F → t'~F

  p ⇓ p'     p is a part of t that $name reads, p' ≠ p
───────────────────────────────────                (E-Builtin)
     $name t  →  $name t[p ↦ p']
```

In E-Builtin, the built-in's rule reduces its own parts in order, and it may fire right
after that step. Each built-in reads these parts:

| Built-in | Parts it reads |
|---|---|
| `$fix` | none, so `t` in `$fix t` is never reduced |
| `$struct_to_fields` | the argument |
| `$fields_to_struct` | each node of the list, its `more`, and, if `more = [01]`, its `label` and `rest`; never `value` |
| opcode | the argument, then each field in order, if there is one field per param |

There are no congruence rules for the body of a `λ`, a form, a struct field, or an
ordinary argument.

## Under binders: `shape`

[`banf_shape.shape`](../src/oymo/oymomo/banf_shape.py) is the only code that goes under a `λ`
or into a struct field. It does so only at the positions of BANF's skeleton. Each
position first applies `⇓`. If the result doesn't have the expected shape, `shape`
leaves it as it is, and `convert` reports the error.

```
program(t):     t ⇓ λm. b       ⟹  λm. module(b)
module(b):      b ⇓ {li = fi}   ⟹  {li = function(fi)}
function(f):    f ⇓ λk. g       ⟹  λk. blocks(g)       (a data value: only ⇓)
blocks(g):      g ⇓ {li = bi}   ⟹  {li = block(bi)}
block(b):       b ⇓ λa. t       ⟹  λa. body(t)

body((λx. t) v), with v ⇓ w:
    w is an op       ⟹  (λx. body(t)) op(w)                     (S-Let)
    otherwise        ⟹  body([x ↦ w] t)  (by E-Beta/E-BetaForm) (S-Inline)
body(t):         t → t'  ⟹  body(t');  else terminal(t)

terminal(blocks.l a)    = blocks.l arg(a)                       jump
terminal({fi = ti} c)   = {fi = jump(ti)} atom(c)               branch (2 fields), switch (3+)
terminal(t)             = t                                     [b], args.l, $i, ...

op(t a)          = t arg(a)
op({li = ti})    = {li = atom(ti)}
op(t)            = t                                            (a projection)
arg(a):          a ⇓ {li = ti}  ⟹  {li = atom(ti)};  else a ⇓
jump(t):         t ⇓ blocks.l a  ⟹  blocks.l arg(a);  else t ⇓
atom(t)          = t ⇓
```

An **op** is one of these:

- an application `t a` where `t` is not a struct (`{...} c` is a branch or a switch);
- a struct;
- a projection other than `args.l`.

In a terminal `{f0, ..., f(n-1)} c`, `c` didn't reduce to a byte array, so it's a run-time
selector. Labels are ignored, and the terminal picks a field the same way E-Select does,
so a `c` past the last field takes `f(n-1)`:

- with 2 fields (`if c then t else e`), it becomes a BANF `Branch`;
- with 3 or more fields, it becomes a `Switch` whose default is the last field.

`convert` rejects `{} c`, `{f} c`, and a field that isn't a jump.

`shape` leaves every other position unreduced: a let-bound `λ`, a lambda passed as an
argument, a struct field outside the skeleton, and any form.
