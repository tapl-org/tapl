# TAPL: Types and Programming Languages

<!--
Part of the TAPL project, under the Apache License v2.0 with LLVM
Exceptions. See /LICENSE for license information.
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
-->

TAPL is a modern compiler system's frontend framework designed to help users create their own strongly typed programming languages. It is designed to simplify the process of creating and extending programming languages with strong typing capabilities.

At its core, TAPL provides a strongly typed Python-like language that can be extended with custom parsers and type-checker rules.

> [!IMPORTANT]
> - TAPL is an experimental project with no working compiler or toolchain yet.
> - There is no stable release yet, and it improves with every commit. Please report any issues via the [Tapl Issue Tracker](https://github.com/tapl-org/tapl/issues).
> - It is not an officially supported Google product.


TAPL is inspired by lambda calculus and the principle that the same computational techniques apply to both type and term layers. The project is devoted to and named after Benjamin C. Pierce's book ["Types and Programming Languages"](https://www.cis.upenn.edu/~bcpierce/tapl/).

## How TAPL works
As a compiler frontend, TAPL's primary role is to parse source code and generate an Intermediate Representation (IR) for a backend. Currently, TAPL uses Python's Abstract Syntax Tree (AST) as its backend IR.
The compilation process is unique: for each source file, TAPL generates two Python files:

- *An untyped code file* (e.g., hello_world.py): This contains the direct, executable logic from your TAPL code.
- *A type-checker file* (e.g., hello_world1.py): This file contains all the type-checking logic.

To ensure type safety, the *type-checker file must be run first*. If it executes successfully, the untyped code is guaranteed to be type-safe.

For more details on TAPL's design and architecture:
- [Compilation process diagrams](https://docs.google.com/presentation/d/1I4Fu7Tp_QzyHC84u0REsFZcYi2i3ZvZPXiuHzasHywg/edit?usp=sharing)
- [TAPL calculus documentation](https://github.com/tapl-org/tapl/blob/main/doc/ground-rules.md)

## Getting started

Here is a simple "Hello World!" program in TAPL:
```
language pythonlike

print('Hello World!')
```

To run this code:

1. Clone the repository:
```
git clone https://github.com/tapl-org/tapl.git
```

2. Navigate to the Python package directory:
```
cd tapl/python/tapl-lang
```

3. Run the TAPL CLI using Hatch:
```
hatch run python ./src/tapl_lang/cli/tapl.py  ./src/examples/hello_world.tapl
```

This run the code. Behind the scene, This will generate two files:

- hello_world.py (untyped version of that code)
- hello_world1.py (typechecker for that code)

For **more example**, see [easy.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/easy.tapl)

### Creating and Extending Languages (tutorial)

Goal: add a Pipe operator `|>` to a Python-like TAPL language.

1. Implement the extension
- Create a language module (example name: pipeweaver_language.py) that registers a language named "pipeweaver" and implements parsing for the |> operator.

2. Example TAPL program using new pipeweaver language:
```
language pipeweaver

-2.5 |> abs |> round |> print
```

3. Compile and type-check
- Run the TAPL CLI:
```
hatch run python ./src/tapl_lang/cli/tapl.py ./src/examples/pipe.tapl
```
This generates two files:
- [`pipe1.py`](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/pipe1.py) — type-checker
- []`pipe.py`](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/pipe.py)  — untyped/executable code


Notes
- See the repository file [pipeweaver_language.py](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/tapl_language/pipeweaver/pipeweaver_language.py) for the implementation details and how the parser/transformer registers the operator and type rules.
- Inspect the generated pipe1.py to understand how TAPL emits type-checking code and pipe.py for the runtime translation.

### Implementing Dependent Types

Coming soon: a codelab demonstrating how to implement `concat` — a function that concatenates two fixed-length arrays and returns an array whose type reflects the sum of their lengths.

## Community

join the conversation on our main community platforms:
- [Official Discord Server](https://discord.gg/7N5Gp85hAy).
- [Github Discussions](https://github.com/tapl-org/tapl/discussions)

## Contributing
We welcome and encourage contributions from everyone! Whether it's a small typo fix, a new compiler feature, or a bug report, your help is valued. TAPL is committed to maintaining a welcoming and inclusive environment where all contributors can participate.


## Future Project Goals
- Transpile to C language
- Use a lightweight, Lua-like interpreter as a backend
- Use LLVM/WASM as a backend
