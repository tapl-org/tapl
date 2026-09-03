# Gap

A reduction-oriented functional IR that partially evaluates lambda-calculus
terms until the residual program maps one-to-one onto SSA.

Gap sits between a frontend language and a conventional compiler backend:

```text
frontend program
    → Gap terms
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
t ::= x                          variable
    | λp. t                      abstraction
    | t t                        application
    | { l₁ = t₁, …, lₙ = tₙ }    record
    | t.l                        projection
    | fix t                      fixed point
    | literal(v, ℓ)              literal
    | if t then t else t         conditional

p ::= x                          parameter
    | x : ℓ                      layout-annotated parameter
```

Here:

- `t` and `s` stand for terms.
- `x`, `y`, and `z` stand for variables.
- `l` stands for a record label.
- `ℓ` stands for a storage layout such as `i32`, `bool`, or `utf8`.
- `v` stands for a literal value such as `42`, `"hello"`, or `true`.

Labels, layouts, and literal values are data contained in a term. They are not
terms themselves and do not reduce.

### Meaning of each term

- **Variable** — `x` refers to a variable.
- **Abstraction** — `λp. t` binds one parameter in `t`. A layout annotation
  describes storage, not type. For example, `λ(x : i32). t` stores `x` as
  `i32`.
- **Application** — `t₁ t₂` applies one term to another. Application associates
  to the left, so `f x y` means `(f x) y`.
- **Record** — `{ l₁ = t₁, …, lₙ = tₙ }` contains an ordered list of fields with
  unique labels. Field order is preserved for layout. `{}` is the empty record
  and unit value.
- **Projection** — `t.l` selects field `l` from `t`. The label is fixed in the
  term; it cannot be computed at run time. A missing field is a reduction
  error.
- **Fixed point** — `fix t` provides recursion and unfolds to `t (fix t)`.
- **Literal** — `literal(v, ℓ)` stores value `v` using layout `ℓ`. A literal has
  no subterms.
- **Conditional** — `if c then a else b` chooses between `a` and `b`. The
  condition must reduce to a `bool` literal.

Projection labels and literal layouts are static. If a program must choose a
field or layout at run time, it must express that choice explicitly, for
example with a conditional.

### Derived terms

The following convenient forms stand for core terms:

```text
f x y                ≡ (f x) y
let x = e in body    ≡ (λx. body) e
true                 ≡ literal(true, bool)
false                ≡ literal(false, bool)
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
{ …, l = t, … }.l                 → t
fix t                             → t (fix t)
if literal(true, bool) then a else b  → a
if literal(false, bool) then a else b → b
```

Reduction is strong: Gap may reduce a term anywhere, including inside an
abstraction. Partial evaluation stops when no more chosen reductions can be
performed. The remaining term is the residual program that will map to SSA.

The exact evaluation strategy, including when to unfold `fix`, is still open
work.

#### Factorial

For simplicity, this example writes numerals without layouts and writes
primitives such as `=`, `*`, and `-` directly. These are readability
shorthands, not Gap terms.

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
FV(λ(x : ℓ). t)                    = FV(t) \ {x}
FV(t₁ t₂)                          = FV(t₁) ∪ FV(t₂)
FV({ l₁ = t₁, …, lₙ = tₙ })        = FV(t₁) ∪ … ∪ FV(tₙ)
FV(t.l)                            = FV(t)
FV(fix t)                          = FV(t)
FV(literal(v, ℓ))                  = ∅
FV(if t₁ then t₂ else t₃)          = FV(t₁) ∪ FV(t₂) ∪ FV(t₃)
```

A term is *closed* when `FV(t) = ∅`. Every complete compilation unit must be
closed.

#### Binding and alpha-equivalence

An abstraction is the only core term that binds a variable. A `let` binds
through the abstraction into which it expands.

Two terms are alpha-equivalent if they differ only in bound variable names.
For example, `λ(x : i32). x` and `λ(y : i32). y` are alpha-equivalent.
Changing `i32` to `f32` is not renaming, so those terms are not
alpha-equivalent.

#### Substitution

`[x ↦ s]t` replaces each free occurrence of `x` in `t` with `s`.

```text
[x ↦ s] x                              = s
[x ↦ s] y                              = y                         (y ≠ x)
[x ↦ s] (λx. t)                        = λx. t
[x ↦ s] (λy. t)                        = λy. [x ↦ s]t              (y ≠ x, y ∉ FV(s))
[x ↦ s] (λ(x : ℓ). t)                  = λ(x : ℓ). t
[x ↦ s] (λ(y : ℓ). t)                  = λ(y : ℓ). [x ↦ s]t        (y ≠ x, y ∉ FV(s))
[x ↦ s] (t₁ t₂)                        = ([x ↦ s]t₁) ([x ↦ s]t₂)
[x ↦ s] { l₁ = t₁, …, lₙ = tₙ }        = { l₁ = [x ↦ s]t₁, …, lₙ = [x ↦ s]tₙ }
[x ↦ s] (t.l)                          = ([x ↦ s]t).l
[x ↦ s] (fix t)                        = fix ([x ↦ s]t)
[x ↦ s] literal(v, ℓ)                  = literal(v, ℓ)
[x ↦ s] (if t₁ then t₂ else t₃)        = if [x ↦ s]t₁ then [x ↦ s]t₂ else [x ↦ s]t₃
```

The condition `y ∉ FV(s)` prevents variable capture. If it does not hold,
rename `y` to a fresh name before substituting.

### Type and layout

A type and a layout are independent concepts. The same type may have different
layouts; for example, `Mile` may use either an `i32` or an `i64` layout.
Conversely, the same layout may be used by different types; for example, both
`Mile` and `Meter` may use an `i32` layout while remaining distinct semantic
types. We use layout term to denote how underline bit layout and encondings.

### Literals and lowering

A literal pairs a value with its storage layout:

```text
literal(42, i32)
literal(1.0, f32)
literal("hello", utf8)
literal(0x00112233, MyStructLayout)
```

Lowering converts the value into the concrete representation required by its
layout. For example, `1.0` with the `f32` layout becomes its 32-bit IEEE 754
representation. A hexadecimal value already provides the bits directly, but
its size and structure must still match the given layout.

Each layout must define its encoding rules, including integer width,
floating-point format, string encoding, byte order, and struct padding. This
makes lowering deterministic and formally verifiable. Hexadecimal data is
therefore one kind of literal, not a separate term.

A bare literal value such as `1` is not a term. Gap never infers a literal's
layout from its surrounding context; the layout must always be explicit.
Note: Gap never infers anything at all.

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

Frontend compilers can provide a Gap term as text or binary. Both formats
represent the same abstract language and have the same meaning.

### Text input format

The text format uses S-expressions. Source files, residual programs, and dumps
all use this format.

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
| Layout-annotated abstraction `λ(x : i32). t` | `(:lambda (x i32) t)` |
| Application `f x` | `(f x)` |
| Record `{ first = a, second = b }` | `(:record first = a second = b)` |
| Projection `t.label` | `(:get t label)` |
| Fixed point `fix A` | `(:fix A)` |
| Literal `literal(42, i32)` | `(:literal 42 i32)` |
| Conditional `if c then a else b` | `(:if c a b)` |

Multiple arguments are left-associative text sugar, so `(f x y)` represents
`(f x) y`.

#### Sugars

| Abstract term | Text |
| --- | --- |
| `let x₁ = e₁ … xₙ = eₙ in body` | `(:let x1 = e1 … xn = en body)` |
| `(fix A).label` | `(:fix A label)` |
| `literal(true, bool)` | `true` |
| `literal(false, bool)` | `false` |

The abstract-language section defines how multiple `let` bindings expand.

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
  takes 2, `:if` takes 3, and `:record` takes any number of `label = term`
  fields.
- **Known heads.** A colon-prefixed head is one of the defined structural
  forms. An unknown colon-prefixed head is an error and is never reinterpreted
  as an application.
- **Applications.** A list whose head is not colon-prefixed has at least two
  elements. The head may itself be a list.
- **Parameters.** A `:lambda` parameter is a bare name or a two-element
  `(name layout)`.
- **Labels.** Labels within one `:record` are pairwise distinct.
- **Literals.** A literal value is valid only inside
  `(:literal value layout)`, except for `true` and `false`. A bare numeral or
  other bare literal value is not a term.
- **Scope.** A complete compilation unit is closed. Every variable occurrence
  in it is bound by an enclosing `:lambda`.

Well-formedness does not check whether a projected field exists, an `:if`
condition is a boolean, or a `:fix` argument is a function. Reduction checks
those conditions. Lowering checks whether a literal value fits its layout.

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

The binary format will represent the same abstract terms as the text format.
Its encoding will be defined later.

## Open work

- [x] Design terms
- [x] Bare numerals are not terms. Literal layouts are always explicit and are
  never inferred from context; examples use bare numerals only for simplicity.
- [x] Define one input as one closed compilation unit of the form
  `λenv. λself. { … }`.
- [x] Separate the abstract language from the text and binary input formats.
- [ ] Define literal encoding rules and the primitive set, including the
  `bool` layout and the contents of `env`.
- [ ] Design evaluation.
- [ ] Implement storage size types on lambdas (`i32`, `f64`, `index`, and
  others).
- [ ] Design how to introduce memory and remove the memory parameter when
  generating machine code.
- [ ] Figure out how to reduce `fix` when needed during strong reduction.
- [ ] Add abstraction return-layout syntax.
