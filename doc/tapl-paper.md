---
title: |
  TAPL: A Language Framework \
  Built on the $\xi$-Calculus
author: TAPL Project
date: 2026
abstract: |
  We describe TAPL, a typed programming language framework that compiles to
  Python, built on the $\xi$-calculus presented in the companion paper.
  The $\xi$-calculus defines layering and separation as formal operations on
  terms; TAPL makes these operations concrete. A single `.tapl` source file
  compiles into two Python files---one for evaluation and one for
  type-checking---via the separation operation implemented as a tree
  transformation. We describe the compilation architecture, the concrete syntax
  for working with layers, the type system design, and the language
  extensibility mechanism that allows new languages to be built on top of the
  framework.
documentclass: article
classoption:
  - 11pt
  - letterpaper
geometry: margin=1in
numbersections: true
toc: true
header-includes:
  - \usepackage{amsmath,amssymb,mathtools}
  - \usepackage{xcolor,eso-pic}
  - \AddToShipoutPictureFG{\AtTextCenter{\makebox(0,0){\rotatebox{45}{\scalebox{8}{\textcolor{gray!30}{DRAFT}}}}}}
---

\newpage

# Introduction

The $\xi$-calculus (presented in the companion paper *The $\xi$-Calculus:
Unifying Type Systems through Layered Computation*) extends the untyped lambda
calculus with layering ($t{:}t$) and unlayering ($\xi.t$), providing a unified
mechanism for expressing type system features. It shows that Simply Typed
Lambda Calculus, System F, substructural types, and dependent types are all
configurations of the same system.

TAPL is a practical realization of this calculus. It is a typed programming
language that looks like Python, compiles to Python, and uses the
$\xi$-calculus as its theoretical foundation. The key ideas:

- **Separation is concrete.** The $\xi$-calculus defines separation as a
  formal operation; TAPL implements it as a compiler pass. A single `.tapl`
  source file compiles into two `.py` files---one for evaluation, one for
  type-checking.

- **Types are programs.** The type-checking layer is not a static analysis---it
  is a real Python program that runs before the evaluation layer. Type errors
  are runtime errors in the type-checker file.

- **Dependent types are practical.** Because types are terms in another layer,
  dependent types arise naturally. A matrix type parameterized by its
  dimensions is just a function call that lifts values into the type layer.

- **Languages are extensible.** TAPL is not a single language but a framework
  for building languages. New syntax and type rules are added by extending
  existing grammars, and the separation mechanism ensures consistency across
  layers.

TAPL is named after Benjamin C. Pierce's *Types and Programming Languages*
(MIT Press, 2002), which inspired the project.


# Background: The $\xi$-Calculus

This section provides a brief summary of the $\xi$-calculus. The full
formal treatment---syntax, term classification, evaluation rules, separation
rules, and type system encodings---is given in the companion paper.

The $\xi$-calculus extends the untyped lambda calculus with:

| Syntax | Name | Description |
|---|---|---|
| $x$ | Variable | Standard variable reference |
| $\lambda x.\,t$ | Abstraction | Standard lambda abstraction |
| $t\ t$ | Application | Standard function application |
| $t{:}t$ | Layering | A term existing simultaneously in multiple layers |
| $\xi.\,t$ | Unlayering | Decompose the layers of a term |

Every term is classified as either *single-layer* ($g$) or *multi-layer* ($h$).
The **separation** operation ($\sigma$) transforms multi-layer terms into
layered terms where each component belongs to a single layer. The critical
rules are:

- **Distribution:** $\sigma[\lambda x.\,(t_1{:}t_2)] = (\lambda x.\,t_1){:}(\lambda x.\,t_2)$
  --- a function whose body spans two layers becomes two functions.
- **Cloning:** $\sigma[g\ h] = (g{:}g)\ h$ --- single-layer code is
  duplicated into every layer.
- **Application:** $\sigma[(t_1{:}t_2)\ (t_3{:}t_4)] = (t_1\ t_3){:}(t_2\ t_4)$
  --- each layer's function is applied to that layer's argument.

Type system features are encoded using combinators and the layering operation.
The identity combinator $I = \lambda x.\,x$ and the composition combinator
$B = \lambda f.\,\lambda g.\,\lambda x.\, f\ (g\ x)$ combine with type guard
combinators ($G_a$, $G_b$, $G_D$) to encode STLC, System F, substructural
types, and dependent types respectively---all through the same mechanism.


# Compilation Architecture

## From Source to Layers

For each `.tapl` source file, the TAPL compiler produces two Python files:

1. **The evaluation layer** (e.g., `hello_world.py`): executable runtime code.
2. **The type-checking layer** (e.g., `hello_world1.py`): type constraint code
   that runs first. If it executes without error, the evaluation layer is
   guaranteed to be type-safe.

The compilation pipeline:

$$
\text{Source (.tapl)}
\xrightarrow{\text{Chunker}}
\text{Chunks}
\xrightarrow{\text{Parser}}
\text{Term tree}
\xrightarrow{\text{LayerSeparator}}
\text{Layer trees}
\xrightarrow{\text{Backend}}
\text{Python files}
$$

1. **Chunker:** splits the source into indentation-based chunks.
2. **Language directive:** the first chunk (`language pythonlike`) determines
   which language module to load.
3. **Parser:** grammar rules produce a term tree (potentially multi-layer).
4. **LayerSeparator:** separates the term tree into $N$ single-layer trees.
5. **Backend:** each layer tree is converted to a Python AST and written out.

## The LayerSeparator

The LayerSeparator is the concrete implementation of the $\xi$-calculus
separation operation ($\sigma$). It walks the term tree and calls `separate()`
on each node:

- **Layers nodes** (the concrete representation of $t{:}t$) return their
  components---one term per layer.
- **Single-layer nodes** are cloned into every layer, following the cloning
  rules of the calculus.

```python
def separate(self, ls):
    return ls.build(lambda layer: FunctionDef(
        name=self.name,
        body=layer(self.body),
    ))
```

```python
def separate(self, ls):
    return self.layers  # [layer_0_term, layer_1_term]
```

The separator uses a factory pattern: it runs the factory function once per
layer, and on each pass extracts the corresponding component from each
`Layers` node. The result is $N$ independent term trees, one per layer.


# TAPL-Specific Syntax

TAPL introduces syntactic constructs that directly correspond to operations
in the $\xi$-calculus.

## Literal Lifting: `^`

The `^` operator promotes a value from the evaluation layer into the type
layer. In terms of the calculus, it creates a layered term where the value
participates in both layers.

```
class_name = ^'Matrix({},{})'.format(rows, cols)
```

In normal code (`MODE_SAFE`), `^` switches to `MODE_LIFT`, causing the term to
be evaluated at both layers. This is the mechanism behind dependent types:
writing `Matrix(^2, ^3)` lifts `2` and `3` into the type layer, making
$\mathit{Matrix}(2, 3)$ a distinct type from $\mathit{Matrix}(3, 3)$.

## Double-Layer Expressions: `<expr:Type>`

The `<expr:Type>` syntax explicitly specifies different terms for different
layers, directly representing the layering operation $t{:}t$:

```
self.num_rows = <rows:Int>
```

This means:

- **Evaluation layer (layer 0):** `self.num_rows = rows`
- **Type-checking layer (layer 1):** `self.num_rows = Int`

The parser creates a `Layers` node with `[rows_term, Int_term]`, and the
separator sends each to its respective layer.

This construct is used whenever the type cannot be inferred from the
evaluation-layer code alone:

```
self.values = <[]:List(List(Int))>
```

Evaluation layer: `self.values = []`. Type-checking layer: `self.values` has
type $\mathit{List}(\mathit{List}(\mathit{Int}))$.

## Instance Types: `!`

The `!` sigil distinguishes classes from instances:

- `Dog` refers to the class (the constructor).
- `Dog!` refers to an instance of `Dog`.

This resolves a pervasive ambiguity in Python and ensures that a name refers
to the same kind of entity in both the value layer and the type layer---a
principle called *Intentional Symmetry*.

In the type-level representation, `Dog` is a function type (the constructor)
and `Dog!` is the record type it returns:

$$
\begin{array}{rcl}
\mathit{Dog} &=& \mathit{Function}(\mathit{args}{=}[(\text{name}, \mathit{Str})],\ \mathit{result}{=}\mathit{Dog!}) \\
\mathit{Dog!} &=& \mathit{Record}(\{name: \mathit{Str}\})
\end{array}
$$

## Dynamic Class Names: `class_name`

The `class_name` attribute parameterizes the type-level label of a class.
Combined with `^`, this enables dependent types:

```python
def Matrix(rows, cols):
    class Matrix_:
        class_name = ^'Matrix({},{})'.format(rows, cols)
        ...
    return Matrix_
```

When `Matrix(2, 3)` is called, the type-checker creates a class labeled
$\mathit{Matrix}(2,3)\text{!}$, distinct from $\mathit{Matrix}(3,3)\text{!}$.


# Type System Design

## Type Hierarchy

TAPL's type hierarchy is inspired by Kotlin:

$$
\mathit{Nothing} \ <:\ T \ <:\ \mathit{Any} \ <:\ \mathit{Any} \mid \mathit{NoneType}
$$

- **Nothing**: the bottom type. Subtype of all types. Represents computations
  that never return (e.g., infinite loops, exceptions).
- **Any**: the top type for non-nullable values. Supertype of all types except
  $\mathit{NoneType}$.
- **NoneType**: the type of `None`. Deliberately *not* a subtype of
  $\mathit{Any}$.
- **Any $\mid$ NoneType**: the true top type. Supertype of everything.

By default, types are **non-nullable**. A function returning $\mathit{Int}$
cannot return $\mathit{None}$. To allow it, one must explicitly use
$\mathit{Int} \mid \mathit{None}$.

## Structural Typing

Instance types are implemented as *Records*---structural types with labeled
fields. Subtype checking uses width subtyping:

$$
\{name: \mathit{Str},\ age: \mathit{Int}\} \ <:\ \{name: \mathit{Str}\}
$$

A record is a subtype of another if it has all the required fields with
compatible types. Records carry an optional label (like $\mathit{Dog}\text{!}$)
for readable error messages, but subtype checking is structural, not nominal.

## Function Types

Function types follow standard variance rules: contravariant in parameter
types, covariant in return type.

$$
A <: B \implies (B) \to T \ <:\ (A) \to T
\qquad\qquad
T <: U \implies (A) \to T \ <:\ (A) \to U
$$

## Union and Intersection Types

TAPL reserves `|` and `&` exclusively for type-level operations:

- **Union** ($A \mid B$): a value is either of type $A$ or type $B$.
  A type is a subtype of a union if it is a subtype of any member.
- **Intersection** ($A\ \&\ B$): a value is both of type $A$ and type $B$.
  A type is a subtype of an intersection if it is a subtype of all members.

Since TAPL evaluates terms at the type level using the same operations as the
value level, it cannot distinguish `|` as "bitwise OR" vs. "union." Reserving
`|` and `&` for set-theoretic type operations is the consistent choice.

## Subtype Checking Protocol

Subtype checking uses a bidirectional protocol. Each type implements:

- `is_supertype_of(subtype)`: returns `True`, `False`, or `None` (inconclusive).
- `is_subtype_of(supertype)`: returns `True`, `False`, or `None` (inconclusive).

The checker calls both methods and reconciles the results. Recursive types are
handled through a coinductive assumption stack: when checking $A <: B$, the
pair $(A, B)$ is pushed onto the stack. If the same pair is encountered during
recursion, the check is assumed to hold. Results are cached for performance.


# Language Extensibility

TAPL is designed as a framework for language creation, not as a single fixed
language.

## The Language Interface

Every TAPL language implements the `Language` abstract class with two methods:

- `get_grammar(parent_stack)`: returns the grammar---a mapping from rule
  names to lists of parsing functions.
- `get_predef_headers()`: returns the predefined imports/headers for each
  layer.

Parsing functions take a `Cursor` (a position in the token stream) and return
either a `Term` (success) or `ParseFailed` (backtrack). Rules are tried in
order; the first successful match wins.

## Extending a Grammar

To create a new language, subclass an existing one and modify its grammar. The
`pipeweaver` language demonstrates this by adding a pipe operator (`|>`):

```python
class PipeweaverLanguage(PythonlikeLanguage):
    def get_grammar(self, parent_stack):
        grammar = super().get_grammar(parent_stack).clone()
        grammar.rule_map[TOKEN] = [
            _parse_pipe_token,
            *grammar.rule_map[TOKEN],
        ]
        grammar.rule_map[EXPRESSION] = [
            _parse_pipe_call,
            *grammar.rule_map[EXPRESSION],
        ]
        return grammar
```

New rules are prepended to give them priority over base grammar rules. The
`clone()` call ensures the parent grammar is not mutated.

Using `pipeweaver`, code like:

```
3 |> double |> square |> print
```

is transformed into nested function calls:

```python
print(square(double(3)))
```

## What Extensions Can Do

A language extension can:

- **Add new syntax:** new operators, expression forms, statement types.
- **Add new term types:** custom `Term` subclasses with their own `separate()`
  and code-generation methods.
- **Modify parsing priority:** prepend or append rules to change how ambiguous
  syntax is resolved.
- **Redefine existing rules:** replace entire rule lists to change the grammar.

Because terms carry their own `separate()` method, any new syntax automatically
participates in the layer separation mechanism. You define how your term splits
across layers, and the compiler handles the rest.

## Language Registration

Languages are discovered by module path. When a `.tapl` file starts with
`language pipeweaver`, the compiler loads:

```python
language = importlib.import_module('tapl_language.pipeweaver').get_language()
```

The `tapl_language` namespace package contains language modules, each exporting
a `get_language()` function.


# Design Principles

**Intentional Symmetry.**
A name refers to the same kind of entity in both the value layer and the type
layer. `Dog` is always the class; `Dog!` is always an instance. There is no
context-dependent interpretation.

**Same Techniques at Every Layer.**
Abstraction, application, and substitution work identically at the term level
and the type level. This is a direct consequence of the $\xi$-calculus, where
types are terms.

**Separation Over Erasure.**
Most type systems use *type erasure*: types are checked and discarded before
execution. TAPL uses *separation*: types are split into a separate computation
that runs independently. The type-checker is a real program. This means:

- Type-level computations can be arbitrarily complex (enabling dependent types).
- The type-checker's correctness can be tested like any other program.
- Type errors are runtime errors in the type-checker file, not special compiler
  diagnostics.

**Extensibility as Architecture.**
TAPL is not a fixed language but a framework for building languages. The
`pythonlike` grammar is a reference implementation, not a standard. The
compiler's only fixed requirements are: (1) a `language` directive, (2) a
language module providing a grammar and predefined headers, and (3) terms that
implement `separate()`. Everything else---syntax, type rules, built-in
types---is defined by the language module.


# Conclusion

TAPL demonstrates that the $\xi$-calculus is not merely a theoretical
construct but a practical foundation for language design. The separation
operation, formalized in the companion paper, is implemented as a tree
transformation that decomposes a single source file into independent evaluation
and type-checking layers. The resulting architecture makes dependent types
natural (values are lifted across layers), language extensibility first-class
(new syntax participates in separation automatically), and type-checking
testable (the type-checker is a real program).

The framework invites language designers to define *what each layer computes*
and *how syntax maps to multi-layer terms*. The $\xi$-calculus handles the
rest.

\bigskip
\noindent\textit{TAPL is named after Benjamin C. Pierce's \textbf{Types and
Programming Languages} (MIT Press, 2002), which inspired the project.}
