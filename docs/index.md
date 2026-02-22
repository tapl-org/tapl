---
layout: default
---

TAPL is a typed programming language that looks like Python and compiles to Python. What makes it different:

- **Type checks you write as code.** Not just annotations -- actual logic that runs at compile time. For example, you can make the compiler reject a matrix multiplication where the dimensions don't match, something most type systems can't express.
- **Syntax you can extend.** Add custom operators and expressions to build your own DSL on top of the Python-like language. For example, adding a pipe operator (`|>`) to chain function calls.
- **Compiles to Python.** Produces `.py` files you can inspect, run, and debug.

This doc walks you through two examples: matrix dimension checking with dependent types, and adding a pipe operator via language extensibility.

TAPL stands for "Types and Programming Languages" and is named after Benjamin C. Pierce's [book](https://www.cis.upenn.edu/~bcpierce/tapl/) that inspired the project.

> **Important:**
> - TAPL is experimental with no stable release yet.
> - It improves with every commit. Please report issues via the [Issue Tracker](https://github.com/tapl-org/tapl/issues).
> - It is not an officially supported Google product yet.



## Installation

TAPL requires **Python 3.9** or higher.

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

Behind the scenes, TAPL generates two Python files from your source:

- `hello_world.py` -- the runtime code:

```python
print('Hello World!')
```

- `hello_world1.py` -- the type-checker:

```python
from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
s0.print(s0.Str)
```

TAPL runs the type-checker first. If type-checking fails, TAPL reports the errors and the runtime code never executes. If type-checking succeeds, TAPL then executes the runtime code.

## Language Basics

TAPL's `pythonlike` language looks like Python, with a few targeted syntax differences for its type system.

### Functions and Classes

TAPL functions and classes look like Python and use the same syntax for defining them, except that type names are written in CamelCase (e.g., `Int`, `Str`, `Bool`) instead of lowercase (like Python's `int`, `str`, `bool`). Parameterized types use function-call syntax, such as `List(Int)` for a list of integers or `List(List(Int))` for a nested list.

Here's an example showing both a typed function and a class definition:

```python
language pythonlike

def factorial(n: Int) -> Int:
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

class Dog:
    def __init__(self, name: Str):
        self.name = name

    def bark(self) -> Str:
        return self.name + ' says Woof! Woof!'
```

### The `!` Operator: Distinguishing Classes vs. Instances in Type-Checking

In TAPL, the `!` symbol distinguishes a class from its instances in type annotations. In Python, by contrast, `Dog` typically refers to an instance and `type[Dog]` refers to the class -- but TAPL uses the opposite convention.

- In TAPL, `Dog` refers to the class (the constructor).
- `Dog!` refers to an instance of that class.

Using the `Dog` class defined above, you can define functions as follows:

```python
def greet_dog(dog: Dog!) -> Str:
    return 'Hello, ' + dog.name + '!'

def make_dog(factory: Dog, name: Str) -> Dog!:
    return factory(name)
```

Here, `greet_dog` accepts an instance of `Dog` (`Dog!`) as an argument, while `make_dog` takes the class itself (`Dog`) and uses it to create and return an instance (`Dog!`).

### New Syntax for Working with the Two Layers: Values and Types

TAPL splits every program into two distinct layers:

- The **value layer** -- code that executes at runtime (handling values, computation, and effects).
- The **type layer** -- code that runs during compilation to check correctness (handling types and constraints).

As shown in the Hello World example, there are two `.py` files for these layers: `hello_world.py` for the value layer and `hello_world1.py` for the type layer.

Normally, you just write regular code and the compiler determines the layers automatically. But TAPL provides two special operators to let you explicitly move information between the layers:

- `^expr` (“literal lifting”) -- takes a value from the runtime/value layer and moves it to the type layer, making it available for type-level checks. For example, `^2` makes the number `2` available at the type level, so the compiler can reason about it statically.
- `<expr:Type>` (“double-layer expression”) -- lets you specify both the value layer and type layer components directly. For example, `<rowCount:Int>` pairs the runtime value `rowCount` with the explicit type `Int` in the type layer. This is similar to a type cast.

These operators are what allow TAPL to support dependent types in a natural way. The [Dependent Types with Matrices](#dependent-types-with-matrices) section below shows both operators in action.

## Dependent Types with Matrices

TAPL's support for dependent types -- types that depend on values -- is one of its most distinctive features. This section presents a matrix example, demonstrating how the compiler enforces dimension constraints directly at the type level.

### Defining a Dimension-Parameterized Matrix

The `Matrix(rows, cols)` function creates a class whose type is parameterized by its dimensions:

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

The optional `class_name` attribute sets the type name that appears in error messages for this dynamically created class. It aids in debugging but is not used for type checking. Here, the `^` operator (literal lifting) brings the formatted string to the type layer, giving the class a readable name like `Matrix(2,3)` that makes error messages easier to understand.

The `<expr:Type>` ("double-layer expression") lets you assign both a runtime value and an explicit type. For example, `<rows:Int>` ensures `rows` is available in both the value and type layers as an integer.

### Type-Safe Function Signatures

With dimension-parameterized types, you can write functions that are checked for correct dimensions at compile time:

```python
def accept_matrix_2_3(matrix: Matrix(^2, ^3)!):
    pass
```

Here `Matrix(^2, ^3)!` is the type of a 2x3 matrix instance. The `^2` and `^3` lift the numbers to the type layer, so the compiler knows the matrix dimensions statically.

You can also write generic functions over dimensions:

```python
def add(rows, cols):
    def add_(a: Matrix(rows, cols)!, b: Matrix(rows, cols)!):
        result = Matrix(rows, cols)()
        for i in range(result.num_rows):
            for j in range(result.num_cols):
                result.values[i][j] = a.values[i][j] + b.values[i][j]
        return result
    return add_
```

This `add` function requires both input matrices to have the same dimensions. If you try to add matrices with different sizes, the compiler will raise a type error.

Matrix multiplication similarly enforces that the inner dimensions match:

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

The type signature here requires that the first matrix has dimensions `m` by `n`, the second `n` by `p`, and the result is `m` by `p`. The shared dimension `n` is enforced at the type level.

### Using Matrices

```python
def main():
    matrix_2_2 = Matrix(^2, ^2)()
    matrix_2_2.values = [[1, 2], [3, 4]]
    matrix_2_3 = Matrix(^2, ^3)()
    matrix_2_3.values = [[1, 2, 3], [4, 5, 6]]

    accept_matrix_2_3(matrix_2_3)

    print(add(^2, ^2)(matrix_2_2, matrix_2_2))
    print(multiply(^2, ^2, ^3)(matrix_2_2, matrix_2_3))
```

To run this example:

```bash
tapl matrix.tapl
```

See the full working code in [matrix.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/matrix.tapl).

## Extending the Language

TAPL is built for extensibility -- you can design your own language grammars and introduce custom syntax to make your code clearer and less verbose.

Writing code with deeply nested function calls can often become hard to read. For example:

```python
print(round(abs(-2.5)))
```

A "pipe" operator would let you express this as a left-to-right chain instead. TAPL lets you create exactly this kind of syntax extension by defining new languages.

For example, `pipeweaver` is a custom language that extends `pythonlike` by adding a pipe operator (`|>`). It is included with the `tapl-lang` package as an example of language extensibility. Here's what it looks like in practice:

```python
language pipeweaver

def double(i: Int) -> Int:
    return i * 2

def square(i: Int) -> Int:
    return i * i

3 |> double |> square |> print
3 |> square |> double |> print

```

You can run this code with:

```bash
tapl pipe.tapl
```
Behind the scenes, TAPL generates standard Python with nested function calls:

```python
def double(i):
    return i * 2

def square(i):
    return i * i

print(square(double(3)))
print(double(square(3)))
```

The `pipeweaver` language implementation demonstrates how you can subclass the base grammar and add custom parsing rules -- one for handling the `|>` token and another for parsing pipe call expressions. You can see the full implementation in the [pipeweaver source code](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/tapl_language/pipeweaver/pipeweaver_language.py).

As you can see, you can create your own domain-specific language (DSL) simply by extending existing TAPL languages. Your custom language will also integrate seamlessly with standard Python code.

## What's Next?

Explore TAPL further with the following resources:

- Browse [more examples, like easy.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/easy.tapl) to see TAPL in action.
- Read the [TAPL Concepts](concept) page for a deeper look at the design and architecture.
- Read the [θ-Calculus paper](theta-calculus.pdf) (draft) for the formal theory behind TAPL's type system.
- View [compilation process diagrams](https://docs.google.com/presentation/d/1I4Fu7Tp_QzyHC84u0REsFZcYi2i3ZvZPXiuHzasHywg/edit?usp=sharing) to understand how TAPL translates code.
- Join the [Official Discord Server](https://discord.gg/7N5Gp85hAy) to connect with other developers and the TAPL community.
- Participate in [GitHub Discussions](https://github.com/tapl-org/tapl/discussions) to ask questions and share ideas.
- Report bugs or request features via the [Issue Tracker](https://github.com/tapl-org/tapl/issues).

These links will help you deepen your understanding of TAPL, contribute to the project, or get support from the community.
