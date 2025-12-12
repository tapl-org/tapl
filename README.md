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
As a frontend framework, the core function of TAPL is to parse source code and generate IR for the backend language.
- Currently Tapl uses Python AST as the backend IR.
- The process involves generating two Python files: untyped version of the parsed code and a typechecker file. To ensure type safety, the typechecker file mut be run first. If it completes successfully, the untyped code is considered type-safe.
- [How TAPL compiles code](https://docs.google.com/presentation/d/1I4Fu7Tp_QzyHC84u0REsFZcYi2i3ZvZPXiuHzasHywg/edit?usp=sharing)

## Project status

Tapl is currently an experimental project. There is no working compiler or toolchain.

## Getting started

Simple Hello world programm
```
language pythonlike

print('Hello World!')
```

Clone this repo and run the following command to run it.
```
cd python/tapl-lang
hatch run python ./src/tapl_lang/cli/tapl.py  ./src/examples/hello_world.tapl
```

As you see it generates 2 files:
- hello_world.py (untyped version of that code)
- hello_world1.py (typechecker for that code)

Another example - [easy.tapl](https://github.com/tapl-org/tapl/blob/main/python/tapl-lang/src/examples/easy.tapl)

## Community

Our main community platforms:
- [Official Discord Server](https://discord.gg/7N5Gp85hAy).
- [Github Discussions](https://github.com/tapl-org/tapl/discussions)

## Contributing
We welcome contributions from everyone, whether it's a small typo fix, a new compiler feature, or reporting a bug. TAPL is committed to maintaining a welcoming and inclusive environment where all contributors can participate.


## Future Project Goals
- Transpile to C language
- Use Lua-like light interpreter as a backend
- Use LLVM/WASM as a backend
