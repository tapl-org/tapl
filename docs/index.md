---
layout: default
---

TAPL is a compiler frontend framework with Python-like syntax. No need to build a language from scratch.

- Extend the grammar with your own syntax rules.
- Program your own type-checking logic.

Types in TAPL are programmable, not declarative. You get full control over compile-time verification, including dependent types and substructural types.


> **Important:**
> - TAPL is experimental with no stable release yet.
> - It improves with every commit. Please report issues via the [Issue Tracker](https://github.com/tapl-org/tapl/issues).
> - It is not an officially supported Google product yet.

> **Note:** TAPL stands for *Types and Programming Languages* and is named after Benjamin C. Pierce's [book](https://www.cis.upenn.edu/~bcpierce/tapl/) that inspired the project.

## Installation

TAPL requires **Python 3.12** or higher.

```bash
pip install tapl-lang
```

Verify the installation:

```bash
tapl --help
```

## Hello World

Create a file called `hello_world.tapl`:

```python
language pythonlike

print('Hello World!')
```

Every TAPL file starts with a `language` directive that tells the compiler which language grammar to use. The built-in `pythonlike` language provides a strongly typed, Python-like syntax.

Run it:

```bash
tapl hello_world.tapl
```

Behind the scenes, TAPL compiles your source into two Python files and executes them:

- `hello_world.py` -- the executable code:

```python
from tapl_lang.pythonlike.predef import *
print('Hello World!')
```

- `hello_world1.py` -- the type-checker:

```python
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = predef_scope__sa.tapl.typing.create_scope(parent__sa=predef_scope__sa)
s0.print(s0.Str)
```

The type-checker runs first. If it succeeds, the executable code is guaranteed to be type-safe.

## Language Basics

TAPL's `pythonlike` language looks like Python but with a strong type system enforced at compile time.

### Typed Functions

Functions use type annotations for parameters and return types. Built-in types include `Int`, `Str`, and `Bool`.

```python
language pythonlike

def factorial(n: Int) -> Int:
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)
```

### Classes

Classes work like Python classes, with typed constructors and methods:

```python
class Dog:
    def __init__(self, name: Str):
        self.name = name

    def bark(self) -> Str:
        return self.name + ' says Woof! Woof!'
```

### Class Types vs Instance Types

TAPL distinguishes between a **class** and its **instances** at the type level:

- `Dog` refers to the class itself (the constructor).
- `Dog!` refers to an instance of `Dog`.

This lets you write functions that accept the class as a factory or an instance as a value:

```python
def greet_dog(dog: Dog!) -> Str:
    return 'Hello, ' + dog.name + '!'

def make_dog(factory: Dog, name: Str) -> Dog!:
    return factory(name)
```

Here `greet_dog` takes an instance (`Dog!`) and returns a `Str`. Meanwhile `make_dog` takes the class itself (`Dog`) as a factory parameter and returns a new instance (`Dog!`).

See the full example at [easy.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/easy.tapl).

## The Two Layers: Values and Types

TAPL separates every program into two layers:

- The **value layer** -- the code that runs at runtime (values, computation, side effects).
- The **type layer** -- the code that runs at compile time to check correctness (types, constraints).

The two `.py` files you saw in Hello World correspond to these layers: `hello_world.py` is the value layer, `hello_world1.py` is the type layer.

Most of the time you write normal code and the compiler figures out both layers. But TAPL gives you two special operators to manually move things between layers:

- `^expr` (literal lifting) -- promotes a runtime value into the type layer.
- `<expr:Type>` (double-layer expression) -- lets you specify both layers explicitly.

These operators are what make dependent types possible.

## Dependent Types with Matrices

One of TAPL's most distinctive features is support for dependent types -- types that depend on values. This section walks through a matrix example where the compiler enforces dimension constraints at the type level.

### Defining a Dimension-Parameterized Matrix

The `Matrix(rows, cols)` function returns a class whose type is parameterized by its dimensions:

```python
language pythonlike

def Matrix(rows, cols):

    class Matrix_:
        class_name = ^'Matrix({},{})'.format(rows, cols)

        def __init__(self):
            self.rows = rows
            self.cols = cols
            self.num_rows = <rows:Int>
            self.num_cols = <cols:Int>
            self.values = <[]:List(List(Int))>
            for i in range(self.num_rows):
                columns = <[]:List(Int)>
                for j in range(self.num_cols):
                    columns.append(0)
                self.values.append(columns)

        def __repr__(self):
            return str(self.values)

    return Matrix_
```

The `^` operator (literal lifting) promotes a runtime value into the type layer. For example, `^'Matrix({},{})'.format(rows, cols)` lifts the formatted string into the type layer to give the class a unique type name based on its dimensions.

The `<expr:Type>` syntax (double-layer expression) separates the term layer from the type layer. For instance, `<rows:Int>` means the runtime value is `rows` and the type is `Int`.

### Type-Safe Function Signatures

With dimension-parameterized types, you can write functions that enforce constraints at the type level:

```python
def accept_matrix_2_3(matrix: Matrix(^2,^3)!):
    pass
```

Here `Matrix(^2, ^3)!` is the type of a 2x3 matrix instance. The `^2` and `^3` lift the literals into the type layer, so the compiler knows the exact dimensions.

Functions can also be generic over dimensions:

```python
def sum(rows, cols):
    def sum_(a: Matrix(rows, cols)!, b: Matrix(rows, cols)!):
        result = Matrix(rows, cols)()
        for i in range(result.num_rows):
            for j in range(result.num_cols):
                result.values[i][j] = a.values[i][j] + b.values[i][j]
        return result
    return sum_
```

The `sum` function enforces that both input matrices have the same dimensions. Passing a `Matrix(2, 3)` and a `Matrix(3, 3)` would be a type error.

Matrix multiplication enforces that the inner dimensions match:

```python
def multiply(m, n, p):
    def multiply_(a: Matrix(m, n)!, b: Matrix(n, p)!):
        result = Matrix(m, p)()
        for i in range(a.num_rows):
            for j in range(b.num_cols):
                for k in range(a.num_cols):
                    result.values[i][j] = result.values[i][j] + a.values[i][k] * b.values[k][j]
        return result
    return multiply_
```

The type signature `Matrix(m, n)` times `Matrix(n, p)` produces `Matrix(m, p)` -- the shared dimension `n` must match, and the result dimensions are derived from the inputs.

### Using Matrices

```python
def main():
    matrix_2_2 = Matrix(^2, ^2)()
    matrix_2_2.values = [[1, 2], [3, 4]]
    matrix_2_3 = Matrix(^2, ^3)()
    matrix_2_3.values = [[1, 2, 3], [4, 5, 6]]

    accept_matrix_2_3(matrix_2_3)

    print(sum(^2, ^2)(matrix_2_2, matrix_2_2))
    print(multiply(^2, ^2, ^3)(matrix_2_2, matrix_2_3))
```

Run it:

```bash
tapl matrix.tapl
```

See the full example at [matrix.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/matrix.tapl).

## Extending the Language

You may have noticed that dependent types introduce some boilerplate. Operators like `^` and `<expr:Type>` are powerful but can make code verbose. TAPL is designed to be extensible -- you can create new language grammars that simplify these patterns by adding custom syntax.

As an example, the built-in `pipeweaver` language extends `pythonlike` with a pipe operator (`|>`):

```python
language pipeweaver

-2.5 |> abs |> round |> print
```

Run it:

```bash
tapl pipe.tapl
```

This outputs `2`. The pipe operator passes the result of each expression as the argument to the next function: `-2.5` is piped to `abs`, then to `round`, then to `print`.

The `pipeweaver` language is implemented by subclassing the base grammar and adding two new parsing rules -- one for the `|>` token and one for the pipe call expression. See the [pipeweaver source](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/tapl_language/pipeweaver/pipeweaver_language.py) for the full implementation.

## What's Next

- [More examples (easy.tapl)](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/easy.tapl)
- [Matrix example](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/matrix.tapl)
- [TAPL calculus documentation](https://github.com/tapl-org/tapl/blob/main/doc/ground-rules.md)
- [Official Discord Server](https://discord.gg/7N5Gp85hAy)
- [GitHub Discussions](https://github.com/tapl-org/tapl/discussions)
- [Issue Tracker](https://github.com/tapl-org/tapl/issues)
