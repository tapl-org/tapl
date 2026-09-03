# Gap

A reduction-oriented functional IR that partially evaluates lambda-calculus
terms until the residual program maps one-to-one onto SSA.

Gap sits between a frontend language and a conventional compiler backend:

```text
frontend program
    → Gap terms (same untyped lambda calculus)
    → reduction and partial evaluation
    → residual term
    → SSA
    → machine code
```

The name *Gap* refers to the gap between functional programming and imperative
execution.

## A brief philosophical background

A compiler translates a program into machine code. But what exactly does it
compile? A programming language and machine code are different kinds of
things. Treating them as the same risks a category error.

My current view is that compilation makes abstractions concrete. It chooses or
infers data layouts and an execution order for operations. Engineers often
describe computations in a functional style. They also add imperative details
that constrain the execution order.

A functional program forms a graph of dependencies. The compiler turns that
graph into a valid topological order of operations. Executing those operations
must preserve the semantics of the original program.

Lambda-calculus programs and SSA programs can both be represented as graphs.
Gap transforms the graph of a lambda-calculus program until its remaining
nodes and edges map one-to-one to SSA. This bridges functional code and
imperative execution while preserving the program's semantics.

## Goals

- Formally verifiable
- Compilable to machine code from the residual term's structure
- Strong beta reduction (full support)
- No implicit or automatic decisions; everything should be explicit
- Intended mainly for frontend compilers to generate, rather than for humans
  to write

## Compilation pipeline

1. A frontend creates a Gap term.
2. Gap partially evaluates it with reductions (`β`, `η`, and others).
3. Gap translates the residual term to SSA, driven by the term's structure.
4. A backend lowers SSA to machine code. Possible backends include:
   - MLIR
   - Cranelift
   - QBE
   - C
   - an in-house stack-based pure interpreter, `gapvm`

## Abstract language

A Gap program is an abstract term. The notation in this section explains the
language itself; it is not the syntax of a Gap input file.

### Terms

```text
t ::= r @ μ                      attributed term

r ::= x                          variable
    | λx. t                      abstraction
    | t t                        application
    | { l₁ = t₁, …, lₙ = tₙ }    record
    | t.l                        projection
    | fix t                      fixed point
    | b                          bits
    | if t then t else t         conditional

v ::= x                          variable
    | λx. t                      abstraction
    | { l₁ = v₁, …, lₙ = vₙ }    record
    | b                          bits

n ::= x                          variable
    | n t                        application
    | n.l                        projection
    | fix n                      fixed point
    | if n then t else t         conditional

μ ::= { a₁ = w₁, …, aₙ = wₙ }    metadata

b ::= [0-9]+                     integer
    | "[^"]*"                    string
    | 0x[0-9A-Fa-f]+             hexadecimal bit pattern
```

- `t` is an attributed term
- `r` is a core form
- `v` is a value
- `n` is a neutral

Every node is an attributed term `r @ μ`, including variables. Writing `r`
means `r @ {}`. Metadata is part of the term. The same core form with
different metadata is a different term.

`layout` is the first defined attribute. It is the concrete representation of
the produced value, supplied by the frontend rather than encoded as a core
form:

```text
42 @ { layout = i32 }
```

Later attributes may record source locations or restrict which reductions are
allowed.

Labels, attribute names, and attribute values are data in a term. They are not
terms and do not reduce. A bits value is a core term form.

- Application associates to the left: `f x y` means `(f x) y`.
- Record fields have unique labels. Field order is semantic and is preserved
  through lowering. `{}` is the empty record and the unit value.
- Projection `t.l` selects a label fixed in the term. A missing field is a
  reduction error.
- `fix (λx. t)` unfolds to `[x ↦ fix (λx. t)] t`.
- A bits term has no subterms. Its representation comes from `layout`
  metadata.
- `if t₁ then t₂ else t₃` requires `t₁` to reduce to a bits term. A nonzero
  bits value is true; a zero bits value is false.

Values are:

- variables
- abstractions
- bits terms
- records whose fields are all values

Values are not normal forms. `λx. t` is a value even when `t` still has
redexes.

Application, projection, `fix`, and `if` are elimination forms. They compute
from a value in subject position.

A *neutral* term is an elimination whose subject is a variable or another
neutral:

- `n t`
- `n.l`
- `fix n`
- `if n then t else t`

A variable is both a value and a neutral. Neutrals are residual names and
leftover eliminators, not errors. For example:

- `{ a = x }` is a record value, so `{ a = x }.a → x` even under a binder
- `x.l` stays neutral; it is not stuck

Labels and metadata are static. A run-time choice of field or layout must be
written explicitly, for example with a conditional.

### Derived terms

The following convenient forms stand for core terms:

```text
f x y                ≡ (f x) y
let x = e in body    ≡ (λx. body) e
true                 ≡ 1 @ { layout = bool }
false                ≡ 0 @ { layout = bool }
```

Multiple `let` bindings are sequential:

```text
let x₁ = e₁
let x₂ = e₂
let x₃ = e₃
in body

≡

(λx₁. (λx₂. (λx₃. body) e₃) e₂) e₁
```

Each expression may refer to variables introduced before it. For example,
`e₂` may refer to `x₁`, and `e₃` may refer to both `x₁` and `x₂`.

### Evaluation

Gap computes by reducing terms. The small-step relation `t → t'` is the
computation rules plus the congruence rules below.

Reduction is strong: a redex may be contracted anywhere, including under an
abstraction. The relation is not a strategy. If several redexes exist, any
one of them may step.

Partial evaluation chooses which legal steps to take. It stops when no more
chosen reductions remain. The remaining term is the residual program that
maps to SSA.

The rules are stated on core forms. Every node still carries metadata. The
merge convention after the rules says how attribution is preserved.

Beta reduction substitutes `t₂` for the free occurrences of `x` in `t₁₂`.
The argument need not be a value:

```text
(λx. t₁₂) t₂  →  [x ↦ t₂] t₁₂                  (E-AppAbs)
```

Projection, fixed-point unfolding, and conditionals:

```text
{ …, l = v, … }.l  →  v                        (E-Proj)

fix (λx. t)  →  [x ↦ fix (λx. t)] t            (E-Fix)

if b then t₂ else t₃  →  t₂                    (E-IfTrue)
                                               (b nonzero)

if b then t₂ else t₃  →  t₃                    (E-IfFalse)
                                               (b zero)
```

`E-Proj` waits for a record value: every field must already be a value.
`E-Rcd` reduces fields until they are.

A bits value is *zero* when it denotes the integer 0: decimal `0`, `00`, …,
or hexadecimal `0x0`, `0x00`, …. Any other bits value, including every
string, is *nonzero*. The condition of `if` must already be a bits term.
`true` and `false` are the usual cases.

`E-Fix` may fire whenever its argument is an abstraction. An unrestricted
strategy therefore diverges under strong reduction. Partial evaluation
unfolds `fix` only when an elimination needs it, typically `(fix t).l` or
`(fix t) s`. The exact policy is still open work. One candidate is to
evaluate outer terms before inner terms, which may prevent diverging
unfoldings.

A closed term is *stuck* when it is not a value, not neutral, and no rule
applies. Examples:

- projecting a missing field, or projecting from a non-record constructor
- `if` whose condition is a λ or a record
- a bits term or record in function position

A *neutral* term is *residual*, not stuck. No computation rule applies at
the root, but reduction may continue in other subterms.

Congruence allows a step inside any subterm:

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
────────────────────────────                   (E-Rcd)
{ …, l = t, … } → { …, l = t', … }


      t → t'
────────────────                               (E-Proj1)
     t.l → t'.l


      t → t'
────────────────                               (E-Fix1)
   fix t → fix t'


     t₁ → t₁'
──────────────────────────────────────────     (E-If)
if t₁ then t₂ else t₃ → if t₁' then t₂ else t₃


     t₂ → t₂'
──────────────────────────────────────────     (E-If2)
if t₁ then t₂ else t₃ → if t₁ then t₂' else t₃


     t₃ → t₃'
──────────────────────────────────────────     (E-If3)
if t₁ then t₂ else t₃ → if t₁ then t₂ else t₃'
```

These rules omit metadata on structural nodes for readability.

When a computation rule fires at a redex with root metadata `μ` and produces
a term whose root has metadata `ν`, the result root is `ν ⊕ μ`:

- the merge keeps attributes from both maps
- if both maps contain the same name, `μ` wins
- metadata below the root is unchanged

Congruence preserves the parent node's metadata. Only the reduced child
changes. This keeps the redex's semantic attributes on its contractum.

A simple beta step with empty metadata:

```text
(λx. x) 42
→ 42
```

The same step with metadata shows the merge:

- the application is the redex (`μ = { src = app }`)
- the contractum is the bits node (`ν = { layout = i32 }`)
- the result root is `ν ⊕ μ`

```text
((λx. x) (42 @ { layout = i32 })) @ { src = app }
→ 42 @ { layout = i32, src = app }
```

In the text format that is:

```lisp
(meta
  (apply (lambda x x) (meta (bits 42) (layout i32)))
  (src app))
→ (meta (bits 42) (layout i32) (src app))
```

Projection, `if`, and `fix` merge the same way. The chosen field, chosen
branch, or substituted body keeps its root metadata `ν`. The redex root `μ`
is merged onto it.

#### Factorial

For simplicity, this example writes numerals without their layout metadata and
writes primitives such as `=`, `*`, and `-` directly. The numerals are bits
terms with metadata omitted; the primitives are readability shorthands, not
Gap terms.

```text
let F =
  λself.
    {
      fact = λn.
        if n = 1
        then 1
        else n * (self.fact (n - 1))
    }
in
  (fix F).fact 2
```

Reduction:

```text
(fix F).fact 2
→ (λn. if n = 1 then 1 else n * ((fix F).fact (n - 1))) 2
→ 2 * ((fix F).fact 1)
→ 2 * 1
→ 2
```

#### Mutual recursion

```text
let P =
  λself.
    {
      even = λn. if n = 0 then true  else self.odd  (n - 1),
      odd  = λn. if n = 0 then false else self.even (n - 1)
    }
in
  (fix P).even 2
```

Reduction:

```text
(fix P).even 2
→ (fix P).odd 1
→ (fix P).even 0
→ true
```

### Names and binding

#### Free variables

`FV(t)` is the set of variables used in `t` but not bound by a surrounding
abstraction.

```text
FV(x)                              = {x}
FV(λx. t)                          = FV(t) \ {x}
FV(t₁ t₂)                          = FV(t₁) ∪ FV(t₂)
FV({ l₁ = t₁, …, lₙ = tₙ })        = FV(t₁) ∪ … ∪ FV(tₙ)
FV(t.l)                            = FV(t)
FV(fix t)                          = FV(t)
FV(b)                              = ∅
FV(if t₁ then t₂ else t₃)          = FV(t₁) ∪ FV(t₂) ∪ FV(t₃)
```

Metadata does not contain terms, so it contributes no free variables.

A term is *closed* when `FV(t) = ∅`. Every complete compilation unit must be
closed.

#### Binding and alpha-equivalence

An abstraction is the only core term that binds a variable. A `let` binds
through the abstraction into which it expands.

Two terms are alpha-equivalent if they differ only in bound variable names.
For example, `λx. x` and `λy. y` are alpha-equivalent. Alpha-renaming does not
change metadata. Terms that differ in metadata are not alpha-equivalent.

#### Substitution

`[x ↦ s]t` replaces each free occurrence of `x` in `t` with `s`.

```text
[x ↦ s] x                              = s
[x ↦ s] y                              = y                         (y ≠ x)
[x ↦ s] (λx. t)                        = λx. t
[x ↦ s] (λy. t)                        = λy. [x ↦ s]t              (y ≠ x, y ∉ FV(s))
[x ↦ s] (t₁ t₂)                        = ([x ↦ s]t₁) ([x ↦ s]t₂)
[x ↦ s] { l₁ = t₁, …, lₙ = tₙ }        = { l₁ = [x ↦ s]t₁, …, lₙ = [x ↦ s]tₙ }
[x ↦ s] (t.l)                          = ([x ↦ s]t).l
[x ↦ s] (fix t)                        = fix ([x ↦ s]t)
[x ↦ s] b                              = b
[x ↦ s] (if t₁ then t₂ else t₃)        = if [x ↦ s]t₁ then [x ↦ s]t₂ else [x ↦ s]t₃
```

The equations omit metadata for readability. Substitution preserves the
metadata of every retained or rebuilt node. When an occurrence of `x` with
metadata `μ` is replaced by `s` whose root metadata is `ν`, the replacement
root receives `ν ⊕ μ`, using the same right-precedence merge as reduction.

The condition `y ∉ FV(s)` prevents variable capture. If it does not hold,
rename `y` to a fresh name before substituting.

### Type and layout metadata

A type and a layout are independent concepts. The same type may have different
layouts; for example, `Mile` may use either an `i32` or an `i64` layout.
Conversely, the same layout may be used by different types; for example, both
`Mile` and `Meter` may use an `i32` layout while remaining distinct semantic
types. Layout metadata describes concrete bit representation and encoding; it
does not assign a type to a term.

### Bits and lowering

A bits term is written as the value itself. Its frontend-provided metadata
specifies the storage layout used by lowering:

```text
42         @ { layout = i32 }
"hello"    @ { layout = utf8 }
0x3f800000 @ { layout = f32 }
0x00112233 @ { layout = MyStructLayout }
```

Lowering converts the value into the concrete representation required by its
layout. For example, `42` with the `i32` layout becomes a 32-bit two's
complement word. A hexadecimal value already provides the bits directly, but
its size and structure must still match the given layout.

The three value kinds are integers, strings, and hexadecimal bit patterns.
There is no decimal floating-point value: a float is written as the
hexadecimal pattern of its encoding, as `0x3f800000 @ { layout = f32 }` writes
`1.0`.

Each layout must define its encoding rules, including integer width,
floating-point format, string encoding, byte order, and struct padding. This
makes lowering deterministic and formally verifiable. Hexadecimal data is
therefore one kind of bits value, not a separate term.

Every bits term must have explicit `layout` metadata supplied by the frontend.
Gap never infers it from surrounding context. More generally, Gap never infers
metadata.

### Compilation units

Each Gap input contains exactly one compilation unit. A compilation unit is
one outer abstraction whose parameter is the compilation-unit environment and
whose body returns a recursive-record generator:

```text
λenv.
  λself.
    {
      main = …,
      helper = …
    }
```

The `env` parameter is a record containing the compilation unit's external
dependencies, including primitives. Fields access those dependencies
explicitly with projections such as `env.add-i32`.

The inner abstraction is the recursive-record generator. Its `self` parameter
is in scope in every field, so fields can refer to one another with projections
such as `self.helper`. Applying `fix` to this inner abstraction ties the
recursion and produces the exported record. The exact contents of `env` and
any dedicated recursive-record syntax are defined separately.

A complete compilation unit is closed: all external dependencies enter through
`env`, and no free variables remain.

### Layering stays outside Gap

The `θ`-calculus in this repository extends the lambda calculus with layering
(`t₁:t₂`) and unlayering (`θ.t`), which let a term exist in several
computational layers at once—evaluation and type checking, for example. Gap
does not adopt them. Layering belongs to the frontend and to the type layer; by
the time a program reaches Gap it has been separated, and a Gap term inhabits a
single layer. Gap therefore has no layering form and no `θ`-reduction.

## Input formats

A frontend provides one attributed term as text or binary. The text format
writes attribution in the term with `meta`. The binary format will store the
same `μ` on each node; its encoding is still open work. Text and binary
represent the same abstract language and have the same meaning.

### Text input format

The text format uses S-expressions. Source files, residual programs, and dumps
all use this format. A text file is a complete attributed term; there is no
metadata sidecar.

Every list is a tagged form. The head must be a known name. Application is
written `(apply f x)`, not `(f x)`. Ordinary names remain usable as variables
and as functions; calling a function named `lambda` is `(apply lambda x)`.

#### Forms

| Abstract term | Text |
| --- | --- |
| Variable `x` | `x` |
| Abstraction `λx. t` | `(lambda x t)` |
| Application `f x` | `(apply f x)` |
| Record `{ first = p, second = q }` | `(record first = p second = q)` |
| Projection `t.label` | `(get t label)` |
| Fixed point `fix A` | `(fix A)` |
| Bits `42` | `(bits 42)` |
| Conditional `if c then t else e` | `(if c t e)` |
| `r @ { a₁ = w₁, … }` | `(meta r (a1 w1) …)` |

`apply` is exactly binary. The abstract left-associative sugar `f x y ≡
(f x) y` has no compact text spelling; that term is `(apply (apply f x) y)`.
`(apply f x y)` is an arity error.

Bare `r` means `r @ {}`. Printers omit empty `meta`. `(meta r)` with no
attribute pairs is allowed and equals `r`. Non-empty metadata is written on
the term:

```lisp
(meta (bits 42) (layout i32))
```

#### Sugars

| Abstract term | Text |
| --- | --- |
| `let x₁ = e₁ … xₙ = eₙ in body` | `(let x1 = e1 … xn = en body)` |
| `(fix A).label` | `(fix A label)` |
| `1 @ { layout = bool }` | `true` |
| `0 @ { layout = bool }` | `false` |

The abstract-language section defines how multiple `let` bindings expand.
The boolean sugars expand to `(meta (bits 1) (layout bool))` and
`(meta (bits 0) (layout bool))`.

#### Structural forms and applications

The reserved heads are `lambda`, `record`, `get`, `fix`, `bits`, `if`, `let`,
`apply`, and `meta`. An unknown head is an error and is never reinterpreted as
an application.

`apply` takes exactly two arguments: the function and the argument. Either
may be any term, including a list, as in `(apply (lambda x x) value)`.

Empty lists and lists whose head is not a reserved name are invalid.

#### Metadata

`meta` is the text spelling of `r @ μ`. It is not a new core constructor.
The first argument is the core form `r`. Each following argument is a
two-element list `(name value)`. Those pairs are data, not terms: `(layout
i32)` is legal only in the tail of `meta`. In term position it is an unknown
head.

- `name` is an atom. Names in one `meta` are pairwise distinct.
- `value` is any S-expression. The reader stores it as opaque data and does
  not interpret it.
- The inner `r` must not itself be `meta`. `(meta (meta r (k v)) …)` is an
  error, not an implicit merge. Children of `r` may be `meta` forms.

The shape of each value depends on its key. Parse does not check that shape.
A later verification pass looks up each key and checks the collected
S-expression against that key's schema. Unknown keys and ill-shaped values
fail then, not in the reader. Values do not reduce, even when they look like
terms.

Records and `let` still use `label = term`. Metadata uses `(name value)`.
Field bindings are terms; attribute values are not.

#### Well-formedness

A parsed S-expression is a well-formed term when:

- **Known heads.** The head of every list that is a term is one of the
  reserved heads. An unknown head is an error.
- **Arity.** `lambda` takes 2, `get` takes 2, `fix` takes 1, `bits` takes 1,
  `if` takes 3, and `apply` takes 2. `record` takes any number of
  `label = term` fields. `let` takes any number of `name = term` bindings
  followed by a body. `meta` takes a non-`meta` form plus zero or more
  `(name value)` lists.
- **Parameters.** A `lambda` parameter is a bare name.
- **Labels.** Labels within one `record` are pairwise distinct. Attribute
  names within one `meta` are pairwise distinct.
- **Bits.** A bits value is valid only inside `(bits value)`, except for
  `true` and `false`. A bare numeral, string, or hexadecimal pattern is not
  a term in the text format, even though the abstract language writes the
  value on its own.
- **Scope.** A complete compilation unit is closed. Every variable occurrence
  in it is bound by an enclosing `lambda`.

Well-formedness is a parse check. It does not check whether a projected field
exists, an `if` condition is a boolean, a `fix` argument is a function, a
`bits` node has `layout` metadata, or a metadata value matches its key's
schema. Verification checks metadata keys and value shapes, including that
every `bits` node has a well-formed `layout` (the boolean sugars provide
`bool` themselves). Reduction checks the remaining dynamic conditions.
Lowering checks whether a bits value fits the layout in its metadata.

#### Print options

The same term can be printed in different views:

| Option | Off (source default) | On |
| --- | --- | --- |
| `show-bruijn` | `n` | `n#0` (name and index) |

With `show-bruijn` enabled, the index is the number of enclosing lambdas
between the variable and its binder. A free variable has no index.

The de Bruijn index is only a print and IR view of a named term. It is not a
second language.

TODO: add an option to print without sugars.

#### Why this encoding

- **Tagged forms** — every list starts with a reserved head. Application is
  `apply` because it is a core form, not the default list.
- **Binary `apply`** — `(apply f x)` is one list per application node, the
  same tree that later maps one-to-one onto SSA. Left-associative `f x y`
  remains only in the abstract language.
- **`fix` is a term** — `(fix A)` is the fixed point; `(fix A fact)` is the
  usual fixed-field sugar. Unfolding is
  `(fix A fact) = (get (apply A (fix A)) fact)`.
- **`bits` wraps a bits value** — the abstract language writes the value
  itself, since a bits term is nothing but a bit pattern described by
  `layout`. Text wraps it in `bits` so a value is never confused with a name
  and always has a node `meta` can attach metadata to.
- **`meta` writes `r @ μ`** — `(meta r (k v) …)` is attribution, not a new
  core form. A text file is complete without a sidecar. Attribute values are
  opaque S-expressions until verification.
- **One syntax for source and residual** — after partial beta reduction, the
  remaining applications stay written as `apply`.

#### Compilation unit example

The abstract compilation unit shown earlier has this text representation:

```lisp
(lambda env
  (lambda self
    (record
      main = ...
      helper = ...)))
```

External and recursive dependencies use explicit projections:

```lisp
(get env add-i32)
(get self helper)
```

A bits term with layout metadata:

```lisp
(meta (bits 42) (layout i32))
```

### Binary input format

The binary format will represent the same attributed terms as the text
format, storing each node's metadata with the node. Its core encoding is
defined later.

## Open work

- [x] Design terms
- [x] A bits value `b` is a core term form and is one of an integer, a string,
  or a hexadecimal bit pattern. Its layout is explicit term metadata and is
  never inferred from context; examples omit metadata only for simplicity.
  The text format writes it as `(bits v)`.
- [x] Move layouts out of core term forms and into semantic metadata attached
  to every term node.
- [x] Define one input as one closed compilation unit of the form
  `λenv. λself. { … }`.
- [x] Separate the abstract language from the text and binary input formats.
- [x] Text writes attribution as `(meta r (k v) …)`. A text file needs no
  sidecar. Attribute values are opaque S-expressions at parse time; per-key
  structure is checked at verification.
- [ ] Define the binary encoding of core terms and per-node metadata.
- [ ] Define source-location and permitted-reduction metadata attributes, and
  the verification schemas for each metadata key, including `layout`.
- [ ] Define concrete layout values, bits encoding rules, and the primitive
  set, including the `bool` layout and the contents of `env`.
- [x] Define the small-step evaluation relation (computation and congruence).
- [ ] Choose the partial-evaluation strategy, including when to unfold `fix`
  under strong reduction.
- [ ] Design how to introduce memory and remove the memory parameter when
  generating machine code.
- [ ] Support partial records for the recursive-record generator, so `env`
  can supply some primitives without requiring all of them.
