---
layout: default
---

TAPL is an extensible typed programming language that compiles to Python. It gives you a type system powerful enough to catch bugs that most type systems can't -- while keeping the full Python ecosystem at your fingertips.

Here's what makes it different:

- **Types are programs, not just labels.** In most languages, types are passive annotations like `x: int`. In TAPL, type-checking is done by generated Python code that runs at compile time. This means you can enforce constraints that depend on values -- for example, rejecting a matrix multiplication where the dimensions don't match -- before your code ever runs.
- **Build your own language grammar.** Most languages have a fixed grammar -- you can't add new syntax. TAPL ships with `pythonlike` as its default language, but you're not stuck with it. You can create entirely new language grammars by extending the existing ones -- adding operators, expressions, or any syntax you need. For example, you could add a pipe operator (`|>`) so you write `3 |> double |> print` instead of `print(double(3))`.
- **Compiles to readable Python.** Produces `.py` files you can inspect, run, and debug with your existing tools. You get the full Python ecosystem -- libraries, package managers, debuggers, and toolchains -- with no extra effort.

## Installation

TAPL requires **Python 3.9** or higher. It has no third-party dependencies -- only the Python standard library.

```bash
pip install tapl-lang
```

Verify the installation:

```bash
tapl --help
```

> **Important:**
> - TAPL is experimental with no stable release yet.
> - It improves with every commit. Please report issues via the [Issue Tracker](https://github.com/tapl-org/tapl/issues).
> - It is not an officially supported Google product yet.

## Hello World

Create a file called `hello_world.tapl`:

```python
language pythonlike

print('Hello World!')
```

Every TAPL file starts with a `language` directive that tells the compiler which grammar to use. The built-in `pythonlike` language gives you a typed, Python-like syntax.

Run it:

```bash
tapl hello_world.tapl
# Output: Hello World!
```

Behind the scenes, TAPL generates a Python file from your source -- `hello_world.py`:

```python
print('Hello World!')
```

Before running it, TAPL first runs a type-checker (also generated as plain Python). If the type-checker finds problems, you get error messages and the runtime code never executes. If everything checks out, TAPL considers the runtime code safe and runs it.

> **Tip:** You can always open the generated `.py` files to see exactly what TAPL produced. This is handy for debugging when something doesn't behave as expected.

## Language Basics

If you know Python, you already know most of TAPL. Variables, functions, classes, collections, `if`/`for`/`while`, `try`/`except`/`finally`, and imports all work the way you'd expect. You can import other `.tapl` files the same way you import Python modules, and the imported file is also compiled and type-checked.

Here's a quick example that shows the familiar syntax:

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

The differences are small but important:

### CamelCase Type Names

TAPL uses `Int`, `Str`, `Bool`, `Float` instead of Python's lowercase `int`, `str`, `bool`, `float`:

```python
language pythonlike

x: Int = 42
name: Str = 'hello'
pi: Float = 3.14
```

### Parameterized Types Use Function-Call Syntax

Where Python writes `list[int]`, TAPL writes `List(Int)`. Nesting works the same way: `List(List(Int))` for a list of lists.

### The `!` Operator: Classes vs. Instances

Python type checkers use `type[Dog]` to distinguish the class from an instance. TAPL takes a different approach with the `!` operator:

- `Dog` means the class (the constructor).
- `Dog!` means an instance of that class.

```python
def greet_dog(dog: Dog!) -> Str:
    return 'Hello, ' + dog.name + '!'

def make_dog(factory: Dog, name: Str) -> Dog!:
    return factory(name)
```

`greet_dog` takes an instance (a dog you already created). `make_dog` takes the class itself and uses it as a factory to create a new instance.

## Type Errors

Here's TAPL's type checker in action. Create a file called `type_error.tapl`:

```python
language pythonlike

def one() -> Str:
    return 0
```

TAPL catches this at compile time -- the runtime code never executes:

```
Return type mismatch: expected Str, got Int.
```

Since the type-checker is itself generated Python (`type_error1.py`), you can open it, step through it with a debugger, and see exactly how this error is raised.

## Dependent Types with Matrices

Most type systems can only check things like "this is an integer" or "this is a list of strings." TAPL goes further: it can check properties that depend on actual values. Imagine catching a dimension mismatch in matrix multiplication *before your code even runs*.

This section uses two special TAPL operators. Here's what they do:

- **`^expr`** -- tells the compiler to track a runtime value at compile time too. For example, `^2` makes the number `2` available to the type-checker, so it can reason about dimensions statically. Think of it as "the compiler should know about this value."
- **`<expr:Type>`** -- gives the compiler both the runtime value and its type explicitly. For example, `<rows:Int>` says "at runtime this is `rows`, and the type-checker should treat it as `Int`." Think of it as type casting.

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

- `class_name = ^'Matrix({},{})'.format(rows, cols)` is optional -- the type-checker doesn't use it for type-checking. It just sets a readable name (like `Matrix(2,3)`) for debugging and error messages.
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

A pipe operator (`|>`) would let you write this left-to-right instead. TAPL includes `pipeweaver` as an example of how to create your own language grammar:

> **Note:** The example below uses `language pipeweaver`, not `pythonlike`. This is a custom grammar built on top of `pythonlike` language.

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

The goal is to make `pythonlike` as close to Python as possible. Here's what works today:

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

> The name TAPL comes from Benjamin C. Pierce's [book](https://www.cis.upenn.edu/~bcpierce/tapl/) *Types and Programming Languages*, which inspired the project.
