# TAPL Concepts: A Guide for Language Designers

This document explains the foundational ideas behind TAPL for an audience of programming language creators -- people who design type systems, write compilers, and think about language semantics. It covers the theoretical framework, the compilation architecture, and the design decisions that make TAPL different from conventional approaches.

## Philosophy: Types and Terms Are the Same Thing

The fundamental insight is that types and terms are the same thing, just operating in different layers.

Most language ecosystems treat the type system as a fundamentally different mechanism bolted onto the term language. TypeScript adds types to JavaScript. Mypy adds types to Python. Rust's type system is a separate phase from evaluation. Each requires its own distinct formalism, its own rules, its own machinery.

TAPL rejects that dichotomy. The $\xi$-calculus (as described in `doc/ground-rules.md`) extends lambda calculus with just two operations -- **layering** ($t{:}t$) and **unlayering** ($\xi.t$) -- and then shows that type checking, polymorphism, substructural types, and dependent types all emerge naturally from the same computational substrate. The $t{:}t$ layering operation literally says "this term exists simultaneously at multiple levels," and the **separation** operation decomposes a multi-layer program into its individual layers (one executable, one type-checker). That's why TAPL compiles a single `.tapl` file into two `.py` files -- it's the separation operation made concrete.

This has several profound consequences:

- **Unified type system hierarchy:** Simply Typed Lambda Calculus, System F, substructural types, and dependent types are all encoded using the same mechanism (layering + combinators like $B$, $I$, $G_a$, $G_b$, $G_D$). They aren't different type systems -- they're different configurations of the same system.

- **Dependent types become natural, not exotic:** The matrix example isn't just a demo. It shows that when types are just terms in another layer, dependent types -- where types depend on values -- are not a special feature requiring a proof assistant. They're just terms that happen to reference values. `Matrix(^2, ^3)` lifts values into the type layer because there's nothing special about the type layer. It's just another layer of computation.

- **Language extensibility is a first-class concern:** Because the framework treats grammar rules and type-checking rules as part of the same extensible system, creating a new language (like `pipeweaver`) with the `|>` operator isn't just "adding syntax" -- it's extending both the term layer and the type layer simultaneously, and the framework ensures they stay consistent.

- **The compiler frontend is the interesting part:** By targeting Python AST as a backend IR, TAPL sidesteps the backend problem entirely and focuses on what's actually novel -- the frontend architecture where parsing, type-checking, and code generation all follow from the layered calculus.

In short: TAPL's value is that it provides a **theoretically grounded, practically extensible framework** where the full spectrum of type system features -- from simple types to dependent types -- arise from a single, elegant mechanism rather than being bolted on piecemeal. It makes the ideas from Pierce's book not just theory, but a usable compiler framework.

## The TAPL Calculus (Xi-Calculus)

TAPL is grounded in the **xi-calculus** ($\xi$-calculus), an extension of the untyped lambda calculus with two additional operations:

| Syntax | Name | Description |
|---|---|---|
| $x$ | Variable | Standard variable reference |
| $\lambda x.t$ | Abstraction | Standard lambda abstraction |
| $t\ t$ | Application | Standard function application |
| $t{:}t$ | Layering | A term that exists simultaneously in multiple layers |
| $\xi.t$ | Unlayering | Extract and process the layers of a term |

### Single-Layer vs Multi-Layer Terms

The calculus distinguishes two kinds of terms:

- **Single-layer terms** ($g$): Variables, abstractions over single-layer bodies, applications of single-layer terms, and unlayering. These are conventional lambda calculus terms -- they live in one layer.

- **Multi-layer terms** ($h$): Terms that involve layering ($t{:}t$), or abstractions/applications where at least one component is multi-layer. These are terms that span multiple layers and must be separated before they can be fully evaluated.

This distinction is the engine of the entire system. A multi-layer term is a compact representation of code that *means different things at different layers*. The separation operation decomposes it.

### Separation: The Key Operation

Separation ($\sigma$) is the operation that transforms a multi-layer term into a layered term ($t_1{:}t_2$) where each component belongs to a single layer. The rules are:

**Abstraction distributes over layers:**
$$\sigma[\lambda x. (t_1{:}t_2)] = (\lambda x. t_1){:}(\lambda x. t_2)$$

A function whose body spans two layers becomes two functions, one per layer.

**Application distributes over layers:**
$$\sigma[(t_1{:}t_2)\ (t_3{:}t_4)] = (t_1\ t_3){:}(t_2\ t_4)$$

Applying a layered function to a layered argument produces a layered result, where each layer's function is applied to that layer's argument.

**Cloning -- when only one side is multi-layer:**
$$\sigma[g\ h] = (g{:}g)\ h$$
$$\sigma[h\ g] = h\ (g{:}g)$$

When a single-layer term interacts with a multi-layer term, the single-layer term is **cloned** into both layers. This is how ordinary code (like a function body) appears in both the evaluation layer and the type-checking layer.

These rules have a profound consequence: the same source code can participate in multiple layers simultaneously, and separation ensures each layer gets the right projection of that code.

### Why This Matters for Language Design

The separation rules give you a formal mechanism for deriving a type-checker from a program. You don't write the type-checker by hand. You write a multi-layer program, and the compiler separates it into:

1. An **evaluation layer** -- the executable code.
2. A **type-checking layer** -- the type constraints.

This means that extending the type system is the same operation as extending the term language. Add a new syntactic form, define how it separates, and you get both runtime semantics and type-checking for free.

## Compilation Architecture

### From Source to Layers

TAPL's compilation pipeline makes the calculus concrete. For each `.tapl` source file, the compiler produces **two Python files**:

1. **The untyped code file** (e.g., `hello_world.py`): Contains the executable logic.
2. **The type-checker file** (e.g., `hello_world1.py`): Contains the type-checking logic.

To ensure type safety, the type-checker file runs first. If it executes without error, the untyped code is guaranteed to be type-safe.

### Pipeline Steps

```
Source (.tapl)
    |
    v
[Chunker] -- Splits source into indentation-based chunks
    |
    v
[Language Directive] -- First chunk: "language pythonlike"
    |
    v
[Language Module] -- Loaded dynamically: tapl_language.{name}
    |
    v
[Parser] -- Grammar rules produce a term tree (multi-layer)
    |
    v
[LayerSeparator] -- Separates the term tree into N layers
    |
    v
[Backend (Python AST)] -- Each layer is converted to a Python AST
    |
    v
Output: file.py (layer 0), file1.py (layer 1)
```

The key step is the `LayerSeparator`. It walks the term tree and calls `separate()` on each node. Nodes that are `Layers` (the concrete representation of the layering operation $t{:}t$) split into their components. Single-layer nodes are cloned into every layer. The result is N independent term trees, one per layer.

### The LayerSeparator in Detail

The `LayerSeparator` uses a factory pattern to ensure consistent separation. Each term implements a `separate()` method that returns a list of terms, one per layer. The separator runs the factory function once per layer, and on each pass, it extracts the corresponding layer from each `Layers` node.

For example, a `FunctionDef` node separates by running its body through the separator:

```python
def separate(self, ls):
    return ls.build(lambda layer: FunctionDef(
        name=self.name,
        body=layer(self.body),  # each layer gets its own body
        ...
    ))
```

A `Layers` node simply returns its components:

```python
def separate(self, ls):
    return self.layers  # [layer_0_term, layer_1_term]
```

This is the separation operation from the calculus, implemented as a tree transformation.

## TAPL-Specific Syntax

TAPL introduces several syntactic constructs that directly correspond to operations in the xi-calculus. Understanding these is essential for designing languages on top of TAPL.

### Literal Lifting: `^`

The `^` operator **promotes a value from the evaluation layer into the type layer**. In the calculus, this corresponds to creating a layered term where the value appears in both layers but with different evaluation modes.

```
class_name = ^'Matrix({},{})'.format(rows, cols)
```

Here, `^'Matrix({},{})'` means: this string literal exists in both layers -- as a runtime value in the evaluation layer and as a type-level value in the type-checking layer. The `^` operator transforms the parser mode:

- In `MODE_SAFE` (normal code): switches to `MODE_LIFT`, meaning the term is evaluated at both layers.
- In `MODE_TYPECHECK` (type annotations): switches to `MODE_EVALUATE_WITH_SCOPE`, meaning the term is evaluated with access to the enclosing scope.

This is how dependent types work in TAPL. When you write `Matrix(^2, ^3)`, the values `2` and `3` are lifted into the type layer, so `Matrix(2, 3)` becomes a distinct type from `Matrix(3, 3)`.

### Double-Layer Expressions: `<expr:Type>`

The `<expr:Type>` syntax explicitly specifies different terms for different layers. It is the direct syntactic representation of the layering operation $t{:}t$.

```
self.num_rows = <rows:Int>
```

This means:
- **Evaluation layer (layer 0):** `self.num_rows = rows` -- assign the runtime value.
- **Type-checking layer (layer 1):** `self.num_rows = Int` -- record that the type is `Int`.

The two layers are independent computations. The parser creates a `Layers` node with `[rows_term, Int_term]`, and the separator sends each to its respective layer.

This construct is used whenever the type of an expression cannot be inferred from the evaluation-layer code alone -- for instance, when initializing an empty list where the element type must be declared:

```
self.values = <[]:List(List(Int))>
```

Evaluation layer: `self.values = []`. Type-checking layer: `self.values` has type `List(List(Int))`.

### Instance Types: `!`

TAPL uses the `!` sigil to distinguish between a **class** (the constructor/blueprint) and an **instance** (a created object):

- `Dog` refers to the class itself.
- `Dog!` refers to an instance of `Dog`.

This resolves a pervasive ambiguity in Python, where `Dog` can mean either the class object or the instance type depending on context. In TAPL, names consistently refer to the same kind of object in both the value layer and the type layer -- a principle called **Intentional Symmetry**.

In the implementation, `Dog!` accesses the `result__sa` attribute of the class type. A class is represented as a `Function` kind whose `result` is the instance `Record` type. So `Dog` is a function type (constructor), and `Dog!` is the record type it returns.

```python
# Type-level representation:
# Dog  = Function(args=[('name', Str)], result=Record({name: Str}, label='Dog!'))
# Dog! = Record({name: Str}, label='Dog!')
```

### Dynamic Class Names: `class_name`

The `class_name` attribute inside a class body lets you parameterize the type-level label of a class. Combined with `^`, this enables dependent types:

```
def Matrix(rows, cols):
    class Matrix_:
        class_name = ^'Matrix({},{})'.format(rows, cols)
        ...
    return Matrix_
```

When `Matrix(2, 3)` is called, the type-checker creates a class labeled `Matrix(2,3)!`. When `Matrix(3, 3)` is called, it creates `Matrix(3,3)!`. These are distinct types, enforced at the type level.

## Type System Design

### Type Hierarchy

TAPL's type hierarchy is inspired by Kotlin:

```
Nothing  <:  T  <:  Any  <:  Any | NoneType
```

- **`Nothing`**: The bottom type. Subtype of all types. Represents computations that never return (e.g., infinite loops, exceptions).
- **`Any`**: The top type for non-nullable values. Supertype of all types except `NoneType`.
- **`NoneType`**: The type of `None`. Not a subtype of `Any` -- this is deliberate.
- **`Any | NoneType`**: The true top type. Supertype of everything.

This design means that by default, types are **non-nullable**. A function returning `Int` cannot return `None`. To allow `None`, you must explicitly use `Int | None`. This mirrors Kotlin's null safety and avoids the billion-dollar mistake.

### Structural Typing with Records

Instance types are implemented as **Records** -- structural types with labeled fields. A `Record` is a subtype of another `Record` if it has all the fields of the supertype with compatible types (structural subtyping / width subtyping):

```python
# {name: Str, age: Int} <: {name: Str}   -- True (has all required fields)
# {name: Str} <: {name: Str, age: Int}    -- False (missing 'age')
```

Records carry an optional label (like `Dog!`) for readable error messages, but subtype checking is structural, not nominal.

### Function Types

Function types are contravariant in their parameter types and covariant in their return type, following the standard rule:

- If `A <: B`, then `(B) -> T <: (A) -> T` (contravariant parameters).
- If `T <: U`, then `(A) -> T <: (A) -> U` (covariant return).

### Union and Intersection Types

TAPL reserves `|` and `&` exclusively for type-level union and intersection operations. They are **not** bitwise operators.

- **Union** (`A | B`): A value of type `A | B` is either of type `A` or type `B`. A type is a subtype of a union if it is a subtype of any member.
- **Intersection** (`A & B`): A value of type `A & B` is both of type `A` and type `B`. A type is a subtype of an intersection if it is a subtype of all members.

This design choice reflects the reality that in modern high-level languages, set-theoretic type operations are far more common than bitwise arithmetic. Since TAPL evaluates terms at the type level, it cannot distinguish `|` as "bitwise OR in value context" vs. "union in type context" -- because both contexts use the same operations. Reserving `|` and `&` for types is the consistent choice.

### Subtype Checking

Subtype checking uses a bidirectional protocol. Each type implements:

- `is_supertype_of__sa(subtype)`: Returns `True`, `False`, or `None` (inconclusive).
- `is_subtype_of__sa(subtype)`: Returns `True`, `False`, or `None` (inconclusive).

The checker calls both methods and reconciles the results. This protocol handles recursive types through an assumption stack: when checking `A <: B`, the pair `(A, B)` is pushed onto the stack. If the same pair is encountered during recursive checking, it is assumed to hold (coinductive reasoning). Results are cached for performance.

## Encoding Type System Features

One of TAPL's most significant contributions is showing that multiple type system features emerge from the same mechanism. The xi-calculus can encode:

### Simply Typed Lambda Calculus

In standard STL: $\lambda x{:}T.\ t$

In TAPL calculus: $B\ (\lambda x.t)\ (I{:}(G_a\ T))$

Where:
- $I = \lambda x. x$ (identity combinator)
- $B = \lambda f.\lambda g.\lambda x. f\ (g\ x)$ (composition combinator)
- $G_a = \lambda a.\lambda b.\ \text{if}\ b <: a\ \text{then}\ a\ \text{else}\ error$ (type guard, returns the annotation)

The layering $I{:}(G_a\ T)$ creates a two-layer term: the identity at the evaluation layer (pass the value through) and a type guard at the type-checking layer (check that the argument is a subtype of $T$, return $T$).

### System F (Polymorphism)

In System F: $id = \lambda X.\ \lambda x{:}X.\ x$

In TAPL calculus: $id = \lambda X.\ B\ (\lambda x. x)\ (I{:}(G_a\ X))$

Polymorphism is not a separate feature. It arises naturally because $X$ is just a variable that can be bound to any type. The same abstraction mechanism that works for terms works for types, because types *are* terms.

### Substructural Types

In standard STL: $\lambda x{:}T.\ t$

In TAPL calculus: $B\ (\lambda x.t)\ (I{:}(G_b\ T))$

Where $G_b = \lambda a.\lambda b.\ \text{if}\ b <: a\ \text{then}\ b\ \text{else}\ error$.

The only difference from STL is using $G_b$ instead of $G_a$. $G_a$ returns the annotation type $a$ (discarding the input type), while $G_b$ returns the input type $b$ (preserving it). This distinction is what gives substructural typing its identity -- the type information flows through differently.

### Dependent Types

$T_D = \lambda x.\ t_d$ (a type that depends on a value)

$G_D = \lambda a.\lambda b.\lambda x.\ G_{a|b|D}\ (a\ x)\ (b\ x)$

Dependent type: $\lambda x{:}T_D.\ t$

In TAPL calculus: $B\ (\lambda x.t)\ (I{:}(G_D\ T_D))$

Dependent types use the same layering mechanism, but with a guard combinator $G_D$ that applies both the type function and the value to the argument, then checks compatibility. Since types are just terms, a type that depends on a value is just a function from values to types -- no special machinery required.

In practice, this is what the matrix example demonstrates:

```
def Matrix(rows, cols):
    class Matrix_:
        class_name = ^'Matrix({},{})'.format(rows, cols)
        ...
    return Matrix_
```

`Matrix` is a function from values (`rows`, `cols`) to types (the class `Matrix_`). The `^` operator lifts the values into the type layer, so `Matrix(^2, ^3)` produces a distinct type `Matrix(2,3)!`. The type-checker enforces dimension compatibility because the type-level computation uses the actual dimension values.

## Extending TAPL: Creating New Languages

TAPL is designed as a **framework** for language creation. The built-in `pythonlike` language is itself an extension point.

### The Language Interface

Every TAPL language implements the `Language` abstract class with two methods:

- `get_grammar(parent_stack)`: Returns the grammar (a set of named parsing rules).
- `get_predef_headers()`: Returns the predefined imports/headers for each layer.

### Grammar Structure

A grammar is a mapping from **rule names** to **lists of parsing functions**. Each parsing function takes a `Cursor` (a position in the token stream) and returns either a `Term` (success) or `ParseFailed` (backtrack). Rules are tried in order, and the first successful match wins.

For example, the `EXPRESSION` rule in the base grammar includes parsing functions for assignments, conditionals, lambdas, disjunctions, and so on. Each parsing function can call other rules recursively.

### Extending a Grammar

To create a new language, subclass an existing language and modify its grammar. The `pipeweaver` language demonstrates this pattern:

```python
class PipeweaverLanguage(PythonlikeLanguage):
    def get_grammar(self, parent_stack):
        grammar = super().get_grammar(parent_stack).clone()
        grammar.rule_map[TOKEN] = [_parse_pipe_token, *grammar.rule_map[TOKEN]]
        grammar.rule_map[EXPRESSION] = [_parse_pipe_call, *grammar.rule_map[EXPRESSION]]
        return grammar
```

This adds two parsing rules:

1. A **token rule** that recognizes `|>` as a `PipeToken`.
2. An **expression rule** that parses `expr |> func` and transforms it into `func(expr)`.

The new rules are prepended to the existing rule lists, giving them priority over the base grammar's rules. The `clone()` call ensures the parent grammar is not mutated.

### Language Registration

Languages are discovered by module path. When a `.tapl` file starts with `language pipeweaver`, the compiler does:

```python
language = importlib.import_module('tapl_language.pipeweaver').get_language()
```

The `tapl_language` namespace package contains language modules. Each module exports a `get_language()` function that returns a `Language` instance.

### What a Language Extension Can Do

A language extension can:

- **Add new syntax**: New operators, new expression forms, new statement types.
- **Add new term types**: Custom `Term` subclasses with their own `separate()` and code-generation methods.
- **Modify parsing priority**: Prepend or append rules to change how ambiguous syntax is resolved.
- **Redefine existing rules**: Replace entire rule lists to change the language's grammar.

Because terms carry their own `separate()` method, any new syntax automatically participates in the layer separation mechanism. You define how your term splits across layers, and the compiler handles the rest.

## Design Principles

### Intentional Symmetry

A name should refer to the same kind of entity in both the value layer and the type layer. `Dog` is always the class (constructor). `Dog!` is always an instance. There is no context-dependent interpretation.

### Same Techniques at Every Layer

The same computational mechanisms -- abstraction, application, substitution -- work at the term level and the type level. This is not an accident; it is a consequence of the xi-calculus, where types are terms.

### Separation Over Erasure

Most type systems use **type erasure**: types are checked and then discarded before execution. TAPL uses **separation**: types are split into a separate computation that runs independently. The type-checker is a real program, not a static analysis. This means:

- Type-level computations can be arbitrarily complex (enabling dependent types).
- The type-checker's correctness can be tested like any other program.
- Type errors are runtime errors in the type-checker file, not special compiler diagnostics.

### Extensibility as Architecture

TAPL is not a fixed language. It is a framework for building languages. The `pythonlike` grammar is a reference implementation, not a standard. Language designers are expected to extend, modify, or replace it entirely. The compiler's only fixed requirements are:

1. A `language` directive in the first line.
2. A language module that provides a grammar and predef headers.
3. Terms that implement `separate()` for layer decomposition.

Everything else -- syntax, type rules, built-in types -- is defined by the language module.

## Summary for Language Designers

If you are designing a language on TAPL, here is what matters:

1. **Your language is a grammar** -- a set of parsing rules that produce terms. Extend the base `pythonlike` grammar or start from scratch.

2. **Your terms are multi-layer** -- each term knows how to separate itself into layers. Use `Layers` nodes for terms that mean different things at different layers. Use single-layer terms for code that is cloned into every layer.

3. **Your type system is a program** -- the type-checker layer is real, executable code. Define type-checking by defining what the type layer *does*, not by writing inference rules.

4. **Dependent types are free** -- because types are terms, a type that depends on a value is just a function. Use `^` to lift values into the type layer.

5. **The xi-calculus is your foundation** -- layering and separation give you a formal basis for reasoning about your language's semantics. Every type system feature (simple types, polymorphism, substructural types, dependent types) is an instantiation of the same mechanism.

TAPL's bet is that one mechanism -- layered computation with separation -- is sufficient to express the full spectrum of type system features. The matrix example, the pipeweaver extension, and the formal correspondence results in the calculus all support this bet. As a language designer, your job is to decide what each layer computes and how your syntax maps to multi-layer terms. The framework handles the rest.
