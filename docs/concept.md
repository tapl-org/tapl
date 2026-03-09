# TAPL Concepts


This document explains the ideas behind TAPL and the design decisions that make it different from conventional approaches.

## Core Idea 1: The Type-Checker Is Not Fixed

* Conventional side: The type-checker is a dedicated phase hard-wired inside the compiler. It has its own separate logic, rules, and machinery. Users cannot modify or extend it.

* TAPL side: There is no built-in type-checker. Instead, TAPL compiles a .tapl file into two .py files: one that runs (evaluation layer) and one that checks types (type-checking layer). The type-checking layer is just a regular program that users can influence through type-level code (code that executes during type-checking). Because it's real executable code, types are not limited to simple labels — users can write arbitrary type-check logic.

## Core Idea 2: The Parser Is Not Fixed

* Conventional side: The parser/syntax is fixed inside the compiler. Users write programs in the language but cannot change or extend the language's syntax itself.

* TAPL side: Users can define new syntax, use it immediately in the same project, and share it as reusable language extensions. The parser is a pluggable PEG-based system where grammar rules can be added, reordered, or replaced by users.


## Compilation Pipeline

For each `.tapl` source file, the compiler produces two Python files as described above:

1. **The evaluation layer** (e.g., `hello_world.py`): executable runtime code.
2. **The type-checking layer** (e.g., `hello_world1.py`): type-checker code. If it executes without error, the evaluation layer is guaranteed to be type-safe.


The pipeline:

```
Source (a.tapl)
    |
    v
[Chunker] -- Splits source into indentation-based chunks
    |
    v
[Language Directive] -- First chunk: "language {language-name}"
    |
    v
[Language Module] -- Loaded dynamically: tapl_language.{language-name}.get_language()
    |
    v
[Parser] -- Grammar rules produce a syntax tree
    |
    v
[LayerSeparator] -- Splits the syntax tree into two layers
    |
    v
[Backend (Python AST)] -- Each layer is converted to a Python AST
    |
    v
Output: a.py (layer 0), a1.py (layer 1)
```

> **Note:** TAPL numbers layers from 0. Layer 0 is evaluation, layer 1 is type-checking. Since layer 0 is the primary output, the `0` is omitted by convention — so `a.tapl` produces `a.py` and `a1.py`.


## Summary

TAPL is not a fixed language but a framework. It provides a compiler whose core is minimal and generic. The only fixed requirements are: (1) a `language` directive, (2) a language module that provides a grammar and predefined headers, and (3) syntax nodes that know how to split themselves across layers. Everything else — syntax, type rules, built-in types — is defined by the user. See the [deep dive](deep-dive.md) for details on these mechanisms.
