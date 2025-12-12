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
> - There is no stable release yet, and it improves with every commit. Please report any issues via the Tapl Issue Tracker.
> - It is not an officially supported Google product.


## How TAPL works
As a compiler frontend, TAPL's primary role is to parse source code and generate an Intermediate Representation (IR) for a backend. Currently, TAPL uses Python's Abstract Syntax Tree (AST) as its backend IR.
The compilation process is unique: for each source file, TAPL generates two Python files:

- *An untyped code file* (e.g., hello_world.py): This contains the direct, executable logic from your TAPL code.
- *A type-checker file* (e.g., hello_world1.py): This file contains all the type-checking logic.

To ensure type safety, the *type-checker file must be run first*. If it executes successfully, the untyped code is guaranteed to be type-safe.

- The process involves generating two Python files: untyped version of the parsed code and a typechecker file. To ensure type safety, the typechecker file mut be run first. If it completes successfully, the untyped code is considered type-safe.
- For a high-level view of the compilation process, see the diagrams: [How TAPL compiles code](https://docs.google.com/presentation/d/1I4Fu7Tp_QzyHC84u0REsFZcYi2i3ZvZPXiuHzasHywg/edit?usp=sharing)

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

This run the code. Behind the scene, This will generate two files: hello_world.py (the untyped code) and hello_world1.py (the type checker).


As you see it generates 2 files:
- hello_world.py (untyped version of that code)
- hello_world1.py (typechecker for that code)

For more example, see [easy.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/easy.tapl)

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
