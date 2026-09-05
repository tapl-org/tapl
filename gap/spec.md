# Gap

A frontend emits one Gap term. Partial evaluation reduces it. The residual
term maps one-to-one onto SSA.

```text
frontend → Gap → residual → SSA → machine code
```

The abstract language is the IR. The Text section is only concrete syntax.
Implement the AST and reducer from the abstract language; implement the
reader/printer from Text.

## Syntax

```text
t ::= x                          # variable
    | λx. t                      # abstraction
    | t t                        # application (also record select)
    | { t = t, … }               # record (keys are terms)
    | fix t                      # fixed point
    | b                          # bits

v ::= x                          # variable
    | λx. t                      # abstraction
    | { v = v, … }               # record value
    | b                          # bits

n ::= x                          # residual eliminator; subject is x or n
    | n t
    | fix n

b ::= [0-9]+                     # integer
    | "[^"]*"                    # string
    | 0x[0-9A-Fa-f]+             # hex bit pattern
```

A record key is a term, not a separate syntactic class. A record is a
value only when every key and every field is a value. `λx. t` is a value
even when `t` still has redexes. A variable is both a value and a
neutral.

```text
f x y                         ≡ (f x) y          # application is left-assoc
{}                            ≡ unit
keys(v_record) pairwise distinct
b has no subterms
eliminators = { application, fix }
```

Field order is semantic: preserve it in the AST, reducer, and printer.

```text
{ a = x } a  →  x                                # select under binders
x a          ↛                                   # neutral, not stuck
```

Application of a record to a matching key is computation, including under
λ. Application whose function is a variable (or other neutral) is residual:
keep the node and reduce elsewhere.

## Sugar

Desugar before or during parse. The reducer sees only core `t`.

```text
f x y                         ≡ (f x) y
let x = e in body             ≡ (λx. body) e
true                          ≡ 1
false                         ≡ 0

# each eᵢ may mention x₁…xᵢ₋₁
let x₁ = e₁; …; xₙ = eₙ in t  ≡ (λx₁. (… (λxₙ. t) eₙ …)) e₁
```

## Evaluation

Small-step `t → t'`. Reduction is strong: any redex may fire, including
under λ. The relation is not a strategy. Partial evaluation chooses which
legal steps to take. What remains is the residual.

Dispatch on application:

1. Function is `λx. t` → `E-AppAbs` (argument need not be a value).
2. Function is a record value and argument equals a key → `E-AppRcd`.
3. Function is `b` → stuck.
4. Function is a variable or other neutral → residual `n t`.
5. Otherwise reduce the function or argument (`E-App1`, `E-App2`), or
   reduce inside the record (`E-Rcd1`, `E-Rcd2`) until (1) or (2) applies.

```text
(λx. t) s                     →  [x ↦ s] t                    (E-AppAbs)

{ …, vₖ = v, … } vₖ           →  v                            (E-AppRcd)

fix (λx. t)                   →  [x ↦ fix (λx. t)] t          (E-Fix)
```

`E-AppRcd` waits until the record is a value and the argument is a value.
Two values are equal when they are the same constructor and their
children are equal: same variable name, same bits denotation (`0`, `00`,
`0x0` are the same integer 0), records with the same fields in order,
abstractions up to α.

If reducing keys makes two keys equal, that is a reduction error.

`E-Fix` may fire whenever its argument is an abstraction. Unrestricted
use diverges. Unfold `fix` only when an eliminator needs it
(`(fix t) s`). The exact PE strategy is unspecified.

```text
stuck(t)  ≜  t ∉ v ∧ t ∉ n ∧ ¬∃t'. t → t'
```

Stuck includes a missing record key and `b` in function position.
A neutral is residual, not stuck: do not report an error; leave it for SSA.

Congruence — implement by recursing into any child:

```text
      t → t'
────────────────                               (E-Abs)
   λx. t → λx. t'


     t₁ → t₁'
────────────────                               (E-App1)
   t₁ t₂ → t₁' t₂


     t₂ → t₂'
────────────────                               (E-App2)
   t₁ t₂ → t₁ t₂'


      t → t'
────────────────────────────                   (E-Rcd1)
{ …, t = u, … } → { …, t' = u, … }             # reduce a key


      u → u'
────────────────────────────                   (E-Rcd2)
{ …, t = u, … } → { …, t = u', … }             # reduce a field


      t → t'
────────────────                               (E-Fix1)
   fix t → fix t'
```

## Binding

Free variables include record keys.

```text
FV(x)                         = {x}
FV(λx. t)                     = FV(t) \ {x}
FV(t₁ t₂)                     = FV(t₁) ∪ FV(t₂)
FV({ t₁ = u₁, …, tₙ = uₙ })   = ⋃ᵢ (FV(tᵢ) ∪ FV(uᵢ))
FV(fix t)                     = FV(t)
FV(b)                         = ∅

closed(t)                     ≜  FV(t) = ∅
```

A compilation unit must be closed. Only `λ` binds. A record key does not
bind: `{ x = t }` has free `x` unless an enclosing λ binds it.
Alpha-equivalent terms differ only in bound names; treat them as the
same when comparing binders.

Capture-avoiding substitution. If `y ∈ FV(s)`, rename `y` to a fresh name
before substituting under `λy`. Substitute into keys and fields.

```text
[x ↦ s] x                     = s
[x ↦ s] y                     = y                              (y ≠ x)
[x ↦ s] (λx. t)               = λx. t                          # shadow
[x ↦ s] (λy. t)               = λy. [x ↦ s] t                  (y ≠ x, y ∉ FV(s))
[x ↦ s] (t₁ t₂)               = ([x ↦ s] t₁) ([x ↦ s] t₂)
[x ↦ s] { tᵢ = uᵢ }ᵢ          = { [x ↦ s] tᵢ = [x ↦ s] uᵢ }ᵢ
[x ↦ s] (fix t)               = fix ([x ↦ s] t)
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
CU  ::=  λenv. λself. { "main" = …, "helper" = … }
FV(CU) = ∅
```

`env` is a record of external dependencies (primitives). `self` is the
recursive-record generator. Access fields by application:
`env "add-i32"`, `self "helper"`. Tie recursion with `fix` on the inner λ.

No layering form and no `θ`.

## Text

Tagged S-expressions. Application is `(apply f x)`, never `(f x)`.

```text
x                             ⇔  x
λx. t                         ⇔  (lambda x t)
t₁ t₂                         ⇔  (apply t1 t2)
{ t₁ = u₁, … }                ⇔  (record t1 = u1 …)
fix t                         ⇔  (fix t)
b                             ⇔  (bits b)
let xᵢ = eᵢ in t              ⇔  (let x1 = e1 … xn = en t)
(fix t) s                     ⇔  (fix t s)
1                             ⇔  true
0                             ⇔  false
```

```text
(apply t1 t2 t3)              error            # apply is exactly binary
f x y                         ⇔  (apply (apply f x) y)
(fix t s)                     ⇔  (apply (fix t) s)
```

A record field is `term = term`. A bare name on either side is a
variable. A bare numeral, string, or hex token is not a term; wrap it in
`(bits …)`.

Reserved heads: `lambda`, `record`, `fix`, `bits`, `let`, `apply`. An
unknown head is an error; do not treat it as application. Empty lists
are invalid.

```text
arity(lambda) = 2
arity(fix) = 1
arity(bits) = 1
arity(apply) = 2
arity(record) = (t = t)*
arity(let) = (x = t)* t

λ-param                       =  atom
keys in one record            pairwise distinct as terms
b only in (bits b)            except true, false
CU                            closed
```

Parse checks the table above. It does not check whether a record
application finds a key or whether `fix` is applied to a λ. The reducer
checks those.

```lisp
(lambda env
  (lambda self
    (record
      (bits "main") = ...
      (bits "helper") = ...)))
```
