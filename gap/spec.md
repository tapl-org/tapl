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

μ ::= { a₁ = w₁, …, aₙ = wₙ }    metadata

b ::= [0-9]+                     integer
    | "[^"]*"                    string
    | 0x[0-9A-Fa-f]+             hexadecimal bit pattern
```

Every node is an attributed term `r @ μ`, including variables. Writing `r`
means `r @ {}`. Metadata is part of the term: the same core form with
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
- `if t₁ then t₂ else t₃` requires `t₁` to reduce to a bits term. if bits not equals 0 then true otherwise false.

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

### Computation

Gap computes by reducing terms. The central rule is beta reduction:

```text
(λx. t) s → [x ↦ s]t
```

It replaces the free occurrences of `x` in `t` with `s`.

Records, fixed points, and conditionals have similarly direct reductions:

```text
{ …, l = t, … }.l                              → t
fix t                                          → t (fix t)
if (1 @ { layout = bool }) then t₁ else t₂     → t₁
if (0 @ { layout = bool }) then t₁ else t₂     → t₂
```

These rules omit metadata on structural nodes for readability. When a redex
with root metadata `μ` produces a term whose root has metadata `ν`, the result
root has `ν ⊕ μ`. The merge keeps attributes from both maps and `μ` wins when
both maps contain the same name. Metadata below the root is unchanged. This
preserves the redex's semantic attributes on its contractum.

Reduction is strong: Gap may reduce a term anywhere, including inside an
abstraction. Partial evaluation stops when no more chosen reductions can be
performed. The remaining term is the residual program that will map to SSA.

The exact evaluation strategy, including when to unfold `fix`, is still open
work.

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

A frontend provides a core term as text or binary together with a metadata
sidecar that associates every parsed node with its metadata map. The pair
represents one attributed term. Metadata is semantic, so the core term alone is
not a complete Gap input.

The general sidecar encoding and the node identifiers it uses are still open
work. Text and binary inputs must use the same association model so that they
represent the same abstract language and have the same meaning.

### Text input format

The text format uses S-expressions for the core term. Source files, residual
programs, and dumps all use this format together with their metadata sidecars.

A list is an application unless its head is a colon-prefixed structural form.
Application is therefore the default, while language structure remains
explicitly marked.

Colon-prefixed names belong to the language. Ordinary names are unrestricted,
so names such as `lambda`, `record`, and `if` may still be used as functions.

#### Forms

| Abstract term | Text |
| --- | --- |
| Variable `x` | `x` |
| Abstraction `λx. t` | `(:lambda x t)` |
| Application `f x` | `(f x)` |
| Record `{ first = p, second = q }` | `(:record first = p second = q)` |
| Projection `t.label` | `(:get t label)` |
| Fixed point `fix A` | `(:fix A)` |
| Bits `42` | `(:literal 42)` |
| Conditional `if c then t else e` | `(:if c t e)` |

Multiple arguments are left-associative text sugar, so `(f x y)` represents
`(f x) y`.

The table intentionally shows no metadata syntax. For example, the `layout =
i32` metadata for `(:literal 42)` is supplied by the sidecar.

#### Sugars

| Abstract term | Text |
| --- | --- |
| `let x₁ = e₁ … xₙ = eₙ in body` | `(:let x1 = e1 … xn = en body)` |
| `(fix A).label` | `(:fix A label)` |
| `1 @ { layout = bool }` | `true` |
| `0 @ { layout = bool }` | `false` |

The abstract-language section defines how multiple `let` bindings expand.
The boolean sugars introduce their shown metadata without a sidecar entry.

#### Structural forms and applications

Structural heads are `:lambda`, `:record`, `:get`, `:fix`, `:literal`, `:if`,
and `:let`. An unknown colon-prefixed head is an unknown structural form, not
an application. Every non-colon head is a function being applied, including
`lambda`, `record`, `if`, `=`, `*`, and `-`.

An application must have at least one argument. Empty and single-element lists
are invalid. A list may itself be the function in an application, as in
`((:lambda x x) value)`.

#### Well-formedness

A parsed S-expression is a well-formed term when:

- **Arity.** Each structural head takes exactly its defined number of
  arguments: `:lambda` takes 2, `:get` takes 2, `:fix` takes 1, `:literal`
  takes 1, `:if` takes 3, and `:record` takes any number of `label = term`
  fields.
- **Known heads.** A colon-prefixed head is one of the defined structural
  forms. An unknown colon-prefixed head is an error and is never reinterpreted
  as an application.
- **Applications.** A list whose head is not colon-prefixed has at least two
  elements. The head may itself be a list.
- **Parameters.** A `:lambda` parameter is a bare name.
- **Labels.** Labels within one `:record` are pairwise distinct.
- **Literals.** A bits value is valid only inside `(:literal value)`, except
  for `true` and `false`. A bare numeral, string, or hexadecimal pattern is
  not a term in the text format, even though the abstract language writes the
  value on its own. The combined input must give every `:literal` node
  `layout` metadata; the boolean sugars provide `bool` themselves.
- **Scope.** A complete compilation unit is closed. Every variable occurrence
  in it is bound by an enclosing `:lambda`.

Well-formedness does not check whether a projected field exists, an `:if`
condition is a boolean, or a `:fix` argument is a function. Reduction checks
those conditions. Lowering checks whether a literal value fits the layout in
its metadata.

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

- **Unmarked application** — `(f x)` is the calculus. Wrapping every call in
  `:app` would hide the shape that later becomes SSA.
- **Structural namespace** — the quiet `:` prefix distinguishes language forms
  without reserving ordinary names.
- **`:fix` is a term** — `(:fix A)` is the fixed point; `(:fix A fact)` is the
  usual fixed-field sugar. Unfolding is
  `(:fix A fact) = (:get (A (:fix A)) fact)`.
- **`:literal` wraps a bits value** — the abstract language writes the value
  itself, since a bits term is nothing but a bit pattern described by
  `layout`. Text wraps it in `:literal` so a value is never confused with a
  name and always has a node the sidecar can attach metadata to.
- **One syntax for source and residual** — after partial beta reduction, the
  remaining applications stay written as applications.

#### Compilation unit example

The abstract compilation unit shown earlier has this text representation:

```lisp
(:lambda env
  (:lambda self
    (:record
      main = ...
      helper = ...)))
```

External and recursive dependencies use explicit projections:

```lisp
(:get env add-i32)
(:get self helper)
```

### Binary input format

The binary format will represent the same core terms as the text format and
use the same metadata-association model. Its core encoding and the shared
sidecar encoding will be defined later.

## Open work

- [x] Design terms
- [x] A bits value `b` is a core term form and is one of an integer, a string,
  or a hexadecimal bit pattern. Its layout is explicit term metadata and is
  never inferred from context; examples omit metadata only for simplicity.
  The text format still writes it as `(:literal v)`.
- [x] Move layouts out of core term forms and into semantic metadata attached
  to every term node.
- [x] Define one input as one closed compilation unit of the form
  `λenv. λself. { … }`.
- [x] Separate the abstract language from the text and binary input formats.
- [ ] Define the metadata sidecar encoding and stable node association for text
  and binary inputs.
- [ ] Define source-location and permitted-reduction metadata attributes.
- [ ] Define concrete layout values, literal encoding rules, and the primitive
  set, including the `bool` layout and the contents of `env`.
- [ ] Design evaluation.
- [ ] Design how to introduce memory and remove the memory parameter when
  generating machine code.
- [ ] Figure out how to reduce `fix` when needed during strong reduction.
