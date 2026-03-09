# TAPL Concepts



> **Draft -- Work in Progress.** This document is not finished and may contain inconsistent or unreliable information. Last updated: February 27, 2026.

This document explains the ideas behind TAPL and the design decisions that make it different from conventional approaches.

## Core Idea 1: The Type-Checker Is Not Fixed

* Conventional side: The type-checker is a dedicated phase hard-wired inside the compiler. It has its own separate logic, rules, and machinery. Users cannot modify or extend it.

* TAPL side: There is no built-in type-checker. Instead, TAPL compiles a .tapl file into two .py files: one that runs (evaluation layer) and one that checks types (type-checking layer). The type-checking layer is just a regular program that users can influence through type-level code. Because it's real executable code, types are not limited to simple labels — users can write arbitrary type-chedck logic.

## Core Idea 2: The Parser Is Not Fixed

* Conventional side: The parser/syntax is fixed inside the compiler. Users write programs in the language but cannot change or extend the language's syntax itself.

* TAPL side: Users can define new syntax, use it immediately in the same project, and share it as reusable language extensions. The parser is a pluggable PEG-based system where grammar rules can be added, reordered, or replaced by users.


## How It Works

TAPL is grounded in two foundations: **[theta-calculus](theta-calculus.pdf)** and a **[PEG parser](https://en.wikipedia.org/wiki/Parsing_expression_grammar)**.

Theta-calculus provides the model used to implement TAPL's type-checking program generation, and the PEG parser provides a pluggable syntax system so users can define and adopt new syntax forms.


## Compilation Pipeline

For each `.tapl` source file, the compiler produces two Python files as mentioned before:

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

> **Note:** Why the `1` suffix? Internally, TAPL treats a program as having not just two but *n* layers, numbered starting from 0. Layer 0 is the evaluation layer, layer 1 is the type-checking layer, and so on. So `a.tapl` would technically produce `a0.py` and `a1.py`. Since the evaluation layer (index 0) is the primary output, the `0` is omitted by convention -- giving you `a.py` and `a1.py`.


# Summary

TAPL is not a fixed language but a framework. The `pythonlike` grammar is a reference implementation, not a standard. The compiler's only fixed requirements are: (1) a `language` directive, (2) a language module providing a grammar and predefined headers, and (3) syntax nodes that implement `separate()`. Everything else -- syntax, type rules, built-in types -- is defined by user.
