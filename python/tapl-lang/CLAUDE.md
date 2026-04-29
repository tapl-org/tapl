# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
hatch run full-check          # run type check, fmt, and tests (the canonical pre-commit check)
hatch run types:check         # mypy type checking only
hatch fmt                     # ruff lint + format
hatch test                    # run all tests
hatch test tests/path/to/test_file.py::test_name   # run a single test
```

The project uses [hatch](https://hatch.pypa.io/) as the build/env manager. Tests require the `hatch-test` environment (installed automatically by `hatch test`).

## Architecture

TAPL is a typed language that compiles `.tapl` source files into multiple parallel Python files — one per **layer** — and then executes them in order.

### Compilation pipeline

```
.tapl source
    → Chunker       (core/chunker.py)       indentation-based block splitting
    → Language/Parser (core/language.py, core/parser.py)  grammar-driven parse → Term tree
    → LayerSeparator (core/syntax.py)       split unified tree into N per-layer trees
    → Python Backend (lib/python_backend.py) Term tree → Python ast.AST per layer
    → ast.unparse()                         emit Python source files
```

Entry point: `lib/compiler.py:compile_tapl()`. The CLI (`cli/tapl.py`) writes each layer to disk and runs them in reverse order (typecheck layer first, evaluate layer last).

### The two-layer model

Almost all TAPL programs produce exactly two layers:

| Layer | Index | Mode constant | Purpose |
|-------|-------|--------------|---------|
| Evaluate | 0 | `MODE_EVALUATE` | Normal runtime Python code |
| Typecheck | 1 | `MODE_TYPECHECK` | Type-checking code that runs as Python |

`MODE_SAFE = Layers([MODE_EVALUATE, MODE_TYPECHECK])` is the default mode for most user-facing constructs. `EVALUATE_ONLY:` / `TYPECHECK_ONLY:` block syntax lets you write code that appears only in one layer.

### Terms

`syntax.Term` (in `core/syntax.py`) is the base AST node. Every term must implement:
- `children()` — yields child Terms for tree traversal
- `separate(ls: LayerSeparator)` — splits this term into one Term per layer
- `unfold()` — optional desugaring; returns `self` by default, but higher-level terms return simpler terms

`lib/terms.py` defines all concrete terms, organized in three sections:
1. **Python AST Terms** — mirror `ast` module classes (`FunctionDef`, `If`, `Assign`, …)
2. **Untyped Terms** — extensions like `Select`, `Path`, `BranchTyping`
3. **Typed Terms** — dual-layer terms with a `mode` field (`TypedFunctionDef`, `TypedAssign`, `TypedIf`, …)

`python_backend.AstGenerator` generates Python `ast.AST` by visiting the term tree, calling `unfold()` when it encounters a term it doesn't handle directly.

### Type system at runtime

The typecheck layer executes as real Python code. Scope objects (`lib/scope.py`) hold variable types as regular Python attribute assignments; the `Scope` class intercepts attribute access to enforce subtype checks. `lib/kinds.py` defines the type lattice (`Union`, `Intersection`, `Any`, `Nothing`, `Function`, `Record`). `lib/tapl_typing.py` provides the runtime helpers injected into the typecheck layer (e.g. `create_scope`, `create_function`, `add_return_type`).

**`__sa` suffix convention**: fields with `__sa` are internal/system attributes on `Scope` and type objects, invisible to user code and skipped by `DynamicAttributeMixin`.

### Language plugins

The first line of a `.tapl` file must be `language <name>`. The compiler does `importlib.import_module(f'tapl_language.{name}')` to load the language. The only built-in language is `pythonlike` (`src/tapl_lang/pythonlike/`), which defines the grammar (`grammar.py`) and language class (`language.py`).

### Golden tests

`tests/tapl_lang/pythonlike/goldens/` contains `.tapl` source files alongside their expected outputs:
- `<name>.py` — approved evaluate-layer Python
- `<name>1.py` — approved typecheck-layer Python
- `<name>.output` — approved stdout/stderr from running both files

Tests use the [approvaltests](https://github.com/approvals/ApprovalTests.Python) library. When a golden file changes, the test fails with a diff; run `.approval_tests_temp/approve_all.py` to promote received outputs to approved. `goldens/` and `examples/` directories are excluded from ruff and pyright.
