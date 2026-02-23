---
layout: default
---

TAPL is a typed programming language that looks like Python and compiles to Python. What makes it different:

- **Type checks you write as code.** Not just annotations -- actual logic that runs at compile time. You can make the compiler reject a matrix multiplication where the dimensions don't match, something most type systems can't express.
- **Syntax you can extend.** Add custom operators and expressions to build your own DSL on top of the Python-like language. For example, adding a pipe operator (`|>`) to chain function calls.
- **Compiles to readable Python.** Produces `.py` files you can inspect, run, and debug with your existing tools.

> **Important:**
> - TAPL is experimental with no stable release yet.
> - It improves with every commit. Please report issues via the [Issue Tracker](https://github.com/tapl-org/tapl/issues).
> - It is not an officially supported Google product yet.

> The name TAPL comes from Benjamin C. Pierce's [book](https://www.cis.upenn.edu/~bcpierce/tapl/) *Types and Programming Languages*, which inspired the project.

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

Every TAPL file starts with a `language` directive that tells the compiler which grammar to use. The built-in `pythonlike` language gives you a strongly typed, Python-like syntax.

Run it:

```bash
tapl hello_world.tapl
```

Behind the scenes, TAPL generates two Python files from your source:

- `hello_world.py` -- your actual runtime code:

```python
print('Hello World!')
```

- `hello_world1.py` -- the type-checker (auto-generated, you don't write this):

```python
from tapl_lang.lib import tapl_typing
from tapl_lang.pythonlike.predef1 import predef_scope as predef_scope__sa
s0 = tapl_typing.create_scope(parent__sa=predef_scope__sa)
s0.print(s0.Str)
```

TAPL runs the type-checker first. If it finds problems, you get error messages and the runtime code never executes. If everything checks out, TAPL runs the runtime code.

> **Tip:** You can always open the generated `.py` files to see exactly what TAPL produced. The runtime file (`hello_world.py`) is plain Python. The type-checker file (`hello_world1.py`) is also plain Python that validates your types. This is handy for debugging when something doesn't behave as expected.

## Language Basics

TAPL's `pythonlike` language looks and feels like Python. The main differences are in how types are written.

### Variables

Typed variables work like you'd expect. The only difference is that TAPL uses CamelCase type names (`Int`, `Str`, `Bool`, `Float`) instead of Python's lowercase (`int`, `str`, `bool`, `float`):

```python
language pythonlike

x: Int = 42
name: Str = 'hello'
pi: Float = 3.14
```

### Functions

Functions look just like Python, with type annotations:

```python
language pythonlike

def factorial(n: Int) -> Int:
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

print(factorial(5))
```

Parameterized types use function-call syntax: `List(Int)` for a list of integers, `List(List(Int))` for a nested list.

### Classes

Classes also look like Python:

```python
language pythonlike

class Dog:
    def __init__(self, name: Str):
        self.name = name

    def bark(self) -> Str:
        return self.name + ' says Woof! Woof!'

my_dog = Dog('Buddy')
print(my_dog.bark())
```

### The `!` Operator: Classes vs. Instances

In Python, when you write `Dog` in a type hint, it's sometimes ambiguous -- does it mean the class itself or an instance of it? TAPL removes that ambiguity with a simple rule:

- `Dog` means the class (the constructor).
- `Dog!` means an instance of that class.

```python
def greet_dog(dog: Dog!) -> Str:
    return 'Hello, ' + dog.name + '!'

def make_dog(factory: Dog, name: Str) -> Dog!:
    return factory(name)
```

`greet_dog` takes an instance (a dog you already created). `make_dog` takes the class itself and uses it as a factory to create a new instance.

### Collections

Lists, sets, and dictionaries work like Python:

```python
language pythonlike

numbers = [1, 2, 3]
numbers.append(4)

unique = {1, 2, 3}
unique.add(4)

config = {'key1': 'value1', 'key2': 'value2'}
config['key3'] = 'value3'
```

### Union Types

Use `|` to say a value can be one of several types:

```python
language pythonlike

def display(value: Int | Str):
    print(value)

display(42)
display('hello')
```

Note: `|` and `&` are reserved for type operations in TAPL. They are not bitwise operators.

### Error Handling

Try/except/finally works like Python:

```python
language pythonlike

try:
    result = 10 / 0
except ZeroDivisionError:
    print('Cannot divide by zero')
finally:
    print('Execution completed')
```

### Imports

You can import other `.tapl` files the same way you import Python modules:

```python
language pythonlike

import examples.easy

my_dog = examples.easy.Dog('Simba')
print(my_dog.bark())
```

The imported file is also compiled and type-checked by TAPL.

## Type Errors

One of the main reasons to use TAPL is catching bugs before your code runs. Here's what that looks like in practice.

Say you write a function that promises to return a `Str` but actually returns an `Int`:

```python
language pythonlike

def one() -> Str:
    return 0
```

When you run `tapl` on this file, you'll get:

```
Return type mismatch: expected Str, got Int.
```

The runtime code never executes. TAPL caught the bug at compile time.

This applies to function arguments too -- if a function expects a `Dog!` and you pass it a `Str`, TAPL will tell you before anything runs.

## Dependent Types with Matrices

Most type systems can only check things like "this is an integer" or "this is a list of strings." TAPL goes further: it can check properties that depend on actual values. Imagine catching a dimension mismatch in matrix multiplication *before your code even runs*.

This section uses two special TAPL operators. Here's what they do:

- **`^expr`** -- tells the compiler to track a runtime value at compile time too. For example, `^2` makes the number `2` available to the type-checker, so it can reason about dimensions statically. Think of it as "the compiler should know about this value."
- **`<expr:Type>`** -- gives the compiler both the runtime value and its type explicitly. For example, `<rows:Int>` says "at runtime this is `rows`, and the type-checker should treat it as `Int`." Think of it as an explicit type annotation for cases where the compiler can't infer the type on its own.

### Defining a Dimension-Parameterized Matrix

The `Matrix(rows, cols)` function creates a class whose type is tagged with its dimensions:

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

A few things to note:

- `class_name = ^'Matrix({},{})'.format(rows, cols)` sets a readable name for the type (like `Matrix(2,3)`) so error messages make sense. The `^` makes this string available to the type-checker.
- `<rows:Int>` tells the compiler: "the runtime value is `rows`, and the type is `Int`."
- `<[]:List(List(Int))>` tells the compiler: "the runtime value is an empty list `[]`, and the type is `List(List(Int))`."

### Type-Safe Function Signatures

Now you can write functions where the compiler checks dimensions for you:

```python
def accept_matrix_2_3(matrix: Matrix(^2, ^3)!):
    pass
```

`Matrix(^2, ^3)!` means "an instance of a 2x3 matrix." The `^2` and `^3` make the dimensions visible to the type-checker.

You can also write functions that are generic over dimensions:

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

Both matrices must have the same dimensions. If you try to add a 2x2 and a 2x3, the compiler will reject it.

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

The first matrix is `m` by `n`, the second is `n` by `p`, and the result is `m` by `p`. The shared `n` is enforced at compile time.

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

Run it:

```bash
tapl matrix.tapl
```

See the full working code in [matrix.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/matrix.tapl).

## Extending the Language

TAPL lets you add your own syntax. You define new grammars by extending existing ones, and TAPL handles both runtime code generation and type-checking for your new syntax automatically.

Here's a practical example. Deeply nested function calls are hard to read:

```python
print(round(abs(-2.5)))
```

A pipe operator (`|>`) would let you write this left-to-right instead. TAPL ships with `pipeweaver`, a custom language that adds exactly this:

```python
language pipeweaver

def double(i: Int) -> Int:
    return i * 2

def square(i: Int) -> Int:
    return i * i

3 |> double |> square |> print
3 |> square |> double |> print
```

Run it:

```bash
tapl pipe.tapl
```

Behind the scenes, TAPL generates standard Python with nested calls:

```python
def double(i):
    return i * 2

def square(i):
    return i * i

print(square(double(3)))
print(double(square(3)))
```

The `pipeweaver` language is implemented by subclassing the base grammar and adding custom parsing rules. You can see how it works in the [pipeweaver source code](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/tapl_language/pipeweaver/pipeweaver_language.py). The same approach lets you build any DSL on top of TAPL.

## What's Supported

Here's a quick reference of Python features that work in TAPL's `pythonlike` language:

**Basics:** variables, functions, classes, `if`/`elif`/`else`, `for`, `while`, `try`/`except`/`finally`

**Types:** `Int`, `Str`, `Bool`, `Float`, `NoneType`, `List(T)`, `Set(T)`, `Dict(K, V)`, union types (`A | B`), intersection types (`A & B`)

**Collections:** lists, sets, dictionaries (including indexing, `append`, `add`, `remove`, `del`)

**Other:** imports between `.tapl` files, `language` directive for choosing grammars, custom language extensions

**Not yet supported:** some parts of the Python standard library, decorators, async/await, comprehensions, `*args`/`**kwargs`. TAPL is experimental and the set of supported features grows with every commit.

## What's Next?

Explore TAPL further:

- Browse [more examples, like easy.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/easy.tapl) to see TAPL in action.
- Read the [TAPL Concepts](concept) page for a deeper look at the design and architecture.
- Read the [θ-Calculus paper](theta-calculus.pdf) (draft) for the formal theory behind TAPL's type system.
- View [compilation process diagrams](https://docs.google.com/presentation/d/1I4Fu7Tp_QzyHC84u0REsFZcYi2i3ZvZPXiuHzasHywg/edit?usp=sharing) to understand how TAPL translates code.
- Join the [Official Discord Server](https://discord.gg/7N5Gp85hAy) to connect with other developers and the TAPL community.
- Participate in [GitHub Discussions](https://github.com/tapl-org/tapl/discussions) to ask questions and share ideas.
- Report bugs or request features via the [Issue Tracker](https://github.com/tapl-org/tapl/issues).
