# Gap

A frontend emits one Gap term. Partial evaluation reduces it. The residual
term maps one-to-one onto SSA if possible otherwise error.

```text
frontend → Gap → residual → SSA → machine code
```

Implement the AST and reducer from this grammar; implement the
reader/printer for the same syntax.

## Syntax

```text
t ::= x                          # variable
    | (lambda x t)               # abstraction
    | (apply t t)                # application (also record select)
    | (record b = t …)           # record
    | (record t b = t …)         # record with default
    | (fix t)                    # fixed point
    | b                          # bits (bare token)

v ::= x                          # variable
    | (lambda x t)               # abstraction
    | (record b = v …)           # record value
    | (record v b = v …)         # record value with default
    | b                          # bits

n ::= x                          # residual eliminator; subject is x or n
    | (apply n t)
    | (fix n)

b ::= [0-9]+                     # integer
    | "[^"]*"                    # string
    | 0x[0-9A-Fa-f]+             # hex bit pattern
```

Field order is sorted by bits at parse: integers by value, then strings
by bytes (`0`, `00`, `0x0` are the same key). Preserve that order in the
AST, reducer, and printer.

```text
(apply (record "a" = x) "a")  →  x             # select under binders
(apply (record d "a" = x) "b") →  d            # miss → default (once values)
(apply x "a")             ↛                    # neutral, not stuck
```

Application of a record to a matching key is computation, including under
`(lambda …)`. A miss uses the default if the record has one, else stuck.
Application whose function is a variable (or other neutral) is residual:
keep the node and reduce elsewhere.

A leading bare term is the default, not a key; at most one. A bare term
after a field is an error. A bare numeral, string, or hex token is bits.

Reserved heads: `lambda`, `record`, `fix`, `apply`. An unknown head is
an error; do not treat it as application. Empty lists are invalid.

```text
arity(lambda) = 2
arity(fix) = 1
arity(apply) = 2
arity(record) = t? (b = t)+                  # optional default, then one or more fields

x ∩ b = ∅                     # lexer: if token matches b it is bits, never a variable
lambda-param                  =  atom and not b
keys in one record            pairwise distinct by bits denotation
CU                            closed
```

Parse checks the table above, including key distinctness. It does not
check whether a record application finds a key or whether `fix` is
applied to a `(lambda …)`. The reducer checks those.

## Evaluation

Small-step `t → t'`. Reduction is strong: any redex may fire, including
under `(lambda …)`. The relation is not a strategy. Partial evaluation
chooses which legal steps to take. What remains is the residual.

Dispatch on application:

1. Function is `(lambda x t)` → `E-AppAbs` (argument need not be a value).
2. Function is a record value and argument equals a key (bits
   denotation) → `E-AppRcd`.
3. Function is a record value, no key equals the argument, default
   present → `E-AppRcdDefault`.
4. Function is `b` → stuck.
5. Function is a variable or other neutral → residual `(apply n t)`.
6. Otherwise reduce the function or argument (`E-App1`, `E-App2`), or
   reduce inside the record (`E-Rcd0`, `E-Rcd2`) until (1), (2), or (3)
   applies.

```text
(apply (lambda x t) s)        →  [x ↦ s] t                    (E-AppAbs)

(apply (record … bk = v …) bk)
                              →  v                            (E-AppRcd)

(apply (record d …) v)        →  d                            (E-AppRcdDefault)
                                                      # no key equals v

(fix (lambda x t))            →  [x ↦ (fix (lambda x t))] t   (E-Fix)
```

`E-AppRcd` and `E-AppRcdDefault` wait until the record is a value and
the argument is a value. Keys are already bits; only the argument is
compared. Key match wins over the default. Two values are equal when
they are the same constructor and their children are equal: same
variable name, same bits denotation (`0`, `00`, `0x0` are the same
integer 0), records with the same fields (sorted) and the same default
(both absent, or equal), abstractions up to α.

`E-Fix` may fire whenever its argument is an abstraction. Unrestricted
use diverges. Unfold `fix` only when an eliminator needs it
(`(apply (fix t) s)`). The exact PE strategy is unspecified.

```text
stuck(t)  ≜  t ∉ v ∧ t ∉ n ∧ ¬∃t'. t → t'
```

Stuck includes a missing record key with no default, and `b` in function
position.
A neutral is residual, not stuck: do not report an error; leave it for SSA.

Congruence — implement by recursing into any child:

```text
      t → t'
────────────────                               (E-Abs)
(lambda x t) → (lambda x t')


     t₁ → t₁'
────────────────                               (E-App1)
(apply t₁ t₂) → (apply t₁' t₂)


     t₂ → t₂'
────────────────                               (E-App2)
(apply t₁ t₂) → (apply t₁ t₂')


      d → d'
────────────────────────────────────────       (E-Rcd0)
(record d …) → (record d' …)                   # reduce the default


      u → u'
────────────────────────────────────────       (E-Rcd2)
(record … b = u …) → (record … b = u' …)       # reduce a field


      t → t'
────────────────                               (E-Fix1)
   (fix t) → (fix t')
```

## Binding

Free variables include the default and fields. Keys are bits; `FV(b) = ∅`.

```text
FV(x)                         = {x}
FV((lambda x t))              = FV(t) \ {x}
FV((apply t₁ t₂))             = FV(t₁) ∪ FV(t₂)
FV((record b₁ = u₁ … bₙ = uₙ))
                              = ⋃ᵢ FV(uᵢ)
FV((record d b₁ = u₁ … bₙ = uₙ))
                              = FV(d) ∪ ⋃ᵢ FV(uᵢ)
FV((fix t))                   = FV(t)
FV(b)                         = ∅

closed(t)                     ≜  FV(t) = ∅
```

A compilation unit must be closed. Only `lambda` binds. Record keys do
not bind. Alpha-equivalent terms differ only in bound names; treat them
as the same when comparing binders.

Capture-avoiding substitution. If `y ∈ FV(s)`, rename `y` to a fresh name
before substituting under `(lambda y …)`. Substitute into fields and the
default, not into keys.

```text
[x ↦ s] x                     = s
[x ↦ s] y                     = y                              (y ≠ x)
[x ↦ s] (lambda x t)          = (lambda x t)                   # shadow
[x ↦ s] (lambda y t)          = (lambda y [x ↦ s] t)           (y ≠ x, y ∉ FV(s))
[x ↦ s] (apply t₁ t₂)         = (apply ([x ↦ s] t₁) ([x ↦ s] t₂))
[x ↦ s] (record bᵢ = uᵢ)ᵢ     = (record bᵢ = [x ↦ s] uᵢ)ᵢ
[x ↦ s] (record d bᵢ = uᵢ)ᵢ   = (record [x ↦ s] d bᵢ = [x ↦ s] uᵢ)ᵢ
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

Each input is one closed term. Keys are bits, so they do not open the
unit:

```text
CU  ::=  (lambda env
           (lambda self
             (record
               "main" = …
               "helper" = …)))
FV(CU) = ∅
```

`env` is a record of external dependencies (primitives). `self` is the
recursive-record generator. Access fields by application:
`(apply env "add-i32")`, `(apply self "helper")`. Tie recursion with
`fix` on the inner `lambda`.

No layering form and no `θ`.
