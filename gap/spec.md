# Gap

```text
frontend → Gap → residual → SSA/LLVM IR → machine code
```

- A frontend emits one Gap term
- Gap partially evaluates it; whatever cannot reduce is the residual term
- The residual must map one-to-one onto SSA, otherwise it is an error
- Build the AST and reducer from the grammar below, and the reader and printer
  from that same syntax: the text you read is the term you reduce

## Syntax

```text
t ::= x                          # variable
    | (lambda x t)               # abstraction
    | (apply t t)                # application
    | (record l = t …)           # record
    | t.l                        # projection
    | (fix t)                    # fixed point
    | (if t t t)                 # conditional
    | b                          # bits (bare token)

v ::= x                          # variable
    | (lambda x t)               # abstraction
    | (record l = v …)           # record value
    | b                          # bits

n ::= x                          # residual eliminator; subject is x or n
    | (apply n t)
    | n.l
    | (fix n)
    | (if n t t)                 # branch on an unknown condition

b ::= [0-9]+                     # integer
    | "[^"]*"                    # string
    | 0x[0-9A-Fa-f]+             # hex bit pattern
```

Three shapes matter when writing the reducer:

- `t` is any term
- `v` is a value, the shape a rule waits for. `(lambda x t)` is already a value
  even when its body still contains redexes
- `n` is a neutral term: an elimination whose innermost subject is a variable,
  such as `x.a`. A neutral is residual rather than an error; it survives to SSA

Names, labels, and bits:

- A name on its own is a variable: `env`, `x`
- The same spelling after a `.`, or to the left of an `=`, is a label instead:
  `env.puts`, `main = t`
- Labels are field names rather than terms, so they never reduce
- Keep record fields in written order, in the AST, the reducer, and the printer
- A bare numeral, string, or hex token is bits; bits need no wrapper

```text
(record a = x).a              →  x             # select under binders
(record a = x).b              ↛                 # residual (miss)
x.a                           ↛                 # residual
```

Projection is the only way to read a field:

- When the record has that label, the projection reduces to the field's value.
  This may happen anywhere, including inside a `(lambda …)` body
- When the label is missing, nothing fires: keep the node as residual
- When the subject is a variable or another neutral, keep the node and look for
  work elsewhere in the term

`apply` performs β-reduction only. Applying a record to something is not a field
lookup, so such a node stays residual.

Every other list is a form with a reserved head:

- The only heads are `lambda`, `record`, `fix`, `apply`, and `if`
- Any other head is an error, never an implicit application
- The empty list is invalid

```text
arity(lambda) = 2
arity(fix) = 1
arity(apply) = 2
arity(if) = 3
arity(record) = (l = t)+                         # one or more fields

x ∩ b = ∅                     # lexer: if token matches b it is bits, never a variable
lambda-param                  =  atom and not b
l                             =  atom and not b  # AST: label ≠ variable
labels in one record          pairwise distinct
```

The parser checks that whole table, including that no two fields of one record
share a label. It deliberately does not check:

- whether a projection will find its field
- whether `fix` is applied to a `(lambda …)`
- whether the condition of an `if` is bits

Partial evaluation fires those rules when a term happens to match them, and
otherwise leaves the node residual.

## Evaluation

- Reduction is strong: any redex may fire wherever it sits, including under a
  `(lambda …)`
- The rules say which steps are legal, not which order to take them in
- Partial evaluation picks the order; every node it leaves alone becomes part of
  the residual

For each elimination, try the cases in order and take the first that matches:

```text
# apply — first match
(apply (lambda x t) s)        E-AppAbs                         # s need not be v
else                          E-App1 | E-App2
# no rule → residual (keep the node; leave for SSA)
# (apply b _); (apply n t); (apply rcd _)

# proj — first match
rcd.l  l ∈ keys               E-Proj                           # rcd ∈ v
else                          E-Proj1 | E-Rcd
# no rule → residual (keep the node; leave for SSA)
# miss; b.l; n.l

# if — first match
(if b t₂ t₃)  b ≠ 0           E-IfNonzero                      # take t₂
(if b t₂ t₃)  b = 0           E-IfZero                         # take t₃
else                          E-If1 | E-If2 | E-If3
# no rule → residual (keep the node; leave for SSA)
# (if n t t); (if (lambda x t) t t); (if rcd t t)
```

The computation rules:

```text
(apply (lambda x t) s)        →  [x ↦ s] t                    (E-AppAbs)

(record … l = v …).l          →  v                            (E-Proj)
                                                                  # wait until record is a value

(fix (lambda x t))            →  [x ↦ (fix (lambda x t))] t   (E-Fix)
                                                                  # only under (apply (fix t) s)
                                                                  # or (fix t).l

(if b t₂ t₃)   b ≠ 0          →  t₂                           (E-IfNonzero)
(if b t₂ t₃)   b = 0          →  t₃                           (E-IfZero)
                                                                  # wait until the condition is bits
```

The congruence rules say only that a step inside any child is a step of the
whole term:

```text
# recurse into any child
      t → t'
────────────────                               (E-Abs)
(lambda x t) → (lambda x t')

     t₁ → t₁'
────────────────                               (E-App1)
(apply t₁ t₂) → (apply t₁' t₂)

     t₂ → t₂'
────────────────                               (E-App2)
(apply t₁ t₂) → (apply t₁ t₂')

      u → u'
────────────────────────────────────────       (E-Rcd)
(record … l = u …) → (record … l = u' …)       # field

      t → t'
────────────────                               (E-Proj1)
     t.l → t'.l

      t → t'
────────────────                               (E-Fix1)
   (fix t) → (fix t')

           t₁ → t₁'
────────────────────────────                   (E-If1)
(if t₁ t₂ t₃) → (if t₁' t₂ t₃)

           t₂ → t₂'
────────────────────────────                   (E-If2)
(if t₁ t₂ t₃) → (if t₁ t₂' t₃)                 # legal even before t₁ is bits

           t₃ → t₃'
────────────────────────────                   (E-If3)
(if t₁ t₂ t₃) → (if t₁ t₂ t₃')
```

## Binding

Only `lambda` binds a name, and `FV(t)` collects the variables that nothing
binds:

```text
FV(x)                         = {x}
FV((lambda x t))              = FV(t) \ {x}                   # only lambda binds
FV((apply t₁ t₂))             = FV(t₁) ∪ FV(t₂)
FV((record lᵢ = uᵢ)ᵢ)         = ⋃ᵢ FV(uᵢ)                     # labels are not terms
FV(t.l)                       = FV(t)
FV((fix t))                   = FV(t)
FV((if t₁ t₂ t₃))             = FV(t₁) ∪ FV(t₂) ∪ FV(t₃)
FV(b)                         = ∅

closed(t)                     ≜  FV(t) = ∅
```

Substitution below is written on names:

- Labels are never substituted
- The implementation stores binders as de Bruijn indexes, so it needs no
  renaming and no α-conversion

```text
# if y ∈ FV(s), rename y fresh before substituting under (lambda y …)
[x ↦ s] x                     = s
[x ↦ s] y                     = y                              (y ≠ x)
[x ↦ s] (lambda x t)          = (lambda x t)                   # shadow
[x ↦ s] (lambda y t)          = (lambda y [x ↦ s] t)           (y ≠ x, y ∉ FV(s))
[x ↦ s] (apply t₁ t₂)         = (apply ([x ↦ s] t₁) ([x ↦ s] t₂))
[x ↦ s] (record lᵢ = uᵢ)ᵢ     = (record lᵢ = [x ↦ s] uᵢ)ᵢ      # not labels
[x ↦ s] (t.l)                 = ([x ↦ s] t).l
[x ↦ s] (fix t)               = (fix [x ↦ s] t)
[x ↦ s] (if t₁ t₂ t₃)         = (if ([x ↦ s] t₁) ([x ↦ s] t₂) ([x ↦ s] t₃))
[x ↦ s] b                     = b
```

## Bits

- Three kinds: non-negative integer, string, hex bit pattern
- Write a negative number as a hex token
- There is no decimal float syntax: write a float as the hex of its encoding

```text
b ∈ { 42, "hello", 0x3f800000 }

b = 0                         ⇔  every bit of b is 0
0, 0x0, 0x00000000, ""        = 0               # "" has no bits, so it is zero
1, 0x1, "0", "hello"          ≠ 0               # "0" is the byte 0x30
```

An `if` reads its condition as bits and compares the bit pattern, not the kind:
zero is the only false condition, every other bits value is true. A condition
that is not bits fires no rule, so the `if` stays residual.

## Compilation unit

Each input is one closed term: two nested lambdas around a record. Field names
are labels rather than terms, so they never leave the unit open.

```text
CU  ::=  (lambda env
           (lambda module
             (record
               main = …
               helper = …)))
FV(CU) = ∅
```

- `env` holds everything the unit needs from outside, primitives included; read
  from it by projection, as in `env.add-i32`
- `module` is the recursive-record generator, so fields reach one another
  through `module.helper`
- `fix` on the inner `lambda` ties the recursion
- Gap has no layering form and no `θ` calculus from the Tapl project


