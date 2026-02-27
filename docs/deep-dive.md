# TAPL Deep Dive


> **Draft -- Work in Progress.** This document is not finished and may contain inconsistent or unreliable information. Last updated: February 27, 2026.

## The LayerSeparator

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
