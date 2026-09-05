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
    | (record t = t …)           # record (keys are terms)
    | (record t t = t …)         # record with default
    | (fix t)                    # fixed point
    | b                          # bits (bare token)

v ::= x                          # variable
    | (lambda x t)               # abstraction
    | (record v = v …)           # record value
    | (record v v = v …)         # record value with default
    | b                          # bits

n ::= x                          # residual eliminator; subject is x or n
    | (apply n t)
    | (fix n)

b ::= [0-9]+                     # integer
    | "[^"]*"                    # string
    | 0x[0-9A-Fa-f]+             # hex bit pattern
```

A record key is a term, not a separate syntactic class. A record is a
value only when the default (if present) and every key and every field
is a value. `(lambda x t)` is a value even when `t` still has redexes.
A variable is both a value and a neutral.

```text
(apply t1 t2 t3)              error            # apply is exactly binary
(apply (apply f x) y)                          # nest for more args
(record)                      ≡ unit
(record d)                    ≡ default only
keys(v_record) pairwise distinct
default is not a key
b has no subterms
eliminators = { apply, fix }
```

Field order is semantic: preserve it in the AST, reducer, and printer.

```text
(apply (record a = x) a)  →  x                 # select under binders
(apply (record d a = x) b) →  d                # miss → default (once values)
(apply x a)               ↛                    # neutral, not stuck
```

Application of a record to a matching key is computation, including under
`(lambda …)`. A miss uses the default if the record has one, else stuck.
Application whose function is a variable (or other neutral) is residual:
keep the node and reduce elsewhere.

A record field is `term = term`. A leading bare term is the default, not
a key; at most one. A bare term after a field is an error. A bare name
on either side of `=` is a variable. A bare numeral, string, or hex
token is bits.

Reserved heads: `lambda`, `record`, `fix`, `let`, `apply`. An unknown
head is an error; do not treat it as application. Empty lists are
invalid.

```text
arity(lambda) = 2
arity(fix) = 1
arity(apply) = 2
arity(record) = t? (t = t)*                  # optional default, then fields
arity(let) = (x = t)* t

x ∩ b = ∅                     # lexer: if token matches b it is bits, never a variable
lambda-param                  =  atom and not b
keys in one record            pairwise distinct as terms
CU                            closed
```

Parse checks the table above. It does not check whether a record
application finds a key or whether `fix` is applied to a `(lambda …)`.
The reducer checks those.

## Sugar

Desugar before or during parse. The reducer sees only core `t`.

```text
(let x = e t)                 ≡ (apply (lambda x t) e)
true                          ≡ 1
false                         ≡ 0
(fix t s)                     ≡ (apply (fix t) s)

# each eᵢ may mention x₁…xᵢ₋₁
(let x1 = e1 … xn = en t)     ≡ (apply (lambda x1 (… (apply (lambda xn t) en) …)) e1)
```

## Evaluation

Small-step `t → t'`. Reduction is strong: any redex may fire, including
under `(lambda …)`. The relation is not a strategy. Partial evaluation
chooses which legal steps to take. What remains is the residual.

Dispatch on application:

1. Function is `(lambda x t)` → `E-AppAbs` (argument need not be a value).
2. Function is a record value and argument equals a key → `E-AppRcd`.
3. Function is a record value, no key equals the argument, default
   present → `E-AppRcdDefault`.
4. Function is `b` → stuck.
5. Function is a variable or other neutral → residual `(apply n t)`.
6. Otherwise reduce the function or argument (`E-App1`, `E-App2`), or
   reduce inside the record (`E-Rcd0`, `E-Rcd1`, `E-Rcd2`) until (1),
   (2), or (3) applies.

```text
(apply (lambda x t) s)        →  [x ↦ s] t                    (E-AppAbs)

(apply (record … vk = v …) vk)
                              →  v                            (E-AppRcd)

(apply (record d …) v)        →  d                            (E-AppRcdDefault)
                                                      # no key equals v

(fix (lambda x t))            →  [x ↦ (fix (lambda x t))] t   (E-Fix)
```

`E-AppRcd` and `E-AppRcdDefault` wait until the record is a value and
the argument is a value. Key match wins over the default. Two values
are equal when they are the same constructor and their children are
equal: same variable name, same bits denotation (`0`, `00`, `0x0` are
the same integer 0), records with the same fields in order and the same
default (both absent, or equal), abstractions up to α.

If reducing keys makes two keys equal, that is a reduction error.

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


      t → t'
────────────────────────────────────────       (E-Rcd1)
(record … t = u …) → (record … t' = u …)       # reduce a key


      u → u'
────────────────────────────────────────       (E-Rcd2)
(record … t = u …) → (record … t = u' …)       # reduce a field


      t → t'
────────────────                               (E-Fix1)
   (fix t) → (fix t')
```

## Binding

Free variables include record keys and the default.

```text
FV(x)                         = {x}
FV((lambda x t))              = FV(t) \ {x}
FV((apply t₁ t₂))             = FV(t₁) ∪ FV(t₂)
FV((record t₁ = u₁ … tₙ = uₙ))
                              = ⋃ᵢ (FV(tᵢ) ∪ FV(uᵢ))
FV((record d t₁ = u₁ … tₙ = uₙ))
                              = FV(d) ∪ ⋃ᵢ (FV(tᵢ) ∪ FV(uᵢ))
FV((fix t))                   = FV(t)
FV(b)                         = ∅

closed(t)                     ≜  FV(t) = ∅
```

A compilation unit must be closed. Only `lambda` binds. A record key does
not bind: `(record x = t)` has free `x` unless an enclosing `lambda` binds
it. Alpha-equivalent terms differ only in bound names; treat them as the
same when comparing binders.

Capture-avoiding substitution. If `y ∈ FV(s)`, rename `y` to a fresh name
before substituting under `(lambda y …)`. Substitute into keys, fields,
and the default.

```text
[x ↦ s] x                     = s
[x ↦ s] y                     = y                              (y ≠ x)
[x ↦ s] (lambda x t)          = (lambda x t)                   # shadow
[x ↦ s] (lambda y t)          = (lambda y [x ↦ s] t)           (y ≠ x, y ∉ FV(s))
[x ↦ s] (apply t₁ t₂)         = (apply ([x ↦ s] t₁) ([x ↦ s] t₂))
[x ↦ s] (record tᵢ = uᵢ)ᵢ     = (record [x ↦ s] tᵢ = [x ↦ s] uᵢ)ᵢ
[x ↦ s] (record d tᵢ = uᵢ)ᵢ   = (record [x ↦ s] d [x ↦ s] tᵢ = [x ↦ s] uᵢ)ᵢ
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

Each input is one closed term. Keys are ordinary terms; bits keep the
unit closed:

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
