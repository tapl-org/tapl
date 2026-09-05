# Gap

A frontend emits one Gap term. Gap partially evaluates that term, and whatever
cannot reduce is left behind as the residual term. The residual must map
one-to-one onto SSA; if it does not, that is an error.

```text
frontend → Gap → residual → SSA/LLVM IR → machine code
```

Build the AST and the reducer from the grammar below, and build the reader and
printer from that same syntax: the text you read is the term you reduce.

## Syntax

```text
t ::= x                          # variable
    | (lambda x t)               # abstraction
    | (apply t t)                # application
    | (record l = t …)           # record
    | t.l                        # projection
    | (fix t)                    # fixed point
    | b                          # bits (bare token)

v ::= x                          # variable
    | (lambda x t)               # abstraction
    | (record l = v …)           # record value
    | b                          # bits

n ::= x                          # residual eliminator; subject is x or n
    | (apply n t)
    | n.l
    | (fix n)

b ::= [0-9]+                     # integer
    | "[^"]*"                    # string
    | 0x[0-9A-Fa-f]+             # hex bit pattern
```

Three shapes matter when writing the reducer:

- `t` is any term.
- `v` is a value, the shape a rule waits for. `(lambda x t)` is already a value
  even when its body still contains redexes.
- `n` is a neutral term: an elimination whose innermost subject is a variable,
  such as `x.a`. A neutral is not an error; it is residual and survives to SSA.

A name on its own is a variable, as in `env` or `x`. The same spelling after a
`.`, or to the left of an `=`, is a label instead, as in `env.puts` and
`main = t`. Labels are field names rather than terms, so they never reduce.
Keep record fields in the order they were written, in the AST, in the reducer,
and in the printer.

```text
(record a = x).a              →  x             # select under binders
(record a = x).b              ↛                 # residual (miss)
x.a                           ↛                 # residual
```

Projection is the only way to read a field:

- When the record already has that label, the projection reduces to the field's
  value. This may happen anywhere, including inside a `(lambda …)` body.
- When the label is missing, nothing fires: keep the node as residual.
- When the subject is a variable or another neutral, keep the node and look for
  work elsewhere in the term.

`apply` performs β-reduction only. Applying a record to something is not a field
lookup, so such a node stays residual.

A bare numeral (non-negative integers. use hex token for negative numbers), string, or hex token is bits; bits need no wrapper.

The only heads a list may have are `lambda`, `record`, `fix`, and `apply`. A
list with any other head is an error rather than an implicit application, and
the empty list is invalid.

```text
arity(lambda) = 2
arity(fix) = 1
arity(apply) = 2
arity(record) = (l = t)+                         # one or more fields

x ∩ b = ∅                     # lexer: if token matches b it is bits, never a variable
lambda-param                  =  atom and not b
l                             =  atom and not b  # AST: label ≠ variable
labels in one record          pairwise distinct
```

The parser checks everything in that table, including that no two fields of one
record share a label. Two things are deliberately left unchecked: whether a
projection will find its field, and whether `fix` is applied to a `(lambda …)`.
Partial evaluation fires those rules when a term happens to match them, and
otherwise leaves the node residual.

## Evaluation

Reduction is strong, so any redex may fire wherever it sits, including under a
`(lambda …)`. The rules say which steps are legal, not which order to take them
in; partial evaluation picks the order, and every node it leaves alone becomes
part of the residual.

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
```

The computation rules:

```text
(apply (lambda x t) s)        →  [x ↦ s] t                    (E-AppAbs)

(record … l = v …).l          →  v                            (E-Proj)
                                                                  # wait until record is a value

(fix (lambda x t))            →  [x ↦ (fix (lambda x t))] t   (E-Fix)
                                                                  # only under (apply (fix t) s)
                                                                  # or (fix t).l
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
FV(b)                         = ∅

closed(t)                     ≜  FV(t) = ∅
```

Substitution must avoid capture: before going under `(lambda y …)`, rename `y`
to a fresh name if `y` occurs free in the term being substituted. Labels are
never substituted. Internally we use de Bruijn indexes so no need for alpha reduction.

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
[x ↦ s] b                     = b
```

## Bits

Bits come in three kinds: non-negative integer, string, and hex bit pattern. There is no
decimal float syntax, so write a float as the hex of its encoding.

```text
b ∈ { 42, "hello", 0x3f800000 }
```

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

`env` is the record holding everything the unit needs from outside, primitives
included; read from it by projection, as in `env.add-i32`. The inner `module`
parameter is the recursive-record generator, so fields reach one another through
`module.helper`, and `fix` on that inner `lambda` ties the recursion.

Gap has no layering form and no `θ` calculus from Tapl project.

## Residual to LLVM IR

Since `env` is a variable, `env.l` can never reduce; each one names an external
function, and the table below says how to emit it. A residual the table does not
cover is an error. `env.puts` has LLVM type `i32 (ptr)`. An unused `self`
produces no IR, and `main` returns its lowered body rather than a synthetic `0`.

```text
(lambda env
  (lambda self
    (record
      main = (apply env.puts "Hello World!"))))
```

```llvm
@s = private unnamed_addr constant [13 x i8] c"Hello World!\00"

declare i32 @puts(ptr)

define i32 @main() {
  %0 = call i32 @puts(ptr @s)
  ret i32 %0
}
```

```text
(lambda env t)                 ↦  declare each env.l used in t
(lambda self t)                ↦  t                            # unused self
(record main = t)              ↦  define i32 @main() { ret lower(t) }
(apply env.puts s)             ↦  call i32 @puts(ptr lower(s))
"…"                            ↦  private [n x i8] global       # n = |bytes|+1
```
