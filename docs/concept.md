# TAPL Concepts



> **Draft -- Work in Progress.** This document is not finished and may contain inconsistent or unreliable information. Last updated: February 25, 2026.

This document explains the ideas behind TAPL -- the theoretical framework, the compilation architecture, and the design decisions that make it different from conventional approaches.

## The Core Idea 1: Types Are Just Code at Another Level

Most languages treat the type system as a fundamentally different mechanism from the code you actually write. In TypeScript, Rust, or Java, the type checker is a dedicated phase inside the compiler -- separate logic, separate rules, separate machinery from the code that actually runs. In other words, there is a split between your code and the compiler's type-checker.

TAPL rejects that split. There is no built-in type-checker hidden inside the compiler. Instead, TAPL takes one `.tapl` file and produces two `.py` files: one that runs, and one that checks the types. Each file is self-contained -- you can run them independently. Because the type-checking output is just a regular program, types in TAPL are not limited to simple labels like `Int` or `String`. Users can write real, executable logic inside type definitions, which means type checking can verify much richer rules than traditional type systems allow.

A practical consequence is that basic type annotations, generics, type-constructors, and dependent types are all configurations of the same mechanism -- not separate type systems bolted together.

## The Core Idea 2: Syntax Is Not Fixed

Most languages treat syntax as fixed: users can write programs in the language, but they cannot change or extend the language itself.

TAPL rejects that limitation. Users can create their own syntax on the fly, start using it immediately in the same project, and share it with others as reusable language extensions. This is syntax liberation: programming language syntax is no longer fixed by the language designer, but open to programmers themselves. As a result, teams can invent and evolve new domain-specific syntax far more freely than traditional languages allow.




## How It Works

TAPL is grounded in two foundations: **[theta-calculus](theta-calculus.pdf)** and a **[PEG parser](https://en.wikipedia.org/wiki/Parsing_expression_grammar)**.

Theta-calculus provides the model used to implement TAPL's type-checking mechanism, and the PEG parser provides a pluggable syntax system so users can define and adopt new syntax forms.


## Compilation Pipeline

For each `.tapl` source file, the compiler produces two Python files:

1. **The evaluation layer** (e.g., `hello_world.py`): executable runtime code.
2. **The type-checking layer** (e.g., `hello_world1.py`): type constraint code that runs first. If it executes without error, the evaluation layer is guaranteed to be type-safe.

The pipeline:

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
[Parser] -- Grammar rules produce a syntax tree (multi-layer)
    |
    v
[LayerSeparator] -- Splits the syntax tree into N layers
    |
    v
[Backend (Python AST)] -- Each layer is converted to a Python AST
    |
    v
Output: file.py (layer 0), file1.py (layer 1)
```

### The LayerSeparator

The LayerSeparator walks the syntax tree and calls `separate()` on each node. Nodes that represent layering split into their components. Single-layer nodes are cloned into every layer.

A `FunctionDef` node separates by running its body through the separator:

```python
def separate(self, ls):
    return ls.build(lambda layer: FunctionDef(
        name=self.name,
        body=layer(self.body),
    ))
```

A `Layers` node simply returns its components:

```python
def separate(self, ls):
    return self.layers  # [layer_0_term, layer_1_term]
```

The separator uses a factory pattern: it runs the factory function once per layer, and on each pass extracts the corresponding component from each `Layers` node. The result is N independent syntax trees, one per layer.

## Syntax

TAPL introduces syntactic constructs that map directly to the layering mechanism.

### Literal Lifting: `^`

The `^` operator promotes a value from the evaluation layer into the type layer. It creates a layered expression where the value participates in both layers.

```
class_name = ^'Matrix({},{})'.format(rows, cols)
```

In normal code (`MODE_SAFE`), `^` switches to `MODE_LIFT`, meaning the expression is evaluated at both layers. This is how dependent types work: `Matrix(^2, ^3)` lifts `2` and `3` into the type layer, so `Matrix(2, 3)` becomes a distinct type from `Matrix(3, 3)`.

### Double-Layer Expressions: `<expr:Type>`

The `<expr:Type>` syntax explicitly specifies different expressions for different layers -- the direct representation of layering.

```
self.num_rows = <rows:Int>
```

This means:
- **Evaluation layer (layer 0):** `self.num_rows = rows` -- assign the runtime value.
- **Type-checking layer (layer 1):** `self.num_rows = Int` -- record that the type is `Int`.

The parser creates a `Layers` node with `[rows_expr, Int_expr]`, and the separator sends each to its respective layer.

Use this when the type can't be inferred from the evaluation-layer code alone:

```
self.values = <[]:List(List(Int))>
```

Evaluation layer: `self.values = []`. Type-checking layer: `self.values` has type `List(List(Int))`.

### Instance Types: `!`

The `!` sigil distinguishes classes from instances:

- `Dog` refers to the class (the constructor).
- `Dog!` refers to an instance of `Dog`.

This resolves a common ambiguity in Python where `Dog` can mean either the class object or the instance type depending on context. In TAPL, names consistently refer to the same kind of entity in both layers -- a principle called **Intentional Symmetry**.

In the type-level representation, `Dog` is a function type (the constructor) and `Dog!` is the record type it returns:

```python
# Dog  = Function(args=[('name', Str)], result=Record({name: Str}, label='Dog!'))
# Dog! = Record({name: Str}, label='Dog!')
```

### Dynamic Class Names: `class_name`

The `class_name` attribute parameterizes the type-level label of a class. Combined with `^`, this enables dependent types:

```python
def Matrix(rows, cols):
    class Matrix_:
        class_name = ^'Matrix({},{})'.format(rows, cols)
        ...
    return Matrix_
```

When `Matrix(2, 3)` is called, the type-checker creates a class labeled `Matrix(2,3)!`. When `Matrix(3, 3)` is called, it creates `Matrix(3,3)!`. These are distinct types, enforced at the type level.

## Type System

### Type Hierarchy

TAPL's type hierarchy is inspired by Kotlin:

```
Nothing  <:  T  <:  Any  <:  Any | NoneType
```

- **`Nothing`**: The bottom type -- subtype of all types. Represents code that never returns (exceptions, infinite loops). Similar to `never` in TypeScript.
- **`Any`**: The top type for non-nullable values. Supertype of all types except `NoneType`.
- **`NoneType`**: The type of `None`. Deliberately *not* a subtype of `Any`.
- **`Any | NoneType`**: The true top type. Supertype of everything.

By default, types are **non-nullable**. A function returning `Int` cannot return `None`. To allow it, use `Int | None` explicitly. This mirrors Kotlin's null safety.

### Structural Typing

Instance types are **Records** -- structural types with named fields. A type is a subtype of another if it has all the required fields:

```python
# {name: Str, age: Int} <: {name: Str}   -- True (has all required fields)
# {name: Str} <: {name: Str, age: Int}    -- False (missing 'age')
```

Records carry an optional label (like `Dog!`) for readable error messages, but subtype checking is structural, not nominal.

### Function Types

Function subtyping follows the standard rule: a function is a subtype of another if it accepts broader input types and returns a narrower output type:

- If `A <: B`, then `(B) -> T <: (A) -> T` (parameters: broader input is OK)
- If `T <: U`, then `(A) -> T <: (A) -> U` (return: narrower output is OK)

### Union and Intersection Types

TAPL reserves `|` and `&` exclusively for type-level operations -- they are **not** bitwise operators.

- **Union** (`A | B`): A value is either of type `A` or type `B`. A type is a subtype of a union if it's a subtype of any member.
- **Intersection** (`A & B`): A value is both of type `A` and type `B`. A type is a subtype of an intersection if it's a subtype of all members.

Since TAPL evaluates code at the type level using the same operations as the value level, it can't distinguish `|` as "bitwise OR" vs. "union." Reserving `|` and `&` for types is the consistent choice.

### Subtype Checking

Subtype checking uses a bidirectional protocol. Each type implements:

- `is_supertype_of(subtype)`: Returns `True`, `False`, or `None` (inconclusive).
- `is_subtype_of(supertype)`: Returns `True`, `False`, or `None` (inconclusive).

The checker calls both methods and reconciles the results. Recursive types are handled by tracking in-progress checks: when checking `A <: B`, the pair `(A, B)` is pushed onto a stack. If the same pair comes up again during recursion (a cycle), the check is assumed to hold. Results are cached for performance.

## Language Extensibility

TAPL is a framework for building languages, not a single fixed language.

### The Language Interface

Every TAPL language implements the `Language` abstract class:

- `get_grammar(parent_stack)`: Returns the grammar -- a mapping from rule names to lists of parsing functions.
- `get_predef_headers()`: Returns the predefined imports/headers for each layer.

Parsing functions take a `Cursor` (a position in the token stream) and return either a syntax node (success) or `ParseFailed` (backtrack). Rules are tried in order; the first match wins.

### Extending a Grammar

To create a new language, subclass an existing one and modify its grammar. The `pipeweaver` language adds a pipe operator (`|>`):

```python
class PipeweaverLanguage(PythonlikeLanguage):
    def get_grammar(self, parent_stack):
        grammar = super().get_grammar(parent_stack).clone()
        grammar.rule_map[TOKEN] = [_parse_pipe_token, *grammar.rule_map[TOKEN]]
        grammar.rule_map[EXPRESSION] = [_parse_pipe_call, *grammar.rule_map[EXPRESSION]]
        return grammar
```

New rules are prepended to give them priority over the base grammar. The `clone()` call ensures the parent grammar isn't mutated.

With `pipeweaver`:

```
3 |> double |> square |> print
```

becomes:

```python
print(square(double(3)))
```

### What Extensions Can Do

A language extension can:

- **Add new syntax**: new operators, expression forms, statement types.
- **Add new node types**: custom `Term` subclasses with their own `separate()` and code-generation methods.
- **Modify parsing priority**: prepend or append rules to change how ambiguous syntax is resolved.
- **Redefine existing rules**: replace entire rule lists to change the grammar.

Because each syntax node carries its own `separate()` method, any new syntax automatically participates in layer separation. You define how your node splits across layers, and the compiler handles the rest.

### Language Registration

Languages are discovered by module path. When a `.tapl` file starts with `language pipeweaver`, the compiler loads:

```python
language = importlib.import_module('tapl_language.pipeweaver').get_language()
```

The `tapl_language` namespace package contains language modules, each exporting a `get_language()` function.

## Design Principles

**Intentional Symmetry.**
A name refers to the same kind of entity in both the value layer and the type layer. `Dog` is always the class; `Dog!` is always an instance. No context-dependent interpretation.

**Same Techniques at Every Layer.**
Functions, function calls, and variable binding work identically at the runtime level and the type level. This is a direct consequence of types being code.

**Unlayering Over Erasure.**
Most type systems use *type erasure*: types are checked and then thrown away before execution. TAPL uses *unlayering*: types are split into a separate program that runs independently. The type-checker is a real program. This means:

- Type-level computations can be arbitrarily complex (enabling dependent types).
- The type-checker can be tested like any other program.
- Type errors are runtime errors in the type-checker file, not special compiler diagnostics.

**Extensibility as Architecture.**
TAPL is not a fixed language but a framework. The `pythonlike` grammar is a reference implementation, not a standard. The compiler's only fixed requirements are: (1) a `language` directive, (2) a language module providing a grammar and predefined headers, and (3) syntax nodes that implement `separate()`. Everything else -- syntax, type rules, built-in types -- is defined by the language module.

## Summary

If you're building on TAPL, here's what matters:

1. **Your language is a grammar** -- a set of parsing rules that produce syntax nodes. Extend the base `pythonlike` grammar or start from scratch.

2. **Your syntax nodes are multi-layer** -- each node knows how to split itself into layers. Use `Layers` nodes for expressions that mean different things at different layers. Use single-layer nodes for code that gets cloned into every layer.

3. **Your type system is a program** -- the type-checker layer is real, executable code. Define type-checking by defining what the type layer *does*, not by writing formal typing rules.

4. **Dependent types are free** -- because types are code, a type that depends on a value is just a function. Use `^` to lift values into the type layer.

5. **The theta-calculus is the foundation** -- layering and unlayering give you a formal basis for reasoning about your language's semantics. For the full formal treatment, see the [theta-calculus paper](theta-calculus.pdf).
