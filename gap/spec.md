# Gap

A frontend emits one Gap term. Partial evaluation reduces it. The residual
term maps one-to-one onto SSA if possible otherwise error.

```text
frontend → Gap → residual → SSA/LLVM IR → machine code
```

Implement the AST and reducer from this grammar; implement the
reader/printer for the same syntax.

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

- A name standing alone is a variable: `env`, `x`
- The same spelling after `.` or left of `=` is a label: `env.puts`, `main = t`
- A label is not a term; it does not reduce
- Field order is as written; keep that order in the AST, reducer, and printer

```text
(record a = x).a              →  x             # select under binders
(record a = x).b              ↛                 # residual (miss)
x.a                           ↛                 # residual
```

- A matching label is computation, including under `(lambda …)`
- A miss is residual: keep the node
- A subject that is a variable (or other neutral) is residual: keep the
  node and reduce elsewhere
- Application is only β; a record in function position is residual

A bare numeral, string, or hex token is bits.

Reserved heads: `lambda`, `record`, `fix`, `apply`. An unknown head is
an error; do not treat it as application. Empty lists are invalid.

```text
arity(lambda) = 2
arity(fix) = 1
arity(apply) = 2
arity(record) = (l = t)+                         # one or more fields

x ∩ b = ∅                     # lexer: if token matches b it is bits, never a variable
lambda-param                  =  atom and not b
l                             =  atom and not b  # AST: label ≠ variable
labels in one record          pairwise distinct
CU                            closed
```

Parse checks the table above, including label distinctness. It does not
check whether a projection finds a field or whether `fix` is applied to
a `(lambda …)`. PE fires those rules when they match; otherwise the node
is residual.

## Evaluation

Strong `t → t'`: any redex may fire, including under `(lambda …)`. PE
chooses which legal steps (strategy unspecified); the rest is residual.

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

```text
(apply (lambda x t) s)        →  [x ↦ s] t                    (E-AppAbs)

(record … l = v …).l          →  v                            (E-Proj)
                                                                  # wait until record is a value

(fix (lambda x t))            →  [x ↦ (fix (lambda x t))] t   (E-Fix)
                                                                  # only under (apply (fix t) s)
                                                                  # or (fix t).l
```

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

Three value kinds: integer, string, hexadecimal bit pattern. There is no
decimal float; write a float as the hex of its encoding.

```text
b ∈ { 42, "hello", 0x3f800000 }
```

## Compilation unit

Each input is one closed term. Labels are not terms, so they do not open
the unit:

```text
CU  ::=  (lambda env
           (lambda self
             (record
               main = …
               helper = …)))
FV(CU) = ∅
```

`env` is a record of external dependencies (primitives). `self` is the
recursive-record generator. Access fields by projection: `env.add-i32`,
`self.helper`. Tie recursion with `fix` on the inner `lambda`.

No layering form and no `θ`.

## Residual to LLVM IR

`env.l` is residual (`env` is a variable). A residual not in the table is
an error. `env.puts` has LLVM type `i32 (ptr)`. Unused `self` emits no
IR. `main` returns the lowered body, not a synthetic `0`.

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
