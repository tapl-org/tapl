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
  - `ll-bootstrap` `.ll` features needed before the bootstrap
    - `fn-address` Indirect call through `'ptr'`
    - 🚫 `ptr-compare` Pointer comparison and `'null' {}`
    - `ptr-casts` `'ptrtoint'`, `'inttoptr'`
  - `alcor` Alcor: a typed language, two oymomo programs per file
    - `alcor-decide` Alcor decisions
      - `alcor-survey` Syntax survey: twenty-nine languages plus C (Zig … Scala; Nelua, Ada, Modula-2, Oberon, OCaml, Racket; Python, JavaScript, TypeScript, C#, Visual Basic, R)
      - 🚫 `alcor-syntax` Syntax, decided per topic, checked with samples and a grammar sketch
      - `alcor-layer1` What layer 1 means
      - `alcor-ub` Undefined behaviour: checked and optimized build modes
      - `alcor-generics` Generics: syntax, type-argument inference, lowering
      - `alcor-safety-syntax` Syntax for dependent and substructural types
    - `alcor-layers` Two layers: split a file, run layer 1, type values
      - 🚫 `l1-two-layer` `<expr:Type>` two-layer expressions, split into two oymomo programs
      - 🚫 `l1-subprocess` Layer 1 → oymomo → `.ll` → `clang` → run as a subprocess
      - 🚫 `l1-runtime` Type values, equality, located errors
    - 🚫 `alcor-core` Functions, integers, locals, `if`, loops, `switch`, both layers, built with `oymo build`
    - `alcor-memory` Pointers, structs, arrays, strings, `void`, casts; `extern` to libc
      - 🚫 `alcor-memory-frontend` Alcor syntax and lowering for memory
    - 🚫 `e2e-libc` End-to-end tests calling libc and a small C library
    - 🚫 `tagged-unions` Enums and tagged unions; `switch` binds the payload
    - 🚫 `l1-generics` System F generics: `List(T)`, `Map(K, V)`
  - `types-files` Multiple files and function pointers
    - `imports` Module interfaces and imports between files
      - 🚫 `l1-interfaces` Module interfaces: each export as `<form:type>`
    - `fn-pointers` Function pointers and callbacks
      - 🚫 `alcor-fn-values` Alcor function values → function pointers; closures as code + `void *`
      - 🚫 `interfaces` Interfaces: fat pointers (data, table); tables built by layer 1
  - `rewrite-tools` Tools for the rewrite
    - `bootstrap-stdlib` Bootstrap standard library, `oymo test`, new `oymo/` folder
      - 🚫 `stdlib-core` Strings, slices, I/O, allocator interface, first allocators
      - 🚫 `oymo-test` `oymo test`
      - 🚫 `folder-split` Goldens into `oymo/`; CI tests `oymo/` alone
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
  - `ll-coverage` oymomo writes any `.ll`
    - `ll-structure` Calculus, ANF and entry shapes for `.ll`
      - `ll-anf` Terminators, switch cases, opcode options
        - 🚫 `undefined` Undefined behaviour in oymomo: folding and `'unreachable'`
        - 🚫 `ll-tail-calls` `musttail` calls and unreachable blocks
        - 🚫 `sparse-switch` Branch arms with case values
        - 🚫 `opcode-options` Options on opcodes (`align`, `volatile`, orderings, flags); `poison`, `undef`
      - `ll-entries` Entry fields, attributes, module level
        - 🚫 `attr-slots` Attribute slots: entries, parameters and results, `cc`
        - 🚫 `ll-module-level` Aliases, `module asm`, constant expressions in initializers
    - `ll-types` Types: `void`, wide integers, floats, vectors
      - 🚫 `wide-ints` Every `'iN'` LLVM takes, `'i128'` first
      - `floats` `'float'`, `'double'`
        - 🚫 `float-forms` `'float'`, `'double'`: literals, params, results, declarations
        - 🚫 `float-arith` `'fadd'`, `'fsub'`, `'fmul'`, `'fdiv'`, `'frem'`, `'fneg'`
        - 🚫 `float-compare` Comparisons: every `fcmp` predicate
        - 🚫 `float-convert` `'fpext'`, `'fptrunc'`, `'fptosi'`, ... conversions
        - 🚫 `float-intrinsics` `'sqrt'`, `'fabs'`, `'floor'`, ... exact intrinsics
      - 🚫 `ll-vectors` Vector opcodes, `extractelement`, `insertelement`, `shufflevector`
    - `ll-memory` Bulk memory, volatile, atomics
      - 🚫 `bulk-memory` `'memcpy'`, `'memmove'`, `'memset'`
      - 🚫 `ll-volatile-asm` `volatile` loads and stores; inline asm
      - 🚫 `ll-atomics` `'atomicrmw'`, `'cmpxchg'`, `'fence'`, orderings
    - `ll-code` Instructions, poison, intrinsics
      - 🚫 `ll-poison` `poison` and `undef` in bodies, poison flags, `'freeze'`
      - 🚫 `ll-instructions` `select` and `getelementptr` flags
      - 🚫 `bswap` `'bswap'` for byte order per access
      - 🚫 `ll-intrinsics` `ctpop`, `ctlz`, `abs`, overflow checks, `assume`, `lifetime`, `trap`, …
    - `ll-attrs` Attributes, linkages, thread-locals
      - 🚫 `noalias` `noalias` on params and results
      - 🚫 `ll-function-attrs` Calling conventions; function, parameter and result attributes
      - 🚫 `ll-symbol-fields` Global `align`, `linkage`, visibility, `unnamed_addr`, `section`, `comdat`
      - 🚫 `ll-tls` `thread_local` on global variables
    - `ll-metadata` Metadata and debug info
      - 🚫 `line-tables` `-g` line tables from meta places
      - 🚫 `ll-debug-info` Params, locals, types as DWARF metadata
      - 🚫 `alias-scopes` `!alias.scope`, `!noalias`, if `noalias` isn't enough
      - 🚫 `ll-instr-metadata` `!range`, `!tbaa`, `!prof`, `!llvm.loop`, module flags
    - 🚫 `ll-check` Every row tested; clang's `-O2` output written in oymomo
  - `safety` Memory safety
    - 🚫 `assigned-before-use` Layer-1 check: a variable is assigned before it is read
    - 🚫 `dependent-types` `Array(u8, ^16)`, `Index(n)`; unproven index is a build error
    - 🚫 `substructural-types` `Own(T, A)`, second-class borrows; stdlib moves
  - `api` Exports and APIs
    - 🚫 `c-calls-mizar` `export`, `.a`/`.so`, generated `.h`
    - 🚫 `c-api` C API and Python package
    - 🚫 `registry` Language registry and oymomo API; example `calc`
    - 🚫 `mizar-api` Mizar API; cross-language imports
    - 🚫 `label-opcodes` Opcodes between labels and byte arrays: `'struct.get'`, `'struct.labels'`, `'struct.with'`
  - `c-abi` Full C ABI
    - 🚫 `build-systems` `cc`-style flags, `-MD`/`-MF`, `compile_commands.json`, pkg-config
    - 🚫 `mizar-floats` Mizar `f32`, `f64`; libm through headers
    - 🚫 `by-value-structs` By-value structs, x86-64 SysV, both directions; unions
    - 🚫 `volatile-asm` `volatile` and inline asm
  - `c-headers` C headers
    - 🚫 `c-import` C headers → oymomo: `c_import`, `oymo import-c`
    - 🚫 `mizar-headers` C headers in Mizar, type-checked
    - 🚫 `meta-c-import` `c_import` origins and debug types from a ctype
  - `quality` Debug info, optimization, safety, separate compilation
    - 🚫 `debug-info` Mizar params, locals, types in DWARF
    - `optimization` `-O0..-O3`, LTO across C and Mizar
      - 🚫 `lto` `-O` levels and LTO
    - 🚫 `safety-checks` Checked build traps on overflow, OOB, null; UBSan on C
    - 🚫 `asan` ASan
    - 🚫 `separate-compilation` Separate compilation, incremental rebuilds
    - 🚫 `header-places` Places in generated files: source vs generated, not oymomo vs other
    - 🚫 `label-free` Labels and names out of the logic: positions, de Bruijn indices, fingerprints
  - `completion` Standard library, rest of C, tools
    - 🚫 `full-stdlib` Closures; formatted I/O, containers, pool and Boehm allocators
    - 🚫 `value-gc` Lua-style incremental GC for `Value`, replacing the arena
    - 🚫 `rest-of-c` `static inline` and function-like macros from headers
    - 🚫 `dev-tools` `oymo fmt` for Mizar, full LSP, published VS Code extension
- `threads-1-0` Threads, distribution, 1.0
  - 🚫 `atomics` Atomics in Mizar; C11 `_Atomic`
  - 🚫 `tls` Thread-local storage in Mizar; `_Thread_local` shared with C
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

## Leaf details

### `fn-address` Indirect call through `'ptr'`

- Indirect call through a `'ptr'` operand with a function type (`g.f` as an address in
  operands and initializers is done)
- A function type `{'function', {…}, t}` as a value's type: LLVM `ptr`; it fits wherever a
  `'ptr'` or another function type does
- An argument `p.l` or a value `x` of a function type heads a call: `p.cmp {x, z}` →
  `%c = call i32 %p.cmp(i32 %x, i32 %z)`; a `'void'` result has no value
- Every call is positional; a written label must be the parameter's at its position
  (`g.gcd {[30000000], [12000000]}` is accepted too)
- No closures: a function value is an entry's address
- Running by reduction: `g.sort {…, g.asc}` runs `asc` through `p.cmp`; no special rule
- Function types as today: C calling convention, no attributes
- oymomo-calculus.tex 8.3, 8.6, 8.8, 9.8, 10.2, 10.4, 10.8 (Lean unchanged: `Op.call`
  takes any path); code: ingot reader (kinds, call labels), type inference, translation;
  goldens: a callback through `p.cmp`, a table of addresses read by `'load'`, a positional
  direct call

### `ptr-compare` Pointer comparison and `'null' {}`

- `'icmp' {'eq', 'ptr', p, q}` and the other nine predicates on `'ptr'`, and against `{}`
  (`ptr null`): the lowering already works; pin it with tests and a golden
- `'null' {}`, if added, carries result type `'ptr'` (for untyped block parameters), pure,
  no fold
- Goal program: length of a linked list, load `next` until `'icmp' {'eq', …}` with null
- Commit: `oymomo: compare pointers`
- Decide: is `'null' {}` needed alongside `{}` at `'ptr'`?
- Decide: should `'icmp' {'eq', 'ptr', …}` of two nulls fold?

### `ptr-casts` `'ptrtoint'`, `'inttoptr'`

- `'ptrtoint' {'ptr', p, 'i64'}`, `'inttoptr' {'i64', n, 'ptr'}`, shaped like `'zext'`
- Any integer type (truncates or zero-extends); pure, no fold
- Goal program: round an address up to 16 bytes within a 32-byte `alloca`
- Tests and a golden
- Commit: `oymomo: add pointer casts`

### `alcor-survey` Syntax survey: twenty-nine languages plus C (Zig … Scala; Nelua, Ada, Modula-2, Oberon, OCaml, Racket; Python, JavaScript, TypeScript, C#, Visual Basic, R)

- Write the survey before any syntax decision, in `docs/alcor_survey.md`
- Status and aim of each (Oct 2026: Zig 0.16 pre-1.0; C3 0.8, 1.0 planned 2028; Odin
  stable, no 1.0 label; Hare 0.26 pre-1.0; Jai closed beta; Goose experimental;
  Carbon experimental; Swift 6; Rust 1.99; C++23, C++26 coming; D 2.x; Cpp2
  experimental; Terra; Java 25–27; Go 1.26; Kotlin 2.4; Scala 3.10)
- Per topic, a table of the twenty-nine plus C, with pros and cons:
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
  - Module systems: unit, resolution, cycles, init, interfaces, generics across
    modules, symbol names, packages, per-platform code

### `alcor-syntax` Syntax, decided per topic, checked with samples and a grammar sketch

- Write each kernel decision in `docs/alcor_kernel_syntax.md`; sugar in
  `docs/alcor_sugar_syntax.md`, after the kernel
- Keep decided: `name: Type` declarations:
  `var count: i32 = 0;` · `fn add(a: i32, b: i32) -> i32 { a + b }`
- Decide per survey topic, one numbered decision each: what Alcor takes, from whom,
  what it rejects, one example
- Rules: keep the form mainstream languages share (C's first) unless fixing a known
  problem; everything is an expression; a type is a layer-1 expression; lowers simply
  to oymomo; when two surveyed languages agree, take that
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
- Write it down: Alcor is a typed language that writes two oymomo programs, one per
  layer; the compiler has no type checker of its own; a closed program's layer 1 reduces
  to constants
- Decide: does layer 1 lower exactly like layer 0, or may it use features layer 0
  can't (closures, a GC)?
- Decide: how layer-1 code calls layer-0 code (link or merge the oymomo programs)
- Decide: who builds and runs the guard (`unit.guard.ll`), and how its located errors reach
  the user and `oymo lsp`, now that oymo ends at the `.ll`

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

### `l1-two-layer` `<expr:Type>` two-layer expressions, split into two oymomo programs

- `<expr:Type>` two-layer expressions in the Alcor tree
- Split each file into two oymomo programs, one per layer
- Decide: which syntax goes to which layer

### `l1-subprocess` Layer 1 → oymomo → `.ll` → `clang` → run as a subprocess

- Lower layer 1 to a second oymomo program
- Write it as `.ll`, build with `clang`, run as a subprocess at build time
- Errors come back with locations; no error means layer 0 type-checks
- Keep locations through reduction

### `l1-runtime` Type values, equality, located errors

- Small layer-1 runtime: type values (`Int32`, `Ptr(T)`, struct types), equality,
  located errors

### `alcor-core` Functions, integers, locals, `if`, loops, `switch`, both layers, built with `oymo build`

- Grammar on the PEG engine; tree classes with `separate()`
- Lower layer 0 to an ingot: functions → regions of blocks, `if`/`while` → blocks and
  jumps, locals → `alloca`, `switch`
- Layer-1 types: integers, function types
- Register `language alcor` as built in
- Alcor API: public tree classes and constructors, locations from any file
- Code in `src/oymo/alcor/`
- No type checker in the compiler: layer-1 code checks types; release notes say so
- Done when: `fact`, `fib`, `gcd` in Alcor build, link with clang and run; a call with a wrong
  integer type is a located layer-1 error

### `alcor-memory-frontend` Alcor syntax and lowering for memory

- Alcor syntax and lowering for pointers, structs, arrays, strings
- Layer-1 types: raw `Ptr(T)`, structs, arrays
- `void` functions, null, pointer comparison, casts, `memcpy`/`memset` through declarations
  of `llvm.memcpy`/`llvm.memset`
- Hand-written `extern` declarations to call C; first-order calls, Alcor → C only
- clang links libc when the user links `unit.ll`
- Memory via `malloc`/`free` through `extern`
- Done when: hello world with `puts`; linked list with `malloc`/`free`;
  `puts(42)` → `app.oymo:3:6: expected Ptr(c_char), got Int32`

### `e2e-libc` End-to-end tests calling libc and a small C library

- C arguments `int`-sized or wider, and pointers; `char`, `short` and `_Bool` arguments
  wait for `attr-slots` (`zeroext`/`signext`)
- End-to-end tests calling libc and a small C test library, built and run
- Linked by hand, as oymo ends at the `.ll`: `oymo build hello.oymo`, then
  `clang -Wno-override-module oymo-out/unit.ll util.c -o hello`
- Done when: that `hello` runs; a program reverses a file

### `tagged-unions` Enums and tagged unions; `switch` binds the payload

- Alcor enums and tagged unions
- Layer-1 types: enums, tagged unions
- Lower tagged unions to oymomo structs and `switch`
- `switch` binds the payload
- Decide: unions: a form of their own, or a byte array with size and alignment
  (as far as tagged unions need); an ingot is platform-neutral, so a member's size may
  differ by target (`'ptr'`)
- Done when: expression evaluator: tagged-union tree, recursive `eval`; the evaluator
  type-checks

### `l1-generics` System F generics: `List(T)`, `Map(K, V)`

- Generics as decided: `List(T)`, `Map(K, V)`, type parameters as layer-1 values
- Lowering as decided (one copy per type, or shared)
- Done when: `List(T)` at two types; `List(i32)` for `List(u8)` is an error

### `l1-interfaces` Module interfaces: each export as `<form:type>`

- Each export as `<form:type>` (form: what oymomo needs to call; layer-1 type)
- Alcor imports between files; calls across files type-checked
- Done when: ten Alcor files importing each other; wrong-type imported call is an error

### `alcor-fn-values` Alcor function values → function pointers; closures as code + `void *`

- Alcor function values lower to function pointers
- A capture-free function crosses to C as a function pointer
- A closure crosses as code + `void *` environment, written by hand; no trampolines
- Decide: does the compiler need closures?
- Done when: an Alcor function passed to `qsort` and `qsort_r`

### `interfaces` Interfaces: fat pointers (data, table); tables built by layer 1

- An interface is a struct type of function types; `Dyn(I)` is `{data, table}`, the
  table a pointer to `I`'s functions for one concrete type
- Layer 1 builds each (type, interface) table once, as read-only data, from the
  type's functions of the same names; conversion to `Dyn(I)` is explicit (`as`)
- A call `w.write(msg)` on a `Dyn(I)` lowers to `w.table.write(w.data, msg)`; objects
  keep C layout (no hidden table pointer)
- Decide: syntax for interfaces, `Dyn(I)` and its sugar, and functions per type (with
  no overloading, two types' `write` need a receiver namespace such as `fn File.write`)
- Decide: implicit satisfaction (Go) or a written `impl` (Rust)
- Done when: one function takes a writer and is called with a file and a buffer

### `stdlib-core` Strings, slices, I/O, allocator interface, first allocators

- Generic growable arrays and hash map
- Strings, string builder, slices
- Number formatting (no `printf`)
- File I/O; running a process (to call `clang`)
- Non-variadic libc only: `fopen`/`creat`, not `open` with a mode; `posix_spawnp` to start
  a process
- Allocator interface; arena and libc allocators
- Lives in `oymo/lib/`

### `oymo-test` `oymo test`

- `oymo test`, as `zig test` does
- Done when: word count over a large file (hash map, arena), tests via `oymo test`
- Decide: does `oymo test` build and run the tests (it needs clang), now that oymo ends at
  the `.ll`?

### `folder-split` Goldens into `oymo/`; CI tests `oymo/` alone

- Move `tests/goldens/` from `oymo-py/` to `oymo/tests/goldens/` when the bootstrap starts
- Nothing in `oymo/` refers to a path outside it; `oymo-py/` reads `oymo/` only
- CI builds and tests a copy of `oymo/` alone
- New tests are goldens or `oymo test` files

### `lsp` `oymo lsp` and a VS Code extension

- `oymo lsp`: any `.oymo` language; parse and layer-1 errors as you type
- VS Code extension in `oymo/editors/vscode/`:
  - highlighting for oymomo and Alcor, picked by the header
  - starts the server; runs whichever `oymo` is on `PATH`
- Done when: VS Code underlines a type error

### `seed-decide` Seed: storage, refresh, oymomo or `.ll`

- Pick the seed form: normal-form oymomo text in split files (proposed) or `bootstrap/oymo.ll`
- Record the decision before `rewrite-core` starts
- An oymomo-text seed means `stage0` reads the printed normal form; a change to that form
  needs a new `stage0`
- Decide: storage and refresh: commit and regenerate only when needed, Git LFS, or a
  release artifact
- Decide: target-independent seed (oymomo seed, or `zig1.wasm`-like + small interpreter
  in C)?
- Decide: is the seed target-independent for 64-bit targets? 32-bit (wasm32): a second
  `stage0.ll`, or left out
- Decide: `c_import` bakes in `long`, `size_t`, struct layouts: ban target-dependent C
  types in the compiler (CI check), or one seed per target
- Decide: how the core finds a language: (a) linked in at build time, (b) static table
  filled at link time (needs `section`/`llvm.used` from `ll-symbol-fields` before the
  bootstrap), (c) `.so` loaded at run time. Leaning: a now, c later
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

### `undefined` Undefined behaviour in oymomo: folding and `'unreachable'`

- One place for every case LLVM leaves undefined, at the oymomo level; `alcor-ub` builds
  Alcor's checked and optimized modes on it
- Folding: today E-Opcode gives no result where LLVM is undefined (`udiv`/`sdiv`/`urem`/`srem`
  by 0, `sdiv` of the minimum by −1, a shift by the width or more); the call stays as
  run-time code (oymomo-calculus.tex 5.4k, 6.6)
- `'unreachable' {}` as a block end: LLVM's `unreachable`; uses: after a call that never
  returns (`exit`, `abort`), a `switch` default that can't happen, facts a frontend proved,
  the optimized mode of `alcor-ub`; never folds
- oymomo-calculus.tex 5, 6, 8–10; Lean (`anf_normal`, `op` partiality); code; goldens: a function
  ending in `exit`, a division by a literal 0
- Decide: an undefined call found at compile time: keep it as run-time code (today), reject
  it as stuck with an error, or fold it to `poison` (then `ll-poison`'s `poison` in bodies
  comes first)
- Decide: `'unreachable'`: spelling, opcode call or own form, only at a block's end or also
  bound by a `let`

### `ll-tail-calls` `musttail` calls and unreachable blocks

- `musttail` call as a block end: LLVM's `musttail call` and its `ret`
- Goldens
- Decide: spelling of `musttail` in ANF (a terminal `g.f {…}` is rejected today), and on an
  indirect call (`fn-address`)
- Decide (Nov 5, user: "Decide later"): an unreachable block; the translation leaves it out
  today, which changes the program under the "adds none, changes none" rule; reject it with
  a located error instead?

### `sparse-switch` Branch arms with case values

- A branch whose arms carry case values, as LLVM's `switch iN c, label %d [iN v, label %b …]`;
  the dense branch `{J_i} P` stays
- oymomo-calculus.tex 5, 8, 10; Lean (the reduction rule, confluence, `anf_normal`); code;
  goldens: a switch on character codes
- Decide: spelling (a label can't hold byte 00, so a case value can't be a label), the
  reduction rule, and how case values get their type

### `opcode-options` Options on opcodes (`align`, `volatile`, orderings, flags); `poison`, `undef`

- One convention for options on opcodes, the opcodes of today included
- Covers `align`, `volatile`, atomic orderings and `syncscope`, poison flags (`nsw`, `nuw`,
  `exact`, `disjoint`, `nneg`, `samesign`), and `inbounds`, `nuw`, `nusw` on variadic
  `'getelementptr'`
- `align` on `'load'`, `'store'` and `'alloca'`, the first option: a literal power of two,
  read unsigned; too large `align` is undefined behaviour, unchecked
- Spelling of `poison` and `undef`, for bodies and predefs
- `'fcmp'`'s shape, for `float-compare`
- oymomo-calculus.tex 5, 8, 10; code: the convention in the opcode table, `align`; tests:
  unaligned `'i32'` read from a packed struct, `align 1`
- Decide: the convention (one trailing struct of options, labeled fields, or other)
- Decide: spelling of `poison` and `undef` (marker opcodes like `'layout.size'`, or other)
- Decide: `'fcmp'`: one opcode `{pred, type, a, b}` as `'icmp'`, or one per predicate

### `attr-slots` Attribute slots: entries, parameters and results, `cc`

- An entry slot: function attributes, linkages, visibility, `section`, `align`,
  `thread_local`, `comdat`, `unnamed_addr`
- A parameter and result slot in the function type
- `cc` in the function type, so an indirect call (`fn-address`) has it
- Every attribute value fits: flags, integers (`dereferenceable(8)`), types (`byval(T)`,
  `sret(T)`), ranges (`range(i32 0, 10)`), structured values (`memory(argmem: read)`,
  `initializes((0, 16))`), strings (`"frame-pointer"="all"`)
- `comdat` with its selection kind (`any`, `largest`, …)
- Rules for `'unit.merge'`, `'unit.rebase'`, `'unit.make_reducible'` and `emit-header`
- First names: `zeroext`, `signext`, `sanitize_address` (`asan`)
- oymomo-calculus.tex 9, 10; Lean (`UnitOps.lean`: `isHole`, `isDecl`, merge); code
  (`ingot.py`, `header.py`, `llvm_translate.py`); goldens
- Decide: the slot shapes
- Decide: do hints that can be dropped (`noalias`, `nonnull`, `noinline`, …) go in meta
  instead
- Decide: the merge rule for attributes, and how linkages (`weak`, `linkonce_odr`,
  `extern_weak`, …) combine with `link` and `'unit.merge'`

### `ll-module-level` Aliases, `module asm`, constant expressions in initializers

- Aliases: a new entry kind
- `module asm`
- Constant expressions in predefs (`init`, `value`): `getelementptr`, `ptrtoint`, difference
  of two addresses, `'layout.size'`, `'layout.offset'`, `'layout.align'`
- `poison` and `undef` in predefs, spelled as `opcode-options` decides
- oymomo-calculus.tex 8–10; Lean (`Anf.lean` operands, `UnitOps.lean`); code; goldens
- Decide: alias target (`λg. g.target` vs `link`)
- Decide: where `module asm` sits in the ingot
- Decide: spellings of constant expressions in predefs

### `wide-ints` Every `'iN'` LLVM takes, `'i128'` first

- Types `'iN'` for every width LLVM takes; `'i128'` first
- Folding at any width
- Tests: `'i128'` arithmetic folds as LLVM computes it; a golden

### `float-forms` `'float'`, `'double'`: literals, params, results, declarations

- Add LLVM's floating-point types by their LLVM names (oymomo-calculus.tex 10): `'half'`,
  `'bfloat'`, `'float'`, `'double'`, `'fp128'`, `'x86_fp80'`, `'ppc_fp128'`; `'float'` and
  `'double'` first
- A float is a value like an integer: param, result, struct field, let, declaration
- Literal is its IEEE 754 bits, little-endian (typed by its use): `[0000803f]` as `'float'`,
  `[000000000000f03f]` as `'double'` are 1.0
- Every bit pattern is a value, NaN payloads included
- Wrong size: `A constant of type float is a byte array of 4 bytes.`
- No implicit change of bits or type
- `.ll`: float constant from its bits; NaN with payload as bits bitcast from an integer
  constant
- Tests: return a `'double'` param; `float 1.0`; NaN payload kept; float struct field;
  `sqrt` declaration; 3-byte `'float'` error; golden `float.oymo`
- Decide: decimal literals as sugar for bytes? Hex float or decimal?
- Decide: float vectors: every symbol accepts them where LLVM does; reduction folds only
  scalars?

### `float-arith` `'fadd'`, `'fsub'`, `'fmul'`, `'fdiv'`, `'frem'`, `'fneg'`

- Opcodes `{type, a, b}`: `'fadd'`, `'fsub'`, `'fmul'`, `'fdiv'`, `'frem'`;
  `'fneg'` `{type, value}`
- LLVM's default FP environment only: round to nearest even, no traps, no fast-math, no
  constrained intrinsics
- `'float'` computed in binary64, then rounded to binary32
- Never fold a NaN result; a NaN operand folds if the result isn't NaN
- `'fneg'` flips only the sign bit; folds even on a NaN
- `fdiv` by zero gives ∞ or NaN
- Printed as LLVM: `fadd double a, b`
- Tests: edge operands (`±0`, `±1`, smallest subnormal, largest finite, `±∞`, NaN, both
  types) vs LLVM; `1.0 + 2.0` folds to `[0000000000000840]`; `0.0 / 0.0` stays;
  `'float'` `0.1 + 0.2` folds to the `float` bits

### `float-compare` Comparisons: every `fcmp` predicate

- `fcmp` with each predicate, shaped as `opcode-options` decides, giving `'i1'`:
  - ordered: `oeq`, `one`, `ogt`, `oge`, `olt`, `ole`
  - unordered: `ueq`, `une`, `ugt`, `uge`, `ult`, `ule`
  - `ord`, `uno`
- No `fcmp false`/`fcmp true`
- `-0.0` equals `+0.0` under `oeq`
- Error: `'icmp'` on a float type names the `fcmp` spelling to use
- Tests: every predicate × `{-∞, -1, -0, +0, 1, +∞, NaN}` vs LLVM; literal folds; `uno`
  with NaN folds to `[01]`

### `float-convert` `'fpext'`, `'fptrunc'`, `'fptosi'`, ... conversions

- Fields `{type, value, to}`, like `'zext'`: `'fpext' {'float', x, 'double'}`
- `'fpext'` `float` → `double`; `'fptrunc'` `double` → `float`, rounded
- `'fptosi'`, `'fptoui'`: toward zero; NaN, ∞, out of range: not folded
- `'sitofp'`, `'uitofp'`: rounded to nearest
- `'bitcast'`: any → any same-size type LLVM can bitcast (not structs)
- Error: `'fpext': to must be wider than double, got float.`
- Tests: `fptrunc` rounds to nearest even; `fptosi -1.5` is `-1`; `sitofp` of `2^53 + 1`
  rounds; `fptoui` of `-1.0`, NaN, `2^32` to `'i32'` not folded; `'bitcast'` of
  `[0000803f]` from `'float'` to `'i32'` is `[0000803f]`; narrowing and size errors
- Decide: add saturating `'fptosi_sat'`/`'fptoui_sat'`?

### `float-intrinsics` `'sqrt'`, `'fabs'`, `'floor'`, ... exact intrinsics

- Exact intrinsics only, `llvm.NAME` without the prefix:
  - `{type, value}`: `'sqrt'`, `'fabs'`, `'floor'`, `'ceil'`, `'round'`, `'roundeven'`,
    round toward zero (`llvm.trunc`)
  - `{type, magnitude, sign}`: `'copysign'`
  - `{type, a, b}`: `'minnum'`, `'maxnum'`, `'minimum'`, `'maximum'`
  - `{type, a, b, c}`: `'fma'`, rounded once
- Transcendentals are libm declarations:
  `sin = {type = {'function', {x = 'double'}, 'double'}, link = 'sin'}`
- Tests: edge operands vs LLVM; `fma` where twice-rounded differs; `minnum(NaN, 1.0)` is
  `1.0`, `minimum` is NaN; `minimum(-0.0, +0.0)` is `-0.0`; `'sqrt'` is
  `call double @llvm.sqrt.f64`
- Done when: `hypot(3.0, 4.0) = 5.0`; every float symbol matches LLVM on edge operands
  (NaN results: "is a NaN")
- Decide: name of `llvm.trunc`: one `'trunc'` by `type`, `'trunc_toward_zero'`, or
  `'ftrunc'`

### `ll-vectors` Vector opcodes, `extractelement`, `insertelement`, `shufflevector`

- Integer opcodes and `'icmp'` on `{'vector', n, t}`
- `'extractelement'`, `'insertelement'`, `'shufflevector'`
- Decide: does reduction fold vectors, or only scalars?

### `bulk-memory` `'memcpy'`, `'memmove'`, `'memset'`

- Three impure opcodes, result `{}`, bound by a `let` that only orders them (5.4e):

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

### `ll-volatile-asm` `volatile` loads and stores; inline asm

- `volatile` on `'load'`, `'store'` and the bulk ops, passed as `opcode-options` decides
- `'asm'` inline asm, as LLVM has it
- Goldens

### `ll-atomics` `'atomicrmw'`, `'cmpxchg'`, `'fence'`, orderings

- `'atomicrmw'`, `'cmpxchg'`, `'fence'`, atomic `'load'`/`'store'`, orderings, `syncscope`,
  as LLVM has them; orderings and `syncscope` passed as `opcode-options` decides
- Never folded
- Goldens
- Decide: fields of `'atomicrmw'`, `'cmpxchg'` (two orderings) and `'fence'`

### `ll-poison` `poison` and `undef` in bodies, poison flags, `'freeze'`

- `poison` and `undef` in bodies, spelled as `opcode-options` decides
- Flags that make results poison (`nsw`, `nuw`, `exact`, `disjoint`, `nneg`, `samesign`),
  passed as `opcode-options` decides
- `'freeze'`
- Goldens
- Decide: which poison-making flags

### `ll-instructions` `select` and `getelementptr` flags

- `'select' {type, c, a, b}` (LLVM `select`) for value choices
- `inbounds`, `nuw`, `nusw` on `'getelementptr'`, passed as `opcode-options` decides
- Goldens

### `bswap` `'bswap'` for byte order per access

- `'bswap' {'i32', x}`: `llvm.bswap.iN`, pure, folded
- Test: read a big-endian `'i32'` header field on a little-endian target

### `ll-intrinsics` `ctpop`, `ctlz`, `abs`, overflow checks, `assume`, `lifetime`, `trap`, …

- `ctpop`, `ctlz`, `cttz`, `abs`, `smin`/`smax`/`umin`/`umax`, `fshl`/`fshr`,
  `bitreverse`, `*.with.overflow`, `*.sat`
- `assume`, `expect`, `lifetime.start`/`end`, `trap`, `stacksave`/`stackrestore`,
  `returnaddress`, `prefetch`
- Goldens
- Decide: an opcode each (folded where pure), or a declaration named `"llvm.ctpop.i32"`
  called through `g` (never folded)

### `noalias` `noalias` on params and results

- `noalias` in `attr-slots`'s parameter and result slot: `ptr noalias %dst`,
  `noalias ptr @malloc(...)`
- Breaking the promise is undefined behaviour, unchecked
- Test: `dst[i] = src[i] * 2` over two `'ptr'` params; `-O2` leaves no `vector.memcheck`

### `ll-function-attrs` Calling conventions; function, parameter and result attributes

- Calling conventions in the `cc` slot (`attr-slots`): `fastcc`, `coldcc`, `tailcc`, …
- Function attributes in the entry slot: `nounwind`, `noreturn`, `noinline`,
  `alwaysinline`, `cold`, `memory(…)`, `willreturn`, `uwtable`, …
- Parameter and result attributes in the parameter slot: `nonnull`, `dereferenceable(n)`,
  `captures(none)`, `readonly`, `returned`, `noundef`, `byval`, `sret`, `range(…)`
- `prefix`, `prologue`
- Goldens

### `ll-symbol-fields` Global `align`, `linkage`, visibility, `unnamed_addr`, `section`, `comdat`

- In the entry slot (`attr-slots`): global `align`, linkages (`private`, `weak`,
  `linkonce_odr`, `extern_weak`, `common`, `appending`, …), visibility, `dso_local`,
  `unnamed_addr`, `local_unnamed_addr`, `section`, `comdat`, `externally_initialized`
- `llvm.used`, `llvm.compiler.used`, `llvm.global_ctors`/`dtors`: globals with `appending`
  linkage
- Code; goldens

### `ll-tls` `thread_local` on global variables

- `thread_local` in the entry slot (`attr-slots`), with LLVM's models (`localdynamic`,
  `initialexec`, `localexec`)
- Golden
- Decide: spelling of general-dynamic `thread_local` (no explicit model) vs a model name

### `line-tables` `-g` line tables from meta places

- `-g` on `emit-llvm` and `build`; the user passes `-g` to clang when linking
- One `DICompileUnit` per `File` in `meta.proto` holding a definition's place:
  - `DIFile(filename, directory, checksumkind: CSK_MD5, checksum)` from `File.path` and
    `File.md5`
  - `language: DW_LANG_C11`, `producer: "oymo <version>"`, `emissionKind: LineTablesOnly`
  - module flags `Dwarf Version` 5, `Debug Info Version` 3
- One `DISubprogram` per definition: `line:` from the symbol field's `Tag`, `scopeLine:`
  from the `body` lambda's `Tag`; empty `DISubroutineType`
- `!DILocation` (line, byte column from `File.position`) on every `let` and terminator; no
  place: `line: 0`
- Code from another `File` under a `DILexicalBlockFile`; no `inlinedAt`
- Each distinct location built once
- Tests: golden IR; passes `opt -passes=verify`
- Breakpoints, line stepping, backtraces in `gdb`/`lldb`
- Done when: `gdb` breaks on a line of a `.oymo` file and steps by its lines

### `ll-debug-info` Params, locals, types as DWARF metadata

- Metadata helpers: compile unit with module flags, file, subprogram, location, basic
  and composite types; each adds a node (reusing an equal one) and returns its index
- `DILocalVariable` for params and locals; `DIBasicType`, `DIDerivedType`,
  `DICompositeType`; the frontend gives names and types
- Goldens
- Decide: locals: is a location enough, or do `alloca`s need `#dbg_declare` records
  (`DILocalVariable`)?

### `alias-scopes` `!alias.scope`, `!noalias`, if `noalias` isn't enough

- Only for a program `noalias` can't serve
- Scoped aliasing metadata `!alias.scope`, `!noalias` per access, carried in `meta.proto`
- Decide: `meta.proto` schema for scope declarations on `Tags` and attachments on `Tag`

### `ll-instr-metadata` `!range`, `!tbaa`, `!prof`, `!llvm.loop`, module flags

- On instructions (fields on `Tag` in `meta.proto`): `!range`, `!nonnull`, `!noundef`,
  `!tbaa`, `!prof` branch weights, `!llvm.loop` hints, `!invariant.load`
- Module flags on `Tags` in `meta.proto`
- `source_filename` from `Tags.files`
- Call hints `tail`, `notail` on `Tag`
- Goldens
- Decide: `meta.proto` schema fields and reduction merge rules for each kind

### `ll-check` Every row tested; clang's `-O2` output written in oymomo

- Each golden passes `opt -passes=verify`
- Done when: every row of `docs/ll_coverage.md` has a golden or is "not planned"; the `.ll`
  clang writes for a C test program at `-O2` can be written in oymomo, construct for
  construct, except constructs marked "not planned"

### `assigned-before-use` Layer-1 check: a variable is assigned before it is read

- Layer-1 code checks that each variable is assigned on every path before it is read
- Then `var x: i32;` with no value is allowed
- Same pass as the substructural checks (a state per name; branches must agree)

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

### `label-opcodes` Opcodes between labels and byte arrays: `'struct.get'`, `'struct.labels'`, `'struct.with'`

- Labels are bytes now (`"\FF"`), so a label and a byte array can hold the same bytes;
  only an opcode moves between them (user: "the reason we need is to enable convertion
  between label and bytearray")
- With `s = {name = [01], age = [02]}`: `'struct.get' {s, 'name'}` ⟶ `[01]` (a label from
  data); `'struct.labels' s` ⟶ `{'name', 'age'}`; `'struct.with' {s, 'id', [07]}` ⟶
  `{name = [01], age = [02], id = [07]}`
- Uses: `unit.rebase` with a prefix built as data, paths as data (`data-addresses`),
  frontends that generate names
- Later (user: "Later: a new leaf `label-opcodes`; this leaf only makes labels bytes"):
  design when a use needs them
- Moved after the bootstrap (user: "i dont think we will need label-opcodes in bootstrap
  phase, right? if yes, move the leaf after the bootstrap"): frontends write labels in
  source, and `'unit.rebase'` already turns its byte-array prefix into labels
- Decided: a missing label gives no step (the call stays; the translation rejects it)
- Decide: `'struct.labels'` on unlabeled fields, `'struct.with'` replace or add, a label
  with byte 00, `'struct.get'` with `[]`

### `build-systems` `cc`-style flags, `-MD`/`-MF`, `compile_commands.json`, pkg-config

- `cc`-style flags: `-c`, `-o`, `-I`, `-L`, `-l`
- `-MD` / `-MF` dependency files
- `compile_commands.json`
- pkg-config: `oymo build --pkg-config sdl2`
- Done when: a Makefile uses `oymo -c` for `cc -c`, rebuilds only changes, links SDL via
  pkg-config

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
- Unions in the representation `tagged-unions` decides

### `volatile-asm` `volatile` and inline asm

- Mizar syntax for `volatile` and inline asm
- Done when: a signal handler sets a `volatile` flag; `rdtsc` via inline asm

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

### `debug-info` Mizar params, locals, types in DWARF

- Params, locals, types of Mizar in DWARF
- Variables printed in Mizar's or a language author's source
- Done when: `gdb` breaks in Mizar, steps, prints locals, in a program mixed with C

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

### `asan` ASan

- Pass `-fsanitize=address` to `clang`
- Definitions carry `sanitize_address` (`attr-slots`)
- Done when: ASan catches use after free in the linked-list program, with its Alcor line

### `separate-compilation` Separate compilation, incremental rebuilds

- Separate compilation and multiple modules, on module interfaces
- Incremental rebuilds
- Done when: changing one function body in the compiler rebuilds one object
- Decide: partial normalization: normalize a file before the glue binds it?

### `header-places` Places in generated files: source vs generated, not oymomo vs other

- Today `source.write` never writes a place into a `language oymomo` file (oymomo code is
  usually generated), so a header generated from a hand-written oymomo unit carries no
  places back to its definitions
- Idea: decide by source vs generated instead: never write places into generated files
  (under the destination folder, `out/`), keep places into source files of any language
- Every source file has the extension `.oymo`, Alcor and Mizar too; the `language` line
  says which
- Postponed until after the bootstrap (user: "lets return back to 'never write places into
  language oymomo files'. and put a roadmap leaf after bootstrap")

### `label-free` Labels and names out of the logic: positions, de Bruijn indices, fingerprints

- Plan (user): "remove all labels and parameter names, only keep unlabeled struct and
  bruijn index. for fingerprint and translate to production ready binary. the purpose is
  code logic should not depend on struct label and parameter name"
- A copy only: a pass computes a label-free copy of an ingot; ingots, ANF and headers keep
  their labels
- Every label in a body points into a struct of known shape (`p.a` from the function's
  type, `r.loop` from its region, `g.math.gcd` from the ingot), so the pass turns each
  `x.l` into a position and each name into a de Bruijn index without changing meaning
- Fingerprints: a hash of the copy changes only when the logic does
- Release `.ll` from the copy: locals unnamed; `link` names stay
- Decide: the fingerprint's hash and use

### `full-stdlib` Closures; formatted I/O, containers, pool and Boehm allocators

- Closures; split into code + `void *` environment when passed to C
- Formatted I/O, containers
- Pool and Boehm GC allocators
- On top of the bootstrap standard library
- Done when: one program runs with arena and Boehm allocators, switched in one line
- Decide: how does a closure capture a linear value? May a function value be linear
  (called exactly once)?

### `value-gc` Lua-style incremental GC for `Value`, replacing the arena

- Incremental mark-and-sweep in the `Value` library (as Lua 5.1+); objects don't move
- Roots: conservative stack scanning first; a shadow stack or LLVM stack maps later
- Write barrier inside the library's table writes
- Pin a `Value` passed to C while C holds it
- Same interface as the arena: no program changes
- Done when: a long-running loop over `Value`s runs in bounded memory

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
- VS Code breakpoints and launch configs via `gdb`/`lldb` (`line-tables`)
- Publish the extension on VS Marketplace and Open VSX
- Done when: editor shows errors as you type, goes to definition in C headers, hover types

### `atomics` Atomics in Mizar; C11 `_Atomic`

- C11 `_Atomic`
- Mizar syntax
- Done when: two pthreads share an atomic counter; total always right

### `tls` Thread-local storage in Mizar; `_Thread_local` shared with C

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
