# Roadmap

Anyone can write Mizar, or their own language, and mix it with C in one program, with no
glue code. One package, `oymo`: oymomo, Alcor, Mizar and the toolchain.

- Before 1.0, a release is tagged by its date (`2026.10.22`); its notes list the ids it
  finished. Each is a toolchain someone can use. `production` is 1.0; semver after.
- The compiler builds LLVM IR through an LLVM API (llvmlite before the bootstrap, the
  LLVM C API after) and runs `clang`; no JIT before 1.0.
- Before 1.0, oymomo, Alcor and Mizar syntax, public API and CLI may break.
- 🚫 marks a blocked leaf. Each node has a fixed id.

## Tree

- `pre-bootstrap` Before the bootstrap: the Python compiler
  - `foundations` CLI, confluence, deps
    - `deps` Compile-time dependencies between `.oymo` files
      - `struct-tools` Module ops: `'module.link'`, `'module.instantiate'`
      - 🚫 `named-types` LLVM named and opaque struct types in a module's `types`
      - 🚫 `deps-cli` Many files: `--unit=each|merge|apply`, `-e` glue
      - 🚫 `ssa-sugar` Sugars: `letrec`, `let _ =`, `blocks`, typed lambdas
      - 🚫 `typed-consts` Folding keeps constants' types
      - 🚫 `deps-goldens` Golden tests: diamond, template pattern, merged declarations
    - `line-tables` `-g` line tables from spans
  - `alcor-l0` Alcor layer 0
    - `alcor-decide` Alcor decisions
      - `alcor-survey` Syntax survey: Zig, C3, Odin, Hare, Jai, Goose
      - 🚫 `alcor-syntax` Syntax, decided per topic, checked with samples and a grammar sketch
      - `alcor-layer1` What layer 1 means
      - `alcor-ub` Undefined behaviour: checked and optimized build modes
      - `alcor-generics` Generics: syntax, type-argument inference, lowering
      - `alcor-safety-syntax` Syntax for dependent and substructural types
    - 🚫 `alcor-core` Functions, integers, locals, `if`, loops, `switch`, with `oymo run`
    - `alcor-memory` Pointers, structs, arrays, strings, `void`, casts; `extern` to libc
      - 🚫 `ptr-compare` Pointer comparison and `'null' {}`
      - 🚫 `ptr-casts` `'ptrtoint'`, `'inttoptr'`
      - 🚫 `bulk-memory` `'memcpy'`, `'memmove'`, `'memset'`
      - 🚫 `void` Result type `{}`, a call as a statement
      - 🚫 `alcor-memory-frontend` Alcor syntax and lowering for memory
    - `build` `oymo build`: executables, `-c` objects, `.c` files linked in
      - 🚫 `target` Host triple and data layout in the `.ll`
      - 🚫 `obj-link` `.o` via `clang -c`, link with `cc`
      - 🚫 `driver` `oymo build a.oymo -o a`, `oymo run`, `-c`
      - 🚫 `e2e-libc` End-to-end tests calling libc and a small C library
    - 🚫 `undefined` Undefined behaviour in oymomo: folding, `'unreachable'`, poison
    - 🚫 `tagged-unions` Enums and tagged unions; `switch` binds the payload
  - `types-files` Types and multiple files
    - `layer1` Layer 1: basic types and generics
      - 🚫 `l1-subprocess` Layer 1 → oymomo → `.ll` → `clang` → run as a subprocess
      - 🚫 `l1-runtime` Type values, equality, located errors
      - 🚫 `l1-two-layer` `<expr:Type>` two-layer expressions
      - 🚫 `l1-basic-types` Integers, `Ptr(T)`, structs, enums, tagged unions, function types
      - 🚫 `l1-generics` System F generics: `List(T)`, `Map(K, V)`
    - `imports` Module interfaces and imports between files
      - 🚫 `l1-interfaces` Module interfaces: each export as `<form:type>`
    - `fn-pointers` Function pointers and callbacks
      - 🚫 `fn-address` `module.f` as an address; indirect call through `'ptr'`
      - 🚫 `alcor-fn-values` Alcor function values → function pointers; closures as code + `void *`
  - `rewrite-tools` Tools for the rewrite
    - `bootstrap-stdlib` Bootstrap standard library, `oymo test`, new `oymo/` folder
      - 🚫 `stdlib-core` Strings, slices, I/O, allocator interface, first allocators
      - 🚫 `oymo-test` `oymo test`
      - 🚫 `folder-split` `oymo/` → `oymo-py/`; new self-contained `oymo/`
    - `debugging` Debugging and editors
      - 🚫 `asan` ASan
      - 🚫 `lsp` `oymo lsp` and a VS Code extension
- `bootstrap` Bootstrap: oymo in Alcor
  - `seed-decide` Seed: storage, refresh, oymomo or `.ll`
  - 🚫 `rewrite-core` PEG engine and the oymomo pipeline in Alcor
  - `rewrite-alcor` Alcor grammar, both layers, layer-1 subprocess, `oymo lsp`
    - 🚫 `frontend-interface` The compiler is an oymomo core plus frontends
    - 🚫 `emit-oymomo` `oymo emit-oymomo`: normal-form oymomo as text, one file per module
  - `self-host` Self-hosting
    - 🚫 `stage0` `stage0.ll`: normal-form oymomo text → `.ll`
    - 🚫 `seed-files` Seed files, `build.sh`, CI builds from the seed
    - 🚫 `deps-seed` Seed files are normal-form output, no `deps`
    - 🚫 `mizar-ext` `language mizar` as an extension of Alcor, adding nothing yet
    - 🚫 `own-repo` `oymo/` exported to its own repository
- `single-thread` Single-threaded, in the Alcor-written compiler
  - `safety` Memory safety
    - 🚫 `dependent-types` `Array(u8, ^16)`, `Index(n)`; unproven index is a build error
    - 🚫 `substructural-types` `Own(T, A)`, second-class borrows; stdlib moves
  - `api` Exports and APIs
    - 🚫 `c-calls-mizar` `export`, `.a`/`.so`, generated `.h`
    - 🚫 `c-api` C API and Python package
    - 🚫 `registry` Language registry and oymomo API; example `calc`
    - 🚫 `mizar-api` Mizar API; cross-language imports
  - `c-abi` Full C ABI
    - 🚫 `build-systems` `cc`-style flags, `-MD`/`-MF`, `compile_commands.json`, pkg-config
    - `floats` `f32`, `f64`; libm
      - 🚫 `float-forms` `'f32'`, `'f64'`: literals, params, results, imports
      - 🚫 `float-arith` `'fadd'`, `'fsub'`, `'fmul'`, `'fdiv'`, `'frem'`, `'fneg'`
      - 🚫 `float-compare` Comparisons, one symbol per predicate
      - 🚫 `float-convert` `'fpext'`, `'fptrunc'`, `'fptosi'`, ... conversions
      - 🚫 `float-intrinsics` `'sqrt'`, `'fabs'`, `'floor'`, ... exact intrinsics
      - 🚫 `mizar-floats` Mizar `f32`, `f64`; libm through headers
    - 🚫 `by-value-structs` By-value structs, x86-64 SysV, both directions; unions
    - 🚫 `varargs` Call `printf`; define `...` functions via `va_list`
    - 🚫 `volatile-asm` `volatile` and inline asm
  - `c-headers` C headers
    - 🚫 `c-import` C headers → oymomo: `c_import`, `oymo import-c`
    - 🚫 `mizar-headers` C headers in Mizar, type-checked
    - 🚫 `meta-c-import` `c_import` origins and debug types from a ctype
  - `quality` Debug info, optimization, safety, separate compilation
    - 🚫 `debug-info` Params, locals, types in DWARF
    - `optimization` `-O0..-O3`, LTO across C and Mizar
      - 🚫 `align` Optional `align` on `'load'`, `'store'`, `'alloca'` and global variables
      - 🚫 `noalias` `{'noalias', 'ptr'}` on params and results
      - 🚫 `bswap` `'bswap'` for byte order per access
      - 🚫 `alias-scopes` `!alias.scope`, `!noalias`, if `noalias` isn't enough
      - 🚫 `lto` `-O` levels and LTO
    - 🚫 `safety-checks` Checked build traps on overflow, OOB, null; UBSan on C
    - 🚫 `separate-compilation` Separate compilation, incremental rebuilds
  - `completion` Standard library, rest of C, tools
    - 🚫 `full-stdlib` Closures; formatted I/O, containers, pool and Boehm allocators
    - 🚫 `rest-of-c` `static inline` and function-like macros from headers
    - 🚫 `dev-tools` `oymo fmt` for Mizar, full LSP, published VS Code extension
- `threads-1-0` Threads, distribution, 1.0
  - 🚫 `atomics` rmw, cmpxchg, fences, orderings; C11 `_Atomic`
  - 🚫 `tls` Thread-local storage; `_Thread_local` shared with C
  - 🚫 `threads` Threads in stdlib, thread-safe allocators, TSan
  - 🚫 `distribution` Standalone binary, CMake module, reproducible builds
  - 🚫 `production` 1.0 Frozen and versioned; spec, fuzzing, benchmarks, docs
- `after-1-0` After 1.0
  - 🚫 `targets` 1.1–1.3 Linux AArch64, macOS AArch64, Windows x86-64
  - 🚫 `translate-c` `oymo translate-c`: C → Mizar
  - `spindle` Spindle, a VM, in Mizar
    - 🚫 `vm-bytecode` Stack bytecode and a compiler to it
    - 🚫 `vm-core` `Spindle` and `Fiber`, host functions, host calls back
    - 🚫 `vm-coroutines` Coroutines across host calls
    - 🚫 `vm-symbols` VM-only symbols: `'ctpop'`, `'trace'`
    - 🚫 `vm-memory` Memory as a host library
  - `mizar-later` SIMD, language versions in the header
- `someday` Someday / maybe
  - `block-comments` `/* */` block comments; stuck-term errors shown in them
  - `more-layers` Back to more than two layers, if real use cases appear

## Leaf details

### `struct-tools` Module ops: `'module.link'`, `'module.instantiate'`

- semantics.tex E-Opcode: `op(b)(dᵢ) = d'`, any data; Lean: `op`'s result type
- `'module.…'` ops take and return closed normal forms (data grows to closed normal
  forms); they may compare and rewrite bodies
- semantics.tex and Lean: a grammar of normal forms, so the op's premise is syntactic, as
  data is today; the strategy normalizes op operands first
- Revisit: user decided "foundationally, there is no strategy": merging and instantiating
  are user code (semantics.tex 8.5, 8.6), so `'module.link'` and `'module.instantiate'`
  may not be needed; generic merge code needs struct tools (concat, labels) on structs
  holding `λ`s
- Compile-time only: a call that doesn't fold is rejected by translation
- Tests: link, conflicts, instantiate and run `gcd`, non-module
  operand stays

### `named-types` LLVM named and opaque struct types in a module's `types`

- A module field `types` beside `symbols`: `pair = {'i8', 'i32'}` is
  `%pair = type { i8, i32 }`; `FILE = 'opaque'` is `%FILE = type opaque`
- A type shape `{'struct', l}`, `l` a label of `types`, is LLVM's `%l`; `'opaque'` only as a
  `types` entry
- `let` naming in the source stays the compile-time way to name a type
- semantics.tex 9.1, Lean if needed, code, a golden
- Decide: named types in the ingot at all, or literal types only until a need appears
- Decide: spelling: `types`, `{'struct', l}`, `'opaque'`
- Decide: `'module.link'` on one type name: equal bodies merge, opaque takes the body,
  different bodies rename one (`pair.1`)

### `deps-cli` Many files: `--unit=each|merge|apply`, `-e` glue

- Format `oymo <command> [flags] <files…> [-- args]`; flags anywhere; `--` passes the
  rest to the program
- `--unit` says how files become compilation units:

  ```
  $ oymo run a.oymo b.oymo c.oymo                         each (default): a unit per file, linked
  $ oymo emit-llvm --unit=merge a.oymo b.oymo -o ab.ll    one unit: built-in glue
  $ oymo normal --unit=apply link.oymo a.oymo b.oymo      one unit: LINK A B
  $ oymo run -e "λa. λb. a b" a.oymo b.oymo               -e means apply
  $ oymo run a.oymo -- 5 7                                program arguments
  ```

- `merge`: `'module.link' {F₁, …, Fₙ}`; `oymo merge` prints it
- `-e` with `--unit=each` or `merge`: error; unknown value: error listing the three
- `each`: `run` builds every unit with `clang` and links; `emit-llvm`, `normal` need
  `-o DIR` for more than one file; `check` checks every unit
- For `check`, `emit-llvm`, `normal`, `run`; not `fmt`
- Each file parsed and resolved alone, the glue too
- Every file starts with `language oymomo`; an `-e` glue has no header
- A span's row carries its file; errors print `b.oymo:3:5: error: …`

### `ssa-sugar` Sugars: `letrec`, `let _ =`, `blocks`, typed lambdas

- `letrec x = t₁ in t₂` ≝ `let x = fix (λx. t₁) in t₂`
- `let _ = v in e`: a `let` kept only for its effect
- `blocks g = {l₁ = b₁, …} in t` ≝ `m [] (λg. {t, l₁ = b₁, …})` (a region); always the struct form
- Typed lambdas `λ(i: 'i32'). e` for block parameters, if inference needs help
- semantics.tex Section 3, grammar, printer; reserved words
- Decide: a better name than `blocks`

### `typed-consts` Folding keeps constants' types

- Constants that reach an ingot untyped (literal-only block parameters)
- Decide: how reduction folds at compile time and still keeps a constant's type; e.g.
  `{'const', t, b}` accepted and returned by opcodes; branches on it are stuck (5.5)
- Decide: `'select' {type, c, a, b}` opcode (LLVM `select`) for value choices

### `deps-goldens` Golden tests: diamond, template pattern, merged declarations

- Golden: diamond: `a`, `b`, `c`, `d` linked once each; `d` defines, `b` and `c` declare
- Golden: template pattern: a generic instantiated once in a file's `code`
- Golden: `puts` imported by two files, merged by `'module.link'`
- Test: mutual recursion between blocks of one group

### `line-tables` `-g` line tables from spans

- `-g` on `emit-llvm` and `run` (`run` passes `-g` to `clang`); `oymo build` takes it when it exists
- One `DICompileUnit` per row holding a function's span:
  - `DIFile(filename, directory, checksumkind: CSK_MD5, checksum)` from the row
  - `language: DW_LANG_C11`, `producer: "oymo <version>"`, `emissionKind: LineTablesOnly`
  - module flags `Dwarf Version` 5, `Debug Info Version` 3
- One `DISubprogram` per definition: `line:` from the symbol's field span, `scopeLine:`
  from the `body` lambda's span; empty `DISubroutineType`
- `!DILocation` (line, byte column) on every `let` and terminator; null span: `line: 0`
- Code from another row's file under a `DILexicalBlockFile`; no `inlinedAt`
- Each distinct location built once
- Tests: golden IR; passes `opt -passes=verify`
- Breakpoints, line stepping, backtraces in `gdb`/`lldb`
- Done when: `gdb` breaks on a line of a `.oymo` file and steps by its lines

### `alcor-survey` Syntax survey: Zig, C3, Odin, Hare, Jai

- Write the survey before any syntax decision
- Status and aim of each (Oct 2026: Zig 0.16 pre-1.0; C3 0.8, 1.0 planned 2028; Odin
  stable, no 1.0 label; Hare 0.26 pre-1.0; Jai closed beta)
- Per topic, a table of the five plus C, with pros and cons:
  - Declarations: `name: Type`, `:=`, `const`/`var`/`let`, `::` constants
  - Functions: keyword or none (`fn`, `proc`, `name :: (...)`), params, multiple results
  - Types: `*T`, `[*]T`, `[]T`, `[N]T`, slices, optionals, int names
  - Structs, enums, unions: declaration, literals, field access through a pointer
  - Control flow: `if`/`while`/`for`, `switch` and fallthrough, `defer`, labelled
    `break`
  - Errors: error unions, optionals and faults, multiple results, tagged unions
  - Compile-time code: `comptime`, `#run`, C3 macros; closeness to layer 1
  - Generics: types as values, `$T`, generic modules; fit to layer-1 functions
  - Modules and C: imports, visibility, `extern`/`export`, header import
  - Memory: allocators as params or implicit context, `defer free`, no hidden
    allocation; owned pointers, borrows, unchecked code
  - Undefined behaviour handling
  - Lexical details: semicolons, comments, string and number literals, keyword count

### `alcor-syntax` Syntax, decided per topic, checked with samples and a grammar sketch

- Keep decided: `name: Type` declarations:
  `count: i32 = 0;` · `fn add(a: i32, b: i32) -> i32 { return a + b; }`
- Decide per survey topic, one numbered decision each: what Alcor takes, from whom,
  what it rejects, one example
- Rules: keep C's form unless fixing a known C problem; a type is a layer-1
  expression; lowers simply to oymomo; when two of the five agree, take that
- Check with sample programs: hello world, a struct with a function on it, a function
  as an argument, `Matrix(^2, ^3)`, a C header import
- Write a grammar sketch and precedence table
- No indentation syntax
- Decide: function keyword (`fn` or other) and exact declaration forms
- Decide: allocator passing: explicit param or implicit context
- Decide: header import syntax

### `alcor-layer1` What layer 1 means

- Write it down: a type is a layer-1 value; each function's layer-1 version checks its
  arguments' types; an error stops the build
- Decide: does layer 1 lower exactly like layer 0, or may it use features layer 0
  can't (closures, a GC)?

### `alcor-ub` Undefined behaviour: checked and optimized build modes

- Write down two build modes:
  - checked: trap with message and location on overflow, out-of-bounds, null
  - optimized: undefined, as C and LLVM
- Use after free / double free: never checked at run time; layer-1 errors for owned
  pointers, undefined for raw ones
- Out-of-bounds checked at run time only where layer 1 proved nothing

### `alcor-generics` Generics: syntax, type-argument inference, lowering

- System F style: `List(T)`, `Map(K, V)`, `fn get(T: Type, l: List(T), i: usize) -> T`;
  checked once for every `T`; a type parameter is a layer-1 value
- Decide: syntax
- Decide: inference of type arguments
- Decide: lowering: one copy per type, or one shared copy taking sizes

### `alcor-safety-syntax` Syntax for dependent and substructural types

- Decide syntax for:
  - lifted build-time values: `Array(u8, ^16)`, `Matrix(^2, ^3)`
  - run-time values in types: `buf: Ptr(Array(u8, n))`, `i: Index(n)`
  - `Own(T, A)`, `Ref(T)`, borrow `&p`
  - `alloc(a, T)`, `free(a, p)`
  - explicit `Ptr(T)` ↔ `Own(T, A)` (e.g. `unsafe`)
  - annotations on C functions that return or consume owned values
- Decide: affine types too, or linear plus explicit `drop`?

### `alcor-core` Functions, integers, locals, `if`, loops, `switch`, with `oymo run`

- Grammar on the PEG engine; tree classes with `separate()`
- Lower layer 0 to an oymomo program (`module -> {...}`): functions → structs of
  blocks, `if`/`while` → blocks and jumps, locals → `alloca`, `switch`
- Register `language alcor` as built in
- Alcor API: public tree classes and constructors, locations from any file
- Code in `src/oymo/alcor/`
- No type checker; release notes say so
- Done when: `fact`, `fib`, `gcd` in Alcor run with `oymo run`

### `ptr-compare` Pointer comparison and `'null' {}`

- `'icmp' {'eq', 'ptr', p, q}` and the other nine predicates on `'ptr'`; only the LLVM
  lowering changes
- `'null' {}`: gives `'ptr'`, pure, no fold, LLVM `ptr null`
- Goal program: length of a linked list, load `next` until `'icmp' {'eq', …}` with `'null' {}`
- Tests and a golden
- Commit: `oymomo: compare pointers`
- Decide: should `'icmp' {'eq', 'ptr', …}` of two `'null' {}` fold?

### `ptr-casts` `'ptrtoint'`, `'inttoptr'`

- `'ptrtoint' {'ptr', p, 'i64'}`, `'inttoptr' {'i64', n, 'ptr'}`, shaped like `'zext'`
- Any integer type (truncates or zero-extends); pure, no fold
- Goal program: round an address up to 16 bytes within a 32-byte `alloca`
- Tests and a golden
- Commit: `oymomo: add pointer casts`
- Decide: how a program learns the target's pointer width and byte order: a
  module-level value, a type (`'iptr'`), or not at all

### `bulk-memory` `'memcpy'`, `'memmove'`, `'memset'`

- Three impure opcodes, result `{}`, bound by a `let` that only orders them (4.4c):

  | Opcode | Fields | LLVM |
  |---|---|---|
  | `'memcpy'` | `{dst, src, len}` | `@llvm.memcpy.p0.p0.iN(ptr, ptr, iN, i1 false)` |
  | `'memmove'` | `{dst, src, len}` | `@llvm.memmove.p0.p0.iN(...)` |
  | `'memset'` | `{dst, byte, len}` | `@llvm.memset.p0.iN(ptr, i8, iN, i1 false)` |

- `len`'s integer type picks `iN`; `volatile` is `false`, no field
- Declare the intrinsics by name
- Goal program: copy 1024 `'i32'`; under `-O2` one `memcpy` call remains
- Tests and a golden
- Commit: `oymomo: add bulk memory ops`

### `void` Result type `{}`, a call as a statement

- `{'function', params, {}}` for functions returning nothing
- A call as a statement
- LLVM `void` declarations, definitions, calls, `ret void`

### `alcor-memory-frontend` Alcor syntax and lowering for memory

- Alcor syntax and lowering for pointers, structs, arrays, strings
- `void` functions, null, pointer comparison, casts, `memcpy`/`memset`
- Hand-written `extern` declarations to call C; first-order calls, Alcor → C only
- `oymo run` links libc
- Memory via `malloc`/`free` through `extern`
- Done when: hello world with `puts`; linked list with `malloc`/`free`

### `target` Host triple and data layout in the `.ll`

- A real `Target`: host triple and data layout written in the `.ll`
- From the module's `target` field; the host's when absent

### `obj-link` `.o` via `clang -c`, link with `cc`

- `.o` via `clang -c` on the `.ll`
- Link with the system `cc`
- Compile `.c` inputs with `cc`

### `driver` `oymo build a.oymo -o a`, `oymo run`, `-c`

- `oymo build a.oymo -o a`: executable
- `oymo build ... -c`: object file
- `oymo build hello.oymo util.c -o hello`: `.c` files linked in
- `oymo run` through the same build path

### `e2e-libc` End-to-end tests calling libc and a small C library

- `zeroext`/`signext` on `i1`, `i8`, `i16` where needed
- End-to-end tests calling libc and a small C test library, built and run
- Done when: `oymo build hello.oymo util.c -o hello` runs; a program reverses a file

### `undefined` Undefined behaviour in oymomo: folding, `'unreachable'`, poison

- One place for every case LLVM leaves undefined, at the oymomo level; `alcor-ub` builds
  Alcor's checked and optimized modes on it
- Folding: today E-Opcode gives no result where LLVM is undefined (`udiv`/`sdiv`/`urem`/`srem`
  by 0, `sdiv` of the minimum by −1, a shift by the width or more); the call stays as
  run-time code (semantics.tex 4.4e, 5.6)
- `'unreachable' {}` as a block end: LLVM's `unreachable`; uses: after a call that never
  returns (`exit`, `abort`), a `switch` default that can't happen, facts a frontend proved,
  the optimized mode of `alcor-ub`; never folds
- Poison and undef: LLVM's `poison` value, flags that make results poison (`nsw`, `nuw`,
  `exact`), `freeze`
- semantics.tex 4, 5, 7–9; Lean (`anf_normal`, `op` partiality); code; goldens: a function
  ending in `exit`, a division by a literal 0
- Decide: an undefined call found at compile time: keep it as run-time code (today), reject
  it as stuck with an error, or fold it to `poison`
- Decide: `'unreachable'`: spelling, opcode call or own form, only at a block's end or also
  bound by a `let`
- Decide: `llvm.trap` for checked builds here or in `alcor-ub`
- Decide: which poison-making flags and `freeze`, and when

### `tagged-unions` Enums and tagged unions; `switch` binds the payload

- Alcor enums and tagged unions
- Lower tagged unions to oymomo structs and `switch`
- `switch` binds the payload
- Decide: unions: a form of their own, or a byte array with size and alignment
  (as far as tagged unions need)
- Done when: expression evaluator: tagged-union tree, recursive `eval`

### `l1-subprocess` Layer 1 → oymomo → `.ll` → `clang` → run as a subprocess

- Lower layer 1 to a second oymomo program
- Write it as `.ll`, build with `clang`, run as a subprocess at build time
- Errors come back with locations; no error means layer 0 type-checks
- Keep locations through reduction

### `l1-runtime` Type values, equality, located errors

- Small layer-1 runtime: type values (`Int32`, `Ptr(T)`, struct types), equality,
  located errors

### `l1-two-layer` `<expr:Type>` two-layer expressions

- `<expr:Type>` two-layer expressions in the Alcor tree; split each layer out

### `l1-basic-types` Integers, `Ptr(T)`, structs, enums, tagged unions, function types

- Layer-1 types: integers, raw `Ptr(T)`, structs, enums, tagged unions, function types
- Done when: `puts(42)` → `app.oymo:3:6: expected Ptr(c_char), got Int32`; the
  evaluator type-checks

### `l1-generics` System F generics: `List(T)`, `Map(K, V)`

- Generics as decided: `List(T)`, `Map(K, V)`, type parameters as layer-1 values
- Lowering as decided (one copy per type, or shared)
- Done when: `List(T)` at two types; `List(i32)` for `List(u8)` is an error

### `l1-interfaces` Module interfaces: each export as `<form:type>`

- Each export as `<form:type>` (form: what oymomo needs to call; layer-1 type)
- Alcor imports between files; calls across files type-checked
- Done when: ten Alcor files importing each other; wrong-type imported call is an error

### `fn-address` `module.f` as an address; indirect call through `'ptr'`

- `module.f` as an address
- Indirect call through `'ptr'` with a function type

### `alcor-fn-values` Alcor function values → function pointers; closures as code + `void *`

- Alcor function values lower to function pointers
- A capture-free function crosses to C as a function pointer
- A closure crosses as code + `void *` environment, written by hand; no trampolines
- Decide: does the compiler need closures?
- Done when: an Alcor function passed to `qsort` and `qsort_r`

### `stdlib-core` Strings, slices, I/O, allocator interface, first allocators

- Generic growable arrays and hash map
- Strings, string builder, slices
- Number formatting (no `printf`)
- File I/O; running a process (to call `clang`)
- Allocator interface; arena and libc allocators
- Lives in `oymo/lib/`

### `oymo-test` `oymo test`

- `oymo test`, as `zig test` does
- Done when: word count over a large file (hash map, arena), tests via `oymo test`

### `folder-split` `oymo/` → `oymo-py/`; new self-contained `oymo/`

- Rename `oymo/` (Python compiler) to `oymo-py/`
- New `oymo/` with `README.md`, `LICENSE`, `lib/`, `tests/goldens/` (moved from
  `oymo-py`)
- Nothing in `oymo/` refers to a path outside it; `oymo-py/` reads `oymo/` only
- CI builds and tests a copy of `oymo/` alone
- New tests are goldens or `oymo test` files

### `asan` ASan

- Pass `-fsanitize=address` to `clang`
- Done when: ASan catches use after free in the linked-list program, with its Alcor line

### `lsp` `oymo lsp` and a VS Code extension

- `oymo lsp`: any `.oymo` language; parse and layer-1 errors as you type
- VS Code extension in `oymo/editors/vscode/`:
  - highlighting for oymomo and Alcor, picked by the header
  - starts the server; runs whichever `oymo` is on `PATH`
  - breakpoints and launch configs via `gdb`/`lldb`
- Done when: VS Code underlines a type error

### `seed-decide` Seed: storage, refresh, oymomo or `.ll`

- Pick the seed form: normal-form oymomo text in split files (proposed) or `bootstrap/oymo.ll`
- Record the decision before `rewrite-core` starts
- Decide: storage and refresh: commit and regenerate only when needed, Git LFS, or a
  release artifact
- Decide: target-independent seed (oymomo seed, or `zig1.wasm`-like + small interpreter
  in C)?
- Decide: is the seed target-independent for 64-bit targets? 32-bit (wasm32): a second
  `stage0.ll`, or left out
- Decide: `c_import` bakes in `long`, `size_t`, struct layouts: ban target-dependent C
  types in the compiler (CI check), or one seed per target
- Decide: how the core finds a language: (a) linked in at build time, (b) static table
  filled at link time, (c) `.so` loaded at run time. Leaning: a now, c later
- Decide: how is `stage0.ll` produced: generated once from a small oymo program and
  committed, or written by hand
- Decide: how are the Alcor seed files split (e.g. lexer, parser, checker, lowering);
  each file is a linkage unit
- Decide: trust: should CI compare stage 3 built from the seed and from the frozen
  Python compiler?
- Decide: what the extension interface looks like, and is it ready for `mizar-ext`?
- Decide: what is in Alcor: start from integers, pointers, structs, arrays, strings,
  tagged enums, `switch`, recursion, heap; generics and closures only if needed
- Decide: which language owns layer 1: Alcor parses and erases types, Mizar checks
  (stage 2)?
- Decide: which language do users extend: usually Mizar; Alcor as a minimal base?

### `rewrite-core` PEG engine and the oymomo pipeline in Alcor

- Write in `oymo/compiler/`, mirroring `oymo-py/src/oymo/`, file by file:
  - `core/`: PEG engine
  - `oymomo/`: parser, reduction, strategy, ANF and module checks, translation
  - `ir/`: LLVM IR through the LLVM C API (`extern` bindings), where the Python
    compiler uses llvmlite
  - `driver/`: the `oymo` command
- Add nothing new; same behaviour and logic as the Python compiler
- Widest int stays `i64`
- Run the confluence test and the oymomo goldens against it
- Check that reduction handles a megabyte-size term in reasonable time
- Measure seed size and build time
- Done when: byte-identical `.ll` vs the Python compiler on every oymomo test, both
  printed by LLVM (`llvm-dis`)

### `frontend-interface` The compiler is an oymomo core plus frontends

- Design the frontend interface: source in; tree with locations and errors out
- Same interface for Alcor, Mizar, `calc` and Python frontends; a high-level frontend
  may return a Mizar tree
- Port the Alcor frontend in `compiler/alcor/`: Alcor grammar on the PEG engine, both
  layers
- Layer-1 subprocess and error channel as in the Python compiler
- `oymo lsp` in the driver
- Done when: same output as the Python compiler on every Alcor test (layer-1 errors too);
  VS Code extension works unchanged

### `emit-oymomo` `oymo emit-oymomo`: normal-form oymomo as text, one file per module

- Add `oymo emit-oymomo`: write a program's normal-form oymomo as text, one file per module
- Keep the printed normal form stable
- Each file declares the symbols it exports and imports
- Reduction stops at the file boundary: no specialization across files
- Add `emit-oymomo` to the Python compiler only if CI checks the seed against it

### `stage0` `stage0.ll`: normal-form oymomo text → `.ll`

- Write `bootstrap/stage0.ll`: translates normal-form oymomo text only (no reduction) to `.ll`
- Builds with `clang` alone
- Output uses the portable `.ll` subset:
  - no `target triple`, no `target datalayout`
  - only `i8`/`i32`/`i64`, `ptr`, `getelementptr` for offsets
  - no hard-coded pointer size
  - C calls with scalars and pointers only, no structs by value
  - no C `long`; `size_t` as `i64`
- `clang` links the resulting `.ll` files

### `seed-files` Seed files, `build.sh`, CI builds from the seed

- Commit the seed files:

  | File | Holds |
  |---|---|
  | `bootstrap/stage0.ll` | normal-form oymomo text → `.ll` |
  | `bootstrap/oymomo.oymo` | core: parser, reduction, strategy, translation, extension interface, driver |
  | `bootstrap/alcor/*.oymo` | Alcor frontend, one file per part |
  | `bootstrap/clang-version` | minimum and tested clang and libLLVM version |

- Generate all `.oymo` seed files from the compiler's source (Alcor, layer 0 only)
- `build.sh` builds from the seed:

  ```
  clang   stage0.ll                  -> stage0
  stage0  oymomo.oymo                -> oymomo.ll
  stage0  alcor/*.oymo               -> alcor/*.ll
  clang   oymomo.ll alcor/*.ll -lLLVM -> stage1    # knows Alcor only
  stage1  compiler/                  -> stage2     # adds Mizar
  stage2  compiler/                  -> stage3     # must match stage2 byte for byte
  ```

- Regenerate the seed when the source uses a feature the old seed lacks
- CI builds from the seed on every change, with the minimum and tested clang versions
- CI builds the seed for two targets
- Freeze the Python compiler
- Done when: with `clang`, libLLVM and no Python, a fresh clone builds from the seed, builds
  itself twice to identical output, passes every test

### `deps-seed` Seed files are normal-form output, no `deps`

- Write seed files as normal-form output; no `deps` in them

### `mizar-ext` `language mizar` as an extension of Alcor, adding nothing yet

- Register `language mizar` as an extension of Alcor that adds nothing yet
- Use only the public extension interface; grow the interface if Mizar needs more
- Code in `compiler/mizar/`; built by stage 1 from `compiler/`
- Done when: every Alcor test passes as `language mizar`; stage 2 knows Mizar
- Decide: list what Mizar adds and the syntax of each, checked against Alcor's survey
- Decide: does Mizar lower to an Alcor tree or straight to oymomo?
- Decide: can an extension add types to layer 1 (`f32`, atomics), or only syntax?

### `own-repo` `oymo/` exported to its own repository

- Move docs from `oymo-py/docs/` to `oymo/docs/`; links point at `compiler/`
- Export with `git subtree split --prefix=oymo` (or `git filter-repo`), keeping history
- Move the CI workflow from the tapl root to the new repo's `.github/`
- Delete `oymo-py/`; tag `oymo-py-final`
- Decide: when is the public launch? Recommended: soft launch at `substructural-types`
  (site, tutorial, posts), main launch at `mizar-headers`

### `dependent-types` `Array(u8, ^16)`, `Index(n)`; unproven index is a build error

- Lift build-time values with `^`: `Array(u8, ^16)`, `Matrix(^2, ^3)`
- Name run-time values in types: `buf: Ptr(Array(u8, n))`, `i: Index(n)` (`0 .. n`)
- Facts from layer-0 tests: inside `if (i < n)`, `i: Index(n)`; facts drop at branch end
- `buf[i]` needs `i: Index(n)`, else a layer-1 error or a checked (trapping) access
- First version: equalities and `<`/`<=` on variables and constants; no solver
- Stdlib arrays and slices carry lengths in types
- Done when: index with no bounds test fails; inside `if (i < n)` builds; word count uses
  sized slices
- Decide: is an SMT solver (e.g. Z3) ever worth its build time and dependency?

### `substructural-types` `Own(T, A)`, second-class borrows; stdlib moves

- `Own(T, A)` linear: freed or passed on exactly once; lowers like `Ptr(T)`
- A struct or tagged union with a linear field is linear
- Borrows: `&p` gives `Ref(T)`; `p` can't be freed or moved meanwhile; passed to calls,
  never stored or returned
- Checking: one pass per body; environment name → type, plus live / consumed /
  borrowed for linear names
  - errors: use of consumed; live linear name at `return` or block end
  - `if` branches consume the same names; loop bodies keep the state
- Allocators: `alloc(a, T)` → `Own(T, A)`; `free(a, p)` consumes `p`
  - arena gives `Ref(T)` tied to it; freeing it needs no live borrow
  - GC allocator gives unrestricted references
- Raw `Ptr(T)` unchecked; explicit `Ptr(T)` ↔ `Own(T, A)` (syntax from the survey)
- Annotations on C functions returning (`malloc`, `fopen`) or consuming (`free`,
  `fclose`) owned values; stdlib wrappers use them
- Interfaces carry ownership
- Move the stdlib to `Own`; move the compiler module by module
- Done when: the `alcor-memory` linked list with `Own` type-checks; use after free /
  double free / leak fails the build; one compiler module rewritten with `Own`
- Decide: affine types too, or linear plus explicit `drop`?
- Decide: do second-class borrows suffice for the compiler's source, or are stored
  references with regions needed?

### `c-calls-mizar` `export`, `.a`/`.so`, generated `.h`

- `export` on a function or global → `linkage = 'export'`; the rest `'local'`
- The label is the C name; no mangling
- Exported constants and global variables (`extern int counter;` reads a global variable)
- Callbacks: an oymomo function passed to C and called back
- Generate `.h` from the module interface: prototypes, structs, include guards; layer-1
  types (`unsigned`, `const char *`, named structs); LLVM types alone give `int`-sized and
  `void *`
- Output `.a` and `.so`: `oymo build lib.oymo --emit=h,a,so`
- Scalars and pointers only; by-value struct at the boundary: error "pass a pointer"
- Done when: a C `main` calls a Mizar library through a header that reads as
  hand-written

### `c-api` C API and Python package

- C API (via exports): build, emit, check, errors as data
- Python package in `oymo/python/`: wheel with the native compiler, binding over the C API
- Build API: `executable`, `object_file`, `static_library`, `shared_library`, `header`,
  `emit_llvm`; target, emit, link C files and libraries
- Trees cross serialized, with locations
- The `oymo` command is the package's driver; the CLI is a thin layer over the build API
- Done when: `pip install oymo`, then `oymo build hello.oymo`, and the same via the Python
  build API

### `registry` Language registry and oymomo API; example `calc`

- Languages from Python packages via the `oymo.languages` entry point
  (e.g. `calc = "calc_lang:frontend"`)
- The driver resolves the `language <name>` header
- Unknown language: error naming the package to install, if known, and listing installed
  languages
- oymomo API: build terms in Python (or give text), check, errors as data with locations
- `calc` in `oymo/examples/calc/`, own `pyproject.toml`: arithmetic → oymomo terms,
  registered as `language calc`
- Examples use only the public API; built and run in CI
- Done when: with `calc` installed, `language calc` / `1 + 2 * 3` builds a binary
  printing `7`
- Decide: load languages at run time as `.so` (`OYMO_LANGUAGE_PATH`,
  `frontend(source, length, out_tree)`), so native and Python languages are found alike?

### `mizar-api` Mizar API; cross-language imports

- Public Mizar tree classes and constructors; locations from any file
- Layer-1 errors as data
- `calc` gets a Mizar backend
- Cross-language module interfaces: Mizar-lowering frontends give forms and types;
  oymomo-lowering ones give forms only, unchecked in layer 1
- Done when: `calc`→Mizar type error located in the `calc` file; Mizar imports from `calc`
  with type checks

### `build-systems` `cc`-style flags, `-MD`/`-MF`, `compile_commands.json`, pkg-config

- `cc`-style flags: `-c`, `-o`, `-I`, `-L`, `-l`
- `-MD` / `-MF` dependency files
- `compile_commands.json`
- pkg-config: `oymo build --pkg-config sdl2`
- Done when: a Makefile uses `oymo -c` for `cc -c`, rebuilds only changes, links SDL via
  pkg-config

### `float-forms` `'f32'`, `'f64'`: literals, params, results, imports

- Add forms `'f32'` (LLVM `float`) and `'f64'` (`double`)
- A float is a value like an integer: param, result, struct field, let, import
- Literal is its IEEE 754 bits, little-endian: `[0000803f]~'f32'`,
  `[000000000000f03f]~'f64'` are 1.0
- Every bit pattern is a value, NaN payloads included
- Wrong size: `A f32 constant needs 4 bytes.`
- No implicit change of bits or form
- `.ll`: float constant from its bits; NaN with payload as bits bitcast from an integer
  constant
- Tests: return an `'f64'` param; `float 1.0`; NaN payload kept; float struct field;
  `sqrt` import; 3-byte `'f32'` error; golden `float.oymo`
- Decide: other float forms (`'f16'`, `'bf16'`, `'f128'`, `x86_fp80`): which, and when?
- Decide: decimal literals (`1.5~'f64'` as sugar for bytes)? Hex float or decimal?
- Decide: float vectors: every symbol accepts them where LLVM does; reduction folds only
  scalars?

### `float-arith` `'fadd'`, `'fsub'`, `'fmul'`, `'fdiv'`, `'frem'`, `'fneg'`

- Opcodes `{form, a, b}`: `'fadd'`, `'fsub'`, `'fmul'`, `'fdiv'`, `'frem'`;
  `'fneg'` `{form, value}`
- LLVM's default FP environment only: round to nearest even, no traps, no fast-math, no
  constrained intrinsics
- `'f32'` computed in binary64, then rounded to binary32
- Never fold a NaN result; a NaN operand folds if the result isn't NaN
- `'fneg'` flips only the sign bit; folds even on a NaN
- `fdiv` by zero gives ∞ or NaN
- Printed as LLVM: `fadd f64 a, b`
- Tests: edge operands (`±0`, `±1`, smallest subnormal, largest finite, `±∞`, NaN, both
  forms) vs LLVM; `1.0 + 2.0` folds to `[0000000000000840]`; `0.0 / 0.0` stays;
  `'f32'` `0.1 + 0.2` folds to the `f32` bits

### `float-compare` Comparisons, one symbol per predicate

- One symbol per predicate, `'fcmp_' + predicate`, `{form, lhs, rhs}` → `'i1'`:
  - ordered: `oeq`, `one`, `ogt`, `oge`, `olt`, `ole`
  - unordered: `ueq`, `une`, `ugt`, `uge`, `ult`, `ule`
  - `ord`, `uno`
- No `fcmp false`/`fcmp true`
- `-0.0` equals `+0.0` under `oeq`
- Error: `'icmp' takes an integer type, got f32; for floats use 'fcmp_ult'.`
- Tests: every predicate × `{-∞, -1, -0, +0, 1, +∞, NaN}` vs LLVM; literal folds;
  `'fcmp_uno'` with NaN folds to `[01]~'i1'`

### `float-convert` `'fpext'`, `'fptrunc'`, `'fptosi'`, ... conversions

- Fields `{form, value, to}`, like `'zext'`: `'fpext' {'f32', x, 'f64'}`
- `'fpext'` f32 → f64; `'fptrunc'` f64 → f32, rounded
- `'fptosi'`, `'fptoui'`: toward zero; NaN, ∞, out of range: not folded
- `'sitofp'`, `'uitofp'`: rounded to nearest
- `'bitcast'`: any → any same-size form LLVM can bitcast (not structs)
- Error: `'fpext': to must be wider than f64, got f32.`
- Tests: `fptrunc` rounds to nearest even; `fptosi -1.5` is `-1`; `sitofp` of `2^53 + 1`
  rounds; `fptoui` of `-1.0`, NaN, `2^32` to `'i32'` not folded; `'bitcast'` of
  `1.0~'f32'` to `'i32'` is `[0000803f]`; narrowing and size errors
- Decide: add saturating `'fptosi_sat'`/`'fptoui_sat'`?

### `float-intrinsics` `'sqrt'`, `'fabs'`, `'floor'`, ... exact intrinsics

- Exact intrinsics only, `llvm.NAME` without the prefix:
  - `{form, value}`: `'sqrt'`, `'fabs'`, `'floor'`, `'ceil'`, `'round'`, `'roundeven'`,
    round toward zero (`llvm.trunc`)
  - `{form, magnitude, sign}`: `'copysign'`
  - `{form, a, b}`: `'minnum'`, `'maxnum'`, `'minimum'`, `'maximum'`
  - `{form, a, b, c}`: `'fma'`, rounded once
- Transcendentals are libm imports: `sin = {x = 'f64'} => 'f64'`
- Tests: edge operands vs LLVM; `fma` where twice-rounded differs; `minnum(NaN, 1.0)` is
  `1.0`, `minimum` is NaN; `minimum(-0.0, +0.0)` is `-0.0`; `'sqrt'` is
  `call double @llvm.sqrt.f64`
- Done when: `hypot(3.0, 4.0) = 5.0`; every float symbol matches LLVM on edge operands
  (NaN results: "is a NaN")
- Decide: name of `llvm.trunc`: one `'trunc'` by `form`, `'trunc_toward_zero'`, or
  `'ftrunc'`

### `mizar-floats` Mizar `f32`, `f64`; libm through headers

- Mizar `f32`, `f64` on the oymomo float forms
- libm through headers
- Done when: Mizar calls `sqrt` and `pow` from libm

### `by-value-structs` By-value structs, x86-64 SysV, both directions; unions

- C ABI lowering for x86-64 SysV: by-value structs and `sret`
- Same lowering on imports, C-callable definitions, indirect calls; internal
  oymomo-to-oymomo calls may skip it
- Unions as C has them
- Differential tests: per signature, C caller and callee from clang, both directions
- Fallback: reject by-value structs at the boundary (pass `'ptr'`), with a clear error
- Done when: a small C library rewritten in Mizar passes its unchanged C tests
- Decide: ABI lowering: own code or clang's CodeGen?
- Decide: unions: a form of their own, or a byte array with size and alignment?

### `varargs` Call `printf`; define `...` functions via `va_list`

- Varargs declarations and calls
- `va_list` in definitions
- Default argument promotions: `float` → `double`, small ints → `int`
- Register rules: `%al` on x86-64
- Mizar syntax for variadic functions
- Done when: `printf("%d %f %s\n", ...)` from Mizar; a Mizar `...` function called from C
- Decide: how the function type says varargs (e.g. a 4th field `'varargs'`), how a call
  passes extra arguments (calls give exactly the callee's parameter labels today), and
  how each extra argument gets its type (a byte array has no use to take it from)

### `volatile-asm` `volatile` and inline asm

- `volatile` flag on `'load'`/`'store'`, as LLVM has it
- `'asm'` inline asm, as LLVM has it
- Mizar syntax for both
- Done when: a signal handler sets a `volatile` flag; `rdtsc` via inline asm
- Decide: one `volatile` field for `'load'`, `'store'` and the bulk ops, or `volatile`
  variants?

### `c-import` C headers → oymomo: `c_import`, `oymo import-c`

- `c_import(header, target, flags)`: libclang's C API from the Alcor-written compiler,
  run once; one `CDecl(form, ctype)` per declaration
- form: `module` field, struct form, or byte-array constant
- ctype: C type as plain data (signedness, width, pointee, `const`, fields,
  typedef/enum names, function pointer signatures), each with its form
- Mapping:

  | C declaration | form | ctype |
  |---|---|---|
  | function | import signature `{...} => R` | parameter and result C types |
  | variable | data form, or `'ptr'` for a cell | C type, `const` or not |
  | struct / typedef / enum | struct form / form / `'i32'` | named C type |
  | `#define N 42` | byte array `[2a000000]~'i32'` | `int` |

- `int`, `long` through the target; pointers → `'ptr'`; structs → struct forms in order
- `flags` (`-I`, `-D`, `--target`) are part of the import
- Preprocessor run by libclang with `flags`; macros via
  `PARSE_DETAILED_PROCESSING_RECORD`
- Object-like macros: add `static const __auto_type __oymo_N = (N);`, read value and
  type with `clang_Cursor_Evaluate`
- Skip and list: non-constant macros, function-like macros
- Scope: functions, structs, enums, typedefs, object-like macros; later unions, bitfields
- Check struct layout against clang's `sizeof` / `offsetof`
- `CDecl` public (Python via the binding)
- `oymo import-c stdio.h` prints declarations
- Done when: `calc` calls `sqrt` from `<math.h>` via `c_import`

### `mizar-headers` C headers in Mizar, type-checked

- Header import syntax; calls `c_import` once with the build's target and flags
- Each `CDecl(form, ctype)` is `<form:ctype>`; `LayerSeparator` splits it
- Layer 0: the form, unchanged
- Layer 1: ctype → Mizar type: `int` → `c_int`, `const char *` → `Ptr(Const(c_char))`,
  struct → struct type, typedef → its name in messages, its target for equality
- Pointers → raw `Ptr(T)`, never `Own`
- Same names in both layers; a skipped name is missing from both, with its reason
- Layer 1 checks the target's C types (`c_long` as `c_import` reported it)
- Error messages name a name's header
- Replace the compiler's own `extern`s for libc and libclang
- Test: every type made from a ctype has the ctype's form
- Done when: Mizar imports `<stdio.h>`, `<string.h>`, `<math.h>`; `puts(42)` is a layer-1
  error
- Decide: how strict is the C mapping: `int` → `long` implicit or an error?
  `char *` → `const char *` accepted?

### `meta-c-import` `c_import` origins and debug types from a ctype

- `CDecl(form, ctype, origin)`; origin is file, line, column
- Write origins as metadata (`!origin`)
- ctype → `DIBasicType` / `DIDerivedType` / `DICompositeType`, exact for C (`unsigned`,
  `const`, typedefs)

### `debug-info` Params, locals, types in DWARF

- Metadata helpers: compile unit with module flags, file, subprogram, location, basic
  and composite types; each adds a node (reusing an equal one) and returns its index
- Params, locals, types in DWARF
- Variables printed in Mizar's or a language author's source
- Done when: `gdb` breaks in Mizar, steps, prints locals, in a program mixed with C
- Decide: locals: is a location enough, or do `alloca`s need `#dbg_declare` records
  (`DILocalVariable`)?

### `align` Optional `align` on `'load'`, `'store'`, `'alloca'` and global variables

- One more positional field, last, a literal power of two, read unsigned:

  | Opcode | Fields |
  |---|---|
  | `'load'` | `{type, ptr}`, `{type, ptr, align}` |
  | `'store'` | `{type, value, ptr}`, `{type, value, ptr, align}` |
  | `'alloca'` | `{type}`, `{type, count}`, `{type, count, align}` |

- A global variable or constant: an entry field `align = [08]` beside `type` and
  `init`/`value`
- `'alloca'`: `count` must be written to give `align`
- Too large `align` is undefined behaviour, unchecked
- Test: unaligned `'i32'` read from a packed struct, `align 1`

### `noalias` `{'noalias', 'ptr'}` on params and results

- Tagged type `{'noalias', 'ptr'}`; `'noalias'` becomes a reserved tag (9.1)
- Allowed on: a parameter or the result in a function's type
  (`malloc = {type = {'function', {size = 'i64'}, {'noalias', 'ptr'}}}`); elsewhere an
  error
- Everywhere else it counts as `'ptr'` (a jump may pass it to a block parameter)
- LLVM: `ptr noalias %dst`, `noalias ptr @malloc(...)`
- Breaking the promise is undefined behaviour, unchecked
- Test: `dst[i] = src[i] * 2` over two `'ptr'` params; `-O2` leaves no `vector.memcheck`

### `bswap` `'bswap'` for byte order per access

- `'bswap' {'i32', x}`: `llvm.bswap.iN`, pure, folded
- Test: read a big-endian `'i32'` header field on a little-endian target
- Decide: how does a program learn the target's pointer width and byte order: a
  module-level value, a type (`'iptr'`), or not at all?

### `alias-scopes` `!alias.scope`, `!noalias`, if `noalias` isn't enough

- Only for a program `noalias` can't serve
- Scoped aliasing metadata `!alias.scope`, `!noalias` per access
- New field on `'load'`/`'store'`; scope declarations
- Decide: scopes declared in `module`, or written inline on each access?

### `lto` `-O` levels and LTO

- `-O0..-O3` passed to `clang`
- `oymo -c -flto` emits bitcode; clang's LTO link inlines C into Mizar and back
- Done when: a C→Mizar call is inlined under `-flto` (checked in disassembly)

### `safety-checks` Checked build traps on overflow, OOB, null; UBSan on C

- Two build modes:
  - checked: traps with message and location on overflow, out-of-bounds, null
  - optimized: undefined, as C and LLVM
- Out-of-bounds checked at run time only where layer 1 proved nothing
- Use after free / double free never checked at run time
- UBSan on the C side
- Done when: an OOB write is caught by the checked build and by ASan (optimized), with
  the Mizar line

### `separate-compilation` Separate compilation, incremental rebuilds

- Separate compilation and multiple modules, on module interfaces
- Incremental rebuilds
- Done when: changing one function body in the compiler rebuilds one object
- Decide: partial normalization: normalize a file before the glue binds it?

### `full-stdlib` Closures; formatted I/O, containers, pool and Boehm allocators

- Closures; split into code + `void *` environment when passed to C
- Formatted I/O, containers
- Pool and Boehm GC allocators
- On top of the bootstrap standard library
- Done when: one program runs with arena and Boehm allocators, switched in one line
- Decide: how does a closure capture a linear value? May a function value be linear
  (called exactly once)?

### `rest-of-c` `static inline` and function-like macros from headers

- `static inline` functions from headers
- Function-like macros from headers
- Done when: a `static inline` function and a function-like macro from a system header
- Decide: skip them, translate to oymomo (shared with `translate-c`), or compile with
  clang into a small `.o`?

### `dev-tools` `oymo fmt` for Mizar, full LSP, published VS Code extension

- `oymo fmt` for Mizar
- LSP: errors as you type, go to definition (into C headers), hover with layer-1 types,
  completion, find references, rename
- Any LSP editor (Neovim, Emacs, Helix) works with `oymo lsp`
- Publish the extension on VS Marketplace and Open VSX
- Done when: editor shows errors as you type, goes to definition in C headers, hover types

### `atomics` rmw, cmpxchg, fences, orderings; C11 `_Atomic`

- `'atomicrmw'`, `'cmpxchg'`, `'fence'`, atomic `'load'`/`'store'`, orderings, as LLVM
  has them
- C11 `_Atomic`
- Mizar syntax
- Done when: two pthreads share an atomic counter; total always right

### `tls` Thread-local storage; `_Thread_local` shared with C

- LLVM `thread_local`
- Mizar syntax
- `_Thread_local` imported and exported
- Done when: four threads count in thread-locals; a C `_Thread_local` read from Mizar

### `threads` Threads in stdlib, thread-safe allocators, TSan

- Threads in the stdlib (pthreads): mutexes, condition variables
- Thread-safe allocators: libc allocator, per-thread arenas, threaded Boehm
- TSan
- Done when: a worker pool over a queue runs clean under TSan

### `distribution` Standalone binary, CMake module, reproducible builds

- Standalone binary with bundled clang and lld; pinned LLVM
- Standalone binary builds built-in languages only
- CMake: `find_package(oymo)`, `.oymo` as a source language, on the `cc`-style flags
- Reproducible: no time stamps, paths mapped like `-ffile-prefix-map`; CI builds twice
- Done when: a CMake project (C + Mizar) builds with the standalone binary, no Python or
  clang, twice, identical objects

### `production` Frozen and versioned; spec, fuzzing, benchmarks, docs

- No new features
- Stability: oymomo frozen and versioned; Mizar spec; API frozen, semver, deprecation
  policy; oymomo, Alcor and Mizar syntax, API, CLI stable
- Correctness: confluence test kept green and extended; fuzz parser, reduction,
  translation; differential tests vs clang `-O0`/`-O2`
- Speed of code: benchmark set (same programs in C and Mizar), within a set % of
  `clang -O2`, in CI
- Speed of compiler: measured on its own source; budget per 10k lines; cache layer-1
  results for unchanged files
- Target: Linux x86-64 (ELF, SysV, glibc and musl); `--target` built so new targets only
  add entries
- Docs: tutorial, Mizar reference, C interop guide, language author's guide (both
  lowerings, API reference)
- Done when: a few-thousand-line Mizar program mixed with C (e.g. JSON lib + threaded
  CLI), debugged with `gdb`, indistinguishable from C to its users; a second example
  language written by an outsider from the language author's guide alone
- Decide: how Mizar libraries use each other: package manager, or none (vendored, or pip
  packages shipping `.oymo`)

### `targets` Linux AArch64, macOS AArch64, Windows x86-64

- Per target: a `Target` entry, its C ABI, object format, linker, differential tests in CI
- Seed gains an `.ll` per target, if the seed is per target
- Linux AArch64: AAPCS64, structs ≤16 bytes in registers, HFAs in float registers
- macOS AArch64: Apple's AAPCS64 variant (varargs on stack), Mach-O, `ld64`, `_` prefix
- Windows x86-64: Win64 (structs >8 bytes by pointer, 32-bit `long`), COFF,
  `link.exe`/`lld-link`, `.dll`, `.lib`

### `translate-c` `oymo translate-c`: C → Mizar

- `oymo translate-c lib.c -o lib.oymo`
- Reuse `c_import`'s libclang parsing (same flags and target) and type mapping; add
  function bodies
- Output passes the C file's own tests unchanged
- Untranslatable parts stay C via the C ABI; list them
- Share code with `rest-of-c`

### `vm-bytecode` Stack bytecode and a compiler to it

- Bytecode compiled once from the checked input: names → slots, labels → offsets
- Stack machine, ten instructions:

  | Instruction | Stack | Input |
  |---|---|---|
  | `const k` | → v | constant, defined data |
  | `get s` / `set s` | → v / v → | variable / let, block param |
  | `op o` | a... → r | core opcode |
  | `call f` | a... → r | call to a function |
  | `host h, n` | a... → r | import, struct make, field get, non-core symbol |
  | `jump L` / `jump_if L` | / c → | jump after its moves / branch on `c != 0` |
  | `switch n, L0 ... Ln` | s → | the `s`-th target, or the last |
  | `return` | r → | pop frame, push `r` in the caller's |

- Frame: window of the fiber's one value stack: params, block params and lets, operands
- Jump pushes args, stores them last to first; branch/switch edges with moves get a stub
- `Program`: code array, constant pool, function table (entry, arity, slots,
  `max_stack`), host slots (name, arity), data; a listing printer
- Tests: every op/terminator; swap is correct; `max_stack` is the deepest stack
- Decide: what Spindle runs: the normal-form oymomo program, or LLVM IR after LLVM's optimizer
- Decide: values in a C/Mizar port: `iN` ≤ 64 fits a word; wider ints and host values
  need handles released when a fiber dies?

### `vm-core` `Spindle` and `Fiber`, host functions, host calls back

- VM knows integers (`iN` unsigned below `2^N`); every other value is the host's
- State is two host objects, nothing global:
  - `Spindle(program, symbols, imports, max_host_depth)`: checks bytecode (jump targets,
    stack depths, arity) and bindings at load
  - `Fiber`: value stack, frame stack, status `suspended | running | normal | dead`;
    `resume(value, fuel)` → `Returned(v)`, `Yielded(v)`, `OutOfFuel()`; `frames()`;
    `host` slot; `machine.call(function, args, fuel)`
- No host stack for VM calls; fuel suspends; next `resume` goes on
- Undefined operation stops the fiber with function and block in the error
- Host function `f(fiber, *args)` returns a value, `Yield(value, k)` or
  `Call(function, args, k)`
- Host calls back: `fiber.call(...)` nests a loop (no yield inside; depth ≤ 200);
  errors catchable
- Unbound import or symbol is an error
- C API and generated header: `spindle_new`, `fiber_resume`, host functions registered
  from C; one `.a`/`.so`; Python via the same API
- Tests: opcodes on edge operands; sum loop; recursion 10000 deep; division by zero kills
  the fiber; endless loop → `OutOfFuel()`, resumable; bad bytecode rejected; two
  `Spindle`s independent; callback chains; differential vs LLVM on every golden
- Decide: trap where LLVM is undefined, or not?
- Decide: common imports (`putchar`, `malloc`) in the default library?
- Decide: REPL and CLI (`oymo run --spindle a.oymo`)?
- Decide: make struct make / field get core instructions for speed?

### `vm-coroutines` Coroutines across host calls

- `Yield` from a host function suspends the fiber; `resume(value)` continues
- Continuation `k(fiber, v)` in `Yield`/`Call`, so yields cross host calls
- `'yield' {form, value}` symbol in a coroutines library; impure, not core, no LLVM
- Resuming another fiber nests a loop; the resumer is `normal`
- Fibers created from oymomo code via function values
- Errors: yield inside `fiber.call`; resuming a running or dead fiber
- Tests: generator over five resumes then `Returned`; yield crosses a host `Call`;
  resuming another fiber sees its yields

### `vm-symbols` VM-only symbols: `'ctpop'`, `'trace'`

- `'ctpop'`: pure, LLVM `llvm.ctpop`, not core, folds
- `'trace'`: impure, no LLVM lowering, not core; a tracer binding appends and returns
- `'trace'` in `.ll` output: `'trace' runs only in the VM.`
- Tests: `'ctpop' {'i32', 7}` is 3; two `trace`s ordered by `$seq`; rebinding `'ctpop'`
  changes the VM, not folding; golden `vm_symbol.oymo`
- Decide: which VM-only symbols first (`trace`; then layer-1 helpers)?

### `vm-memory` Memory as a host library

- Memory library binds `'alloca'`, `'getelementptr'`, `'load'`, `'store'` on one byte
  buffer per `Spindle`; a pointer is an integer offset
- Layout as the target's data layout, in its byte order
- `alloca` on a per-fiber stack, freed by `'stacksave'`/`'stackrestore'` around functions
  calling `'alloca'`
- Offset 0 never handed out; out of range is an error
- Tests: layouts of `{i8, i32}`, `<{i8, i32}>`, `[3 x i32]` match LLVM; store `'i32'`,
  load `'i8'` gives the target's byte; `alloca` freed on return; two fibers' `alloca`s
  don't overlap; differential on memory programs
- Done when: every LLVM-run test program gives the same result in the VM

### `mizar-later` SIMD, language versions in the header

- SIMD in Mizar
- Language versions in the header (`language mizar 2`)

### `block-comments` `/* */` block comments; stuck-term errors shown in them

- `/* */` block comment syntax
- Show stuck-term error messages in a block comment

### `fields-strict` `$fields_to_struct` argument allows only its own labels

- `$fields_to_struct` argument must be
  `A = {more=[01], label=utf8, value=term, rest=A} | {more=[00]}`; no other labels

### `more-layers` Back to more than two layers, if real use cases appear

- Go back to multiple layers instead of two (term, type), if real use cases appear
