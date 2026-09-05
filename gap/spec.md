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
(apply (record "a" = x) "b") ↛                 # residual (miss, no default)
(apply x "a")             ↛                    # residual
```

Application of a record to a matching key is computation, including under
`(lambda …)`. A miss uses the default if the record has one, else residual:
keep the node. Application whose function is a variable (or other
neutral) is residual: keep the node and reduce elsewhere.

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
applied to a `(lambda …)`. PE fires those rules when they match;
otherwise the node is residual.

## Evaluation

Strong `t → t'`: any redex may fire, including under `(lambda …)`. PE
chooses which legal steps (strategy unspecified); the rest is residual.

```text
# apply — first match
(apply (lambda x t) s)        E-AppAbs                         # s need not be v
(apply rcd v)  v ≡ key        E-AppRcd                         # rcd ∈ v
(apply rcd v)  no key ≡ v     E-AppRcdDefault                  # rcd ∈ v, has default
else                          E-App1 | E-App2 | E-Rcd0 | E-Rcd2
# no rule → residual (keep the node; leave for SSA)
# miss, no default; (apply b _); (apply n t)
```

```text
(apply (lambda x t) s)        →  [x ↦ s] t                    (E-AppAbs)

(apply (record … bk = v …) bk)
                              →  v                            (E-AppRcd)
                                                                  # keys already b; arg ≡ key

(apply (record d …) v)        →  d                            (E-AppRcdDefault)
                                                                  # no key ≡ v; match wins

(fix (lambda x t))            →  [x ↦ (fix (lambda x t))] t   (E-Fix)
                                                                  # only under (apply (fix t) s)
```

```text
v ≡ v'                        ≜  same constructor ∧ children ≡
x ≡ x
b ≡ b'                        ≜  denotation(b) = denotation(b')   # 0, 00, 0x0
(lambda x t) ≡ (lambda y s)   ≜  α
(record …) ≡ (record …)       ≜  same fields (sorted) ∧ same default
                                                                  # both absent, or ≡
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

      d → d'
────────────────────────────────────────       (E-Rcd0)
(record d …) → (record d' …)                   # default

      u → u'
────────────────────────────────────────       (E-Rcd2)
(record … b = u …) → (record … b = u' …)       # field

      t → t'
────────────────                               (E-Fix1)
   (fix t) → (fix t')
```

## Binding

```text
FV(x)                         = {x}
FV((lambda x t))              = FV(t) \ {x}                   # only lambda binds
FV((apply t₁ t₂))             = FV(t₁) ∪ FV(t₂)
FV((record bᵢ = uᵢ)ᵢ)         = ⋃ᵢ FV(uᵢ)                     # keys are b
FV((record d bᵢ = uᵢ)ᵢ)       = FV(d) ∪ ⋃ᵢ FV(uᵢ)
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
[x ↦ s] (record bᵢ = uᵢ)ᵢ     = (record bᵢ = [x ↦ s] uᵢ)ᵢ      # not keys
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
