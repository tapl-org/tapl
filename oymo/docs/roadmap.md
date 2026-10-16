# Roadmap: from oymomo to a production Tenon toolchain

Status: **proposed**; 0 of 36 releases before 1.0.

This is the top-level order of work. It does not design anything: designs live in the
plans ([plans.md](plans.md)), mostly in the two roadmaps
[plan_c_interop.md](plan_c_interop.md) and [plan_tenon.md](plan_tenon.md). This file
cuts those plans into **releases**, so that work lands incrementally and **every
release is a toolchain someone can install and use**, not a half-built pipeline.
Releases are **as small as possible**: each adds one capability, so each lands soon
and each can be tried on its own.

The releases come in three stages:

1. **Stage A — the bootstrap set, in Python.** Only what is needed to write a compiler
   in Tenon: Tenon layer 0 as early as possible, BANF removed, then native binaries, tagged unions,
   layer 1 (types), imports between files, function pointers and a small standard
   library.
2. **Stage B — bootstrap.** oymo is rewritten in Tenon, builds itself, and the Python
   compiler is frozen. From here the compiler writes LLVM IR as text and hands it to
   `clang`: no llvmlite, no Python in the compiler.
3. **Stage C — everything else, in the Tenon compiler**: C calling Tenon, the Python
   package and language authors' API, the full C ABI, C headers, debug info,
   optimization, safety, threads, distribution, then 1.0.

## Releases

### [Stage A — the bootstrap set, in Python](#stage-a--the-bootstrap-set-in-python)

- [ ] [0.1](#01--oymomo-to-llvm-ir-from-the-command-line) — oymomo to LLVM IR, from the command line
- [ ] [0.2](#02--confluence-reduction-order-doesnt-change-the-result) — confluence: reduction order doesn't change the result
- [ ] [0.3](#03--tenon-layer-0-first-part-functions-and-integers) — Tenon layer 0, first part: functions and integers
- [ ] [0.4](#04--banf-removed) — BANF removed
- [ ] [0.5](#05--tenon-layer-0-second-part-memory-and-calls-to-c) — Tenon layer 0, second part: memory and calls to C
- [ ] [0.6](#06--native-binaries) — native binaries
- [ ] [0.7](#07--enums-and-tagged-unions) — enums and tagged unions
- [ ] [0.8](#08--tenon-layer-1-types) — Tenon layer 1, types
- [ ] [0.9](#09--module-interfaces-and-imports-between-files) — module interfaces and imports between files
- [ ] [0.10](#010--function-pointers-and-callbacks) — function pointers and callbacks
- [ ] [0.11](#011--the-bootstrap-standard-library-and-oymo-test) — the bootstrap standard library, and `oymo test`

### [Stage B — bootstrap](#stage-b--bootstrap)

- [ ] [0.12](#012--oymo-in-tenon-first-part-oymomo-to-llvm-ir) — oymo in Tenon, first part: oymomo to LLVM IR
- [ ] [0.13](#013--oymo-in-tenon-second-part-the-tenon-frontend) — oymo in Tenon, second part: the Tenon frontend
- [ ] [0.14](#014--self-hosting) — self-hosting

### [Stage C — everything else, in the Tenon compiler](#stage-c--everything-else-in-the-tenon-compiler)

Single-threaded:

- [ ] [0.15](#015--c-calls-tenon-exports-generated-headers-libraries) — C calls Tenon: exports, generated headers, libraries
- [ ] [0.16](#016--the-c-api-and-the-python-package) — the C API and the Python package
- [ ] [0.17](#017--the-language-registry-and-the-oymomo-api) — the language registry and the oymomo API
- [ ] [0.18](#018--the-tenon-api-for-language-authors) — the Tenon API for language authors
- [ ] [0.19](#019--build-system-integration) — build-system integration
- [ ] [0.20](#020--floats) — floats
- [ ] [0.21](#021--by-value-structs-the-c-abi-for-x86-64) — by-value structs: the C ABI for x86-64
- [ ] [0.22](#022--varargs) — varargs
- [ ] [0.23](#023--volatile-and-inline-asm) — `volatile` and inline asm
- [ ] [0.24](#024--c-headers-to-oymomo-declarations) — C headers to oymomo declarations
- [ ] [0.25](#025--c-headers-in-tenon) — C headers in Tenon
- [ ] [0.26](#026--debug-info) — debug info
- [ ] [0.27](#027--optimization-and-lto) — optimization and LTO
- [ ] [0.28](#028--safety-checks-and-sanitizers) — safety checks and sanitizers
- [ ] [0.29](#029--separate-compilation) — separate compilation
- [ ] [0.30](#030--the-full-standard-library) — the full standard library
- [ ] [0.31](#031--the-rest-of-c) — the rest of C
- [ ] [0.32](#032--developer-tools) — developer tools

Multi-threaded:

- [ ] [0.33](#033--atomics) — atomics
- [ ] [0.34](#034--thread-local-storage) — thread-local storage
- [ ] [0.35](#035--threads-in-the-standard-library) — threads in the standard library

Finishing:

- [ ] [0.36](#036--distribution) — distribution
- [ ] [1.0](#10--production) — production

### After 1.0

- [ ] [1.x](#1x--more-targets) — more targets: Linux AArch64, macOS AArch64, Windows x86-64
- [ ] [After 1.0](#after-10--oymo-translate-c) — `oymo translate-c`: C source to Tenon
- [ ] [After 1.0](#after-10--spindle-in-tenon) — Spindle, the embeddable VM, written in Tenon

## Goal

**Anyone can write Tenon, or their own language, and it mixes with C in one program
with no glue code.** The mixing is oymomo's job ([plan_c_interop.md](plan_c_interop.md)):
whatever lowers to oymomo gets C interop by generating oymomo.

### One package, three ways in

There is **one package, `oymo`**, with one version number. It contains oymomo, Tenon
and the toolchain, and is used in three ways:

| Who | Writes | Gets |
|---|---|---|
| A Tenon user | Tenon source | types (layer 1), C headers, binaries and libraries |
| A language author, high level | a frontend that **lowers to Tenon** | all of Tenon's: a type checker as code, C headers, C ABI |
| A language author, low level | a frontend that **lowers to oymomo** | full control of the code; C ABI, linking, `.h` generation |

A language author's frontend is **their own library**, in their own package and
repository, that depends on `oymo` and uses only its **public API**: nothing of theirs
lives in `oymo`. TAPL's Python languages are the model: a language is a library, and
the toolchain is shared.

From Stage B on, the compiler is a native program written in Tenon. The `oymo` Python
package (from 0.16) ships it with a Python binding over its C API, so language authors
still write their frontends in Python.

```
oymo build app.oymo util.c -o app         # `language tenon` and C, one command, one binary
oymo build lib.oymo --emit=h,a,so         # a Tenon library C can use unchanged
oymo build gen.oymo -o app                 # `language oymomo`, from a generator
```

### One file extension, a `language` header

Every source file is a **`.oymo` file**, whatever its language. Its first line names
the language, and the rest of the file is in that language (the golden tests already
start with `language oymomo`):

```
language tenon
...
```

- `oymomo` and `tenon` are built into the compiler. Any other name is looked up in the
  installed Python packages: a language author's package registers its frontend under
  the entry point group `oymo.languages` (`calc = "calc_lang:frontend"`), so
  `pip install calc-lang` is enough for `oymo build hello.oymo` to build a
  `language calc` file (from 0.17).
- A frontend is a Python function from source text to a tree, an oymomo tree or a
  Tenon tree (the two lowering targets), with source locations. The tree crosses to
  the native compiler in a serialized form that keeps the locations.
- So a **mixed build is one command**: `oymo build a.oymo b.oymo c.c`, where `a` is
  `language tenon`, `b` is `language calc` and `c.c` is C, links into one binary.
- An unknown name is an error that says which package to install, if known, and lists
  the installed languages. The standalone binary (0.36), with no Python, builds the
  built-in languages only.

```python
# a language author's library, in its own package
import oymo.tenon, oymo.build
tree = my_lang_to_tenon(parse(source))          # or: my_lang_to_oymomo(...)
oymo.build.executable(tree, c_files=['util.c'], output='app')
```

```mermaid
flowchart LR
  tenon["Tenon source"] --> fe["Tenon frontend"]
  hi["your language, high level (Python)"] -- "Tenon API, serialized tree" --> fe
  hdr["C headers"] --> imp["c_import (libclang)"] --> fe
  fe --> o["oymomo"]
  lo["your language, low level (Python)"] -- "oymomo API, serialized tree" --> o
  o --> ll["LLVM IR text"] --> clang["clang"] --> obj[".o"]
  obj --> link["cc / ld"]
  cobj["C .o / .a / .so"] --> link
  link --> out["binary, .a, .so"]
  o --> h["generated .h"]
```

### The public API

From 0.16, each release adds to a **public API**: the Python modules a language author
may import. Every other module is internal and may change in any release. The API has
a layer for each way in:

- **oymomo API**: build oymomo terms (or give oymomo text), check them, and get errors
  as data, with locations.
- **Tenon API**: build a Tenon syntax tree (or give Tenon text), with the source
  locations of the author's language attached, so a layer-1 error points at *their*
  source, not at generated Tenon.
- **Build API**: target, emit (`.ll`, `.o`, `.a`, `.so`, `.h`, binary), link with C
  files and libraries. The CLI is a thin layer over it.
- **C API**: `c_import`, giving `CDecl(form, ctype)` (from 0.24).

## Rules for every release

A release is cut only when all of these hold:

1. **Installable**: in Stage A, `pip install oymo` (the Python compiler); in Stage B,
   built from the repository with `clang` alone (the seed, 0.14); from 0.16,
   `pip install oymo` again (the native compiler with its Python binding); from 0.36
   also a standalone binary.
2. **Usable alone**: a README section shows a real task done with only this release.
3. **End-to-end tests**: each milestone below is a test in CI that builds and runs the
   program (in the JIT before 0.6, as a binary from 0.6), not only a golden `.ll` file.
4. **The API is tested from outside** (from 0.17): an example language lives in its own
   package (`examples/<name>/`, with its own `pyproject.toml`), installs `oymo` as a
   dependency, imports only the public API, and is built and run in CI. If an example
   needs an internal module, the API is missing something.
5. **Errors, not crashes**: input the release does not support yet gets a message that
   names the missing feature, never a crash or a traceback.
6. **Green**: the full check passes (`hatch run full-check` in Stage A, the Tenon
   compiler's own test suite from Stage B); the plans it closes are moved to
   [implemented/](implemented/).

Before 1.0 a release may break the oymomo syntax, the Tenon syntax, the public API or
the CLI; its notes say how to migrate. From 1.0 on, all four are stable
([1.0](#10--production)). From 0.14 a Tenon syntax change also means changing the
compiler's own source, so Tenon's syntax is decided with care in 0.3–0.8.

## Repository layout

The Tenon-written oymo will move to **its own repository**, named `oymo`. So everything
it needs lives in **one self-contained folder** from the first day it exists, and the
move is one command.

At 0.11, today's `oymo/` folder (the Python compiler) is renamed **`oymo-py/`**, and a
new **`oymo/`** is created for the product:

```
tapl/
  oymo-py/               the Python compiler (Stage A), removed after 0.14
    src/oymo/, tests/, pyproject.toml, docs/ (until 0.14)
  oymo/                  everything the new repository holds:
    README.md, LICENSE
    lib/                 Tenon's standard library (0.11)
    tests/goldens/       moved here from oymo-py (0.11): `.oymo` inputs and expected
                         outputs, run against both compilers in Stage B
    compiler/            the compiler in Tenon (0.12), mirroring oymo-py/src/oymo:
      core/                PEG engine
      oymomo/              parser, reduction, shape, translation
      ir/                  the IR builder (text first; the LLVM C API later)
      tenon/               the Tenon frontend, both layers
      driver/              the `oymo` command
    bootstrap/oymo.ll    the seed (0.14)
    build.sh             builds from the seed with `clang` alone (0.14)
    docs/                roadmap, plans and notes, moved from oymo-py (0.14)
    python/              the Python package (0.16): pyproject.toml, src/oymo/
    examples/calc/       the example language, its own package (0.17)
```

- **One rule: nothing inside `oymo/` refers to a path outside it.** Dependencies go one
  way: during Stages A and B the Python compiler in `oymo-py/` reads
  `oymo/tests/goldens/` and builds `oymo/lib/` and `oymo/compiler/`; nothing in
  `oymo/` reaches back into `oymo-py/`. CI checks it by building and testing a copy of
  `oymo/` alone.
- **`compiler/` mirrors `oymo-py/src/oymo/`** (`core/`, `oymomo/`, `tenon/`), so each
  Python module has an obvious Tenon counterpart and the port is reviewed file by file.
- **New tests are goldens or `oymo test` files**, which both compilers run; tests
  written in Python stay with the Python compiler.
- **The docs move at 0.14.** They describe the Python code today (notes.md links to
  its files), so they stay in `oymo-py/docs/` until the Python compiler is retired;
  at 0.14 they move to `oymo/docs/`, with those links pointing at `compiler/`.
- **The export, after 0.14**: `git subtree split --prefix=oymo` (or `git filter-repo`)
  makes the new repository with the folder's full history. The CI workflow, which
  must sit at the tapl root until then, moves to the new repository's `.github/`.
  `oymo-py/` is then deleted from tapl, with a git tag (`oymo-py-final`) kept.

## Stage A — the bootstrap set, in Python

What a compiler written in Tenon needs, and nothing more. The test for each feature:
does the rewrite of oymo (0.12, 0.13) need it? Floats, by-value structs at the C
boundary, varargs, C headers, debug info and threads don't, so they wait for Stage C.
The Python compiler uses llvmlite for these releases only, for what it already does.

## 0.1 — oymomo to LLVM IR, from the command line

**Who uses it:** a language author who wants a simple IR above LLVM. Most of the
pipeline exists; this release puts a command in front of it.

- `oymo emit-llvm a.oymo -o a.ll`, `oymo check a.oymo` (parse, reduce, verify BANF,
  print stuck terms; from 0.4, check the shaped program), `oymo fmt` (the printer), `oymo run --jit a.oymo` (llvmlite
  MCJIT runs `main` and prints its result; Tenon runs in it from 0.3, and layer 1 from
  0.8).
- Errors with file, line and column for parse errors and stuck terms.

**Milestone:** `oymo run --jit fact.oymo` prints `120`.

## 0.2 — confluence: reduction order doesn't change the result

**Who uses it:** everyone who generates oymomo: what it means no longer depends on how
oymo happens to reduce it.

| From | Work |
|---|---|
| [plan_confluence.md](plan_confluence.md) 1–4 | a full-β reference reducer and a confluence test; a form on a form is replaced; built-in rules commute with reduction; `shape` is a reduction |

**Tenon does not start before this release**: both its layers lower to oymomo, and so
does every language author's code. It also settles oymomo's shape, so BANF can be
removed next (0.4).

**Milestone:** the confluence test passes on every golden program and on generated
terms, with the known counterexample fixed.

## 0.3 — Tenon layer 0, first part: functions and integers

**Who uses it:** anyone who wants to try Tenon. The first release for people who are
not compiler writers.

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) Phase 0 | syntax (from a survey of Zig, C3, Odin, Hare and Jai, pros and cons per topic), memory model and undefined behaviour: decided |
| [plan_tenon.md](plan_tenon.md) Phase 1 | grammar on the PEG engine and lowering to oymomo for functions, integers, locals, `if`, loops, `switch`; `language tenon` built in |

Programs run with `oymo run --jit`; there are no native binaries yet. Layer 0 has forms
but no type checker: a mistake gives wrong code, as in C without warnings. The release
notes say so.

**Milestone:** `fact`, `fib` and `gcd` written in Tenon run with `oymo run --jit`.

## 0.4 — BANF removed

**Who uses it:** nobody sees a change; the compiler gets simpler before anything is
built on it, and before it is rewritten.

| From | Work |
|---|---|
| [todo.md](todo.md) | oymomo translates to LLVM IR directly and BANF goes; BANF's checks move into that translation and into `shape` |
| new | **the IR builder**: the translation calls a small builder interface (new module, new function, new block, add instruction, add global), never LLVM or text directly. Its first implementation sits on llvmlite's `ir` module, which builds IR text; the Tenon compiler ports the interface with a text implementation (0.12) |

Why here: confluence (0.2) has settled oymomo's shape, and 0.3 added no oymomo
feature. Every oymomo feature after this (`void`, null, casts, `memcpy`, unions,
function pointers) is built once, in the direct translation, and the rewrite (0.12,
0.13) ports that translation as it is, **with no change of behaviour or logic**.

**Milestone:** every test and example gives the same output as in 0.3, with BANF's code
deleted.

## 0.5 — Tenon layer 0, second part: memory and calls to C

**Who uses it:** the same users, now with pointers, structs and libc.

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) Phase 1 | pointers, structs, arrays, string literals |
| [plan_c_interop.md](plan_c_interop.md) 1.2 | `void` functions |
| [plan_memory_advanced.md](plan_memory_advanced.md) 1–3 | pointer comparison, `'null' {}`, pointer casts, `'memcpy'` / `'memset'` |
| new | `extern` declarations written by hand, to call C; the JIT finds libc's symbols in the running process |

Calls go one way, Tenon to C, and are first-order.

**Milestones:** hello world with `puts`; a linked list with `malloc` / `free`; both in
the JIT.

## 0.6 — native binaries

**Who uses it:** Tenon and oymomo users, now shipping executables.

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) Phase 2 | real `Target`, `.o` from `TargetMachine`, link with `cc`, `oymo build`, `-c` |
| [plan_c_interop.md](plan_c_interop.md) 3.1 | `zeroext` / `signext` on small ints, enough for most of libc |
| new | `oymo build app.oymo util.c`: `.c` files in the same command are compiled with `cc`, and Tenon calls them |

**Milestones:** `oymo build hello.oymo util.c -o hello` gives a binary that runs on
Linux x86-64; a Tenon program reads a file named on its command line and writes it
back reversed.

## 0.7 — enums and tagged unions

**Who uses it:** anyone modelling data with variants; the compiler's syntax trees
(0.12) need them.

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) Phase 1 | enums; tagged unions and a `switch` that matches on the tag and binds the payload, lowered to oymomo structs and switch |
| [plan_c_interop.md](plan_c_interop.md) 1.5 | the decision on unions in oymomo, as far as tagged unions need it |

**Milestone:** an expression evaluator in Tenon: a tagged union for the syntax tree, a
recursive `eval` over it.

## 0.8 — Tenon layer 1, types

**Who uses it:** Tenon users, now with type errors and memory-safety errors at build
time. A compiler of the size of oymo is not written without them.

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) Phase 2 | layer 1 lowered to a second oymomo program, JIT-run at compile time (0.1's `--jit`) |
| [plan_tenon.md](plan_tenon.md) 0.6 | **dependent types** (`Array(u8, n)`, `Index(n)`, bounds facts from tests) and **substructural types** (`Own(T, A)`, second-class borrows): use after free, double free, leaks and unproven indexing are layer-1 errors |
| [plan_metadata.md](plan_metadata.md) 1–3 | source locations kept through reduction, so a layer-1 error points at the source |

Why in Stage A: the compiler (0.12, 0.13) is the largest Tenon program, and adding
ownership to tens of thousands of lines afterwards is far harder than writing them
with it.

**Milestones:** `puts(42)` with a hand-written `extern` stops the build with
`app.oymo:3:6: expected Ptr(c_char), got Int32`; the expression evaluator of 0.7
type-checks, with its tree nodes as `Own` values; a use after `free` in the linked
list of 0.5 stops the build.

## 0.9 — module interfaces and imports between files

**Who uses it:** anyone whose program outgrows one file, as the compiler will.

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) Phase 2 | **module interfaces**: each exported name as a pair like `c_import`'s, the **form** (layer 0, what oymomo needs to call it) and the **layer-1 type**, which appears here because types appear in layer 1. Other languages on oymo read and write them from 0.18 |
| new | **imports between files**, through those interfaces: a program in several `.oymo` files, built in one command (separate compilation comes in 0.29) |

**Milestone:** a program of ten Tenon files, importing each other; calling an imported
function with the wrong type is a layer-1 error.

## 0.10 — function pointers and callbacks

**Who uses it:** Tenon programs with tables of functions (the compiler's parser and
passes), and programs that pass callbacks to C.

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) 1.6 | function pointers and indirect calls |
| [plan_tenon.md](plan_tenon.md) Phase 3 | Tenon function values, lowering to function pointers; a closure crosses to C as code plus a `void *` environment, written by hand ([Non-goals](#non-goals)) |

**Milestone:** a Tenon function is passed to `qsort` and to `qsort_r` with a `void *`
environment.

## 0.11 — the bootstrap standard library, and `oymo test`

**Who uses it:** anyone writing a real program in Tenon; first of all the rewrite of
oymo.

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) Phase 5 | the part of the standard library a compiler needs, written in Tenon over libc: growable arrays, a hash map, strings and a string builder, number formatting (no `printf`: varargs come in 0.22), file I/O, running a process (to call `clang`), and the allocator interface with an arena and the libc allocator |
| new | the [repository layout](#repository-layout) begins: `oymo/` renamed `oymo-py/`; the new `oymo/` holds `lib/` (this library) and `tests/goldens/`, moved from `oymo-py` |
| new | `oymo test`: test functions in `.oymo` files, run and reported, as `zig test` does |

**Milestone:** a word-count program over a large file, with a hash map and an arena;
its tests run with `oymo test`.

## Stage B — bootstrap

oymo is rewritten in Tenon, compiled by the Python compiler, then by itself. At the
end of Stage B the Python compiler is frozen and the product no longer needs Python or
llvmlite.

## 0.12 — oymo in Tenon, first part: oymomo to LLVM IR

**Who uses it:** oymomo users: the same language, now compiled by a native program.

| From | Work |
|---|---|
| new | in `oymo/compiler/` ([layout](#repository-layout)): the oymomo pipeline in Tenon, ported as it is: parser, reduction, `shape`, and the direct translation to LLVM IR (0.4) with its IR builder. The builder's first implementation writes `.ll` text, which `clang` compiles and links. There is no BANF to port |
| new | the confluence test of 0.2 and every oymomo golden test, run against the Tenon compiler |

**Milestone:** the Tenon-written compiler, built by the Python compiler, gives the same
program output as the Python compiler on every oymomo test.

## 0.13 — oymo in Tenon, second part: the Tenon frontend

**Who uses it:** Tenon users: the same language, now compiled by a native program.

| From | Work |
|---|---|
| new | the PEG engine, the Tenon grammar and the lowering of both layers, in Tenon |
| new | layer 1 without a JIT: the layer-1 program is compiled to a native program and run as a subprocess; its errors come back with their locations |

**Milestone:** the Tenon-written compiler, built by the Python compiler, gives the same
output as the Python compiler on every Tenon test, layer-1 errors included.

## 0.14 — self-hosting

**Who uses it:** everyone: the compiler is now one native program, built from the
repository with `clang` alone.

| From | Work |
|---|---|
| new | **three-stage build**: the compiler built by the Python compiler (stage 1) builds itself (stage 2), which builds itself again (stage 3); stages 2 and 3 must be byte-identical |
| new | **the seed**: the compiler's own LLVM IR, committed as `oymo/bootstrap/oymo.ll`. Building from scratch is `clang bootstrap/oymo.ll -o oymo-seed`, then the seed builds today's source. The seed is regenerated when the compiler's source starts using a feature the old seed doesn't know |
| new | the Python compiler is frozen; llvmlite is no longer a dependency |
| new | the docs move from `oymo-py/docs/` to `oymo/docs/`; `build.sh` builds from the seed |
| new | **the export**: `oymo/` becomes its own repository, with its history; `oymo-py/` is removed from tapl, tagged `oymo-py-final` ([layout](#repository-layout)) |

**Milestone:** on a machine with `clang` and no Python, a fresh clone of the new
repository builds from the seed, builds itself twice to identical output, and passes
every test.

## Stage C — everything else, in the Tenon compiler

Every remaining feature is added to the Tenon compiler only. Releases are grouped:
single-threaded programs first (0.15–0.32), then multi-threaded ones (0.33–0.35), then
finishing.

## 0.15 — C calls Tenon: exports, generated headers, libraries

**Who uses it:** someone who wants a fast routine in a C program, written in Tenon or
generated as oymomo.

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) 1.8 | linkage: exported vs internal; C name ≠ label |
| [plan_c_interop.md](plan_c_interop.md) Phase 4 | exported data, generated `.h`, `.a` and `.so` |
| [plan_tenon.md](plan_tenon.md) Phase 3 | `export` on a function or a global |
| new | the generated `.h` is made from the module interface (0.9) and uses its layer-1 types where there are any: `unsigned`, `const char *` and named structs, which oymomo's forms alone can't tell from `int` and `void *` |

Scalars and pointers only at the C boundary; a by-value struct there is an error that
says "pass a pointer" until 0.21.

**Milestone:** a C `main` calls a Tenon library through its generated header, and the
header reads as a hand-written one would.

## 0.16 — the C API and the Python package

**Who uses it:** Python users and language authors, who get `pip install oymo` back,
now with the native compiler inside.

| From | Work |
|---|---|
| new | the compiler exports a C API (with 0.15's exports and generated header): build, emit, check, errors as data |
| new | the `oymo` Python package, in `oymo/python/`: a wheel with the native compiler and a Python binding over its C API; the `oymo` command is its driver |
| new | the build API in Python: `executable`, `object_file`, `static_library`, `shared_library`, `header`, `emit_llvm` |
| new | the serialized tree format, with source locations, in which a Python frontend's tree crosses to the compiler |

**Milestone:** `pip install oymo` on a fresh machine, then `oymo build hello.oymo` and
a Python script that builds the same program through the build API.

## 0.17 — the language registry and the oymomo API

**Who uses it:** a language author who generates oymomo from Python.

| From | Work |
|---|---|
| new | the oymomo API: build oymomo terms in Python, check them, errors as data |
| new | the `language` header resolved by the driver: `oymomo` and `tenon` built in, the `oymo.languages` entry point group for everything else |
| new | **example language `calc`** in `oymo/examples/calc/`: arithmetic expressions, lowered to oymomo terms through the public API, registered as `language calc` |

**Milestone:** with `calc` installed from its own package, `oymo build one.oymo` on
`language calc` / `1 + 2 * 3` gives a binary that prints `7`.

## 0.18 — the Tenon API for language authors

**Who uses it:** language authors who want a higher target than oymomo, with types.

| From | Work |
|---|---|
| new | the Tenon API: syntax tree classes and their constructors are public; a tree carries the source locations of the author's files; layer-1 errors as data |
| new | `calc` gets a second backend that lowers to Tenon |
| [plan_tenon.md](plan_tenon.md) Phase 2 | module interfaces across languages: a frontend that lowers to Tenon gives forms and types; one that lowers to oymomo gives forms only, and its names are unchecked in layer 1 |

**Milestones:** a type error in a `calc` program lowered to Tenon is reported at the
line and column of its `language calc` file; a Tenon file imports a function from a
`language calc` file, and calling it with the wrong type is a layer-1 error.

## 0.19 — build-system integration

**Who uses it:** C projects that add Tenon files to an existing build.

| From | Work |
|---|---|
| new | flags so Make and CMake call `oymo` as they call `cc`: `-c`, `-o`, `-MD` / `-MF` dependency files, and an entry in `compile_commands.json` |
| new | finding C libraries: `-I`, `-L`, `-l` and `oymo build --pkg-config sdl2` |

**Milestone:** a Makefile builds a mixed C and Tenon project with `oymo -c` in place of
`cc -c`, rebuilds only what changed, and links SDL found through pkg-config.

## 0.20 — floats

| From | Work |
|---|---|
| [plan_floats.md](plan_floats.md) 1–5 | `'f32'`, `'f64'`, arithmetic, comparisons, conversions, exact intrinsics |

**Milestone:** a Tenon program calls `sqrt` and `pow` from libm and prints the result.

## 0.21 — by-value structs: the C ABI for x86-64

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) 1.5 | unions as C has them |
| [plan_c_interop.md](plan_c_interop.md) Phase 3.2–3.3 | by-value structs and `sret`, on both sides of a call, for x86-64 SysV (other targets in 1.x) |
| [plan_c_interop.md](plan_c_interop.md) 3.5 | differential tests against clang, both directions |

**Milestone (drop-in):** a small C library rewritten in Tenon passes its unchanged C
test suite.

## 0.22 — varargs

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) 1.7, 3.4 | varargs declarations and calls, default argument promotions, `va_list` for definitions |

**Milestone:** `printf("%d %f %s\n", ...)` from Tenon; a Tenon function with `...`
called from C.

## 0.23 — `volatile` and inline asm

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) 1.10 | a `volatile` flag on `'load'` / `'store'`, and `'asm'`, each as LLVM has it |

**Milestone:** a signal handler sets a `volatile` flag that the main loop reads; a
function uses `rdtsc` through inline asm.

## 0.24 — C headers to oymomo declarations

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) Phase 5 | `c_import`, calling libclang's C API from the Tenon compiler: `CDecl(form, ctype)`, public as the C API (in Python through the binding) |
| new | `oymo import-c stdio.h` prints oymomo declarations |

**Milestone:** `calc` calls `sqrt` from `<math.h>` through `c_import`, with no
hand-written declaration.

## 0.25 — C headers in Tenon

**Who uses it:** every Tenon user; this is when "seamless" is true from the user's
seat.

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) Phase 4 | header import in Tenon, forms to layer 0, ctypes to layer 1 |
| [plan_metadata.md](plan_metadata.md) 6 | origins of imported names in error messages |
| new | the compiler's own hand-written `extern`s for libc and libclang replaced by header imports |

**Milestone:** a Tenon program imports `<stdio.h>`, `<string.h>` and `<math.h>`, with
no `extern` written by hand, and `puts(42)` is a layer-1 error.

## 0.26 — debug info

| From | Work |
|---|---|
| [plan_metadata.md](plan_metadata.md) 4–5 | DWARF in the emitted LLVM IR, so `gdb` / `lldb` step through the source, Tenon's or a language author's |

**Milestone:** `gdb` sets a breakpoint in a Tenon function, steps line by line and
prints locals, in a program mixed with C.

## 0.27 — optimization and LTO

| From | Work |
|---|---|
| new | `-O0..-O3`, passed to `clang` |
| [plan_memory_advanced.md](plan_memory_advanced.md) 5 | `noalias` |
| new | **LTO across C and Tenon**: both compile to LLVM, so `oymo -c -flto` emits LLVM bitcode and clang's `-flto` link inlines C into Tenon and back. Few languages offer this cheaply, and it strengthens the drop-in story |

**Milestone:** a call from C into a small Tenon function is inlined under `-flto`
(checked in the disassembly).

## 0.28 — safety checks and sanitizers

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) 0.5 | the checked build mode: traps on overflow, out-of-bounds and null, with the source location; out-of-bounds checks only where layer 1 (0.8) proved nothing |
| new | **sanitizers**: `-fsanitize=address,undefined` on a mixed C and Tenon program, as a production C toolchain is expected to (TSan comes with threads, 0.35) |

**Milestone:** an out-of-bounds write in Tenon is caught by the checked build and, in
an optimized build, by ASan, both with the Tenon source line.

## 0.29 — separate compilation

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) Phase 6 | modules and separate compilation, on top of 0.9's interfaces |
| new | incremental builds: only changed files and their dependents are rebuilt |

**Milestone:** changing one function body in the compiler's own source rebuilds one
object.

## 0.30 — the full standard library

| From | Work |
|---|---|
| [plan_tenon.md](plan_tenon.md) Phase 5 | the rest of the single-threaded standard library on top of 0.11's: formatted I/O, more containers, a pool allocator, and a garbage-collecting allocator over the Boehm collector |

**Milestone:** the same program runs with the arena allocator and with the Boehm
allocator, changed in one line.

## 0.31 — the rest of C

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) open question 4 | `static inline` functions and function-like macros in headers |

**Milestone:** a program calls a `static inline` function and uses a function-like
macro from a system header.

## 0.32 — developer tools

| From | Work |
|---|---|
| new | formatter (`oymo fmt` for Tenon), a language server (go to definition, errors in the editor), syntax highlighting |

**Milestone:** an editor shows layer-1 errors as you type, and goes to the definition
of a name imported from a C header.

## 0.33 — atomics

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) 1.10 | `'atomicrmw'`, `'cmpxchg'`, `'fence'`, atomic `'load'` / `'store'` with a memory ordering, each as LLVM has it; Tenon syntax for them; C11 `_Atomic` types from headers |

**Milestone:** a Tenon program with two threads (pthreads, from `<pthread.h>`) shares a
counter through atomics and always gets the right total.

## 0.34 — thread-local storage

| From | Work |
|---|---|
| [plan_c_interop.md](plan_c_interop.md) Phase 6 | thread-local globals in oymomo (LLVM `thread_local`); Tenon syntax for them; `_Thread_local` variables imported from and exported to C |

**Milestone:** each of four threads counts in its own thread-local variable; a C
library's `_Thread_local` variable is read from Tenon.

## 0.35 — threads in the standard library

| From | Work |
|---|---|
| new | a thread API in the standard library over pthreads: threads, mutexes, condition variables |
| new | thread-safe allocators: the libc allocator, per-thread arenas, and the Boehm allocator in its threaded mode |
| new | **TSan**: `-fsanitize=thread` on a mixed C and Tenon program |

**Milestone:** a parallel program (a worker pool over a queue) runs clean under TSan.

## 0.36 — distribution

| From | Work |
|---|---|
| new | a standalone binary with LLVM (clang and lld) bundled, for users with no Python and no system clang; pinned LLVM version |
| new | a CMake module (`find_package(oymo)`, `.oymo` as a source language), on top of 0.19's flags |
| new | **reproducible builds**: the same input always gives byte-identical `.o` files (no time stamps, paths mapped as `-ffile-prefix-map` does); CI builds twice and compares |

**Milestone:** a CMake project with C and Tenon builds with the standalone binary on a
machine with no Python and no clang, twice, to identical objects.

## 1.0 — production

**Who uses it:** teams shipping software on Linux x86-64, and language authors
publishing languages built on oymo. Nothing new in the language; this release is
about trust.

| Area | Work |
|---|---|
| Stability | oymomo syntax and semantics frozen and versioned; Tenon language spec; public API frozen, semantic versioning, deprecation policy; **language versions** in the header (`language tenon 2`), so a language can change after 1.0 without breaking old files, as Rust's editions do |
| Correctness | the confluence test of 0.2 kept green and extended to every new rule; fuzzing of parser, reduction and translation; differential tests against clang at `-O0` and `-O2` |
| Speed of the code | a benchmark set (the same programs in C and Tenon); target: within a set percentage of `clang -O2`, measured in CI |
| Speed of the compiler | measured on its own source; a budget per 10k lines; layer-1 results cached between builds, so the type checker is not rebuilt for unchanged files; if text IR is too slow, a second IR-builder implementation over the **LLVM C API** (in-process, no printing and re-parsing), behind the same interface |
| Target | Linux x86-64 (ELF, SysV ABI, glibc and musl); `--target` written so 1.x only adds entries |
| Libraries | how one Tenon library uses another, decided and documented: a package manager, or none (vendored sources, or pip packages that ship `.oymo` files) |
| Docs | tutorial, Tenon reference, C interop guide, and a **language author's guide**: lowering to Tenon, lowering to oymomo, the public API reference |

**Milestones:** a real program of a few thousand lines (for example a JSON library and
a multi-threaded CLI tool using it) is written in Tenon, mixed with existing C, built
on Linux x86-64, debugged with `gdb`, and its C users can't tell it isn't C; and a
second example language, written by someone who doesn't work on oymo, is built from
the language author's guide alone. The compiler itself, a Tenon program of tens of
thousands of lines, is the largest test.

## 1.x — more targets

Each target is one 1.x release: a `Target` entry, its C ABI rules
([plan_c_interop.md](plan_c_interop.md) Phase 3), its object format and linker, and
the differential tests against clang run on it in CI. Language authors get each new
target with no change to their code. The seed gains an `.ll` file per target.

| Release | Target | What is new |
|---|---|---|
| 1.1 | Linux AArch64 (ARM servers, Raspberry Pi) | AAPCS64 ABI: structs up to 16 bytes in registers, HFAs (structs of floats) in float registers |
| 1.2 | macOS AArch64 (Apple Silicon) | Apple's AAPCS64 variant (varargs always on the stack), Mach-O objects, `ld64`, `_` symbol prefix |
| 1.3 | Windows x86-64 | Win64 ABI (structs over 8 bytes by pointer, `long` is 32 bits), COFF objects, `link.exe` / `lld-link`, `.dll` and `.lib` |

## After 1.0 — `oymo translate-c`

`oymo translate-c lib.c -o lib.oymo` turns C source into Tenon, as Zig's
`translate-c` and c2rust do, so rewriting a C file in Tenon starts from a working
translation instead of a blank file.

- It builds on 0.24: libclang already parses the file, with the same flags and target,
  and `c_import` already maps declarations and types. translate-c adds function
  bodies: statements and expressions to Tenon syntax.
- The output builds and passes the C file's own tests unchanged (the drop-in milestone
  of 0.21, done by a tool). Idiomatic Tenon is the user's next step, not the tool's.
- Not translated: what Tenon can't express, such as some preprocessor tricks; those
  parts are left as C, called through the C ABI, and listed in a report.
- It shares its code with 0.31 (`static inline` functions and function-like macros in
  headers).

## After 1.0 — Spindle in Tenon

Spindle ([plan_vm.md](plan_vm.md)), the tiny VM embedded like Lua, is written in Tenon
instead of Python. It stays a side project, so no release waits for it; after 1.0 it
becomes a real product.

- **Why Tenon**: plan_vm.md already designs Spindle "so a C port is a straight
  translation" (a stack bytecode, a pure interpreter, state as host objects). Tenon is
  that port: C-level speed and no runtime, with Tenon's types.
- **Embeddable from C and Python**: Spindle exports a C API with a generated header
  (0.15), as Lua does (`spindle_new`, `fiber_resume`, host functions registered from
  C), so a C program embeds it with one `.a` or `.so`. Python reaches it through the
  same C API.
- **What it runs**: BANF is gone (0.4), so Spindle's input is the shaped oymomo
  program, or LLVM IR as plan_vm.md's second pipeline proposes, with LLVM's optimizer
  in front. Decided in plan_vm.md before the rewrite starts.
- **Same results as LLVM**: the differential tests of plan_vm.md, every program run
  both in Spindle and compiled by LLVM, carry over unchanged.

## Non-goals

Not planned, before or after 1.0, so no release waits for them:

- **C++ interop**: no classes, templates, exceptions or name mangling (Carbon's and
  Swift's problem, not ours).
- **A built-in garbage collector**: memory is managed through **allocators the user
  chooses**, passed explicitly (as in Zig). Most are manual (`malloc` / `free`, arena,
  pool); a garbage-collecting allocator (for example the Boehm collector, a C library)
  is one more choice, not a runtime every program carries.
- **Trampolines**: a closure is never packed into a bare C function pointer, since
  that needs machine code made at run time in writable and executable memory, which
  hardened systems forbid. Two ways cross instead, both from 0.10
  ([plan_c_interop.md](plan_c_interop.md)):
  1. **A plain function**, capturing nothing, crosses as a C function pointer
     (`qsort`).
  2. **A closure crosses as two values**, its code and a `void *` to its environment,
     where the C API takes a user-data pointer (`qsort_r`, `pthread_create`, most
     callback APIs). The code is a plain function that reads its captures through
     the pointer. From 0.10 this is written by hand, as in C; once Tenon has closures
     (plan_tenon Phase 5), Tenon splits a closure into the two values itself.

## Risks

- **Syntax changes after bootstrap are expensive.** From 0.14 every Tenon syntax
  change edits the compiler's source and may need a new seed. Phase 0's decisions
  (0.3) are made with the compiler in mind, and `oymo fmt` can migrate source.
- **The seed must stay buildable.** `bootstrap/oymo.ll` is regenerated whenever the
  compiler's source needs a newer compiler; CI builds from the seed on every change,
  so a stale seed is caught at once.
- **Two compilers during Stage B.** Until 0.14, a change to oymomo or Tenon is made in
  both the Python and the Tenon compiler. Stage B is kept short, and no feature is
  added during it.
- **The build runs code.** Layer 1 executes during compilation, so building untrusted
  code runs it, as Rust's `build.rs` and Zig's `build.zig` do. The docs say so from
  0.8; a sandbox for layer 1 is a later option.
- **Layer 1 makes builds slow.** It is compiled and run on every build (in the JIT
  until 0.13, as a subprocess after). Measured from 0.8; caching is in 1.0's "Speed of
  the compiler" row.
- **Safety types slow down the bootstrap.** Ownership and bounds checking (0.8) can
  make the compiler's own code harder to write, as Rust's borrow checker does. Kept
  small on purpose (second-class borrows, no solver), with raw `Ptr(T)` as the escape
  hatch; if Stage B stalls, the hard parts use raw pointers and are made safe later.
- **`clang` is required** from 0.14 (gcc can't read LLVM IR), until the standalone
  binary (0.36) bundles it.
- **Text IR is slower** than building IR in memory: the compiler prints it and `clang`
  parses it again. Measured on the compiler's own source from 0.14; the fix, if
  needed, is the LLVM C API behind the IR builder (1.0's "Speed of the compiler"
  row), a local change.
- **Moving targets.** Zig, C3 and Carbon all aim at 1.0 in 2027–2028; Tenon's
  difference (types as code, a platform for other languages) must stay visible in the
  docs from 0.3.

## Order and dependencies

```mermaid
flowchart TD
  subgraph A["Stage A: the bootstrap set, in Python"]
    v01["0.1 CLI"] --> v02["0.2 confluence"] --> v03["0.3 Tenon: functions, integers"]
    v03 --> v04["0.4 BANF removed"] --> v05["0.5 Tenon: memory, C calls"] --> v06["0.6 native binaries"]
    v06 --> v07["0.7 tagged unions"] --> v08["0.8 layer 1"] --> v09["0.9 interfaces, imports"]
    v09 --> v10["0.10 function pointers"] --> v11["0.11 bootstrap std library, test"]
  end
  subgraph B["Stage B: bootstrap"]
    v12["0.12 oymomo in Tenon"] --> v13["0.13 Tenon frontend in Tenon"] --> v14["0.14 self-hosting, seed"]
  end
  subgraph C1["Stage C: single-threaded"]
    v15["0.15 exports, headers"] --> v16["0.16 C API, Python package"] --> v17["0.17 registry, oymomo API"]
    v17 --> v18["0.18 Tenon API"] --> v19["0.19 build systems"] --> v20["0.20 floats"]
    v20 --> v21["0.21 by-value structs"] --> v22["0.22 varargs"] --> v23["0.23 volatile, asm"]
    v23 --> v24["0.24 c_import"] --> v25["0.25 headers in Tenon"] --> v26["0.26 debug info"]
    v26 --> v27["0.27 optimization, LTO"] --> v28["0.28 safety, sanitizers"] --> v29["0.29 separate compilation"]
    v29 --> v30["0.30 full std library"] --> v31["0.31 rest of C"] --> v32["0.32 developer tools"]
  end
  subgraph C2["Stage C: multi-threaded"]
    v33["0.33 atomics"] --> v34["0.34 thread-local storage"] --> v35["0.35 threads in std library"]
  end
  v11 --> v12
  v14 --> v15
  v32 --> v33
  v35 --> v36["0.36 distribution"] --> v100["1.0 production"]
  v100 --> X["1.1-1.3 targets"]
  v100 --> T["translate-c"]
  v100 --> V["Spindle in Tenon"]
```

The chain is the order of **releases**, not of all work: a release ships when its
work is done, and work for later releases may start earlier. The real dependencies:

- **Confluence (0.2) before Tenon (0.3)**, a hard gate.
- **BANF removed (0.4) before any new oymomo feature**, so each is built once, in the
  direct translation, and the rewrite is a straight port.
- **Tenon layer 0 as early as possible**: 0.3 and 0.5 run in the JIT, before native
  binaries (0.6).
- **Stage A holds only what the rewrite needs.** Its test: does oymo's own source need
  the feature? Everything else waits for Stage C, so Stage B starts as soon as it can.
- **Nothing new during Stage B**: features are added to one compiler, not two.
- **The Python package (0.16) after C calls Tenon (0.15)**, since the binding goes
  through the compiler's C API. The language authors' API (0.17, 0.18) follows it.
- **Header import (0.24, 0.25) after the full C ABI (0.20–0.22)**, since real headers
  declare floats, by-value structs and varargs functions.
- **Single-threaded before multi-threaded**: Part 2 of Stage C adds what sharing memory
  between threads needs; pthreads themselves can be called before.
- Independent of each other, and free to swap numbers if one is ready first: 0.19–0.23
  among themselves, and 0.26–0.32 among themselves.

After 1.0, the 1.x targets, translate-c and Spindle in Tenon are independent tracks.

## Decided

- **One package, `oymo`**, with oymomo, Tenon and the toolchain, one version number
  and one CLI command (`oymo`). Languages built on it are separate libraries that
  depend on it, through its public API.
- **Two lowering targets for language authors**: Tenon (types and C headers for free)
  and oymomo (full control). Both are public API.
- **Bootstrap early.** oymo is rewritten in Tenon as soon as Tenon has what a compiler
  needs (Stage A), with layer 1 included; all other features are added afterwards, to
  the Tenon compiler only. This replaces the earlier decision to self-host after 1.0.
- **The seed** for building from scratch is the compiler's own LLVM IR, committed as
  `bootstrap/oymo.ll`; the Python compiler is frozen at 0.14.
- **An IR builder, text first.** The translation from oymomo goes through a small
  IR-builder interface (from 0.4). The Tenon compiler's first implementation writes
  `.ll` text and runs `clang`, so the bootstrap needs only `clang`, the seed builds
  with `clang` alone, and the port from llvmlite (which also builds IR text) stays
  mechanical. A second implementation over the **LLVM C API** is an option in Stage C,
  when there is a reason: compile speed, in-process optimization and LTO (0.27), or
  bundling libLLVM in the standalone binary (0.36). This is how most languages
  differ: Rust, Odin, C3 and Crystal use the LLVM API; GHC writes `.ll` text; Zig
  moved from the C++ API to writing bitcode itself, to stay independent of LLVM's API.
  Layer 1 runs as a native subprocess, not in a JIT; llvmlite is used only by the
  Python compiler, until 0.14.
- **BANF goes away before the bootstrap (0.4)**, right after confluence (0.2) settles
  oymomo's shape, so the rewrite is a port with no change of behaviour or logic, and
  no oymomo feature is ever built in BANF.
- **Language authors write frontends in Python**, through a binding over the
  compiler's C API (0.16); their trees cross in a serialized form with locations.
- **Spindle ([plan_vm.md](plan_vm.md)) is a side project**, written in Tenon after 1.0
  ([Spindle in Tenon](#after-10--spindle-in-tenon)).
- **1.0 is Linux x86-64 only**; other targets are 1.x releases.
- **The Tenon-written oymo gets its own repository**, `oymo`, after 0.14. Until then it
  lives in one self-contained folder, `tapl/oymo/`, next to the Python compiler,
  renamed `oymo-py/` ([Repository layout](#repository-layout)).
- **One file extension, `.oymo`**, and a `language <name>` first line in every file.
  `oymomo` and `tenon` are built in; other languages are found through the
  `oymo.languages` entry point group, so mixed builds are one `oymo build` command.
- **Lowering to Tenon is by tree**, not text: a frontend builds a Tenon syntax tree
  with its own source locations, so errors point at the author's source.
- **Memory safety in layer 1**: Tenon's layer 1 has dependent and substructural
  types, so use after free, double free, leaks and out-of-bounds access are build-time
  errors, with no run-time cost and no GC; raw pointers and C stay unchecked
  ([plan_tenon.md](plan_tenon.md) 0.6). They ship with layer 1 in 0.8.

## Open questions

1. **When is the public launch?** Options:
   - **0.3**, the first Tenon release. Early feedback, while the syntax can still
     change; but JIT only, no types, so Tenon looks like one more C-like language.
   - **0.14**, when the compiler is written in Tenon. "A language whose compiler is
     written in itself, with types as code" is a strong first message, and the syntax
     has been tested on a large program; but C interop is only one way, and there is
     no Python package for language authors yet.
   - **0.25**, when C headers import into Tenon. The full "seamless with C" story, with
     the language authors' API; but feedback comes late, after most design is fixed.

   Recommended: a **soft launch at 0.14** (a website, the tutorial, a post to
   programming-language communities), and the **main launch at 0.25**, when the claim
   "Zig-level C interop, for any language you build" is true end to end. Decide before
   0.14 ships.

Each release's plans have their own open questions (for example
[plan_tenon.md](plan_tenon.md)'s Phase 0 syntax decisions, before 0.3).
