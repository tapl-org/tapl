# TAPL: Types and Programming Languages

<!--
Part of the TAPL project, under the Apache License v2.0 with LLVM
Exceptions. See /LICENSE for license information.
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
-->

TAPL is an extensible typed programming language that compiles to Python. It gives you a type system powerful enough to catch bugs that most type systems can't -- while keeping the full Python ecosystem at your fingertips.

Here's what makes it different:

- **Types are programs, not just labels.** In most languages, types are passive annotations like `x: int`. In TAPL, type-checking is done by generated Python code that runs at compile time. This means you can enforce constraints that depend on values -- for example, rejecting a matrix multiplication where the dimensions don't match -- before your code ever runs.
- **Build your own language grammar.** Most languages have a fixed grammar -- you can't add new syntax. TAPL ships with `pythonlike` as its default language, but you're not stuck with it. You can create entirely new language grammars by extending the existing ones -- adding operators, expressions, or any syntax you need. For example, you could add a pipe operator (`|>`) so you write `3 |> double |> print` instead of `print(double(3))`.
- **Compiles to readable Python.** Produces `.py` files you can inspect, run, and debug with your existing tools. You get the full Python ecosystem -- libraries, package managers, debuggers, and toolchains -- with no extra effort.

📖 Full documentation: [tapl-lang.org](https://tapl-lang.org)

> [!IMPORTANT]
> - TAPL is experimental with no stable release yet.
> - It improves with every commit. Please report issues via the [Issue Tracker](https://github.com/tapl-org/tapl/issues).
> - It is not an officially supported Google product yet.

## Installation

TAPL requires **Python 3.9** or higher. It has no third-party dependencies -- only the Python standard library.

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

Every TAPL file starts with a `language` directive that tells the compiler which grammar to use. The built-in `pythonlike` language gives you a typed, Python-like syntax.

Run it:

```bash
tapl hello_world.tapl
# Output: Hello World!
```

Behind the scenes, TAPL generates two Python files from your source:

- `hello_world.py` -- your runtime code. This is what actually runs.
- `hello_world1.py` -- the type-checker. This is compile-time code that validates your types.

TAPL runs the type-checker first. If it finds problems, you get error messages and the runtime code never executes. If everything checks out, TAPL considers the runtime code safe and runs it.

> [!TIP]
> You can always open the generated `.py` files to see exactly what TAPL produced. This is handy for debugging when something doesn't behave as expected.

## Language Basics

If you know Python, you already know most of TAPL. Variables, functions, classes, collections, `if`/`for`/`while`, `try`/`except`/`finally`, and imports all work the way you'd expect. The differences are small but important:

- **CamelCase type names:** `Int`, `Str`, `Bool`, `Float` instead of `int`, `str`, `bool`, `float`.
- **Parameterized types use function-call syntax:** `List(Int)` instead of `list[int]`.
- **The `!` operator:** `Dog` means the class (the constructor), and `Dog!` means an instance of that class.

```python
language pythonlike

class Dog:
    def __init__(self, name: Str):
        self.name = name

    def bark(self) -> Str:
        return self.name + ' says Woof! Woof!'

def greet_dog(dog: Dog!) -> Str:
    return 'Hello, ' + dog.name + '!'

my_dog = Dog('Buddy')
print(my_dog.bark())
print(greet_dog(my_dog))
```

## Type Errors

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

TAPL can check properties that depend on actual values -- like catching a dimension mismatch in matrix multiplication *before your code even runs*. Two special operators make this possible:

- **`^expr`** -- tells the compiler to track a runtime value at compile time too. For example, `^2` makes the number `2` available to the type-checker.
- **`<expr:Type>`** -- gives the compiler both the runtime value and its type explicitly. For example, `<rows:Int>` says "at runtime this is `rows`, and the type-checker should treat it as `Int`."

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

Now functions can enforce dimension constraints at compile time. `add` requires both matrices to have the same dimensions, and `multiply` enforces that the inner dimensions match:

```python
def add(rows, cols):
    def add_(a: Matrix(rows, cols)!, b: Matrix(rows, cols)!):
        result = Matrix(rows, cols)()
        for i in range(result.num_rows):
            for j in range(result.num_cols):
                result.values[i][j] = a.values[i][j] + b.values[i][j]
        return result
    return add_

def multiply(m, n, p):
    def multiply_(a: Matrix(m, n)!, b: Matrix(n, p)!):
        result = Matrix(m, p)()
        for i in range(a.num_rows):
            for j in range(b.num_cols):
                for k in range(a.num_cols):
                    result.values[i][j] = result.values[i][j] + a.values[i][k] * b.values[k][j]
        return result
    return multiply_

def main():
    matrix_2_2 = Matrix(^2, ^2)()
    matrix_2_2.values = [[1, 2], [3, 4]]
    matrix_2_3 = Matrix(^2, ^3)()
    matrix_2_3.values = [[1, 2, 3], [4, 5, 6]]

    print(add(^2, ^2)(matrix_2_2, matrix_2_2))
    print(multiply(^2, ^2, ^3)(matrix_2_2, matrix_2_3))
```

```bash
tapl matrix.tapl
```

See the full working code in [matrix.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/matrix.tapl).

## Extending the Language

TAPL lets you add your own syntax. You define new grammars by extending existing ones, and TAPL handles both runtime code generation and type-checking for your new syntax automatically. TAPL includes `pipeweaver` as an example -- a custom grammar built on top of `pythonlike` that adds a pipe operator (`|>`):

```python
language pipeweaver

def double(i: Int) -> Int:
    return i * 2

def square(i: Int) -> Int:
    return i * i

3 |> double |> square |> print
3 |> square |> double |> print
```

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

See the [pipeweaver source code](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/tapl_language/pipeweaver/pipeweaver_language.py) for how it's implemented. The same approach lets you build any DSL on top of TAPL.

## What's Supported

**Basics:** variables, functions, classes, `if`/`elif`/`else`, `for`, `while`, `try`/`except`/`finally`

**Types:** `Int`, `Str`, `Bool`, `Float`, `NoneType`, `List(T)`, `Set(T)`, `Dict(K, V)`, union types (`A | B`), intersection types (`A & B`)

**Collections:** lists, sets, dictionaries (including indexing, `append`, `add`, `remove`, `del`)

**Other:** imports between `.tapl` files, `language` directive for choosing grammars, custom language extensions

**Not yet supported:** some parts of the Python standard library, decorators, async/await, comprehensions, `*args`/`**kwargs`.

## Learn More

- Browse [more examples, like easy.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/easy.tapl).
- Read the [TAPL Concepts](https://tapl-lang.org/concept) page for a deeper look at the design and architecture.
- Read the [θ-Calculus paper](https://github.com/tapl-org/tapl/blob/main/doc/theta-calculus.tex) (draft) for the formal theory behind TAPL's type system.
- View [compilation process diagrams](https://docs.google.com/presentation/d/1I4Fu7Tp_QzyHC84u0REsFZcYi2i3ZvZPXiuHzasHywg/edit?usp=sharing).

## Community

- [Official Discord Server](https://discord.gg/7N5Gp85hAy)
- [GitHub Discussions](https://github.com/tapl-org/tapl/discussions)
- [Issue Tracker](https://github.com/tapl-org/tapl/issues)

## Contributing

We welcome and encourage contributions from everyone! Whether it's a small typo fix, a new compiler feature, or a bug report, your help is valued. TAPL is committed to maintaining a welcoming and inclusive environment where all contributors can participate. See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

## Future Project Goals

- Transpile to C language
- Use a lightweight, Lua-like interpreter as a backend
- Use LLVM/WASM as a backend

> The name TAPL comes from Benjamin C. Pierce's [book](https://www.cis.upenn.edu/~bcpierce/tapl/) *Types and Programming Languages*, which inspired the project.
