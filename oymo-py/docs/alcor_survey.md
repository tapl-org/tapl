# Alcor syntax survey

Zig, C3, Odin, Hare, Jai, Goose, Carbon, Swift, Rust, C++, D, Cpp2, Terra and Nelua each
answer "a better C" differently. Java, Go, Kotlin and Scala, and from the TIOBE top 10
(Oct 2026) Python, JavaScript, C# and Visual Basic, with TypeScript and R, show what
mainstream programmers read every day. Ada, Modula-2, Oberon, OCaml and Racket bring
module and build-time ideas. Each topic below has one table of the twenty-nine plus C
(section 13, module systems, has four), then pros and cons for Alcor, then where the
languages agree. The syntax Alcor chooses is in
[alcor_kernel_syntax.md](alcor_kernel_syntax.md); this survey makes no decisions.

> [!NOTE]
> Checked in Oct 2026 from web-search summaries of the official docs, specs, release
> notes and repos; the official pages could not be opened directly. "(unverified)"
> marks a weak or conflicting source. Jai has no public spec (closed beta); its facts
> come from community docs and beta users. Carbon's and Cpp2's designs still change
> often; Nelua has no numbered releases. Check a detail against the language's own docs
> before a decision rests on it.

Already decided before the survey: `name: Type` declarations and
`fn add(a: i32, b: i32) -> i32 { return a + b; }`. Later decisions are in
[alcor_kernel_syntax.md](alcor_kernel_syntax.md).

The decision rules, from the roadmap: keep the form mainstream languages share (C's
first) unless fixing a known problem; everything is an expression; a type is a layer-1
expression; lowers simply to oymomo; when two of the twenty-nine agree, take that.

## 0. Status and aim

| Language | Version (Oct 2026) | Who | Aim |
|---|---|---|---|
| Zig | 0.16.0 (Apr 2026); 0.17.0 reported Oct 2026 (unverified); pre-1.0 | Andrew Kelley, Zig Software Foundation | No hidden control flow, no hidden allocation, no preprocessor or macros; `comptime` for everything build-time; drop-in C compiler (`zig cc`) |
| C3 | 0.8.x (0.8.0 May 2026, 0.8.6 latest); 0.9 freezes syntax (unverified), 1.0 planned 2028 | Christoffer Lernö | "An evolution, not a revolution" of C; C ABI compatible; modules, slices, optionals, contracts |
| Odin | monthly `dev-YYYY-MM` tags (dev-2026-10, unverified); stable, no 1.0 label | Ginger Bill | "Data-oriented language for sane software development"; used in production (EmberGen) |
| Hare | 0.26.0 (Feb 2026); pre-1.0 | Drew DeVault | Small, stable C successor; no generics or macros on purpose; QBE backend, no Windows or macOS |
| Jai | closed beta (0.2.0xx, unverified) | Jonathan Blow, Thekla | Fast builds, whole language at compile time (`#run`), for games |
| Goose | experimental, no tagged release (unverified) | Wouter van Oortmerssen | Memory safety with no heap, GC, refcounting or lifetime annotations: data stacks, inferred ownership roots; emits C |
| Carbon | no release; nightly toolchain; 0.1 "MVP for evaluation" end of 2026 at the earliest, 1.0 after 2028 | open source, started at Google (2022) | Experimental C++ successor: two-way C++ interop through Clang, checked generics, a path to memory safety |
| Swift | 6.4 (Sep 2026); mature; Embedded Swift experimental | Apple, swift.org steering groups | "Safe, fast, expressive"; safe by default, unsafe opt-in and marked; C and C++ interop through Clang |
| Rust | 1.99 (Oct 2026), edition 2024; mature | Rust Project, Rust Foundation (started at Mozilla) | Memory and thread safety with no GC: ownership, borrows, fenced `unsafe`; zero-cost abstractions |
| C++ | C++23 = ISO/IEC 14882:2024; C++26 technically done (Mar 2026), ISO ballot pending | WG21 (ISO C++ committee) | Zero-overhead abstraction over C (classes, RAII, templates, `constexpr`); C++26 adds reflection and contracts |
| D | DMD 2.113 (Aug 2026); LDC, GDC; stable for about 20 years | Walter Bright, D Language Foundation | "The power of C with the productivity of a modern language"; `-betterC` keeps a subset with no GC or runtime |
| Cpp2 | cppfront 0.8.1 (Jan 2025), no newer tag; experimental | Herb Sutter | A second syntax for C++, "10× simpler, 50× safer", lowering 1:1 to C++ |
| Terra | 1.2.1 (Jul 2026, unverified); maintained, niche | Zachary DeVito (Stanford), maintained by Elliott Slaughter | C-level language whose build-time language is Lua: types are Lua values; LLVM backend |
| Java | JDK 25 LTS (Sep 2025), 26, 27 (Sep 2026); mature, managed runtime | Oracle and OpenJDK | Memory-safe, "write once, run anywhere"; conservative, readable, backward compatible; GC and JIT |
| Go | 1.26 (Feb 2026); 1.27 reported Aug 2026 (unverified); mature, Go 1 promise since 2012 | Google (Griesemer, Pike, Thompson) | Small, simple, readable language for large software; fast builds; GC, goroutines |
| Kotlin | 2.4 (Jun 2026), 2.5 planned Dec 2026; mature | JetBrains, Kotlin Foundation | Fixes Java: null safety, less boilerplate, expressions; JVM, JS, Wasm, Native (LLVM, GC) |
| Scala | 3.10 (Oct 2026), 3.9 LTS (unverified dates); mature; Scala Native 0.5 | EPFL (Odersky), Scala Center | Fuses OO and FP; everything is an expression; Scala Native compiles to LLVM with a GC |
| Nelua | no numbered releases; rolling `master`, `nelua -v` prints `0.2.0-dev` (unverified); alpha | Eduardo Bart (edubart), small community | Lua syntax with static types; compiles to C; Lua metaprogramming at build time; optional GC; "simple, efficient, explicit" |
| Ada | Ada 2022 (ISO/IEC 8652:2023); next revision "Ada 202y" in ARG work (unverified); GNAT in GCC; GNAT Pro / SPARK Pro 26 (2026); mature, since 1983 | ISO WG9 and the Ada Rapporteur Group; AdaCore (GNAT, SPARK); first designed by Jean Ichbiah for the US DoD | Safe, readable, long-lived embedded and real-time systems; strong types, contracts, tasks; SPARK subset proves no run-time errors |
| Modula-2 | ISO/IEC 10514-1:1996 (base), -2 (generics), -3 (OO), all 1998 or earlier; GCC gm2 in GCC 16.2 (Aug 2026), 16.1 (Apr 2026); mature, frozen | Niklaus Wirth (1978, ETH); ISO WG13; gm2 by Gaius Mulley (in GCC since 13) | Safe, strongly typed systems language built on modules; separate definition and implementation; low-level access through `SYSTEM` |
| Oberon | Oberon-07 report rev. 3 May 2016 (final; Project Oberon sources last updated Mar 2020); frozen since Wirth died (Jan 2024); OBNC 0.17.2 (unverified as latest) | Niklaus Wirth, ETH Zurich (Oberon-2: Mössenböck; Component Pascal: Oberon microsystems) | As small as possible but no smaller; one-pass compiler, whole OS and compiler in a book (Project Oberon); safe typed records with extension; GC |
| OCaml | 5.5.2 (Oct 2026, unverified); 5.5.0 mid-2026, 5.4 (Oct 2025); mature, 5.x adds multicore | Inria origin; OCaml core team, OCaml Software Foundation, Tarides, Jane Street | Safe, fast functional language with strong static types, full inference and a rich module system; GC; domains and effect handlers since 5.0 |
| Racket | 9.3 (Aug 2026); line moved from 8.x to 9.0 in Nov 2025; Racket CS (on Chez Scheme) is the default since 8.0 (2021); mature | PLT group (Flatt, Findler, Felleisen, Krishnamurthi and others) | Language-oriented programming: build new languages with macros and `#lang`; teaching; dynamic typing, with Typed Racket and contracts as options |
| Python | 3.15.0 (Oct 2026; planned Oct 1, reported Oct 9 (unverified)); 3.14 (Oct 2025); mature, yearly releases | Python Software Foundation, Steering Council; created by Guido van Rossum | Readable, general-purpose, dynamic language; batteries included; GC; optional JIT and free-threaded builds |
| JavaScript | ECMAScript 2026 (17th edition, June 2026); Node.js 26 became LTS Oct 2026 (unverified); browsers update all the time | Ecma TC39 (ECMA-262); first made by Brendan Eich, Netscape 1995; Node.js by OpenJS Foundation | Dynamic, GC'd scripting for the web and servers; single-thread event loop; never break old code ("don't break the web") |
| TypeScript | 7.0 (Jul 2026, native port in Go, `tsc` in the `typescript` npm package); 6.0 (Mar 2026) last JS-based; 7.1 beta reported Oct 2026 (unverified); mature | Microsoft (Anders Hejlsberg and the TypeScript team) | Typed superset of JavaScript; static types checked then erased to plain JS; tooling for large codebases |
| C# | 14 with .NET 10 LTS (Nov 2025); 15 with .NET 11 in RC (go-live), GA due Nov 10 2026; mature, ECMA-334 | Microsoft (Anders Hejlsberg; Mads Torgersen leads design); open source (Roslyn) | Safe, general managed language on .NET (GC, JIT or Native AOT); low-level escape hatches: `unsafe`, `Span<T>`, `ref struct` |
| Visual Basic | VB 17.13 (2025, with VS 2022 17.13; ships in .NET 10 SDK); no newer language version found (unverified); stable, "no new syntax" policy since 2020 | Microsoft (.NET team, Roslyn compiler) | Easy, readable, English-like language for .NET apps; kept stable, gets only interop with new .NET and C# features; VB6/VBA are older COM-era tools |
| R | 4.6.1 (Jun 2026); 4.6.0 (Apr 2026); 4.6.2 expected late 2026 (unverified); mature, yearly x.y.0 in April | R Core Team, R Foundation (first made by Ihaka and Gentleman) | Statistics and graphics; interactive, vector-based, dynamic; GC; heavy work done in C/Fortran |
| C | C23 = ISO/IEC 9899:2024; C2y in progress; `defer` in TS 25755 | WG14 | Baseline: "trust the programmer", small, fast |

- Closest to Alcor's goals: C3 (stated aim), Odin and Hare (`name: Type`, C fixes), and
  D with `-betterC`, the longest-proven "C, but modern" with build-time code.
- Closest to "a type is a build-time value": Terra (types are Lua values, the strongest
  proof), Zig, Jai and Carbon (`Stack(i32)` is a build-time call). Nelua is close to
  Terra: Lua syntax, full Lua at build time that can see the compiler's types (`@T` is a
  value), and it emits C. Its build-time code is unhygienic, and the file holds two
  languages. It is alpha with no numbered releases, so its facts may drift.
- Closest to "`name: Type` everywhere over an existing language": Cpp2
  (`name: kind = value`, lowered 1:1 to C++). TypeScript adds static types to
  JavaScript, checks them, then erases them to plain JS.
- Other build-time models: Racket builds whole languages from macros and `#lang`, and
  runs macros in their own compile-time phase, so build state never leaks into run time.
  That is far more power than Zig `comptime`, but no hard border stops macros from hiding
  control flow. OCaml does metaprogramming out of band (PPX rewriters). TypeScript's
  type-level code is Turing-complete but cannot make values: a separate type language
  grows complex. Ada, Modula-2 and Oberon have no compile-time code beyond constant or
  static expressions (Ada adds generics). gm2 bolts on the C preprocessor, a sign that
  the gap hurts.
- Module ideas (why Ada, Modula-2, Oberon, OCaml and Racket are here): Ada and Modula-2
  split a spec (`.ads`, `.def`) from a body, so a body edit never rebuilds users. Oberon
  marks an export with one `*` and rejects stale clients by an interface key. OCaml's
  `.mli` is its only hiding tool. Racket keeps all names private until `provide`. C# and
  Visual Basic compile a whole assembly at once, and importers read only metadata. Pros:
  fast rebuilds, clear borders. Cons: two files per module (Ada, Modula-2), and import
  cycles are an error (Oberon, OCaml, Racket).
- Size and safety: Oberon-07 is the small end (33 keywords, a one-pass compiler, OS and
  compiler in one book), a lower bound for a feature budget. Ada is safety-first: checks
  are on by default, and its SPARK subset proves no run-time errors. Oberon fences unsafe
  access in the pseudo-module `SYSTEM`; Racket names its unchecked parts
  (`racket/unsafe/ops`, `ffi/unsafe`).
- Mainstream readers: ten of twenty-nine have a GC or a managed runtime: Java, Go,
  Kotlin, Scala, TypeScript, and the TIOBE top-ten picks Python, JavaScript, C#, Visual
  Basic and R. They say little about memory (C# is the exception, with `unsafe`,
  `Span<T>` and `ref struct`), but they set what "any programmer reads it at once" means.
  Kotlin and Scala are the expression languages Alcor's syntax follows (`if` and blocks
  give values, `val`/`var` with `name: Type`); Go is the small C-family language with
  `name Type` order. Visual Basic is the far end of readable: English-like, with `End X`
  closers, verbose but easy to read. OCaml, Racket and Oberon also have a GC, and Nelua
  has an optional one.
- C++, Carbon and Cpp2 are the C++ family; Swift is far bigger than C (ARC, protocols, a
  runtime); Rust is large (traits, lifetimes). They are here for single ideas: header
  import through Clang, safety modes, owned values, `name: Type` in a C family.
- C++ never breaks compatibility, so each fix sits beside the C feature it fixes (headers
  and modules, `int` and `int32_t`, `T a[N]` and `std::array`): the opposite of "keep the
  shared form unless fixing". JavaScript never breaks old code either ("don't break the
  web"), so two module systems (CommonJS `require` and ES modules) lived side by side for
  about ten years. Visual Basic took the other path: no new syntax since 2020, only
  interop with new .NET features. Java's long previews (`--enable-preview`) show a way to
  test syntax before freezing it.
- Pre-1.0 syntax churns (Zig, C3, Hare, Jai, Carbon, Cpp2, Nelua): borrow ideas, not
  surface details. C3 renamed keywords as late as 0.8.4; Zig moved `@cImport` out of the
  language in 0.17 (unverified); Carbon changed arrays from `[T; N]` to `array(T, N)`;
  Cpp2 is a prototype whose author now works on ISO papers (unverified). Mature languages
  change too: TypeScript 7.0 ported its compiler to Go and dropped old lookup modes, and
  Racket moved from 8.x to 9.0. Modula-2 and Oberon are frozen. Rust's editions (chosen
  per crate, mixed freely) show how to change syntax without splitting code.

## 1. Declarations

| Language | Form | Inference | Constants | Uninitialized |
|---|---|---|---|---|
| Zig | `var count: i32 = 0;` | `var x = 1;` | `const max: u32 = 100;` | `= undefined` |
| C3 | `int count = 0;` | `var` (macros, compile time) | `const MAX = 100;` (compile time only, UPPER case) | zero by default (unverified) |
| Odin | `count: i32 = 0` | `x := 1` | `MAX :: 100` | zero by default; `= ---` |
| Hare | `let count: int = 0;` | `let x = 5;` | `def MAX: size = 64;`; `const` is an immutable binding | `= @undefined` (0.26) |
| Jai | `count: s32 = 0;` | `x := 1;` | `MAX :: 100;` | zero by default; `= ---` |
| Goose | `var count: i32 = 0;` | `let x = 42;` | top-level `let` with a constant | not found |
| Carbon | `var count: i32 = 0;` | `var i: auto = 2;` | `let` (immutable); `N:! i32` (compile time) | not found |
| Swift | `var count: Int32 = 0` | `let name = "alcor"` | `let` (assigned once) | must assign before use |
| Rust | `let mut count: i32 = 0;` | `let x = 1;` | `const MAX: usize = 1024;`, `static` | must assign before use |
| C++ | `int count = 0;` | `auto n = 42;` | `constexpr int N = 64;`, `constinit`, `const` | indeterminate (C++26: erroneous value) |
| D | `int count = 0;` (no spiral: `int* p, q;` both pointers) | `auto x = 3.0;` | `enum N = 16;`, `immutable` | zero by default; `= void` |
| Cpp2 | `count: i32 = 0;` | `y := count + 1;` | `max_n: i32 == 100;` | allowed; checked to be set before use |
| Terra | `var count : int = 0` | `var b = 4.5` | Lua values spliced in, `constant(int, 3)` | undefined |
| Java | `int count = 0;` | `var names = new ArrayList<String>();` | `static final int MAX = 1_000;` | locals: checked before use; fields: zero |
| Go | `var count int32 = 0` | `n := 42` | `const Pi = 3.14159` (untyped, arbitrary precision) | zero by default |
| Kotlin | `var count: Int = 0` | `val n = 1` | `const val MAX = 10` (primitives, `String` only) | must have a value (or `lateinit`) |
| Scala | `var total: Long = 0` | `val count = 0` | `inline val Max = 1024` | must have a value |
| Nelua | `local count: int32 = 0` (`global` for exported) | `local x = 1` | `local MAX <const> = 100`, `local N <comptime> = 10` | zero by default; `<noinit>` leaves it unset |
| Ada | `Count : Integer := 0;` | none; only loop variables (`for X of Xs`) and type-less `X renames F (Y);` (2022) | `Max : constant Integer := 100;`; named number `N : constant := 100;` (universal, exact) | allowed, value may be invalid; `Default_Value` aspect, `pragma Normalize_Scalars`; SPARK flow analysis forbids reading it |
| Modula-2 | `VAR count: INTEGER;` (no initializer) | none | `CONST Max = 100;` (constant expressions) | undefined by default; gm2 can zero locals (unverified) |
| Oberon | `VAR count: INTEGER;` (no initializer) | none | `CONST max = 100;` (constant expression) | undefined (pointers set to `NIL` by the compiler; globals zeroed in practice, unverified) |
| OCaml | `let count : int32 = 0l` | `let n = 42` (full, Hindley-Milner) | every `let` is immutable; mutation via `ref` or `mutable` fields | none; must give a value (`Bytes.create n` has unset content) |
| Racket | `(define count 0)`; Typed: `(define count : Integer 0)` | dynamic typing; Typed Racket infers local types | none (no `const`); a module-level `define` can't be `set!` from outside the module | none; use before init raises an error (`letrec`, module order) |
| Python | `count: int = 0` (hint only) | `x = 1` (dynamic types) | `MAX: Final = 100` (checker only); `UPPER_CASE` by convention | `x: int` leaves it unbound; `NameError` on use |
| JavaScript | `let count = 0;` (`var` is old, function-scoped) | all dynamic; no static types | `const MAX = 100;` (fixed binding only; `Object.freeze` for values) | `let x;` is `undefined`; use before the line is a TDZ error |
| TypeScript | `let count: number = 0;` | `let x = 1;` (`const c = 1` gets literal type `1`) | `const max = 100;` (binding only); `as const` for deep readonly | `let x: number;` (use before assignment is an error); `let x!: number;` |
| C# | `int count = 0;` | `var x = 1;` (locals only); target-typed `Point p = new(1, 2);` | `const int Max = 100;` (build-time); `readonly` fields | locals must be definitely assigned; fields zeroed; `[SkipLocalsInit]` skips zeroing |
| Visual Basic | `Dim count As Integer = 0` | `Dim x = 1` (`Option Infer On`) | `Const Max As Integer = 100` | zero / `Nothing` by default |
| R | `count <- 0L` (also `=`, `assign("count", 0L)`) | dynamic typing; no type notes | none; `lockBinding("x", env)` | none; a name exists once assigned; `missing(arg)` for args |
| C | `int count = 0;` | `auto x = 1.5f;` (C23) | `constexpr int N = 16;` (C23), `#define`, `enum` | indeterminate |

- `name: Type`: nineteen of twenty-nine (not C3, C++, D, Java, C#, which put the type
  first; Go writes `name Type` with no colon, Visual Basic `name As Type`; JavaScript, R
  and plain Racket write no types, though Typed Racket uses `define count : Integer`).
  Python's `: int` is a hint only. D keeps C's order but drops the spiral (`int* p, q;`
  makes two pointers).
- A keyword first: Zig, Hare, Goose, Carbon, Swift, Rust, Terra, Go, Kotlin, Scala, Nelua
  (`local`), Modula-2 and Oberon (`VAR`), OCaml, Racket (`(define`), JavaScript,
  TypeScript, Visual Basic (`Dim`) (eighteen). Greppable, and a statement never starts
  with a bare name. Odin, Jai, Cpp2, Ada and Python have no keyword (`count: i32 = 0`);
  R starts with the bare name (`count <- 0L`). In Modula-2 and Oberon, `VAR` opens a block
  of declarations that take no initializer.
- Nelua's keyword is also its visibility: `local` for the file, `global` for the whole
  program.
- Immutable bindings with `let` or `val`: Goose, Carbon, Swift, Rust (`let mut`), OCaml,
  Kotlin, Scala (seven). In OCaml every `let` is immutable; mutation goes through `ref` or
  `mutable` fields. Java writes `final`, Ada `constant`, Nelua `<const>`; JavaScript and
  TypeScript write `const`; C# has `readonly` fields; Go has only build-time `const`;
  Hare's `let` is mutable, and so is the `let` of JavaScript and TypeScript. Racket and R
  have no `const`: a Racket module-level `define` can't be `set!` from outside the module,
  and R has `lockBinding`.
- `:=` inference: Odin, Jai, Cpp2, Go. Go's `:=` next to `=` causes shadowing bugs (`err`
  declared again in an inner scope). Ada also writes `:=`, but for the initial value after
  a written type (`Count : Integer := 0;`), so there it is not inference.
- Inference is mostly a keyword with no type (`var`, `let`, `val`, `auto`, `local`,
  `Dim`). Ada, Modula-2 and Oberon have none (Ada only for loop variables and `renames`).
  OCaml infers everything (Hindley-Milner). Racket, Python, JavaScript and R have dynamic
  types. C# also infers from the left side (`Point p = new(1, 2);`), and TypeScript gives
  `const c = 1` the literal type `1`.
- Build-time constants are spelled many ways: `::` (Odin, Jai), `==` (Cpp2, a comparison
  to C readers), `:!` (Carbon), `enum N =` (D), `def` (Hare), `const` (Zig, Rust, Go, C#),
  `Const` (Visual Basic), `CONST` (Modula-2, Oberon), `constant` (Ada), `<comptime>`
  (Nelua), `const val` (Kotlin, primitives only), `inline val` (Scala), `static final`
  (Java), `constexpr` (C, C++). Scala's `inline val` and Zig's `const` show a constant can
  just be a build-time value of an ordinary binding. C++'s four words (`const`,
  `constexpr`, `constinit`, `consteval`) show the cost of no single build-time layer.
  JavaScript and TypeScript `const` and Python `Final` are not build-time at all (a fixed
  binding, or a check by an outside tool); OCaml, Racket and R have no separate constant
  form.
- Constants with no type: Go's untyped `const` (arbitrary precision) and Ada's named
  numbers (`N : constant := 100;`, universal and exact) both let a literal fit any numeric
  type where it is used.
- Goose splits binding mutability (`let`/`var`) from data constness (`const u8[:]`), a
  fix for C's `const int *` vs `int *const`. JavaScript shows the gap without the split:
  `const` fixes only the binding, and the value needs `Object.freeze`; TypeScript adds
  `as const` for deep readonly.
- Uninitialized: zero by default (Odin, Jai, D, Go, Nelua, Visual Basic; Java and C#
  fields); an explicit opt-out marker (Zig `undefined`, Odin and Jai `---`, Hare
  `@undefined`, D `= void`, Nelua `<noinit>`, C# `[SkipLocalsInit]`, TypeScript `let x!`);
  always a value (Zig, Kotlin, Scala, OCaml); or checked to be set before use (Swift, Rust,
  Cpp2, Java locals, TypeScript, C# locals). Racket, Python, JavaScript and R catch it at
  run time instead (an error, `NameError`, a TDZ error). Modula-2 and Oberon leave it
  undefined, like C. C++26 makes an uninitialized read an "erroneous value" instead of UB.
- Ada allows an unset value that may be invalid, but lets a type pick a start value
  (`Default_Value`) or a build fill unset scalars (`pragma Normalize_Scalars`); SPARK flow
  analysis forbids the read. OCaml requires a value for every binding, yet
  `Bytes.create n` still hands back unset content: buffers are the hole even there.
- Agree: `name: Type` (nineteen of twenty-nine); a keyword first (eighteen); immutable
  `let`/`val` (seven); `:=` (Odin, Jai, Cpp2, Go); zero by default (Odin, Jai, D, Go,
  Nelua, Visual Basic); checked before use (Swift, Rust, Cpp2, Java, TypeScript, C#).

## 2. Functions

| Language | Definition | Multiple results | Default / named args |
|---|---|---|---|
| Zig | `fn add(a: i32, b: i32) i32 { … }` | struct or tuple, `const q, const r = f();` | no; options struct `.{ .x = 1 }` |
| C3 | `fn int add(int a, int b) { … }` | no (struct or optional) | yes: `add(b: 2, a: 3)` |
| Odin | `add :: proc(a, b: i32) -> i32 { … }` | `-> (q, r: int)`, named results, `q, r := f()` | yes: `f(b = 3)` |
| Hare | `fn add(a: int, b: int) int = a + b;` | tuple, `let (a, b) = f();` | no |
| Jai | `add :: (a: s32, b: s32) -> s32 { … }` | `-> int, bool`, named results | yes: `f(x = 3)` |
| Goose | `fn add(a: i32, b: i32) -> i32 { … }` | `-> i64, bool`, `let v, ok = f();` | not found |
| Carbon | `fn Add(a: i32, b: i32) -> i32 { … }` | tuple `-> (i32, i32)` | no (unverified) |
| Swift | `func add(_ a: Int, by b: Int = 1) -> Int { … }` | tuple `-> (q: Int, r: Int)`, `let (q, r) = f()` | defaults; argument labels are part of the name (`add(_:by:)`) |
| Rust | `fn add(a: i32, b: i32) -> i32 { a + b }` | tuple `-> (u32, u32)`, `let (q, r) = f();` | no; builder structs |
| C++ | `int add(int a, int b)` or `auto add(int a, int b) -> int` | struct, `std::tuple`, `auto [q, r] = f();` | defaults; no named |
| D | `int add(int a, int b) { … }` | struct, `Tuple`, `out` parameters | defaults; named `f(create: true)` (2.108) |
| Cpp2 | `add: (a: i32, b: i32) -> i32 = { … }` | named results `-> (q: i32, r: i32)` | defaults (unverified); no named |
| Terra | `terra add(a : int, b : int) : int … end` | tuple `: {int, double}`, `var a, b = f()` | no |
| Java | `static int add(int a, int b) { … }` (in a class) | a `record` | no; overloading instead |
| Go | `func add(a, b int32) int32 { … }` | `(q, r int)`, named results, `q, r := f()` | no |
| Kotlin | `fun add(a: Int, b: Int): Int = a + b` | `Pair` or a data class, `val (q, r) = f()` | yes: `f(b = 3)` |
| Scala | `def add(a: Int, b: Int): Int = a + b` | named tuple `(q: Int, r: Int)` | yes: `f(b = 3)` |
| Nelua | `local function add(a: int32, b: int32): int32 … end` | `function f(): (integer, integer) return 1, 2 end`, `local q, r = f()` | no; record arg `f{x=1}` by hand |
| Ada | `function Add (A, B : Integer) return Integer is begin return A + B; end Add;`; `procedure` when no result; `function Sq (X : T) return T is (X * X);` | none; `out` / `in out` parameters or a record | yes: `B : Integer := 0`, `F (X => 1, Y => 2)` |
| Modula-2 | `PROCEDURE Add(a, b: INTEGER): INTEGER; BEGIN RETURN a + b END Add;` | none; `VAR` parameters (ISO may return records and arrays) | no in ISO; gm2: last parameter optional, `[x: INTEGER = 0]` |
| Oberon | `PROCEDURE Add(a, b: INTEGER): INTEGER; BEGIN RETURN a + b END Add` (one `RETURN`, at the end) | no; `VAR` (by-reference) parameters; result can't be a record or array | no |
| OCaml | `let add (a : int) (b : int) : int = a + b` (curried) | tuple, `let q, r = f x` | yes: labelled `~x`, optional `?(x = 1)` |
| Racket | `(define (add a b) (+ a b))`, `(lambda (a b) …)` | `(values q r)`, `(define-values (q r) (quotient/remainder 7 2))` | yes: `(define (f x [y 1] #:z [z 2]) …)`, call `(f 1 #:z 3)` |
| Python | `def add(a: int, b: int) -> int:` | tuple, `return q, r`; `q, r = f()` | yes: `def f(x, y=0, *, key=None)`; `/` positional-only; `*args`, `**kwargs` |
| JavaScript | `function add(a, b) { return a + b; }`, `const add = (a, b) => a + b;` | return array or object, `const [q, r] = f();` | defaults `function f(a, b = 1)`; named via destructuring `function f({ x, y = 0 })`, `f({ x: 1 })` |
| TypeScript | `function add(a: number, b: number): number { … }`, `(a, b) => a + b` | tuple `[number, number]`, `const [q, r] = f();` or object | defaults `b = 1`, optional `b?: number`; named via object `{ x = 1 }: Opts` |
| C# | `int Add(int a, int b) { … }`, `=> a + b`; methods in types, local functions, top-level statements | tuples `(int q, int r) F()`, `var (q, r) = F();`; `out` params | yes: `void F(int x = 1)`, `F(x: 2)` |
| Visual Basic | `Function Add(a As Integer, b As Integer) As Integer … End Function`; `Sub` for no result | tuples `As (q As Integer, r As Integer)`, `ByRef` params | yes: `Optional b As Integer = 0`, named `f(b:=2)` |
| R | `add <- function(a, b) a + b`; `\(x) x + 1` | return a `list(q = q, r = r)` | yes: `function(x, n = 1)`, `f(n = 2, 3)`, partial name match, `...` |
| C | `int add(int a, int b) { … }` | struct or out-pointers | no; compound literal idiom |

- `fn` keyword: Zig, C3, Hare, Goose, Carbon, Rust (six of twenty-nine). Others: `func`
  (Swift, Go), `fun` (Kotlin), `def` (Scala, Python), `proc` (Odin), `terra` (Terra),
  `function` (Nelua, JavaScript, TypeScript, R), `PROCEDURE` (Modula-2, Oberon), `let`
  (OCaml), `define` (Racket). Ada (`function` / `procedure`) and Visual Basic (`Function` /
  `Sub`) use a different word when there is no result. None: Jai, C++, D, Cpp2, Java, C#
  (and C), so definitions can't be grepped. OCaml's `let` and Racket's `define` start
  every definition, not just functions. R, JavaScript and TypeScript can also bind a
  function value to a name (`add <- function(a, b)`, `const add = (a, b) => …`).
- `->` before the result: Odin, Jai, Goose, Carbon, Swift, Rust, Cpp2, Python, and C++'s
  trailing `auto f(int a) -> int` (nine). `: T` after the parameters: Kotlin, Scala,
  Terra, Nelua, Modula-2, Oberon, OCaml, TypeScript (eight; reads like a declaration).
  Right after `)`: Zig, Hare, Go. A word: Ada `return Integer`, Visual Basic
  `As Integer`. Before the name: C3, C++, D, Java, C# (and C). No result type at all:
  Racket, JavaScript, R.
- The body's value is its last expression: Scala, Rust, Goose, OCaml, Racket, R. Kotlin
  and Scala write a one-expression body with `=` (`fun add(a: Int, b: Int) = a + b`);
  C# and the JavaScript and TypeScript arrows use `=>`; Ada has expression functions
  (`return T is (X * X)`); Swift returns a single expression implicitly. Always
  `return`: C, Java, Go, Zig, Odin, Nelua, Modula-2, Oberon, Python, and Ada's full
  bodies. Oberon allows only one `RETURN`, at the end, so there is no early return.
- Rust's result without `return` (a last expression with no `;`) is easy to miss;
  Scala and Kotlin have no such `;` rule.
- Ada, Modula-2 and Oberon repeat the name at the end (`end Add;`, `END Add`); Visual
  Basic closes with `End Function`. The closer is easy to read and check, but verbose.
- Where functions live: Java and C# put them in types (C# also has local functions and
  top-level statements); a Visual Basic `Module` is a static class whose members are
  free functions after `Imports`.
- Multiple results: named results (Odin, Jai, Cpp2, Go) or a result list (Goose, Nelua
  `return 1, 2`), tuples (Zig, Hare, Carbon, Swift, Rust, Terra, OCaml, Python,
  TypeScript, C#, Visual Basic; Scala named tuples; C# and Visual Basic name the
  fields), Racket's multiple `values`, an array or object (JavaScript), a `list` (R), a
  record or data class (Java, Kotlin with destructuring), structs (C++ structured
  bindings, C), `out` or by-reference parameters (D, Ada, C#, Modula-2 and Oberon `VAR`,
  Visual Basic `ByRef`). Ada, Modula-2 and Oberon have no multiple results; Oberon can't
  even return a record or array, while ISO Modula-2 can. All lower to a struct return
  with no new ABI concept. Go's bare `return` with named results hides what is returned.
- Named arguments (C3, Odin, Jai, Swift, D, Kotlin, Scala, Ada, OCaml, Racket, Python,
  C#, Visual Basic, R; fourteen of twenty-nine) and defaults (also C++, Cpp2,
  JavaScript, TypeScript; gm2 Modula-2 for the last parameter only) are call-site
  rewriting. Zig gets both from an options struct, JavaScript and TypeScript from a
  destructured object, Nelua from a record argument by hand. Swift's labels become part
  of the function name. OCaml (`~x`), Racket (`#:z`) and Python (after `*`) mark some
  parameters as name-only in the definition; Python's `/` marks positional-only ones.
  R matches partial names, so a short name can bind to a longer parameter. Variadic
  forms: Python `*args`, `**kwargs`, R `...`. Overloading: Java, Kotlin, Scala, C++,
  Swift, D; none in Go.
- Parameter modes state intent and lower to a value or a pointer: Cpp2 `in`, `inout`,
  `out`, `move`; Swift `inout`, `borrowing`, `consuming`; D `ref`, `out`; Ada `in`,
  `out`, `in out`; C# `out`; Modula-2 and Oberon `VAR`; Visual Basic `ByRef`.
- OCaml functions are curried: `let add (a : int) (b : int)` takes one argument at a
  time, so `add 1` is a function that waits for `b`. Partial calls are short to write;
  a C-style call needs all arguments at once.
- Odin's default calling convention passes a hidden `context` pointer; Scala's `using`
  parameters are explicit in the signature and implicit at the call.
- Contracts on the signature: C++26 and Cpp2 `pre(b != 0)`, C3 `@require` in comments.
  Racket's `contract-out` checks values at the module border instead.
- Agree: `fn` (six of twenty-nine); `->` (nine); last expression is the value (Scala,
  Rust, Goose, OCaml, Racket, R; Kotlin, Swift, C#, JavaScript, TypeScript and Ada for
  one-expression bodies); named arguments (fourteen).

## 3. Types

| Language | Pointer | Many-item pointer | Slice | Array | Optional | Integer names | Cast |
|---|---|---|---|---|---|---|---|
| Zig | `*T` | `[*]T` | `[]T` | `[N]T` | `?T` | `i32`, `u8`, `usize`, `u3` | `@intCast(x)`, `@as(T, x)` |
| C3 | `int*` | (same as `int*`) | `int[]` | `int[4]` | `int?` (errors only) | `int`, `long` (64), `usz` | `(long)x` |
| Odin | `^T`, deref `p^` | `[^]T` | `[]T` | `[N]T` | `Maybe(T)` (library) | `i32`, `u8`, `int`, `uintptr` | `cast(T)x`, `T(x)`, `transmute` |
| Hare | `*T` (never null), `nullable *T` | `[*]T` | `[]T` | `[N]T`, `[_]T` | `nullable *T`, `(T \| void)` | `i32`, `u8`, `int`, `size` | `x: u16`, `x as T` |
| Jai | `*T`, address-of `*x` | none | `[]T` | `[N]T`, `[..]T` | none | `s32`, `u8`, `int` (= s64) | `cast(T) x`, `xx x` |
| Goose | `T&` | none | `T[:]` | `T[k]` and five growable kinds | `T?` | `i32`, `u8`, `i64` | `x as T`, `x as! u8` |
| Carbon | `T*` (never null, no arithmetic) | none | library (unsettled) | `array(T, N)` | `Optional(T*)` | `i32`, `u8`, `iN` | `x as T` |
| Swift | `UnsafePointer<T>` (library), `.pointee` | `UnsafeBufferPointer<T>` | `Span<T>` | `[N of T]` (`InlineArray`) | `T?` | `Int32`, `UInt8`, `Int`, `CInt` | `Int32(x)`, `Int32(truncatingIfNeeded: x)` |
| Rust | `*const T`, `*mut T` (raw); `&T`, `&mut T` (borrows) | none | `&[T]` | `[T; N]` | `Option<&T>` | `i32`, `u8`, `usize` | `x as u8` (truncates), `u8::try_from(x)` |
| C++ | `T*`, `T&` | (same as `T*`) | `std::span<T>` | `T a[N]`, `std::array<T, N>` | `std::optional<T>` | `int`, `std::int32_t` | `static_cast<T>(x)`, `std::bit_cast` |
| D | `T*` | (same as `T*`) | `T[]` | `T[N]` (a value, no decay) | `Nullable!T` (library) | `int` (32), `long` (64), `ubyte` | `cast(T) e` |
| Cpp2 | `*T`, deref `p*`, address `x&` (no arithmetic) | none | `std::span<T>` | `std::array<T, N>` | `std::optional<T>` | `i32`, `u8` | `x as T`, `unchecked_narrow<T>(x)` |
| Terra | `&T`, deref `@p` | (same as `&T`) | none | `T[N]` | none | `int32`, `uint8`, `int` (32) | `[T](e)` |
| Java | none (references only) | none | none (FFM `MemorySegment`) | `int[]` (heap, carries its length) | `Optional<T>` (library) | `int`, `long` (no unsigned) | `(int) x` |
| Go | `*T` (no arithmetic outside `unsafe`) | none | `[]T` | `[N]T` | none (`nil`) | `int32`, `uint8`, `int` (word) | `int64(x)` |
| Kotlin | none; Native interop `CPointer<T>` | none | none | `IntArray`, `Array<T>` | `T?` | `Int`, `Long`, `UInt` | `x.toLong()`; `as` for references |
| Scala | none; Native `Ptr[T]` | none | none | `Array[Int]`; Native `CArray[T, N]` | `Option[T]` | `Int`, `Long`; Native `UInt` | `x.toLong`, `asInstanceOf[T]` |
| Nelua | `*T`, `&x`, `$p` | `*[0]T` (unbounded array) | `span(T)` | `[N]T` | none (`nilptr`, `niltype`) | `int32`, `uint8`, `isize`, `usize`, `integer` (int64), `cint` | `(@int32)(x)`; implicit narrowing checked |
| Ada | `access T`, `access all T`, `not null access T` | none; `System.Address`, `Interfaces.C.Pointers` | `A (2 .. 5)`; arrays carry bounds (`String`, `A'Range`) | `array (1 .. N) of T` (any discrete index) | none; `null` on access types, variant record | `Integer`, `Natural`, `type Byte is mod 256;`, `range 0 .. 100`, `Interfaces.Unsigned_8` | `Integer (X)` (checked); `Ada.Unchecked_Conversion` |
| Modula-2 | `POINTER TO T` | none; `ADDRESS` with `ADDADR` (ISO `SYSTEM`) | open array parameters only, `ARRAY OF T`, `HIGH(a)` | `ARRAY [0..N-1] OF T` | none (`NIL`) | `INTEGER`, `CARDINAL`, `LONGINT`; gm2 `SYSTEM.INTEGER32`, `CARDINAL8`; `BYTE`, `WORD`, `LOC` | `VAL(T, x)` (convert), `CAST(T, x)` (bits, ISO `SYSTEM`); PIM `T(x)` |
| Oberon | `POINTER TO R` (records only; Oberon-2 also arrays) | none (`SYSTEM.ADR`, `SYSTEM.GET/PUT`) | open array parameter `ARRAY OF T` (params only) | `ARRAY N OF T` | none (`NIL`) | `INTEGER`, `BYTE`, `REAL`, `CHAR`, `SET` (Oberon-2/CP: `SHORTINT`, `LONGINT`) | `FLOOR(x)`, `FLT(i)`, `ORD(c)`, `CHR(i)`, `SYSTEM.VAL(T, x)`; type guard `p(T)` |
| OCaml | none (boxed values; `ref`, `'a ref`) | none | none (`Bigarray.Array1.sub`; `Bytes.sub` copies) | `int array`, `[\| 1; 2 \|]` (length at run time); `iarray` since 5.4 | `'a option` (`Some x`, `None`) | `int` (63-bit), `int32`, `int64`, `nativeint`, `char`; no unsigned | `Int64.of_int x`, `float_of_int x`; never implicit |
| Racket | none (all values are references); `(box v)`; FFI `_pointer` | FFI only: `ptr-ref`, `ptr-add` | none; ranges `(in-vector v 2 5)`, copy `vector-copy` | `(vector 1 2 3)`, `(make-vector n 0)`, `(make-bytes n)` | none (`#f` by habit); Typed: `(Option T)` | exact integers (fixnum, then bignum), flonums; FFI `_int32`, `_uint8` | `exact->inexact`, `(exact-round x)`; Typed: `(cast x T)`, `(ann x T)` |
| Python | none (all values are references) | none (`ctypes.POINTER(T)`, `memoryview`) | `xs[a:b]` (copies a `list`); `memoryview` shares | `list`, `tuple`, `array.array('i')` | `T \| None` (hint) | `int` (unbounded), `float`, `complex`, `bool` | `int(x)` (converts); `typing.cast(T, x)` (checker only) |
| JavaScript | none (objects are references) | none | none; `a.slice()` copies; typed array view `new Uint8Array(buf, off, len)` | `[1, 2, 3]` (growable); `new Int32Array(n)` (fixed) | none; `null`/`undefined`, `?.`, `??` | none; `Number` (f64), `BigInt` `10n`; typed arrays `Int8Array` … `BigUint64Array` | `Number(x)`, `BigInt(x)`, `String(x)`, `x \| 0` |
| TypeScript | none (objects are references) | none | none (`subarray` views on typed arrays only) | `T[]`, `Array<T>`, tuple `[T, U]` | `T \| undefined`, `x?: T`, `?.`, `??` | `number` (f64), `bigint`; no sized ints | `x as T` (unchecked, no runtime effect); `Number(x)` converts |
| C# | `T*` in `unsafe`; managed `ref T`; class values are GC refs | `T*` with arithmetic (`unsafe`) | `Span<T>`, `ReadOnlySpan<T>`, `xs[1..3]`; implicit span conversions (C# 14) | `T[]` (GC heap); `[InlineArray(N)]` struct; `fixed int a[4]` (`unsafe`) | `T?` (`Nullable<T>` for value types; annotation only for refs) | `int`, `byte`, `sbyte`, `uint`, `long`, `nint` (word), `Int128` | `(int)x`, `checked((int)x)`, `x as T` |
| Visual Basic | none (managed refs; `ByRef`; `IntPtr`); no `unsafe` | none | none in syntax; can use `Span(Of T)` with limits (unverified) | `Dim a(9) As Integer` (upper bound, 10 items), `Integer()` | `Integer?`, `Nullable(Of T)`; `Nothing` | `SByte`, `Byte`, `Short`, `Integer`, `Long`, `UInteger`, `ULong` | `CInt(x)`, `CType(x, T)`, `DirectCast`, `TryCast` |
| R | none (environments and `externalptr` act as references) | none | `x[2:5]` (a copy) | vectors `c(1, 2)`, `numeric(n)`, `array(0, dim = c(2, 3))`, 1-based | none; `NULL`, `NA` | `integer` (32-bit), `double`, `raw` (byte); no 64-bit int in base | `as.integer(x)`, `as.numeric(x)` |
| C | `T *p` | (same as `T *`) | none | `T a[N]`, decays | null pointer | `int32_t`, `size_t`, `_BitInt(N)` | `(T)x` |

- Prefix pointers read left to right with `name: Type` ("p is a pointer to T"): Zig,
  Hare, Jai, Cpp2, Go, Nelua (`*T`), Rust (`*const T`), Odin (`^T`), Terra (`&T`) (nine).
  Word forms read the same way: Ada `access T`, Modula-2 `POINTER TO T`, Oberon
  `POINTER TO R` (records only), which makes twelve in all. Ada's `not null access T`
  puts the null rule in the type. Suffix `T*` keeps C's look: C3, Carbon, D, C++, C#
  (in `unsafe`) (Goose `T&`). Generic-type spelling: Swift `UnsafePointer<T>`, Kotlin
  Native `CPointer<T>`, Scala Native `Ptr[T]`, Python `ctypes.POINTER(T)`: closest to
  Alcor's types-as-calls `Ptr(T)`. Ten have no pointers in the core language: Java,
  Kotlin, Scala, OCaml, Racket, Python, JavaScript, TypeScript, Visual Basic and R.
- Dereference: postfix `p.*` (Zig), `p^` (Odin), `p*` (Cpp2), `!p` (Scala Native); prefix
  `@p` (Terra), `$p` (Nelua); C's `*p` (C++, D, Carbon, Rust, Go).
- Separate one-item and many-item pointers (Zig, Odin, Hare) fix C's `T*` meaning both.
  Nelua writes the many-item kind as `*[0]T`, a pointer to an unbounded array. Go has
  no pointer arithmetic outside `unsafe` (`unsafe.Add`, `unsafe.Slice`). C# allows it
  only in `unsafe`. Ada, Modula-2 and Oberon keep raw addresses apart from typed
  pointers: `System.Address`, `ADDRESS` with `ADDADR`, `SYSTEM.ADR`.
- Unsafe parts fenced off by name: Go and C# `unsafe`, Modula-2 and Oberon `SYSTEM` (in
  Oberon, importing it marks the module unsafe), Racket `ffi/unsafe`. Visual Basic has
  no `unsafe` at all. A pro: one name finds every raw-memory spot in the code.
- Slices built in: Zig, C3, Odin, Hare, Jai, Goose, Rust, D, Go, Ada (`A (2 .. 5)`)
  (ten). Library or generic type: C++, Cpp2, Swift, C# (`Span<T>`, with `xs[1..3]`
  syntax), Nelua (`span(T)`). Open array parameters only, so a slice exists only as a
  parameter: Modula-2, Oberon (`ARRAY OF T`). Copy syntax only: Python `xs[a:b]`
  (`memoryview` shares), R `x[2:5]`. Views on typed arrays only: JavaScript,
  TypeScript, OCaml (`Bigarray`). None: Terra, C, Java, Kotlin, Scala, Racket, Visual
  Basic (Carbon unsettled). The C# compiler checks where a `Span<T>` may escape
  (`ref struct`, `scoped`).
- Fixed arrays: `[N]T` (Zig, Odin, Hare, Jai, Go, Nelua); `T[N]` (C3, D, Terra, C);
  `[T; N]` (Rust); `array(T, N)` (Carbon); words: `array (1 .. N) of T` (Ada),
  `ARRAY [0..N-1] OF T` (Modula-2), `ARRAY N OF T` (Oberon); library (C++, Cpp2
  `std::array`, Swift `[N of T]`, Scala Native `CArray[T, Nat._8]`, awkward without
  number parameters); attribute or `unsafe` only (C# `[InlineArray(N)]`,
  `fixed int a[4]`). Java's `int[]` is a heap object that carries its length. C#'s
  `T[]` also lives on the GC heap. In OCaml, Racket, Python, JavaScript, TypeScript and
  R the length is known only at run time (JavaScript's `Int32Array` is fixed, but its
  size is set at run time; R counts from 1). Visual Basic's `Dim a(9)` gives the upper
  bound, so it holds ten items: an easy off-by-one.
- Ada arrays carry their bounds (`A'Range`, `String`) and can use any discrete type as
  the index. Ada also has range and modular integer types: `range 0 .. 100`,
  `type Byte is mod 256;` (wraps on purpose). Pro: they remove whole classes of bugs
  cheaply. Con: more kinds of integer type to learn and check.
- Non-null by default: Hare (`nullable *T`), Carbon (`Optional(T*)`), Rust (`&T`,
  `Option<&T>`), Swift and Kotlin (`T?`), Zig and Goose (`?T`, `T?`). OCaml has no null
  at all (`'a option`). Ada does the reverse: access types may be null unless marked
  `not null`. Optional as a union: Hare `(T | void)`, Python `T | None` (a hint),
  TypeScript `T | undefined`. C# `T?` is a real type for value types but only an
  annotation for references. Visual Basic has `Integer?`, Typed Racket `(Option T)`.
  Java's implicit nullable references and Go's `nil` are widely seen as mistakes.
  Nelua (`nilptr`), Modula-2 and Oberon (`NIL`) have plain nil pointers too. JavaScript
  has two kinds of nothing (`null`, `undefined`), eased by `?.` and `??` (TypeScript
  too).
- Types as applied calls: Carbon `array(T, N)`, `iN`; Terra `vector(float, 4)`; Swift
  `InlineArray<N, T>`; C `_BitInt(N)`; Zig `@Int(.unsigned, 10)`; Nelua `span(T)`;
  Python `ctypes.POINTER(T)`; Typed Racket `(Option T)`. A width or length parameter
  fits "a type is a layer-1 expression". Nelua goes further: types are values (`@T`),
  and its cast `(@int32)(x)` writes the type as an expression.
- Integer names: `i32`/`u8` (Zig, Odin, Hare, Goose, Carbon, Rust, Cpp2: seven); `int32`
  (Go, Terra, Nelua, OCaml); `s32` (Jai); `Int32` (Swift); `Int`, `Long`, `UInt`
  (Kotlin, Scala); C names (C3, D, C++, C, Java, C#); word names (Visual Basic `Short`,
  `Integer`, `UInteger`; Ada `Integer`, `Natural`; Modula-2 `INTEGER`, `CARDINAL`;
  Oberon `INTEGER`, `BYTE`). gm2 adds sized names (`INTEGER32`, `CARDINAL8`), and Ada
  has `Interfaces.Unsigned_8`. No sized integers: Python and Racket (unbounded, so no
  overflow), JavaScript and TypeScript (f64 numbers plus `BigInt`; exact only up to
  2^53), R (32-bit `integer` only). Java has no unsigned types, another known mistake.
  OCaml (63-bit `int`) has none either, and base R has no 64-bit integer.
- Conversions: `x as T` (Hare, Goose, Carbon, Rust, Cpp2, C#, TypeScript: seven;
  TypeScript's is unchecked and does nothing at run time); `T(x)` (Go, Odin, Swift, Ada,
  Modula-2 PIM, Python, JavaScript, TypeScript: eight); `cast(T) x` (Odin, Jai, D);
  two-argument calls (Modula-2 `VAL(T, x)`, Oberon `SYSTEM.VAL(T, x)`, Visual Basic
  `CType(x, T)`, Typed Racket `(cast x T)`, Python `typing.cast(T, x)`, for the checker
  only); named functions (`x.toLong()` in Kotlin and Scala, OCaml `Int64.of_int x`, R
  `as.integer(x)`, Racket `exact->inexact`, Visual Basic `CInt(x)`, Oberon `FLOOR`,
  `ORD`); `(T)x` (C, Java, C#); `(@int32)(x)` (Nelua); `[T](e)` (Terra);
  `static_cast<T>(x)` (C++).
- Convert and reinterpret spelled apart: Modula-2 `VAL(T, x)` converts, `CAST(T, x)`
  keeps the bits. Likewise Ada `Integer (X)` vs `Ada.Unchecked_Conversion`, Odin `cast`
  vs `transmute`, C++ `static_cast` vs `std::bit_cast`. Checked narrowing has its own
  form in Rust (`u8::try_from(x)`) and C# (`checked((int)x)`). In Ada the plain
  `Integer (X)` is already checked.
- No implicit conversions: Go, Rust, Kotlin, Swift, Odin, Hare, OCaml (seven); widening
  only: Zig, Java, C3, D. Nelua even allows implicit narrowing, with a check (run-time
  checks drop in release builds). C# 14 adds implicit conversions to spans.
- Agree: prefix pointers (nine; twelve with the Ada, Modula-2 and Oberon word forms);
  built-in slices (ten); `[N]T` (six); `i32`/`u8` names (seven); non-null pointers
  (Hare, Carbon, Swift, Rust, Kotlin; OCaml has no null); no implicit conversions
  (seven); `as` casts (seven); `T(x)` (eight).

## 4. Structs, enums, unions

| Language | Struct | Literal | Through a pointer | Tagged union | Methods |
|---|---|---|---|---|---|
| Zig | `const P = struct { x: i32 = 0 };` | `P{ .x = 1 }`, `.{ .x = 1 }` | `.` (auto-deref), `p.*` | `union(enum) { a: f32, b: P }` | functions in the type; `a.f(b)` |
| C3 | `struct P { int x; int y; }` | `{ .x = 1, .y = 2 }` | `.` | none (struct plus enum) | `fn void P.move(&self)` |
| Odin | `P :: struct { x, y: int }` | `P{x = 1}` | `.` | `union { A, B }`, by type | none; `using` |
| Hare | `type p = struct { x: int };` | `p { x = 1 }` | `.` | `(a \| b)`, `match` | none |
| Jai | `P :: struct { x: float; }` | `P.{1, 2}`, `.{x = 1}` | `.` | none (enum plus union) | none; `using` |
| Goose | `struct P { x: f64, y: f64 = 0.0 }` | `P { x: 1.0, .. }` (unverified) | `.` | `enum Shape { Circle { r: f64 }, Dot }` | UFCS: `x.f(a)` is `f(x, a)` |
| Carbon | `class P { var x: i32; }`; structural `{.x: i32}` | `{.x = 1, .y = 2}` | `p->x` (sugar for `(*p).x`) | `choice Shape { Circle(f64), Empty }` | in the class, receiver `[self: Self]` |
| Swift | `struct P { var x: Int }` | `P(x: 1, y: 2)` | `p.pointee.x` | `enum Shape { case circle(radius: Double) }` | in the type or an `extension`; `mutating` |
| Rust | `struct P { x: f32, y: f32 }` | `P { x: 1.0, y: 2.0 }`, `P { x, ..p }` | `.` (auto-deref) | `enum Shape { Circle { r: f32 }, Empty }` | `impl P { fn len(&self) }`; `P::len(&p)` |
| C++ | `struct P { int x, y; };` | `P p{.x = 1, .y = 2};` | `->` | `std::variant<A, B>` (library) | in the class |
| D | `struct P { int x, y; }` | `P(x: 1, y: 2)`, `P s = {x: 1}` | `.` | `SumType!(A, B)` (library) | in the struct; UFCS |
| Cpp2 | `point: @struct type = { x: i32 = 0; }` | `p: point = (1, 2);` (unverified) | `p*.x` | `@union type` (generated accessors) | explicit `this`; UFCS |
| Terra | `struct P { x : int; y : int }` | `{1, 2}`, `{ x = 1 }` | `.` | none | `terra P:m(…)`, called `p:m()` |
| Java | `record Point(int x, int y) {}` | `new Point(1, 2)` | `.` (references) | sealed interface plus records | in the type |
| Go | `type Point struct { X, Y int }` | `Point{X: 1, Y: 2}` | `.` | none (interfaces, type switches) | outside the struct, with a receiver |
| Kotlin | `data class P(val x: Int, val y: Int)` | `P(1, y = 2)` | `.` (references) | `sealed interface` plus classes | in the class; extension functions |
| Scala | `case class Point(x: Double, y: Double)` | `Point(1, 2)` | `.` (references) | `enum Shape { case Circle(r: Double) … }` | in the class; `extension` |
| Nelua | `local Point = @record{x: integer, y: integer}` | `Point{x=1, y=2}`, `(@Point){1, 2}` | `.` (auto-deref), `$p` | none (`@union{…}` untagged, `@enum{…}`) | `function Point:len() … end`, `p:len()`; metamethods `__add`, `__index` |
| Ada | `type Point is record X, Y : Integer := 0; end record;` | `(X => 1, Y => 2)`, `(1, 2)`, `(others => 0)`; `P with delta X => 3` (2022) | `.` (auto-deref), `P.all` | variant record: `type Shape (K : Kind) is record case K is when Circle => R : Float; … end case; end record;` (checked) | primitive subprograms in the same package; `Obj.Op (B)` on `tagged` types; dispatch via `T'Class` |
| Modula-2 | `TYPE Point = RECORD x, y: INTEGER END;` | ISO `Point{1, 2}` (by position) | `p^.x`; `WITH p^ DO … END` | variant record `CASE kind: Kind OF A: r: REAL \| B: … END` (tag not checked by default) | none (ISO OO part 3 has `CLASS`; not in gm2) |
| Oberon | `TYPE P = RECORD x, y: INTEGER END;` | none | `p.x` (auto-deref of `p^.x`) | none; record extension `RECORD (Base) … END` with `IS` and type `CASE` | none in -07 (procedure-typed fields); Oberon-2/CP: `PROCEDURE (p: P) Draw;` |
| OCaml | `type point = { x : int; mutable y : int }` | `{ x = 1; y = 2 }`, `{ p with x = 3 }` | `.` (`p.x`, `p.y <- 3`); `!r` for refs | `type shape = Circle of float \| Rect of point` | none; functions in a module (objects exist: `method`) |
| Racket | `(struct point (x y) #:mutable #:transparent)` | `(point 1 2)` | none; accessors `(point-x p)` | none built in; structs plus `match`; Typed: `(U A B)` | none in structs; generic interfaces `#:methods gen:custom-write`; classes `(send obj m)` |
| Python | `@dataclass class P: x: int = 0` | `P(x=1)` | `.` (everything is a reference) | none built in; `A \| B` hints plus `match`; `enum.Enum` | `def f(self, b):` in the class; `a.f(b)` |
| JavaScript | `class P { x = 0; y = 0; }` or plain object | `{ x: 1, y: 2 }`, `new P()` | `.` (all objects by reference) | none; by convention `{ kind: "a", … }` | in the class body `f() { … }`; `a.f(b)`; prototypes |
| TypeScript | `interface P { x: number }`, `type P = { x: number }`, `class P { x = 0 }` | `{ x: 1, y: 2 }`, `new P()` | `.` (all objects by reference) | discriminated union `{ kind: "a"; r: number } \| { kind: "b"; p: P }`, narrowed by `switch (v.kind)` | in a `class`, `a.f(b)`; `enum E { A, B }` (not erasable) |
| C# | `struct Point { public int X, Y; }`, `record struct Point(int X, int Y);` | `new Point { X = 1, Y = 2 }`, `new(1, 2)`, `p with { X = 3 }` | `p->X` (`unsafe`), `.` through `ref` | C# 15: `union Pet(Cat, Dog);` (type union, boxes by default); closed hierarchies; before: class tree plus patterns | in the type; extension blocks `extension(T t) { … }` (C# 14) |
| Visual Basic | `Structure P : Public X As Integer : End Structure` (also `Class`) | `New P With {.X = 1}` | `.` (classes are refs) | none | inside the type, `Me`; `<Extension>` in a `Module` |
| R | `list(x = 1, y = 2)`; S4 `setClass("P", representation(x = "numeric"))` | `list(x = 1)`, `new("P", x = 1)` | `p$x`, `p@x` (S4); values copy on change | none; `class` attribute plus `inherits()` | generic functions: S3 `print.P <- function(x, ...)`, S4 `setMethod`; `setRefClass` has `obj$f()` |
| C | `struct P { int x; };` | `{ .x = 1 }`, `(struct P){…}` | `->` | manual struct plus union | none |

- `.` through pointers: thirteen of twenty-nine (Zig, C3, Odin, Hare, Jai, Goose, Rust, D,
  Terra, Go, Nelua, Ada, Oberon); Java, Kotlin, Scala, Python, JavaScript, TypeScript and
  Visual Basic have only references and use `.` too, and OCaml uses `.` on records. Nelua
  and Ada also keep an explicit deref (`$p`, `P.all`). Carbon and C++ keep `->`, and so
  does C# for raw pointers in `unsafe` code (it uses `.` through `ref`); Cpp2 writes
  `p*.x`, Swift `p.pointee.x`, Modula-2 `p^.x` (Oberon lets `p.x` stand for it). Racket
  has no `.` and uses accessors, `(point-x p)`; R uses `p$x`, or `p@x` for S4.
- Literals: designated `{ .x = 1 }` (C, C3, Zig, Carbon, C++20); `Point{X: 1}` (Go; Nelua
  `Point{x=1, y=2}`); named fields with no type name (`(X => 1, Y => 2)` Ada,
  `{ x = 1; y = 2 }` OCaml, `{ x: 1, y: 2 }` JavaScript, TypeScript); a constructor call
  (`P(x: 1)` D, Swift; `P(1, y = 2)` Kotlin, Scala; `new P(1, 2)` Java; `P(x=1)` Python;
  `(point 1 2)` Racket; `new("P", x = 1)` R); object initializers (`new Point { X = 1 }`
  C#, `New P With {.X = 1}` Visual Basic). By position: ISO Modula-2 `Point{1, 2}`,
  Nelua `(@Point){1, 2}`, Ada `(1, 2)`. Oberon has no record literal.
- Copy with changes: `P { x, ..p }` Rust, `{ p with x = 3 }` OCaml, `p with { X = 3 }`
  C#, `P with delta X => 3` Ada 2022. Ada's `(others => 0)` fills every field at once.
- A type bound to a name (`const P = struct {…}`, `P :: struct`, Terra's
  `local S = struct {…}`, Nelua's `local Point = @record{…}`, Go's `type P struct {…}`;
  also `TYPE P = RECORD … END` in Modula-2 and Oberon, Ada's `type Point is record`,
  OCaml's `type point = {…}`, TypeScript's `type P = {…}`) is the honest form if types
  are layer-1 values; `struct P {…}` (C, C3, Goose, Swift, Rust, D, C++, Terra, C#) is
  what C readers expect. Python's classes are ordinary run-time values, but it writes
  `class P:`.
- Tagged unions built in with an exhaustive `switch`/`match`: Zig, Odin, Hare, Goose,
  Carbon `choice`, Swift and Rust `enum`, Scala `enum`, OCaml variants (nine). C# 15 adds
  `union Pet(Cat, Dog)`, by type like Odin and Hare, boxed by default. Sealed or closed
  hierarchies with exhaustive matching: Java, Kotlin, C#. Variant records, where a tag
  field picks the fields: Ada (tag checked), Modula-2 (tag not checked by default).
  Unions of struct types told apart by a `kind` field: TypeScript. Library only: C++
  `std::variant`, D `SumType`. Generated: Cpp2 `@union`. None, eleven of twenty-nine: C3,
  Jai, Terra, Go (Go's most criticized gap), Nelua (`@union` is untagged), Oberon (record
  extension with `IS` and type `CASE`), Racket (structs plus `match`; Typed Racket has
  `(U A B)`), Python (`A | B` hints plus `match`), JavaScript (a `kind` field by
  convention), Visual Basic, R (a `class` attribute plus `inherits()`).
- TypeScript's discriminated unions are a light model: plain struct types with a `kind`
  field, narrowed by `switch (v.kind)` through flow typing, with exhaustiveness checked
  through `never`. The cost: the types are erased, with no layout control.
- Methods: in the type (Zig, C3, Carbon, Swift, Rust `impl`, C++, D, Java, Kotlin, Scala,
  Python, JavaScript, TypeScript, C#, Visual Basic); outside the struct with a receiver
  (Go; Oberon-2 and Component Pascal `PROCEDURE (p: P) Draw;`); subprograms in the same
  package as the type (Ada, called `Obj.Op (B)` on `tagged` types, dispatch through
  `T'Class`); called as `x.f(a)` for any `f(x, a)` (UFCS: Goose, D, Cpp2; extension
  functions: Kotlin, Scala, Swift, C# extension blocks, Visual Basic `<Extension>`); a
  method table, `p:m()` (Terra, Nelua, which adds metamethods `__add`, `__index`); generic
  functions picked by class (R: S3 `print.P`, S4 `setMethod`); none (Odin, Hare, Jai,
  Modula-2, Oberon-07, OCaml with functions in a module, Racket structs aside from
  generic interfaces).
- Cpp2's metafunctions (`@struct`, `@enum`, `@union`) make these kinds build-time
  library code instead of keywords. Nelua's `@record{…}`, `@union{…}` and `@enum{…}` are
  type values built at compile time and bound with `local`, close to Terra.
- Fields fixed unless marked: OCaml `mutable y`, Racket `#:mutable`. R copies a value
  when it changes.
- Rust reorders struct fields unless `#[repr(C)]`. Calling sum types `enum` (Rust, Swift,
  Goose, Scala) overloads C's meaning. TypeScript's `enum E { A, B }` emits code, so it
  is not erasable.
- Agree: `.` through pointers or references (twenty of twenty-nine, plus OCaml on
  records); built-in tagged unions (nine, ten with C# 15's `union`, plus sealed types in
  Java, Kotlin, C# and variant records in Ada, Modula-2); UFCS or extension calls (eight);
  designated literals (C, C3, Zig, Carbon, C++).

## 5. Control flow

| Language | Loops | `switch` | Fallthrough | `defer` | Labelled break | As expressions |
|---|---|---|---|---|---|---|
| Zig | `while (c) : (i += 1)`, `for (xs, 0..) \|x, i\|` | `switch (x) { 1, 2 => …, else => … }`, exhaustive | none; `continue :sw v` | `defer`, `errdefer` | `break :blk v` | `if`, `switch`, blocks, loops |
| C3 | C's `for`/`while`/`do`, `foreach (i, x : a)` | C's `case`, implicit break | `nextcase;` | `defer`, `defer catch` | `for OUTER: (…)`, `break OUTER;` | none (`?:`) |
| Odin | `for` only: C form, `for c`, `for x in xs` | `case 1, 2:` | `fallthrough` | block scoped | `outer: for`, `break outer` | none (`x if c else y`) |
| Hare | `for` only: C form, `for (let x .. xs)` | `case 1, 2 => …;`, exhaustive; `match` | none | `defer` | `:outer` (unverified) | `if`, `switch`, `match`, `for` (0.26) |
| Jai | `while c`, `for 0..9` (`it`), `for x, i: a` | `if x == { case 1; … }` | `#through;` | `defer` | `break i;` (by iterator name) | `ifx c then a else b` |
| Goose | `while`, `loop`, `for x in xs`, `for i in 10..13` | `match`, `Pat => e` | none | `defer` (unverified) | not found | `if`, `match`, `block` |
| Carbon | `while (c)`, `for (x: T in r)` | `match (x) { case 0 => {…} default => {…} }` | none | none (destructors) | not found (unverified) | `if c then a else b` |
| Swift | `while c`, `repeat … while`, `for x in xs`; C's `for(;;)` removed | `switch n { case 0: …; default: … }`, exhaustive | `fallthrough` | `defer { … }` | `outer: for`, `continue outer` | `if`, `switch` |
| Rust | `loop`, `while`, `for x in it`; no `for(;;)` | `match c { 'a'..='z' => 1, _ => 0 }`, exhaustive | none | none (destructors, `Drop`) | `'outer: for`, `break 'outer` | `if`, `match`, `loop` |
| C++ | C's, range `for (auto& x : v)`, `if (init; c)` | C's `switch` | default; `[[fallthrough]]` | none (destructors) | none (unverified) | `?:` only |
| D | C's, `foreach (i, x; a)`, `foreach (i; 0 .. n)` | C's `case`; `final switch` exhaustive | an error; `goto case;` | `scope(exit)`, `scope(failure)` | `outer: for`, `break outer;` | `?:` only |
| Cpp2 | `while c next i++ { }`, `for r do (x) { }` | `inspect n -> T { is 0 = …; is _ = …; }` | none | none (destructors) | `outer: while`, `break outer;` | `inspect` |
| Terra | `while c do … end`, `for i = 0, N do … end` | `switch x do case 1 then … end` | none | `defer f()` (experimental) | none (`goto`) | none |
| Java | C's, for-each `for (T x : xs)` | `switch (x) { case 1 -> …; }`, exhaustive on sealed types | old `case X:` falls through; arrow `case X ->` doesn't | none (`try`/`finally`) | `outer: for`, `break outer;` | `switch` (with `yield`) |
| Go | `for` only: C form, `for c`, `for i, v := range xs` | `switch x { case 1, 2: … }` | `fallthrough` | `defer` (function scoped) | `outer: for`, `continue outer` | none |
| Kotlin | `while`, `for (x in xs)`, `for (i in 0 until n)` | `when (x) { 0 -> …; else -> … }` | none | none (`try`/`finally`, `use`) | `outer@ for`, `break@outer` | `if`, `when`, `try` |
| Scala | `while`, `for x <- xs do …` | `n match { case 0 => … }` | none | none (`try`/`finally`, `Using`) | `boundary`/`break(v)` (no keyword) | everything |
| Nelua | `while c do`, `repeat … until c`, `for i=1,10 do`, `for i,v in ipairs(xs) do`; `continue` | `switch a do case 1, 2 then … else … end` | `fallthrough` | `defer … end` (scope) | none; `goto label`, `::label::` | do-expression `(do … in v end)`; `and`/`or` |
| Ada | `loop`, `while C loop`, `for I in 1 .. N loop`, `for X of Xs loop`, `reverse`; `parallel` (2022) | `case X is when 1 \| 2 => … when others => … end case;`, exhaustive | none | none; controlled types (`Finalize`); GNAT extension `finally` (unverified) | `Outer : loop … exit Outer when C;` | `(if C then A else B)`, `(case …)`, `(declare … begin …)` (2022), `(for all X of A => …)`, `A'Reduce ("+", 0)` |
| Modula-2 | `WHILE c DO`, `REPEAT … UNTIL c`, `FOR i := 1 TO n BY 2 DO`, `LOOP … EXIT … END` | `CASE x OF 1, 2: … \| 3..9: … ELSE … END`; no match without `ELSE` is an error | none | none (ISO `FINALLY` only for module end) | none; `EXIT` leaves the inner `LOOP` | none |
| Oberon | `WHILE c DO … ELSIF d DO … END`, `REPEAT … UNTIL c`, `FOR i := 0 TO n BY 2 DO`; `LOOP`/`EXIT` removed in -07 (in Oberon-2) | `CASE x OF 1, 2: … \| 3..5: … END`; no `ELSE` in -07, no match traps | none | none | none (no `break` at all) | none |
| OCaml | `for i = 0 to n - 1 do … done`, `downto`, `while c do … done` | `match x with 1 \| 2 -> … \| _ -> …`, exhaustive (warning) | none (or-patterns) | none; `Fun.protect ~finally` | none (raise an exception) | everything: `if`, `match`, `begin … end`, `let … in` |
| Racket | `(for ([x xs] [i (in-naturals)]) …)`, `for/list`, named `let`, tail calls | `(case x [(1 2) …] [else …])`, `cond`, `match` | none | none; `dynamic-wind`, `call-with-output-file` closes for you | `let/ec` escape continuation; `#:break` in `for` | everything is an expression |
| Python | `while c:`, `for x in xs:`, `for i, x in enumerate(xs):`; loop `else` | `match x: case 1 \| 2: … case _: …` (patterns, not exhaustive) | none | `with` (context managers), `try`/`finally`, `contextlib.ExitStack` | none | `a if c else b`, comprehensions, `:=` |
| JavaScript | `for (let i = 0; i < n; i++)`, `for (const x of xs)`, `for (const k in o)`, `while`, `do … while`, `for await` | `switch (x) { case 1: case 2: …; break; default: … }`, `===`, not exhaustive | default; needs `break` | none; `try … finally`, `using x = …` (`Symbol.dispose`, Stage 4, likely ES2027) | `outer: for (…) { break outer; }` | none; only `?:` (`do` expressions Stage 1) |
| TypeScript | `for (;;)`, `for (const x of xs)`, `for (const k in o)`, `while`, `do … while` | `switch (x) { case 1: case 2: … break; default: … }` (`===`); exhaustive via `never` | implicit without `break`; `noFallthroughCasesInSwitch` flag | `using` / `await using` (5.2, block scoped); `try … finally` | `outer: for (…) { break outer; }` | `?:` only |
| C# | `for (;;)`, `while`, `do … while`, `foreach (var x in xs)` | `switch (x) { case 1: case 2: …; break; }`, patterns, `when` | none (falling off a case is an error); `goto case 2;` | none; `using` declarations, `try`/`finally` | `goto`; `break outer;` / `continue outer;` in C# 15 | `x switch { 1 => "a", _ => "b" }`, `?:`, `throw` expressions; not blocks |
| Visual Basic | `For i = 0 To 9 Step 1 … Next`, `For Each x In xs`, `Do While c … Loop`, `While … End While` | `Select Case x : Case 1, 2 … Case 3 To 5 … Case Is > 9 … Case Else` | none | `Try … Finally`, `Using` | none; `Exit For`, `Continue Do`, `GoTo` | `If(c, a, b)` only |
| R | `for (x in xs)`, `while (c)`, `repeat`; `next`, `break` | `switch(x, a = , b = "ab", "other")` (a function) | yes: empty arg falls to the next | `on.exit(close(f), add = TRUE)` (function scoped) | none | all: `if`, `switch`, `{ }` (loops give invisible `NULL`) |
| C | `for (;;)`, `while`, `do` | `case 1: … break;` | default; `[[fallthrough]]` | TS 25755 | C2y `break outer;` | `?:` only |

- No fallthrough by default: twenty-five of twenty-nine in their modern form. C++,
  JavaScript and TypeScript keep C's, though TypeScript has a `noFallthroughCasesInSwitch`
  flag. Java's old `case X:` falls through, its arrow `case X ->` doesn't. In R an empty arm
  falls to the next one. C# makes falling off the end of a case an error. Opt-in spelling:
  `nextcase` (C3), `fallthrough` (Odin, Swift, Go, Nelua), `#through` (Jai), `goto case`
  (D, C#).
- Arm syntax: C's `case x:` with an implicit `break` (C3, Swift, Go); with a required
  `break` (D, C#); falling through unless you `break` (JavaScript, TypeScript); `=>` arms
  (Zig, Hare, Goose, Carbon, Rust, Scala, Ada `when 1 | 2 =>`, C#'s `switch` expression);
  `->` arms (Java, Kotlin `when`, OCaml `| 1 | 2 ->`); `is 0 = …` (Cpp2 `inspect`);
  `case 1 then` (Terra, Nelua); `1, 2: … | 3..9:` (Modula-2, Oberon); `case 1 | 2:`
  (Python); `Case 1, 2` (Visual Basic); bracketed clauses (Racket); named arguments (R,
  where `switch` is a function). Ranges in arms: `3..9` (Modula-2, Oberon), `Case 3 To 5`
  and `Case Is > 9` (Visual Basic), and Rust's `'a'..='z'`.
- Exhaustive checks: Zig, Hare, Swift, Rust, Java (on sealed types), D's `final switch`,
  Ada, OCaml (only a warning), and TypeScript (through `never`). In Modula-2 a value with
  no arm and no `ELSE` is an error, and Oberon traps; Python's `match` is not exhaustive.
  TypeScript shows a light way to check every case of a tagged union with flow typing.
- C's three-part `for`: kept by C3, Odin, Hare, C++, D, Go, Java, JavaScript, TypeScript,
  C# (ten); dropped by Zig, Jai, Goose, Carbon, Swift, Rust, Cpp2, Terra, Kotlin, Scala,
  Nelua, Ada, Modula-2, Oberon, OCaml, Racket, Python, Visual Basic, R (nineteen). All
  twenty-nine add a range or each form; Modula-2 and Oberon have only a counted
  `FOR i := 1 TO n BY 2`.
- Other loop forms: `repeat … until c` (Nelua, Modula-2, Oberon; Swift's `repeat … while`);
  a loop `else` (Python); `WHILE … ELSIF` (Oberon-07, which also dropped `LOOP`/`EXIT`);
  `parallel` loops (Ada 2022); named `let` and tail calls in place of loops (Racket).
- `defer`: Zig, C3, Odin, Hare, Jai, Goose, Swift, D (`scope(exit)`), Terra, Go, Nelua
  (eleven of twenty-nine), and C's own TS 25755. Go's `defer` runs at function exit, a
  known trap in loops, and so does R's `on.exit(…, add = TRUE)`; block-scoped `defer` (Zig,
  Swift, Nelua) is better. Destructors: C++, Rust, Carbon, Cpp2, and Ada's controlled types
  (`Finalize`); `try`/`finally`: Java, Kotlin, Scala, Python, JavaScript, TypeScript, C#,
  Visual Basic. OCaml's `Fun.protect ~finally` and Racket's `dynamic-wind` are library
  forms. Modula-2 (apart from ISO's `FINALLY` at module end) and Oberon have none.
- Cleanup tied to a value: Python's `with`, C#'s `using` declarations, Visual Basic's
  `Using`, TypeScript's `using`/`await using` (5.2, block scoped) and JavaScript's `using`
  (`Symbol.dispose`, Stage 4). Kotlin's `use`, Scala's `Using` and Racket's
  `call-with-output-file` do it as library calls. Like `defer`, it runs at scope end, but
  the value's type, not the caller, says how to clean up; the cost is a dispose protocol
  that each type must follow.
- Labelled break: Zig, C3, Odin, Hare, Swift, Rust (`'outer:`), D, Cpp2, Go, Java, Kotlin
  (`outer@`), Ada (`exit Outer when C`), JavaScript, TypeScript, C# (new in C# 15)
  (fifteen), and C2y; Scala's `boundary`/`break(v)` carries a value, and Racket's `let/ec`
  escape continuation does the same job. C++, Terra, Nelua, Modula-2, Oberon, OCaml,
  Python, Visual Basic and R have none: Terra and Nelua use `goto`, OCaml raises an
  exception, Visual Basic's `Exit For` picks the loop by its kind, Modula-2's `EXIT` leaves
  only the inner `LOOP`, and Oberon has no `break` at all.
- `if`, `switch` and blocks as expressions: Zig, Hare, Goose, Swift, Rust, Cpp2, Kotlin,
  Scala, Nelua (`(do … in v end)`), Ada, OCaml, Racket, R, and the `switch` of Java and C#
  (fifteen). Kotlin and Scala have no `?:` because `if` is an expression; Java's `yield`
  exists because blocks are not expressions. Ada puts them in parentheses:
  `(if C then A else B)`, `(case …)`, and since 2022 `(declare … begin …)`. Python and
  Visual Basic have only a conditional form (`a if c else b`, `If(c, a, b)`); JavaScript
  has only `?:`, with `do` expressions at Stage 1.
- Loops that give a value: Python's comprehensions, Racket's `for/list`, and Ada 2022's
  `(for all X of A => …)` and `A'Reduce ("+", 0)`. In R a loop used as an expression gives
  an invisible `NULL`.
- Scala 3 and Terra replace braces with `then`/`do` and indentation or `end`; Go puts no
  parentheses around conditions. Nelua does as Terra does (`then`, `do … end`); Python uses
  `:` and indentation; Ada, Modula-2, Oberon, OCaml and Visual Basic close blocks with
  keywords (`end loop`, `END`, `done`, `Next`, `End While`); Racket uses parentheses.
- Agree: no fallthrough (twenty-five); labelled loops (fifteen); `defer` (eleven);
  expressions (fifteen); a range or each loop (twenty-nine).

## 6. Errors

| Language | Mechanism | Propagate | Default / handle | Payload |
|---|---|---|---|---|
| Zig | error union `E!T`, error sets | `try f()` | `f() catch 0`, `orelse` | no (codes) |
| C3 | optional `T?` holding a fault (`excuse`) | `f()!` | `f() ?? 0`, `if (catch e = f())` | no (codes) |
| Odin | last result (`bool`, enum, union) | `f() or_return` | `or_else`, `or_break` | yes (any type) |
| Hare | tagged union with `!` error types, `(T \| io::error)` | `f()?` | `f()!` (abort), `match` | yes |
| Jai | multiple results, `#must` | by hand | by hand | yes |
| Goose | multiple results, `T?`, `guard … else` | `return … from fname` (non-local) | `guard` | yes |
| Carbon | `Optional(T)` or a `choice` result | not settled ("very likely" a `?`) | `match` | yes |
| Swift | `throws(E)` (typed), optionals, `Result` | `try f()` | `try?`, `try!`, `do { } catch { }`, `??` | yes |
| Rust | `Result<T, E>`, `Option<T>` (library enums) | `f()?` | `match`, `unwrap_or` | yes |
| C++ | exceptions; `std::expected<T, E>` (C++23) | by hand | `and_then`, `or_else`, `catch` | yes |
| D | exceptions (`Exception`, `Error`); none in `-betterC` | by hand | `try`/`catch`, `enforce` | yes |
| Cpp2 | C++ exceptions (opt in with `throws`), `std::optional`, `std::expected` | by hand | `inspect`, `is`/`as` | yes |
| Terra | none; C conventions, tuple `{bool, T}` | by hand (or a Lua macro) | by hand | yes |
| Java | checked and unchecked exceptions; `Optional<T>` | implicit (exceptions) | `try`/`catch`/`finally` | yes |
| Go | `(T, error)` as last result | by hand (`if err != nil`) | `errors.Is`, `errors.As` | yes |
| Kotlin | unchecked exceptions; `T?`; `Result<T>` | by hand (`f() ?: return null`) | `?.`, `?:`, `runCatching` | yes |
| Scala | exceptions; `Option`, `Either`, `Try` | `for` comprehension or `boundary` | `match`, `getOrElse` | yes |
| Nelua | multiple results, Lua style `(T, string)`; `error`/`panic` abort | by hand (`if not ok then return nil, err end`) | `assert(f())`, `if not x then` | yes (any value, often a string) |
| Ada | exceptions: `raise E with "msg";`; not in signatures; SPARK proves none raised, `Exceptional_Cases` aspect | automatic (unwinding) | `exception when E => …; when others => …` | string message only (`Exception_Message`, `Exception_Occurrence`) |
| Modula-2 | ISO exceptions: `RAISE` (module `EXCEPTIONS`), `EXCEPT` part of a procedure body | automatic (unwinds until an `EXCEPT` part) | `EXCEPT` then `RETRY` or `RETURN`; `IsCurrentSource`, `M2EXCEPTION.M2Exception()` | number plus message string; no typed values |
| Oberon | none; `ASSERT(c)` and runtime traps halt the command | none | none (Oberon-2/CP: `HALT(n)`) | no |
| OCaml | exceptions (`exception E of string`), `('a, 'e) result`, effect handlers | exceptions: automatic; result: `let*` binding operators | `try f () with Not_found -> 0`, `match f () with \| exception E -> …`, `Option.value ~default` | yes |
| Racket | exceptions: `raise`, `(error 'f "bad ~a" x)`, `exn:fail` struct types | automatic unwinding | `(with-handlers ([exn:fail? (λ (e) 0)]) …)` | yes; any value can be raised; exn structs carry message and continuation marks |
| Python | exceptions, `raise ValueError("x")`; `ExceptionGroup` | automatic (unwinds) | `try: … except E as e: …`, `else`, `finally`; `except*`; `except A, B:` (3.14) | yes (exception objects) |
| JavaScript | exceptions, `throw new Error("m", { cause })`; any value can be thrown; promise rejection | automatic unwinding; `await` rethrows | `try { … } catch (e) { … } finally { … }`, `catch { }`, `p.catch(f)` | yes (any value); `cause`; `Error.isError(e)` (ES2026) |
| TypeScript | exceptions: `throw`, `try`/`catch`; rejected promises | automatic unwinding; `await` rethrows | `try { … } catch (e) { … } finally { … }`; `e` is `unknown`; no `throws` types | yes (any value, usually `Error` with `cause`) |
| C# | exceptions: `throw`, `try`/`catch`/`finally`; unchecked (no throws list) | automatic (stack unwinds) | `catch (IOException e) when (…)`; `??` for null; `TryParse(s, out x)` | yes (exception object) |
| Visual Basic | exceptions `Try … Catch ex As E When cond … Finally`; old `On Error GoTo` | automatic (unwinds) | `Catch`, `Throw` to rethrow | yes (exception object) |
| R | conditions: `stop()`, `warning()`, `signalCondition()`; restarts | automatic unwinding | `tryCatch(f(), error = function(e) 0)`, `try()`, `withCallingHandlers()`, `finally =` | yes: condition objects, `errorCondition(msg, class = "myError", data = x)` |
| C | return codes, `errno`, out-parameters | by hand (`goto fail`) | by hand | yes |

- Errors as values: twelve of twenty-nine and C (the first eleven plus Nelua, whose
  `(T, err)` results follow Lua). Oberon has no mechanism at all: `ASSERT` and traps halt,
  and you return codes by hand through `VAR` parameters, like C. Exceptions with unwinding:
  sixteen of twenty-nine. That's C++, D (none in `-betterC`), Cpp2 (opt in with
  `throws`), Java (checked and unchecked), Kotlin and Scala (unchecked), plus ten of the
  twelve new ones: Ada, Modula-2, OCaml, Racket, Python, JavaScript, TypeScript, C#,
  Visual Basic and R. Unwinding needs run-time support and is hard to lower; Swift's
  `throws` is a plain return path.
- A short propagate operator (`try`, `!`, `or_return`, `?`): Zig, C3, Odin, Hare, Swift,
  Rust (six of twenty-nine); Carbon plans one. By hand: Jai, C++, D, Cpp2, Terra, Go
  (`if err != nil`; Go decided in 2025 to stop pursuing new error syntax), Kotlin
  (`f() ?: return null`), Scala (`for` comprehensions), Nelua
  (`if not ok then return nil, err end`), C. OCaml's `let*` binding operators do for
  `result` what Scala's `for` does. In the exception languages, errors pass up on their
  own, with nothing written at the call site.
- `try` as a prefix: Zig and Swift. `?` as a postfix: Hare and Rust. `??` for a default:
  C3 and Swift; Kotlin's `?:` (elvis) and `?.`, and C#'s `??`, do the same for null.
- Errors as ordinary sum or result types: Hare, Carbon, Rust `Result<T, E>`, Odin, C++
  `std::expected`, Swift `Result`, Scala `Either`, Kotlin `Result<T>`, OCaml
  `('a, 'e) result`. Go's `(T, error)` and Nelua's `(T, err)` are products, not sums, so
  both can be set. C#'s cheap path, `TryParse(s, out x)`, uses an out-parameter, as C
  does. Zig's and C3's codes can't carry data, and neither can Oberon (no errors at all).
  Ada carries only a string message; Modula-2 carries a number and a message, with no
  typed values.
- Any value can be raised: JavaScript, TypeScript and Racket. So TypeScript types the
  caught `e` as `unknown`. R and Racket use class or struct hierarchies (`exn:fail`,
  `class = "myError"`) that handlers test against.
- Wrapping errors with context: Go's `%w`, `errors.Is`, `errors.As`; JavaScript and
  TypeScript `cause`.
- What a function may throw is hidden from callers in most exception languages: Ada (not
  in signatures), C# (no throws list), TypeScript (no `throws` types), JavaScript, Kotlin,
  Scala. Java's checked exceptions and Swift's `throws(E)` are the exceptions to this.
  SPARK takes another route: it proves no exception is raised, and `Exceptional_Cases`
  states which ones may be.
- Handling before or without unwinding: C# and Visual Basic `when` filters run before the
  stack unwinds; R's `withCallingHandlers` and restarts let code go on without unwinding;
  Modula-2's `EXCEPT` part can `RETRY` the procedure; OCaml 5 effect handlers can resume.
  These are strong tools, but all of them need run-time support.
- Many errors at once: Python's `ExceptionGroup` and `except*`.
- Two error paths: in JavaScript and TypeScript, async errors are promise rejections, and
  `await` turns them back into exceptions.
- Visual Basic's old `On Error GoTo` shows how bad unstructured handling is.
- Terra shows a propagate construct can be a build-time macro.
- A split between recoverable errors and bugs: D (`Exception` vs `Error`), Rust
  (`Result` vs `panic!`), Go (`error` vs `panic`), Zig (errors vs `unreachable`), Nelua
  (error results vs `error`/`panic`). Oberon has only the bug side: `ASSERT` and traps.
- Agree: errors as values (twelve); exceptions with unwinding (sixteen); a propagate
  operator (six); prefix `try` (Zig, Swift); postfix `?` (Hare, Rust); contracts (C3,
  C++26, Cpp2; SPARK's `Exceptional_Cases`).

## 7. Compile-time code

| Language | Mechanism | Types as values | Conditional compilation |
|---|---|---|---|
| Zig | `comptime` blocks and parameters; `@typeInfo`, `@Int`, `@Struct` | yes (`type`) | `if (builtin.os.tag == .linux)` |
| C3 | macros (`macro @sq(x) => x * x;`), `$if`/`$for` sublanguage, `$T` | partly (`$Type`, `typeid`) | `$if … $endif`, `@if(cond)` |
| Odin | constants, `when`, `#config`, `#load`, `#assert` | partly (`typeid`, also at run time) | `when ODIN_OS == .Windows { … }` |
| Hare | constant expressions only | no | build tags in file names (`+linux`) |
| Jai | `#run` any code (I/O too), `#insert`, `#code`, `#expand`, build metaprograms | yes (`Type`) | `#if OS == .WINDOWS` |
| Goose | specialization, `const for` over fields (unverified) | no | not found |
| Carbon | `:!` bindings evaluated at compile time; `Stack(i32)` is a call; no macros | yes (`type`) | not found |
| Swift | `#if`; macros as compiler plugins on syntax trees; value generics | no (metatypes at run time) | `#if os(Linux)` |
| Rust | `const fn`, `const { … }` blocks, `macro_rules!`, proc macros | no | `#[cfg(target_os = "linux")]` |
| C++ | `constexpr`/`consteval`, templates, preprocessor; C++26 reflection `^^T`, `[: r :]` | partly (`std::meta::info`, spliced back) | `#if`, `if constexpr` |
| D | CTFE of any function, `static if`, `static foreach`, string `mixin`, `__traits` | no (templates and `alias` compute types) | `static if`, `version` |
| Cpp2 | `==` declarations (constexpr); metafunctions (`@enum`, `@value`) run in cppfront | partly (via metafunctions) | C++'s |
| Terra | Lua: quotes `` `e ``, escapes `[e]`, `macro`, `symbol` | yes (Lua values) | Lua `if` around definitions |
| Java | constant folding; annotation processors (generate source) | no | none |
| Go | untyped constants; `//go:generate`, `//go:embed` | no | `//go:build linux` (file level) |
| Kotlin | `const val`; compiler plugins, KSP; `inline` + `reified` | no | none |
| Scala | `inline`, `inline if`/`match`; match types; quoted macros | partly (a type-level sub-language) | `inline if` |
| Nelua | Lua preprocessor: `## lua line`, `#[expr]#`, `#\|name\|#`; `<comptime>` params; macros as Lua functions | yes (`@integer` is a value of type `type`) | `## if ccinfo.is_linux then … ## end` |
| Ada | static expressions, attributes (`'Size`, `'First`, `'Image`), generics, aspects; no macros; GNAT `gnatprep` preprocessor | no (only generic formal types) | `if Config.Debug then` on a static constant (dead code dropped); `gnatprep` `#if`; per-OS source dirs in GPR |
| Modula-2 | constant expressions only; `SIZE`, `TSIZE(T)`, `MAX(T)`; no macros | no | none in ISO (`<* *>` pragmas are implementation defined); gm2 `-fcpp` runs the C preprocessor (`#ifdef`) |
| Oberon | constant expressions only | no | none in the language (some compilers have pragmas, unverified) |
| OCaml | PPX rewriters (`[%expr …]`, `[@@deriving show]`); no in-language compile-time eval | no (first-class modules carry types: `(module M : S)`) | none in language; dune `(enabled_if …)`, `(select …)`; `ppx_optcomp` `[%%if …]`, cppo |
| Racket | hygienic macros: `define-syntax`, `syntax-rules`, `syntax-parse`; phases: `begin-for-syntax`, `(require (for-syntax racket/base))`; whole languages via `#lang` | no (struct types are runtime values; Typed Racket types are not values) | none built in; a macro tests `(system-type 'os*)` at expansion time; else run-time `case` |
| Python | none; module code runs at import; decorators, metaclasses, `__init_subclass__` | yes (classes are run-time objects; `type`) | none; run-time `if sys.platform == "win32":`; `-O` drops `assert`; `if TYPE_CHECKING:` |
| JavaScript | none; no macros; run-time `eval`, `new Function` | classes and functions are run-time values; `typeof` gives a string | none in the language; bundler defines (`process.env.NODE_ENV`) plus dead-code removal; conditional `exports` |
| TypeScript | type-level code only: conditional types `T extends U ? X : Y`, mapped, template literal types, `infer`; no build-time value code; decorators run at runtime | no (types erased; `typeof x` lifts a value to a type) | none in the language; bundler `define` plus dead-code removal; `tsconfig` `lib`, `paths` |
| C# | `const` folding; source generators (Roslyn plugins add C# at build); attributes; no macros | no (runtime `Type`, `typeof(T)`) | `#if DEBUG` / `#define` (symbols only); `[Conditional("DEBUG")]` |
| Visual Basic | `#Const`, `#If`; `NameOf`; Roslyn source generators; attributes and reflection at run time | no (`GetType(T)` gives a run-time `Type`) | `#If DEBUG Then … #End If`; `DefineConstants` in project |
| R | none; code is data: `quote()`, `substitute()`, `bquote()`, lazy args, `eval()`; package code runs at install time | partly: classes are strings or S4 class objects, `class(x)` | none in R; runtime `if (.Platform$OS.type == "windows")`; `R/unix/`, `R/windows/` in packages |
| C | preprocessor, `constexpr` objects, `_Generic`, `static_assert`, `#embed` | no | `#if` |

- Types as build-time values: Zig, Jai, Carbon, Terra, Nelua (five of twenty-nine); partly:
  C3, Odin, C++26 (reflection), Cpp2 (metafunctions), Scala (match types, a separate
  type-level language) (five); only at run time, with no build time at all: Python,
  JavaScript, R (three); no: Hare, Goose, Swift, Rust, D, Java, Go, Kotlin, Ada, Modula-2,
  Oberon, OCaml, Racket, TypeScript, C#, Visual Basic (sixteen).
- Terra is the strongest proof of layer 1, but uses a second language (Lua) for it. Nelua
  does the same: full Lua at build time, with access to the compiler's AST and types. It
  is powerful, but it is unhygienic and puts two languages in one file.
- D runs any ordinary function at build time (CTFE), with no keyword; types are computed
  in a separate template language. Ada has no build-time run of functions at all; its
  build-time work stops at static expressions, attributes and generics.
- Zig and Jai show one build-time mechanism replaces macros, templates, `#ifdef` and code
  generators.
- Code generators grow where build-time code is missing: Java annotation processors,
  Kotlin KSP and compiler plugins, Go `//go:generate`, C# and Visual Basic source
  generators (Roslyn plugins), OCaml PPX rewriters. That is the strongest argument
  for Alcor's layer 1 among mainstream languages.
- Scala's `inline if` and `inline match`, reduced at build time, are the closest
  mainstream form of an ordinary `if` on a build-time condition. Ada gets a plain `if` on
  a static constant, with the dead code dropped. JavaScript and TypeScript get it only
  outside the language, from bundler defines plus dead-code removal.
- Several mechanisms where layer 1 would be one: C++ four, Rust three (generics, `const
  fn`, macros), Scala three (`inline`, match types, quoted macros compiled separately),
  C# and Visual Basic three (`const`, `#if`, source generators), Ada three plus a
  preprocessor (static expressions, attributes, generics; `gnatprep`), D two, C3 and Odin
  a `$if`/`when` sublanguage, Swift plugin macros.
- A separate type-level language grows complex: TypeScript's conditional, mapped and
  template-literal types are Turing-complete but cannot make values. Scala's match types
  and D's templates split things the same way.
- Racket keeps build-time code in its own phase, with its own imports (`for-syntax`).
  Each module is set up fresh per phase, so build-time state never leaks into run time.
  That is a clean model for build-time code that imports other modules. Its hygienic
  macros (and whole languages via `#lang`) give far more power than Zig `comptime`, but
  nothing stops a macro from hiding control flow.
- With no build time, load time takes its place: Python runs module code, decorators and
  metaclasses at import; R runs package code once at install time and stores the result,
  so importers never read source. R's way is a simple form of build-time evaluation.
- C's bolt-ons (`constexpr`, `typeof`, `_Generic`) show the demand, and so do the C-style
  preprocessors bolted onto Modula-2 (gm2 `-fcpp`) and Ada (GNAT `gnatprep`). `#embed`
  (C, C++26), D's `import("file")` and Go's `//go:embed` are build-time file reads worth
  keeping as functions.
- Constant expressions only: Hare, Modula-2, Oberon (three). Per-platform code then moves
  to files, modules or the build: Hare file-name tags, Go `//go:build`, Ada per-OS source
  dirs in GPR, R `R/unix/` and `R/windows/`, OCaml dune `(enabled_if …)` and `(select …)`.
- A visible marker for build-time names: C3 `$name`, Odin and Jai `$T`, Carbon `:!`, Zig
  `comptime`, Cpp2 `==`, Scala `inline`, Nelua `<comptime>` and `##`/`#[ ]#` for Lua code;
  Racket marks the phase on imports and blocks (`for-syntax`, `begin-for-syntax`); D and
  Terra need none.
- Agree: types as build-time values (Zig, Jai, Carbon, Terra, Nelua; five); ordinary
  functions run at build time (Zig, Jai, D, C++ `constexpr`, Rust `const fn`, Terra,
  Nelua; seven); compile-time `if` (Zig, C3, Odin, Jai, Swift, Rust, D, C++, Scala, Nelua,
  Ada on a static constant, C#, Visual Basic; thirteen).

## 8. Generics

| Language | Generic type | Generic function | Inference | Lowering |
|---|---|---|---|---|
| Zig | `fn List(comptime T: type) type { return struct {…}; }` | `comptime T: type`, `anytype` | from `anytype` arguments | one copy per type |
| C3 | `struct List <Type> {…}`, used `List{int}` (unverified form) | macros with `$T` | explicit for types | one copy per type |
| Odin | `Vec :: struct($T: typeid, $N: int)` | `proc(x: $T)`, `where` constraints | `$T` from arguments | one copy per type |
| Hare | none (by design) | none | none | none |
| Jai | `Pair :: struct (A: Type, B: Type)` | `(a: $T, b: T)`, `#modify` | `$T` from arguments | one copy per type |
| Goose | not found | untyped parameter: `fn larger(a, b)` | from each call | one copy per type |
| Carbon | `class Stack(T:! type)`, used `Stack(i32)` | `fn Max[T:! Ordered](a: T, b: T) -> T` | `[…]` parameters from arguments | one copy per type |
| Swift | `struct Ring<let N: Int, Element>` | `func maxOf<T: Comparable>(_ a: T, _ b: T) -> T` | from arguments | shared code with run-time witness tables; Embedded: one copy per type |
| Rust | `struct Buf<T, const N: usize>` | `fn largest<T: PartialOrd>(xs: &[T]) -> T` | from arguments; `Vec::<u8>::new()` | one copy per type; `dyn Trait` vtables |
| C++ | `template <typename T> struct List`, `std::vector<int>` | `template <std::integral T> T gcd(T a, T b)`, `void f(auto x)` | from arguments; CTAD | one copy per type |
| D | `struct Box(T, size_t N)`, used `Box!(float, 4)` | `T max(T)(T a, T b) if (isIntegral!T)` | from arguments (IFTI) | one copy per type |
| Cpp2 | `pair: <A, B> type = { … }` | `max2: <T> (a: T, b: T) -> T`, `(x: _)` | from arguments | one copy per type (C++ templates) |
| Terra | Lua function `Stack(T)` returning a struct, `terralib.memoize` | Lua function returning a Terra function | none (explicit) | one copy per type |
| Java | `class Box<T>` | `static <T extends Comparable<T>> T max(T a, T b)` | from arguments, `<>` diamond | shared (erasure, boxing) |
| Go | `type Stack[T any] struct {…}` | `func Sum[T Number](xs []T) T` | from arguments | shared per memory shape, plus dictionaries |
| Kotlin | `class Box<T>(val v: T)` | `fun <T : Comparable<T>> maxOf(a: T, b: T): T` | from arguments | shared (erasure) |
| Scala | `class Box[T]` | `def max[T](a: T, b: T)(using Ordering[T]): T` | from arguments | shared (erasure) |
| Nelua | `generalize(function(T) … return @record{…} end)`, use `stack(integer)` | `function f(x: auto)`, `<polymorphic>`; `#[concept(...)]#` constraints | from arguments (`auto`, concepts) | one copy per type (C code per instance) |
| Ada | `generic type T is private; package Stacks is … end Stacks;` | `generic type T is private; function Max (A, B : T) return T;` then `function Max_Int is new Max (Integer);` | none; explicit `is new` instantiation | GNAT: one copy per instance (macro-style); shared code allowed by the standard |
| Modula-2 | ISO part 2: `GENERIC DEFINITION MODULE Stacks(Elem: TYPE);` | none (whole modules only) | none; explicit `DEFINITION MODULE IntStacks = Stacks(INTEGER);` | one copy per refinement; not in gm2 (unverified) |
| Oberon | none | none | none | none |
| OCaml | `type 'a tree = Leaf \| Node of 'a tree * 'a * 'a tree`; functors `Map.Make (String)` | implicit: `let id x = x` is `'a -> 'a` | full (let-polymorphism) | one shared copy (uniform boxed values); functors applied at run time; flambda may specialise |
| Racket | none needed (dynamic); Typed: `(struct (A) node ([v : A]))`, `(define-type (Stack A) (Listof A))` | Typed: `(: id (All (A) (-> A A)))` | Typed: local inference at call sites | erased; one shared copy; contracts guard typed/untyped borders |
| Python | `class Stack[T]: …` (3.12+) | `def first[T](xs: list[T]) -> T:` | by static checkers (mypy, pyright) | erased; one object, duck typing |
| JavaScript | none (dynamic); TypeScript `class Stack<T>` is erased | every function works on any value (duck typing) | not needed | one copy; JIT specializes at run time (hidden classes, inline caches) |
| TypeScript | `interface Box<T> { v: T }`, `class Stack<T>` | `function id<T>(x: T): T`, `<T extends HasLen>`, `<const T>` | from arguments and context | erased; one JS function, no runtime type info |
| C# | `class Stack<T> where T : struct { … }` | `T Sum<T>(T[] xs) where T : INumber<T>` (static abstract interface members) | from arguments | reified at run time: JIT shares one copy for ref types, one copy per value type; Native AOT pre-builds |
| Visual Basic | `Class Stack(Of T) … End Class` | `Function Sum(Of T As Structure)(xs As T()) As T` | from arguments | reified in IL; JIT shares code for ref types, one copy per value type |
| R | none (dynamic typing) | generic = dispatch: `UseMethod("area")`, `setGeneric("area")` | n/a; dispatch on runtime class | runtime lookup by class name (S3 `area.circle`), S4 method tables |
| C | `void *` plus size, macro templates | `_Generic` dispatch | none | erased or text |

- One copy per type: Zig, C3, Odin, Jai, Goose, Carbon, Rust, C++, D, Cpp2, Terra,
  Embedded Swift, Nelua, Ada (GNAT; the standard also allows shared code) and Modula-2
  (ISO generic modules, little implemented) (fifteen of twenty-nine). Nelua puts the whole
  program in one C file, so it re-instantiates generics from source. A middle path: C# and
  Visual Basic reify, storing the IL once; the JIT shares one copy for all ref types and
  makes one copy per value type, and Native AOT must see every use ahead of time. Shared
  code: Java, Kotlin and Scala erase types (boxing primitives); Go shares code per memory
  shape and passes a dictionary; full Swift passes witness tables; OCaml keeps one copy
  over uniform boxed values (flambda may specialise); Python, TypeScript and Typed Racket
  erase their types, and Typed Racket guards the typed/untyped border with contracts.
  Hare and Oberon have no generics.
- Dynamic languages need no generics: JavaScript, R and untyped Racket run one copy on any
  value. JavaScript's JIT specializes at run time (hidden classes, inline caches). In R,
  "generic" means dispatch on the run-time class (S3 `area.circle`, S4 method tables).
- Inference from arguments: twenty-one of twenty-nine. OCaml infers everything:
  `let id x = x` is `'a -> 'a` with no type written. Python leaves it to outside checkers
  (mypy, pyright), not the language. Explicit only in Terra, C3 types, Ada and Modula-2;
  not needed in JavaScript and R.
- Instantiation spelling: a call `List(T)` (Zig, Carbon, Terra, Jai `FixedBuf(64)`, Nelua
  `stack(integer)`, Modula-2 `Stacks(INTEGER)`), matching the roadmap's `List(T)`,
  `Map(K, V)`; close to it are Ada `new Max (Integer)`, OCaml functors `Map.Make (String)`,
  Typed Racket's prefix `(Stack A)` and Visual Basic `Stack(Of T)`, where the `Of` keyword
  marks the type argument; `<T>` (Swift, Rust, C++, Cpp2, Java, Kotlin, TypeScript, C#),
  which makes parsing ambiguous (C++'s `template`, Rust's `::<>`); `[T]` (Go, Scala,
  Python), ambiguous next to indexing; `!(…)` (D); `{…}` (C3).
- Explicit, named instances: Ada and Modula-2 make the user name each copy
  (`function Max_Int is new Max (Integer);`, `DEFINITION MODULE IntStacks = Stacks(INTEGER);`).
  Every copy shows in the source; the cost is a line per use and no inference.
- Generic modules: Ada generic packages, Modula-2 generic modules (whole modules only) and
  OCaml functors take a type or a module and give back a whole module, so one instance
  covers many types and functions at once. OCaml applies functors at run time. Zig and
  Terra get a similar effect from a build-time function that returns a struct.
- Constraints: checked at the definition (Carbon, Swift, Rust traits, Java, Kotlin, Scala
  bounds, Ada formals such as `type T is private` and `with function "<"`, TypeScript
  `extends`, C# `where`, Visual Basic `As`), which needs a constraint language; or
  build-time predicates (D, C++ concepts, Odin `where`, Jai `#modify`, Zig `@typeInfo`,
  Go type sets `~int | ~float64`, Nelua concepts `#[concept(...)]#`). C#'s `INumber<T>`
  uses static abstract interface members, so generic code can use operators on numbers.
  Variance (`out T`, `+T`) in Kotlin and Scala is GC-runtime complexity.
- Terra, Zig and Nelua need no generics feature: a build-time function returns a type
  (Nelua's `generalize` wraps a Lua function over types). In Terra and Nelua the cost is
  two languages in one file, and Nelua's Lua code is unhygienic.
- Rust's const generics allow only integers, `bool` and `char`; Scala Native's
  `CArray[T, Nat._8]` shows the same gap.
- Agree: one copy per type (fifteen); inference (twenty-one); call form `List(T)` (Zig,
  Carbon, Terra, Jai, Nelua, Modula-2); `<T>` (eight); `[T]` (Go, Scala, Python); generic
  modules (Ada, Modula-2, OCaml).

## 9. Modules and C

| Language | Module | Import | Visibility | Call C | C headers |
|---|---|---|---|---|---|
| Zig | file (a struct) | `const std = @import("std");` | private; `pub` | `extern "c" fn puts(s: [*:0]const u8) c_int;` | `@cImport` up to 0.16; build step in 0.17 (unverified) |
| C3 | `module a::b;`, many files | `import std::io;` | public; `@private`, `@local` | `extern fn int puts(char* s);` | none (third-party bindgen) |
| Odin | directory, `package name` | `import "core:fmt"` | public; `@(private)` | `foreign import libc "system:c"`, `foreign libc { … }` | none (bindgen) |
| Hare | directory | `use fmt;` | private; `export` | `@symbol("puts") fn puts(…) int;` (unverified) | none |
| Jai | module | `#import "Basic";`, `#load` | public; `#scope_file` | `strlen :: (s: *u8) -> u64 #foreign libc;` | `Bindings_Generator` at build time |
| Goose | root file names packages | `import mylib from "joe/mylib@v2";` | not found | `extern fn cube_root(x: f64) -> f64 = "cbrt";` | `--include x.h` on the command line |
| Carbon | `package P library "L";` | `import P library "L";` | public in API files; `private` | through the header import | `import Cpp library "circle.h";`, then `Cpp.GetArea(c)` |
| Swift | one module per target | `import Foundation` | `internal` default; six levels | through the header import; export with `@c(name)` | `module.modulemap`, then `import CLib` |
| Rust | crate; `mod net;` tree | `use std::collections::HashMap;` | private; `pub` | `unsafe extern "C" { fn strlen(s: *const c_char) -> usize; }` | none (`bindgen`, libclang) |
| C++ | headers; C++20 `export module m;` | `#include`, `import m;` | `static`, anonymous namespace; `export` in modules | `extern "C" { … }` | `#include` (C is mostly a subset) |
| D | file, `module a.b;` | `import std.stdio : writeln;` | `public` default; module-wide `private` | `extern(C) int f(int);` | ImportC: a built-in C compiler, `import foo;` reads `foo.c` |
| Cpp2 | none of its own (mixed `.cpp2` files) | `#include`, `import std;` | `public`/`private` on members | call C++ directly | `#include` in mixed files |
| Terra | Lua module | `require "mod"` | Lua `local` | `terralib.externfunction` | `local C = terralib.includec("stdio.h")` (embedded Clang) |
| Java | `package a.b;`, `module-info.java` | `import java.util.List;` | package-private default | FFM API (`Linker`) | `jextract` (separate tool) |
| Go | directory, `package main` | `import "fmt"` | lowercase is private | cgo | cgo: header in a comment above `import "C"` |
| Kotlin | `package a.b` | `import a.b.C` | public default | Native `cinterop` | `.def` file plus the `cinterop` tool |
| Scala | `package a.b` | `import a.b.*` | public default | Native `@extern object` | `sn-bindgen` (separate tool) |
| Nelua | file | `local M = require 'mymod'` | `local` private to file; `global` public | `local function puts(s: cstring): cint <cimport, nodecl> end` | `## cinclude '<stdio.h>'`; bindings by hand or `nelua-decl` tool (unverified) |
| Ada | package: spec `.ads` + body `.adb` | `with Ada.Text_IO; use Ada.Text_IO;` | spec visible part public; `private` part; body hidden; `private package` children | `function Puts (S : char_array) return int with Import, Convention => C, External_Name => "puts";` | none; `gcc -fdump-ada-spec` makes bindings |
| Modula-2 | `DEFINITION MODULE M;` (`.def`) plus `IMPLEMENTATION MODULE M;` (`.mod`); local modules | `IMPORT M;` (then `M.f`), `FROM M IMPORT f;` | what the `.def` lists is public; opaque `TYPE T;`; local modules `EXPORT [QUALIFIED]` | gm2: `DEFINITION MODULE FOR "C" libc;` with `...` varargs | none; write the `.def` by hand (gm2 tool `h2def` (unverified)) |
| Oberon | file, `MODULE M; … END M.` | `IMPORT Texts, Out := MyOut;` (alias) | private; `*` exports (variables read-only to importers); Oberon-2/CP: `-` read-only | none in the report; `SYSTEM` module; compiler-specific (OBNC: C body for a module) | none |
| OCaml | file `foo.ml` is module `Foo`; `module M = struct … end` | none needed: `Foo.bar`; `open Foo`, `Foo.(e)` | all public unless hidden by `.mli` or a signature; abstract types | `external puts : string -> unit = "my_puts"` plus C stub; `ctypes` library | none; stubs use `caml/mlvalues.h`; `ctypes` binds by hand |
| Racket | file (`#lang racket/base`); submodules `(module+ test …)` | `(require racket/list)`, `(require "util.rkt")` | private; `(provide f)`, `(provide (contract-out …))` | `ffi/unsafe`: `(define puts (get-ffi-obj "puts" #f (_fun _string -> _int)))`, `define-ffi-definer` | none; types written by hand |
| Python | file (`.py`); package is a directory | `import os`, `from pathlib import Path`, `lazy import json` (3.15) | all public; `_name` by convention; `__all__` | `ctypes`, `cffi` (third party), C API extension modules | none in `ctypes`; `cffi` `cdef("…")` parses declarations |
| JavaScript | file (ES module; `<script type="module">`) | `import { readFile } from "node:fs";`, `import * as m from "./m.js";`, `await import("./m.js")` | private; `export` | none in the language; Node-API addons (`.node`), Deno `Deno.dlopen`, Bun `bun:ffi`; WebAssembly | none; `node-gyp` builds addons from C headers |
| TypeScript | file (ES module) | `import { readFile } from "node:fs";`, `import type { T } from "./t.js";` | private; `export` | none in language; runtime FFI (Node-API addons, `bun:ffi`, `Deno.dlopen`) | none; hand-written `.d.ts` |
| C# | assembly (`.dll`, one project); namespaces are separate | `using System.Text;`, `global using`, `using static` | `public`, `internal`; members `private` by default | `[LibraryImport("libc")] static partial int puts(string s);`, `[DllImport]`, `extern` | none built in; by hand or ClangSharp generator (tool) |
| Visual Basic | `Namespace N`, `Module M` (static members); assembly | `Imports System.Text` | `Public`, `Friend`, `Private`, `Protected` | `Declare Function puts Lib "libc" (s As String) As Integer`, `<DllImport>` | none (write by hand) |
| R | package (a namespace); scripts via `source("f.R")` | `library(stats)`, `stats::median(x)`, `use("pkg", "f")` (recent, unverified) | `NAMESPACE` `export(f)`; others via `pkg:::f` | `.Call("C_fn", x)`, `.C`, `.External`; Rcpp for C++ | C side includes `<Rinternals.h>`; R never reads C headers |
| C | none (`#include`) | `#include "x.h"` | `static` is private | (is the ABI) | is the format |

- No header files: twenty-eight of twenty-nine. C++ added modules after headers and never
  replaced them. Cpp2 is order independent and writes the forward declarations itself.
- A hand-written interface file per module, compiled once and never pasted in: Ada (spec
  `.ads`, body `.adb`) and Modula-2 (`.def`, `.mod`); in OCaml the `.mli` is optional.
  Importers read only the interface, so a body edit never rebuilds them. Ada's spec has a
  `private` part that shows layout to the compiler but not to user code. Modula-2's opaque
  `TYPE T;` hides layout fully but forces a pointer. The cost is two files to keep in step.
  C# and Visual Basic get the same split from assembly metadata, with no second file to
  write.
- What a module is: a file (Zig, D, Nelua, Oberon, OCaml, Racket, Python, JavaScript,
  TypeScript), a directory (Odin, Hare, Go), or a whole target or project (Swift, Rust's
  crate, C# and Visual Basic assemblies). In C# and Visual Basic, namespaces are only names
  and can span assemblies; `internal`/`Friend` means "this assembly".
- Private by default (Zig, Hare, Rust, Swift `internal`, Go lowercase names, Oberon,
  Racket, JavaScript, TypeScript, C# members, R) (eleven; Java's package-private is close)
  vs public by default (C3, Odin, Jai, Carbon, D, Kotlin, Scala, OCaml unless an `.mli`
  hides it, Python) (nine). Ada and Modula-2 decide by place: what is in the spec or `.def`
  is public. Nelua writes `local` (file) or `global` on each name, and all globals share
  one flat namespace, which is weak for big code. Go's capitalization needs no keyword but
  makes renaming painful. Oberon's export is one `*` on the declaration, and exported
  variables are read-only to importers (Oberon-2 adds `-`), so no setters are needed.
  Python's `_name` and `__all__` and R's `pkg:::f` are only advisory. R lists exports in a
  separate `NAMESPACE` file, not in the source. Racket's `contract-out` adds checks at the
  module border.
- Import forms: Modula-2 has both `IMPORT M;` (always `M.f`) and `FROM M IMPORT f;`;
  Oberon can rename on import (`Out := MyOut`). OCaml needs no import at all: `Foo.bar`
  finds `foo.ml`, and `open Foo` brings the names in. R's `stats::median(x)` works the
  same way without `library`.
- Declaring a C function: `extern` (Zig, C3, Goose, Rust, C++ `extern "C"`, D
  `extern(C)`, Scala Native `@extern`, C# `extern` with `[DllImport]`) (eight); OCaml's
  `external` is close. An attribute or aspect on the declaration: Nelua `<cimport>`, Ada
  `with Import, Convention => C`, C# `[LibraryImport]`, Visual Basic `<DllImport>` (or
  `Declare Function … Lib "libc"`). A whole module marked C: Modula-2 (gm2)
  `DEFINITION MODULE FOR "C"`. A library call: Racket `get-ffi-obj`, Python `ctypes`,
  like Java's FFM API and Terra. Glue written in C against the runtime: OCaml stubs, R
  `.Call`, Python extension modules. None in the language: JavaScript, TypeScript, Oberon
  (only compiler-specific ways).
- The C door can be marked unsafe by name: Rust `unsafe extern`, Racket `ffi/unsafe`,
  Oberon's `SYSTEM` module (importing it marks the module as unsafe).
- Importing C headers inside the language: Carbon (`import Cpp library "x.h"`), Swift
  (modulemap, `import CLib`), Terra (`terralib.includec`), D (ImportC), Go (cgo: the
  header in a comment above `import "C"`), C++ and Cpp2 (`#include`), and Zig until 0.16
  (seven of twenty-nine today). Nelua's `## cinclude` only puts the header in the C it
  emits; the bindings are still written by hand. Python's `cffi` parses C declarations
  pasted into a string. A separate tool generates bindings: Jai, Rust (`bindgen`), Java
  (`jextract`), Kotlin (`.def` file and `cinterop`), Scala (`sn-bindgen`), Ada
  (`gcc -fdump-ada-spec`), C# (ClangSharp). By hand: C3, Odin, Hare, Goose, Nelua, Modula-2
  (the `.def`), OCaml, Racket, Python `ctypes`, Visual Basic, R (glue in C). JavaScript,
  TypeScript and Oberon have no header path at all.
- A namespace prefix keeps foreign names visible: Carbon `Cpp.f()`, Terra `C.printf`, Go
  `C.puts`.
- A build tool or script in the language itself: Zig `build.zig`, Jai, Swift
  `Package.swift`, Terra, Go (the `go` tool, no build files), Kotlin (Gradle Kotlin DSL).
  Declarative package files instead: Python `pyproject.toml`, R `DESCRIPTION`, Racket
  `info.rkt`.
- Agree: no headers (twenty-eight); private by default (eleven); `extern` for C (eight);
  header import in the language (seven).
- How each module system works inside (resolution, cycles, init, interfaces, symbols,
  packages) is section 13.

## 10. Memory

| Language | Allocation | Allocator passing | Cleanup | Ownership |
|---|---|---|---|---|
| Zig | `a.alloc(u8, n)` | explicit parameter (`std.mem.Allocator`) | `defer`, `errdefer` | none |
| C3 | `mem::new(Foo)`, `malloc` | explicit first argument (`mem`, `tmem`); `@pool() {…}` | `defer` | none |
| Odin | `make`, `new`, `append` | implicit `context.allocator`, or a defaulted last parameter | `defer delete(x)` | none |
| Hare | `alloc(v)!`, `append(s, x)?` (fail as `nomem`) | none (one global heap) | `defer free(p)` | none |
| Jai | `New(T)`, `alloc` | implicit `context`, `push_allocator(a)` | `defer free(p)` | none |
| Goose | none: scope-bound data stacks | none | scope exit | inferred roots, implicit borrows |
| Carbon | library (unsettled) | not designed | destructors (`destroy`) | not designed yet (the 0.1 safety work) |
| Swift | ARC for classes, copy-on-write collections; `UnsafeMutablePointer<T>.allocate` | none | ARC, `deinit`, `defer` | `~Copyable`, `borrowing`, `consuming`, `consume x` |
| Rust | `Box::new(5)`, `Vec`; global allocator | none on stable | destructors (`Drop`) | moves, `&`/`&mut` borrows, lifetimes `'a`, `unsafe { }` |
| C++ | `new`, `std::make_unique`, containers | template parameter or `std::pmr` resource | destructors (RAII) | `std::unique_ptr` (library), no checking |
| D | GC by default; `malloc` in `-betterC`, `@nogc` | `std.experimental.allocator` (library) | `scope(exit) free(p);`, destructors | `@safe`/`@trusted`/`@system`; DIP1000 `scope` (preview) |
| Cpp2 | `unique.new<T>()`, `shared.new<T>()` | none | destructors; `guard` prefix | move at last use; no checking |
| Terra | `C.malloc` via `includec` | none | `defer C.free(p)` | none |
| Java | `new` (GC); FFM `Arena` | none | GC; `try`-with-resources | none |
| Go | `new`, `make` (GC, escape analysis) | none | GC; `defer` | none; `unsafe` package |
| Kotlin | GC; Native `nativeHeap.alloc`, `memScoped { }` | implicit (`memScoped` receiver) | GC; arena freed at block exit | none; opt-in annotation |
| Scala | GC; Native `stackalloc`, `Zone` | `using Zone` parameter | GC; `Zone` freed at scope exit | none; `unsafe` import |
| Nelua | `new(@T)`, `delete(p)`; GC by default, `-Pnogc` for manual | allocator as a generic parameter, `vector(T, Allocator)`; `general_allocator`, `arena_allocator`, `gc_allocator` | `defer`, `<close>` with `__close`, `__gc` | none |
| Ada | `new T'(…)`, `new Integer'(5)`; stack for most data (bounds, unconstrained returns on secondary stack) | per access type: `for Ptr'Storage_Pool use My_Pool;`; subpools (2012) | `Ada.Unchecked_Deallocation`; controlled types (`Finalize`); scope-based finalization | accessibility levels on `'Access`; SPARK: Rust-like move, borrow, observe for access types |
| Modula-2 | `NEW(p)`, `DISPOSE(p)` (call `ALLOCATE`/`DEALLOCATE` in scope); `Storage` module | none (global `ALLOCATE` in scope) | manual `DISPOSE`; ISO module `FINALLY` | none |
| Oberon | `NEW(p)` (GC heap; no `DISPOSE`) | none | GC (no finalizers in -07) | none; `SYSTEM` is the unsafe escape |
| OCaml | implicit (`{ x = 1 }`, `Array.make n 0`, `ref 0`); GC (minor + major heap) | none | GC; `Gc.finalise`, `Fun.protect ~finally`, `In_channel.with_open_bin` | none (OxCaml modes and uniqueness out of tree) |
| Racket | implicit (`cons`, `make-vector`); FFI `(malloc n 'raw)` | none | GC; custodians (`custodian-shutdown-all`), will executors, `dynamic-wind` | none |
| Python | implicit on object creation, `P()`, `bytearray(n)` | none | reference counting plus cycle GC; `with`, `weakref.finalize`, `__del__` | none |
| JavaScript | `new P()`, `{}`, `[]`, `new ArrayBuffer(n)` (GC) | none | GC; `using` + `Symbol.dispose`; `WeakRef`, `FinalizationRegistry` | none; `ArrayBuffer.prototype.transfer()` detaches; `postMessage` transfer lists |
| TypeScript | `new P()`, `{…}`, `[]` (GC in the JS engine) | none | GC; `using` with `[Symbol.dispose]()`; `FinalizationRegistry` | none; `readonly` in types only |
| C# | `new T()` (GC heap), `stackalloc byte[n]`, `NativeMemory.Alloc(n)` | none; `ArrayPool<T>.Shared` | GC; `IDisposable` + `using`; finalizers | none; `ref struct` (stack only), `scoped`, ref escape rules |
| Visual Basic | `New T()`, `ReDim` (GC) | none | GC; `Using` / `IDisposable`; `Finalize` | none |
| R | implicit; `numeric(n)`, `vector("list", n)`; C: `PROTECT(allocVector(REALSXP, n))` | none | GC (generational); `on.exit()`, `reg.finalizer()` | none; copy on modify (ref counts); environments are shared refs |
| C | `malloc`, `free` | none standard | `goto cleanup`; TS `defer` | none (`restrict` is a promise) |

- Explicit allocator (Zig parameter, C3 first argument, C++ `std::pmr` resource) vs an
  implicit one (Odin and Jai context; Kotlin's `memScoped` receiver; Scala's `using Zone`
  parameter, explicit in the signature and implicit at the call). The rest have none in
  the language. Thirteen use a GC: Java, Go, Kotlin, Scala, Oberon, OCaml, Racket, Python
  (reference counting plus cycle GC), JavaScript, TypeScript, C#, Visual Basic, R. Nelua
  and D use a GC by default, and you can turn it off.
- The allocator can also sit in the type instead of the call. Nelua passes it as a generic
  parameter (`vector(T, Allocator)`), as C++ can with a template parameter. Ada binds a
  storage pool to each access type (`for Ptr'Storage_Pool use My_Pool;`). Both are fixed
  at compile time and leave call sites clean, but you can't pick a different allocator
  per call. Modula-2's `NEW`/`DISPOSE` call whatever `ALLOCATE`/`DEALLOCATE` is in scope,
  which is a crude kind of pluggable allocator. C# has a library pool (`ArrayPool<T>`).
- Scoped arenas freed at block exit: Java FFM `Arena`, Kotlin `memScoped`, Scala `Zone`,
  C3 `@pool`. Related: Nelua's `arena_allocator`, Ada's subpools, and Racket's custodians,
  which shut down a whole group of resources (threads, ports, sockets) at once. Custodians
  are a coarse but useful kind of cleanup scope.
- No hidden allocation: Zig, C3, Hare, Goose, Terra, D `-betterC`, Modula-2, C. Ada uses
  the heap only through `new`, but it puts variable-size results on a secondary stack
  without saying so. Oberon allocates only with `NEW`, but only the GC frees. Hidden: Odin
  and Jai (from the context), Rust, C++, Cpp2, full D, Swift, and the GC languages (boxing,
  closures, `append`). OCaml, Racket, Python and R allocate on almost every value.
- Out-of-memory as an ordinary error (Hare `nomem`, Zig `error.OutOfMemory`).
- Owned values: Rust's moves and checked borrows; Swift's `~Copyable`; C++ `unique_ptr`
  and Cpp2's move at last use (unchecked); D's `@live` (experimental); Scala's capture
  checking (experimental); SPARK's Rust-like move, borrow and observe for Ada access types;
  OxCaml's modes and uniqueness (out of tree). Ada's accessibility levels on `'Access` and
  C#'s `ref struct`, `scoped` and ref escape rules give checked non-GC views without full
  ownership. JavaScript's `ArrayBuffer.prototype.transfer()` detaches the old buffer, a
  light kind of move. R gets value semantics by copy on modify (ref counts), like Swift's
  copy-on-write collections. Prior art for `alcor-safety-syntax`: Rust, Swift and SPARK,
  plus C#'s escape rules, ATS, Austral, Vale.
- Marking unsafe code: Rust `unsafe { }` blocks; Swift strict mode; D `@safe`/`@trusted`/
  `@system` (default `@system`); Go's `unsafe` package; Scala Native's `unsafe` import;
  Java's restricted methods behind `--enable-native-access`; Kotlin's opt-in annotation
  (weaker than a lexical block); Oberon's `SYSTEM` pseudo-module (importing it marks the
  module as unsafe); Racket's `racket/unsafe/ops` and `ffi/unsafe`; C#'s `unsafe` for raw
  `T*`. Ada puts the risk in the name: freeing is `Unchecked_Deallocation`. Visual Basic
  has no pointers and no `unsafe` at all.
- Destructors (C++, Rust, Carbon, Cpp2, Ada controlled types with `Finalize`) free with
  invisible calls; `defer free(p)` keeps the same benefit visible. GC finalizers (C#, Visual
  Basic `Finalize`, Python `__del__` and `weakref.finalize`, JavaScript and TypeScript
  `FinalizationRegistry`, OCaml `Gc.finalise`, Racket will executors, R `reg.finalizer()`,
  Nelua `__gc`) run at an unknown time, so they can't be trusted to free in time.
- Cleanup tied to a value at scope exit: Python `with`, JavaScript and TypeScript `using`
  with `Symbol.dispose`, C# `using` with `IDisposable`, Visual Basic `Using`, Java
  `try`-with-resources, Nelua `<close>` with `__close`. The binding shows the cleanup but
  the call at exit is unseen, so it sits between `defer` and destructors. Pro: you can't
  forget the call. Con: the type has to carry the cleanup. Without it, cleanup falls back
  to helpers: OCaml `Fun.protect ~finally`, Racket `dynamic-wind`, R `on.exit()`.
- Agree: `defer` frees (eleven); scoped arenas (Java, Kotlin, Scala, C3); explicit
  allocators (Zig, C3, C++ `pmr`; in the type in Nelua and Ada); marked unsafe code (ten);
  cleanup tied to a value (six); a GC (thirteen, plus Nelua and D by default).

## 11. Undefined behaviour

| Language | Build modes | Integer overflow | Checked | Still undefined |
|---|---|---|---|---|
| Zig | `Debug`, `ReleaseSafe` (checks on); `ReleaseFast`, `ReleaseSmall` (off) | panic in safe modes, UB in fast; `+%` wraps, `+\|` saturates | bounds, null `.?`, casts, division by zero, inactive union field | use after free, races, aliasing |
| C3 | safe (debug default) and fast | wraps (defined) | bounds, null, division by zero, contracts (`@require`) | everything above in fast mode |
| Odin | none; bounds checks on in all builds | wraps (defined) | bounds, type assertions | null and dangling deref, use after free |
| Hare | debug default, `-R` release | wraps (unverified) | bounds, `as`, `!` | use after free, bad casts |
| Jai | debug (own backend), release (LLVM) | unchecked (unverified) | bounds (`#no_abc` opts out), casts | dangling, use after free |
| Goose | `-O0`..`-O2` | unsigned wraps; signed traps in debug, wraps in release | bounds, references proven statically | not found |
| Carbon | development (trap), hardened (trap or defined, never UB), performance | signed traps in development; may be UB in performance | bounds (unverified), null by type | use after free, races (until the safety design) |
| Swift | `-Onone` and `-O` both keep checks; `-Ounchecked` removes them | traps; `&+` wraps | overflow, bounds, nil `!`, division by zero | `Unsafe*Pointer` misuse, `-Ounchecked` violations |
| Rust | `dev` (checks), `release` | panics in `dev`, wraps in `release`; `wrapping_add`, `checked_add` | bounds always, division by zero | only in `unsafe`: bad pointers, races, aliasing |
| C++ | none in the standard (flags, sanitizers); C++26 hardened library, contract modes | signed UB | hardened library preconditions (C++26) | signed overflow, dangling, raw bounds, races |
| D | debug (default), `-release`, `-boundscheck=on\|safeonly\|off` | wraps (defined) | bounds (kept in `@safe` under `-release`), asserts | `@system` dangling, broken `@trusted` |
| Cpp2 | none; checks on by default, `-no-subscript-checks` etc. | C++'s (signed UB) | bounds, null, division by zero, `as`, contracts | signed overflow, dangling, races |
| Terra | optimize flag only | not documented | none | bounds, null, uninitialized, as in C |
| Java | one mode; checks always on | wraps (defined); `Math.addExact` | bounds, null, division by zero, casts | JNI, restricted FFM, `Unsafe` |
| Go | one mode; checks always on | wraps (defined) | bounds, `nil`, division by zero | races on multiword values, `unsafe`, cgo |
| Kotlin | debug and release differ only in optimization | wraps (defined) | bounds, null (`!!`), casts, division by zero | cinterop pointers |
| Scala | JVM: one mode; Native: debug, release modes | wraps (defined) | bounds, null | Native raw `Ptr` |
| Nelua | debug (checks on); `--release` / `-Pnochecks` (off) | wraps (defined) | bounds, nil deref, narrowing casts, division by zero (unverified) | use after free, dangling pointers, data races, C interop |
| Ada | checks on by default; `-gnatp` / `pragma Suppress (All_Checks)` off; `-gnata` turns on contracts | `Constraint_Error` for signed; `mod` types wrap | range, index, null, discriminant, division, overflow, accessibility, contracts | "erroneous execution": use after `Unchecked_Deallocation`, races on shared vars, failed suppressed checks, bad `Unchecked_Conversion`; SPARK proves absence |
| Modula-2 | gm2: checks off by default; `-fsoft-check-all` or each: `-fnil`, `-findex`, `-frange`, `-fwholediv`, `-fwholevalue`, `-fcase`, `-freturn` | ISO: an exception; gm2 wraps unless `-fwholevalue` (unverified) | bounds, ranges, `NIL`, division by zero, overflow, `CASE` miss, missing `RETURN` (each a flag) | use after `DISPOSE`, uninitialized reads, wrong variant, `CAST`, `ADDRESS` math |
| Oberon | one mode; compiler flags vary | not defined by the report (wraps on most compilers, unverified) | array index, `NIL`, type guard, `CASE` no match, `ASSERT` | uninitialized locals, overflow, `SYSTEM` use |
| OCaml | bytecode (`ocamlc`), native (`ocamlopt`); `-unsafe` drops bounds checks; flambda `-O3` | wraps (defined, modular) | bounds (`Invalid_argument`), division by zero (`Division_by_zero`), stack overflow; no null | `Obj.magic`, `unsafe_get`, `-unsafe`, bad C stubs; races are not UB (bounded memory model) |
| Racket | one mode, checks always on; `errortrace` for debug | none: exact integers grow into bignums; `fx+` checks fixnum range | types of primitive args, arity, bounds, division by zero | `racket/unsafe/ops` (`unsafe-fx+`, `unsafe-vector-ref`) misuse, `ffi/unsafe` |
| Python | one mode; `-O` drops asserts; debug build (`--with-pydebug`); free-threaded build | none (`int` is unbounded) | bounds (`IndexError`), `None` access, division by zero, types at run time | `ctypes` and C extension bugs; races are not UB but not atomic |
| JavaScript | none; sloppy vs strict (`"use strict"`; modules always strict) | f64: exact only to 2^53; bitwise ops wrap to 32 bits; `BigInt` arbitrary; typed arrays wrap (`Uint8ClampedArray` clamps) | all: `TypeError` on `null.x`; out-of-bounds read gives `undefined`; `1/0` is `Infinity` | none in spec; some implementation-defined results (`sort` with bad comparator); `SharedArrayBuffer` races give unspecified values, not UB |
| TypeScript | none (`strict` flags change checks only); output is JS | no overflow: f64 rounding, exact ints to 2^53; `bigint` unbounded; `x \| 0` wraps to 32 bits | runtime: out of bounds gives `undefined`, `null` access throws; types compile-time only | no memory UB; types unsound (`any`, `as`, array variance, bivariant methods) |
| C# | Debug / Release (speed only; same checks) | wraps by default (`unchecked`); `checked(…)` or `<CheckForOverflowUnderflow>` throws | bounds, null, casts, integer division by zero | `unsafe` pointers, `Unsafe.*`, `MemoryMarshal`, interop; races tear structs |
| Visual Basic | Debug, Release (same checks) | throws `OverflowException` by default; `-removeintchecks` makes it wrap | overflow, bounds, `Nothing` deref, casts, division by zero | data races, P/Invoke and `Marshal` misuse |
| R | one mode; byte-code JIT `compiler::enableJIT(3)` | 32-bit int overflow gives `NA` plus a warning; doubles are IEEE | types at runtime, `[[` bounds, int overflow; `x[10]` past end gives `NA` | bugs in C code (`.Call`, `PROTECT` misuse) |
| C | none in the standard (sanitizers) | signed UB; `ckd_add` (C23) | none | all of the above |

- Checks on in debug builds, off or UB in fast builds: Zig, C3, Jai, D, Nelua. Checks
  always on: Java, Go, Kotlin, Scala (JVM), Swift, Odin (bounds), Cpp2 (opt out per check),
  Carbon's hardened mode, Ada (opt out with `-gnatp`), Oberon, OCaml (unless `-unsafe`),
  Racket, Python, JavaScript, TypeScript, C#, Visual Basic, R. C# and Visual Basic say it
  plainly: Debug and Release differ only in speed. The odd one out is Modula-2 in gm2:
  checks are off by default and turned on one flag at a time, though ISO says they raise
  exceptions.
- A third category between defined and UB: Carbon's "hardened" mode and C++26's
  "erroneous behaviour", plus C++26 contract modes (Ada turns contracts on with
  `-gnata`). Ada's own name for UB is "erroneous execution"; it includes a failed check
  that was suppressed. JavaScript has no UB in its spec at all, only some
  implementation-defined results (`sort` with a bad comparator).
- Races without UB: OCaml 5 (bounded memory model), Python (not UB, but not atomic),
  JavaScript (`SharedArrayBuffer` races give unspecified values). Elsewhere races stay
  undefined or close to it: Go (multiword values), C# (structs tear), Ada (shared vars),
  Nelua, Visual Basic, Zig, C++, Cpp2.
- Overflow: UB (Zig fast, C, C++, Cpp2, Carbon performance; Oberon leaves it undefined)
  vs defined wrap (C3, Odin, Hare, D, Rust release, Java, Go, Kotlin, Scala, Nelua, OCaml,
  C#) vs trap or throw by default (Swift always; Ada `Constraint_Error`; Visual Basic
  `OverflowException`; Modula-2 ISO an exception). Java, Go, Kotlin, Scala, C# and OCaml
  wrap silently, which hides bugs; their checked helpers (`Math.addExact`, C# `checked`)
  show the need. C# and Visual Basic run on the same platform with opposite defaults.
  Explicit wrap operators: Zig `+%`, Swift `&+`, Rust `wrapping_add`; Ada wraps by type
  (`mod` types) and C# by scope (`unchecked`).
- No overflow at all: Racket and Python have unbounded integers (Racket's `fx+` still
  checks the fixnum range). R gives `NA` plus a warning. JavaScript and TypeScript use
  f64: exact only to 2^53, bitwise ops wrap to 32 bits, `BigInt` is separate. Cost:
  bignums or floats where a systems language wants fixed-size ints.
- Opting out: per scope (Zig, Odin, Jai); per function (D `@system`); per check for a
  whole file (Cpp2); per expression (C# `checked` / `unchecked`); per operation by name
  (Racket `unsafe-fx+`, `unsafe-vector-ref`; OCaml `unsafe_get`); by pragma (Ada `pragma
  Suppress (All_Checks)`); global (Swift `-Ounchecked`, D `-boundscheck=off`, Go `-B`,
  Ada `-gnatp`, Nelua `-Pnochecks`, OCaml `-unsafe`, Visual Basic `-removeintchecks`).
  Opting in per check: gm2's flags (`-findex`, `-fnil`, `-frange`, `-fwholevalue`, ...).
- Unsafe code fenced by name: Racket (`racket/unsafe/ops`, `ffi/unsafe`), Oberon (the
  `SYSTEM` pseudo-module), C# (`unsafe`, `Unsafe.*`, `MemoryMarshal`), Ada (`Unchecked_`
  prefix on `Unchecked_Deallocation`, `Unchecked_Conversion`), OCaml (`Obj.magic`,
  `unsafe_get`). The name shows up in the code, so a search finds every unsafe spot.
- Wider check sets than bounds and null: Ada (range, discriminant, accessibility),
  Modula-2 (ranges, `CASE` miss, missing `RETURN`), Oberon (type guard, `CASE` no match).
- Out of bounds is not always an error: JavaScript and TypeScript return `undefined`, and
  R's `x[10]` past the end gives `NA`. Memory stays safe, but the bug moves on silently.
- Zero initialization removes uninitialized-read UB (Odin, Jai, D, Go, Nelua). Without it,
  uninitialized reads stay undefined (Modula-2, Oberon locals, Terra, C).
- Use after free stays undefined in all but Goose, safe Rust, safe Swift and the GC
  languages (Java, Go, Kotlin, Scala, Oberon, OCaml, Racket, Python, JavaScript,
  TypeScript, C#, Visual Basic, R). Nelua uses GC by default but still lists use after
  free; Modula-2 (`DISPOSE`) and Ada (`Unchecked_Deallocation`) leave it to the user.
  Rust's "safe code has no UB; UB only inside `unsafe`" is the clearest boundary; Java,
  Kotlin and Scala keep UB only in foreign-memory code, and so do Python (`ctypes`, C
  extensions), R (C code, `PROTECT` misuse) and Visual Basic (P/Invoke, `Marshal`).
- Proof instead of checks: SPARK proves the absence of Ada's erroneous execution, and
  Goose proves references statically. Both remove the run-time cost, at the price of a
  prover.
- Types do not give safety alone: TypeScript has no memory UB, but its types are unsound
  (`any`, `as`, array variance), so a value can differ from its type at run time.
- Debug tools as build options: Go's race detector (`-race`), sanitizers in C and C++,
  Racket's `errortrace`, Python's debug build (`--with-pydebug`).
- Agree: bounds checks on by default (twenty-four of twenty-nine; not C++ raw arrays,
  Terra, Modula-2 in gm2; JavaScript and TypeScript are safe but return `undefined`);
  defined wrap (twelve); trap in checked builds (Zig, C3, Jai, Goose, Carbon, Swift, Rust,
  D, Cpp2, Nelua, Oberon), or throw an exception instead (Ada, Modula-2 ISO, Visual
  Basic, C#, OCaml, Racket, Python, Java, Kotlin, Scala); explicit wrap operators (Zig,
  Swift, Rust; Ada and C# by type or scope).

## 12. Lexical details

| Language | Semicolons | Comments | Raw / multiline strings | Numbers | Keywords |
|---|---|---|---|---|---|
| Zig | required | `//` only; `///` doc | `\\` at each line start | `0x 0o 0b`, `1_000` | about 43; `and`/`or` |
| C3 | required | `//`, nesting `/* */`, `<* *>` doc | `` `raw` `` | `0x 0o 0b`, `1_000` | about 40–50, plus `$`, `@` |
| Odin | optional (inserted at newlines) | `//`, nesting `/* */` | `` `raw` `` | `0x 0o 0b`, `1_000` | about 40 |
| Hare | required, also after `}` | `//` only | `` `raw` `` | `0x 0o 0b`, suffixes `10z` | about 70 (types and built-ins included) |
| Jai | required, not after a closing `}` | `//`, nesting `/* */` | `#string END … END` | `0x 0b`, `1_000` | small, plus many `#` directives |
| Goose | required, not after a closing `}` | `//`, nesting `/* */` | `"""` (unverified) | `0x`, hex floats | about 25 seen |
| Carbon | required | `//` only, on its own line | `'''` block, `#"raw"#` | `0x 0b`, `1_000` | about 70 |
| Swift | optional | `//`, nesting `/* */`, `///` doc | `"""` multiline, `#"raw"#` | `0x 0o 0b`, `1_000` | about 70, plus 30–40 contextual |
| Rust | required (last expression without `;` is the value) | `//`, nesting `/* */`, `///` doc | `r#"raw"#`; plain strings span lines | `0x 0o 0b`, `1_000`, suffixes `10u8` | 38 strict |
| C++ | required | `//`, non-nesting `/* */` | `R"(…)"` | `0x 0b`, leading `0` octal, `1'000` | about 92 |
| D | required | `//`, `/* */`, nesting `/+ +/` | `r"…"`, `` `…` ``, `q"(…)"`, `q{ code }` | `0x 0b`, `1_000`; leading `0` is an error | about 100 |
| Cpp2 | required, not after `= { }` | `//`, non-nesting `/* */` | `R"(…)"`; interpolation `"(x)$"` | C++'s, `1'000` | C++'s plus contextual (`inspect`, `is`, `as`, `next`) |
| Terra | optional | `--`, `--[[ ]]` | `[[ … ]]`, `[==[ … ]==]` | `0x`; suffixes `3LL`, `3.f` | about 31 |
| Java | required | `//`, non-nesting `/* */`, `///` doc | text blocks `"""`; no raw strings | `0x 0b`, `1_000`, leading `0` octal | about 51 plus contextual |
| Go | inserted at line ends | `//`, non-nesting `/* */` | `` `raw` `` | `0x 0o 0b`, `1_000` | 25 |
| Kotlin | optional | `//`, nesting `/* */` | `"""raw"""`; templates `"$x"` | `0x 0b`, `1_000`; no octal | about 28 hard plus soft |
| Scala | optional; indentation syntax optional | `//`, nesting `/* */` | `"""raw"""`; `s"$x"` | `0x 0b`, `1_000`; no octal | about 41 plus soft |
| Nelua | optional | `--`, `--[[ ]]` | `[[raw]]`, `[==[ … ]==]` | `0x`, `0b`, suffixes `1_u8`, `1.0_f32` | about 29: Lua's 22 plus `global`, `switch`, `case`, `defer`, `continue`, `fallthrough`; `and`/`or`/`not` |
| Ada | required (terminators) | `--` only | none; `""` escapes a quote; join with `&` and `ASCII.LF` | `16#FF#`, `2#1010#` (any base 2-16), `1_000`, `1.0E6` | 74 reserved words (2022 added `parallel`), case-insensitive; `and then`, `or else` |
| Modula-2 | separators between statements (before `END` optional) | `(* *)`, nesting | none; `"…"` or `'…'`, no escapes, one line | `0FFH` hex, `17B` octal, `41C` char, `1.0E3`; no `_` | about 40 PIM, 46 ISO; UPPERCASE, case-sensitive |
| Oberon | separators (between statements; optional before `END`) | `(* … *)`, nesting | none; `"…"` or `'…'` with no escapes; `0DX` char codes | `0FFH`, `41X` (char), `1.0E3`; no `_` | 33, all capitals; `&`, `~`, `OR` |
| OCaml | `;` sequences; `;;` optional at top level | `(* nested *)`, `(** doc *)`; no line comment | `{\|raw\|}`, `{id\|…\|id}`; strings may span lines | `0x 0o 0b`, `1_000`, `0l 0L 0n` suffixes | about 60; `mod`, `land`, `lsl` are keywords |
| Racket | none (`;` starts a comment) | `;`, nesting `#\| … \|#`, `#;` datum comment | strings may span lines; here strings `#<<END`; `@` reader (`#lang at-exp`) | `#x1F #o17 #b101`, exact `1/3`, `1e3`, `#e1.5`, `+inf.0`; no `_` separators | no reserved words (all rebindable); about a dozen core forms (`define-values`, `lambda`, `#%app` …) |
| Python | optional; newline ends a statement; indentation blocks | `#` only; docstrings `"""…"""` | `r"…"`, `"""…"""`; `f"…"`, `t"…"` (3.14) | `0x 0o 0b`, `1_000`, `1j` | 35; soft: `match`, `case`, `_`, `type`, `lazy` (3.15); `and`/`or`/`not` |
| JavaScript | optional (automatic insertion, with traps) | `//`, non-nesting `/* */`, `#!` first line | template literals `` `a ${x}` `` (multiline), `String.raw` | `0x 0o 0b`, `1_000`, `1e3`, `10n` (BigInt) | about 40 reserved; contextual `let`, `async`, `of`, `get` |
| TypeScript | optional (auto-inserted) | `//`, `/* */`, `/** */` JSDoc | template literals `` `a ${x}` `` span lines; `` String.raw`…` `` | `0x 0o 0b`, `1_000`, `10n` | about 40 JS reserved plus about 30 contextual (`type`, `interface`, `as`, `satisfies`, `keyof`, `infer`) (unverified count) |
| C# | required | `//`, non-nesting `/* */`, `///` XML doc | `@"verbatim"`, `"""raw multiline"""`, `$"{x}"` | `0x 0b` (no octal), `1_000`, suffixes `10u 10L 1.5f 1m` | 77 reserved plus about 40 contextual (`var`, `record`, `field`, `extension`) |
| Visual Basic | none; line ends a statement (`:` joins, `_` continues) | `'` and `REM` | multiline `"…"` since VB 14; `""` escapes quote; no raw | `&H &O &B`, `1_000`, suffixes `100L`, `1UI` | about 150 reserved (unverified); `AndAlso`/`OrElse`, case-insensitive |
| R | optional; newline ends a complete expression; `;` to join | `#` only; `#'` roxygen doc (by tool) | `r"(raw)"`, `r"---(…)---"` (4.0+); plain strings span lines | `42L`, `0x1F`, `1e-3`, `0x1p-2`, `3i`; no `_`, no `0b`/`0o` | about 20 reserved (`?Reserved`): `if`, `function`, `repeat`, `NA`, … |
| C | required | `//`, non-nesting `/* */` | none (concatenation) | `0x 0b`, `1'000` (C23), leading `0` octal | about 59 |

- Semicolons: required in thirteen of twenty-nine (Ada as a terminator, C# like the C
  family); optional or inserted in eleven: Odin, Swift, Terra, Go, Kotlin, Scala, Nelua,
  Python, JavaScript, TypeScript, R. Go's automatic insertion forces the `{` onto the same
  line; JavaScript's insertion has known traps. Separators between statements, not
  terminators: Modula-2 and Oberon (optional before `END`), OCaml (`;` joins a sequence,
  `;;` is optional at top level). No `;` at all: Racket (`;` starts a comment), Visual Basic
  (a line ends a statement, `:` joins, `_` continues). Python ends a statement at a newline
  and marks blocks by indentation; R ends one at a newline once the expression is complete.
- Block comments: nesting (C3, Odin, Jai, Goose, Swift, Rust, D `/+ +/`, Kotlin, Scala,
  Modula-2, Oberon, OCaml, Racket `#| |#`: thirteen); non-nesting `/* */` (C, C++, Cpp2,
  Java, Go, JavaScript, TypeScript, C#); line comments only: `//` (Zig, Hare, Carbon), `--`
  (Ada), `#` (Python, R), `'` or `REM` (Visual Basic); Lua's `--` and `--[[ ]]` (Terra,
  Nelua). Modula-2, Oberon and OCaml have only `(* *)`, no line comment. Racket's `#;`
  comments out one whole datum, so the reader must parse what it skips. Doc comments vary:
  `///` (Zig, Swift, Rust, Java, C#), `(** *)` (OCaml), `/** */` (TypeScript); Python's
  docstrings are plain strings, and R's `#'` is read by a tool, not the language.
- Raw strings: backticks (C3, Odin, Hare, D, Go: five); `"""` (Swift, Goose, Kotlin,
  Scala, Python, C# raw; Java text blocks, not raw: seven); `#"…"#` (Carbon, Swift; Rust
  `r#"…"#`); `R"(…)"` (C++, Cpp2; R's `r"(…)"` and `r"---(…)---"`); an `r` or `@` prefix
  (Python `r"…"`, D `r"…"`, C# `@"verbatim"`); long brackets (Terra, Nelua); `{|…|}` and
  `{id|…|id}` (OCaml); here strings (Jai `#string END`, Racket `#<<END`). No raw strings at
  all: Ada, Modula-2, Oberon, Visual Basic (and C). Ada and Visual Basic double a quote
  (`""`); Modula-2 and Oberon have no escapes, and Oberon writes special characters as codes
  (`0DX`). Plain strings span lines in Rust, OCaml, Racket, R and Visual Basic (since VB 14).
  Interpolation: Kotlin `"$x"`, Scala `s"$x"`, Swift `"\(x)"`, Cpp2 `"(x)$"`, Python
  `f"…"` (and `t"…"` in 3.14), JavaScript and TypeScript `` `${x}` ``, C# `$"{x}"`: eight.
  Racket's `@` reader (`#lang at-exp`) mixes text and code another way.
- Digit separators: `_` (Zig, C3, Odin, Jai, Carbon, Swift, Rust, D, Java, Go, Kotlin,
  Scala, Ada, OCaml, Python, JavaScript, TypeScript, C#, Visual Basic: nineteen) vs `'`
  (C23, C++, Cpp2); none (Modula-2, Oberon, Racket, R). `0o` octal (Zig, C3, Odin, Hare,
  Swift, Rust, Go, OCaml, Python, JavaScript, TypeScript: eleven, and C2y); other octal
  spellings (Racket `#o17`, Visual Basic `&O`, Modula-2 `17B`, Ada `8#17#`); no octal at
  all (Kotlin, Scala, C#, R); leading `0` still octal (C, C++, Java), an error in D.
- Bases outside the C style: Ada's `16#FF#` takes any base from 2 to 16; Modula-2 and
  Oberon put the base letter last (`0FFH`) and also write characters by code (`41C`,
  `41X`), so a number must start with a digit to tell it from a name; Visual Basic uses
  `&H &O &B`; Racket uses `#x #o #b`. R has no `0b`.
- Literal suffixes: type suffixes (Hare `10z`, Rust `10u8`, Terra `3LL`, OCaml `0l 0L 0n`,
  C# `10u 1.5f 1m`, Visual Basic `100L 1UI`, R `42L`); Nelua puts `_` before a type name
  (`1_u8`, `1.0_f32`), which reads like the type itself. Other kinds: big integers `10n`
  (JavaScript, TypeScript), imaginary `1j` (Python) and `3i` (R), exact `1/3` and `#e1.5`
  (Racket), hex floats (Goose, R `0x1p-2`). A fixed suffix list ties the lexer to built-in
  type names, which matters when types are library code.
- Keyword counts: small (Racket none reserved, R about 20, Goose about 25, Go 25, Kotlin
  about 28 hard, Nelua about 29, Terra about 31, Oberon 33, Python 35, Rust 38, Modula-2
  about 40 PIM and 46 ISO, JavaScript about 40, Scala about 41, Zig about 43); large (Java
  about 51, OCaml about 60, Hare, Carbon, Swift about 70; Ada 74; C# 77; C++ about 92; D
  about 100; Visual Basic about 150, unverified). TypeScript adds about 30 contextual words
  to JavaScript's 40 (count unverified). Soft or contextual keywords (Kotlin, Scala, Swift,
  Java, Cpp2, Python, JavaScript, TypeScript, C#: nine) keep the reserved set small but make
  parsing context-sensitive. C# has about 40 of them; Python adds new ones as soft words
  (`match`, `type`, and `lazy` in 3.15).
- No reserved words: in Racket every name can be rebound, and about a dozen core forms
  (`define-values`, `lambda`, `#%app`) carry the rest. That leaves the most room for
  libraries, but a reader can't trust a word to always mean one thing.
- Case and word operators: Ada and Visual Basic are case-insensitive; Modula-2 and Oberon
  write keywords in capitals and are case-sensitive, so keywords never clash with lowercase
  names. `and`/`or` as words (Zig; Nelua and Python add `not`); short-circuit spelled as
  words in Ada (`and then`, `or else`) and Visual Basic (`AndAlso`, `OrElse`); OCaml makes
  `mod`, `land`, `lsl` keywords; Oberon mixes `&`, `~` and `OR`.
- Lexer clashes: Rust's lifetime `'a`, C++'s `'` separator and Ada's attribute tick
  (`'Size`) vs character literals; Visual Basic gives `'` to comments. Cpp2's postfix `p*`
  vs multiply. Terra's and Nelua's `--` comments, Terra's `~=` and Racket's `;` comment
  break C familiarity. A backtick means a raw string in Go but an interpolating template in
  JavaScript and TypeScript.
- Agree: required `;` (thirteen); `_` separators (nineteen); nesting block comments
  (thirteen); `0o` octal (eleven and C2y); backtick raw strings (five); `"""` strings
  (seven); string interpolation (eight).

## 13. Module systems

How each module system works inside, beyond the syntax of section 9: what a module is,
how an import finds it, what the compiler reads for it, and what that forces (cycles,
initialization, generics, symbol names, packages). Four tables, then the bullets.

**Structure**

| Language | Module | Above it | How an import finds files | Module is a value |
|---|---|---|---|---|
| Zig | file (a struct type) | module (a root file and every file it reaches), package (`build.zig.zon`) | `.zig` path relative to the file, never above the module root; other names bound by `build.zig` (`addImport`) or `-Mname=path` | yes: a build-time struct type (`@typeInfo` works on it) |
| C3 | declared `module a::b;`, many files, several per file | library (`.c3l`), project | by declared name, among all files given (`project.json` globs, `--lib`); not by path | no |
| Odin | directory (`package name` in each file) | collection (`core:`, `vendor:`, `-collection:name=path`) | `"collection:dir"` or a relative directory | no |
| Hare | directory | none | `use a::b;` is `a/b/` under the current directory, then `HAREPATH` | no |
| Jai | file, or a directory with `module.jai` that `#load`s (pastes) the rest | none (a workspace is one program) | import path (`jai/modules/`, `-import_dir`) | partly: a named import is a build-time constant used to qualify |
| Goose | file; `namespace` is a separate naming layer | package (a directory with a main file of the same name) | `import .a;` relative; packages only in the root file, `import x from "repo@ref";` | no |
| Carbon | library: one API file plus `.impl.carbon` files | package (one identifier, the top namespace) | files given on the command line, matched by their `package`/`library` lines (search paths are a TODO) | no |
| Swift | module = one target, a set of files (`-module-name`) | package, products (SwiftPM) | `Foo.swiftmodule`, `.swiftinterface` or a modulemap on `-I`/`-F`, or an explicit module map | no |
| Rust | `mod name;` tree, in `name.rs`, `name/mod.rs` or inline | crate, package, workspace | `mod` paths inside a crate; other crates by `--extern name=path.rlib`, written by Cargo | no |
| C++ | named module of units (interface, partitions, implementations) | none in the language; a build target | none: the build system scans sources (P1689) and passes interface paths (`-fmodule-file=`) | no |
| D | file, named by `module a.b;` | package (directory tree); DUB package | `a/b/c.d` or `.di` under each `-I`; `-i` also compiles what is imported | partly: a build-time symbol (`__traits(allMembers, m)`, `alias` parameters) |
| Cpp2 | none of its own (a C++ translation unit) | C++ build target | C++'s `#include`, `import` | no |
| Terra | Lua file, loaded once by `require`, returning a table | none | `TERRA_PATH` (`./?.t`), as Lua's `package.path` | yes: a Lua table, at build time |
| Java | package over many files; JPMS module (`module-info.java`) over packages | Maven/Gradle artifact | class path or module path: `a.b.C` is `a/b/C.class` | no (reflection objects only) |
| Go | directory (`package name`) | module (`go.mod`), workspace (`go.work`) | import path string: the longest module prefix, then a subdirectory | no |
| Kotlin | package (a namespace only); "module" = the files compiled together | Gradle project, artifact | package name, among sources and the classpath or `.klib`s | no; `object` is used as a namespace value |
| Scala | package over many files; `object` as a module value | subproject, artifact | classpath (`.class`, `.tasty`) | objects yes, packages no |
| Nelua | file | none (search path; no package) | `require 'a.b'` on Lua-style path `?.nelua;?/init.nelua`, `--path` / `NELUA_PATH`; relative `require '.x'` (unverified) | yes: whatever the file `return`s (often a record type) |
| Ada | library unit: package spec + body (GNAT: one unit per file) | child units (`A.B.C`), GPR project (`.gpr`), Alire crate | unit name maps to file name (`Foo.Bar` → `foo-bar.ads`), searched in project source dirs; no paths in code | no; but generic packages are instantiated and passed as formal packages |
| Modula-2 | module (`.def` + `.mod` pair, one name) | none; one flat space of module names; gm2 library sets `-flibs=pim,iso,log` | module name maps to `Name.def` / `Name.mod`, searched on `-I` paths | no |
| Oberon | module (one file, the compile unit) | none in the language (the Oberon system) | name maps to a file: `M.Mod` source, `M.smb` symbol file in the search path (OBNC: `M.obn`) | no |
| OCaml | file (compilation unit `.ml` plus optional `.mli`); nested `struct … end` | library (dune, wrapped as `Lib.Foo`), opam package | no import statement: a capital name `Foo` is looked up as `foo.cmi` in `-I` dirs; dune sets them from `(libraries …)` | no, but first-class modules `(module M : S)` pack one; functors are module functions |
| Racket | file (`#lang` line or `(module name lang …)`); submodules `module`, `module+` | collection (a directory tree), package (`info.rkt`), installation or user scope | `racket/list` → `list.rkt` in collection `racket`, searched in collection paths and links; `"util.rkt"` relative to the file; `(file "/abs")`, `(submod "." test)` | no: declared into a namespace; reflective `dynamic-require`, `module->exports`; units (`racket/unit`) are first-class |
| Python | file (`.py`), or a compiled extension | package (directory, `__init__.py`; namespace packages), distribution (`pyproject.toml`) | dotted name searched along `sys.path` (script dir, `PYTHONPATH`, `site-packages`) by `sys.meta_path` finders; `from . import x` relative | yes: a run-time `module` object, cached in `sys.modules` |
| JavaScript | file (ES module) | package (`package.json`), npm workspaces | specifier is a URL: relative `./m.js` (extension needed in browsers and Node ESM); bare names via import maps (browser) or `node_modules` walk-up plus `exports` field (Node) | yes: namespace object (`import * as m`, `await import()`) |
| TypeScript | file (ES module) | project (`tsconfig.json`, project references), npm package (`package.json`) | `moduleResolution` `nodenext`/`bundler`: relative `./x.js` maps to `x.ts`; bare names searched in `node_modules`, `package.json` `exports`; `paths` | yes at runtime: `import * as m` namespace object, `import()` gives a promise; `typeof import("./m")` as a type |
| C# | assembly (project `.csproj` builds one `.dll`); namespaces are only names | solution (`.sln`/`.slnx`), NuGet package | no path imports: compiler gets every `.cs` in the project (glob) plus referenced assemblies (`<ProjectReference>`, `<PackageReference>`); `using` only opens a namespace | no (runtime `Assembly` object via reflection) |
| Visual Basic | assembly (project, `.vbproj`); namespaces inside it | solution (`.sln`/`.slnx`), NuGet package | no file lookup: all `.vb` files in the project compile together; `Imports` names a namespace; assemblies come from project or package references | no (run-time `Assembly` object via reflection) |
| R | package (namespace); a script file via `source()` | library (install folder), repository (CRAN, Bioconductor) | `library(pkg)` looks up an installed folder in `.libPaths()`; `source()` path relative to the working dir | yes: a namespace is an environment (`asNamespace("stats")`) |
| C | translation unit; `.h` plus `.c` by convention | library (a toolchain idea) | `#include` search paths (`-I`), implementation-defined | no (a struct of function pointers is the idiom) |

**Rules**

| Language | Default visibility; levels | Import cycles | Top-level order | Module init code |
|---|---|---|---|---|
| Zig | private; `pub` (fields always public) | allowed (the artifact is analysed together) | any; analysis is lazy | none; globals are build-time values |
| C3 | public; `@private` (module), `@local` (section) | allowed | any | `@init(priority)`, `@finalizer` |
| Odin | public; `@(private)` (package), `@(private="file")` | error ("packages are libraries") | any | `@(init)`, `@(fini)`, dependencies first |
| Hare | module; `export` | error (a dependency's `.td` must exist first; `@init` order) | any | `@init`, `@fini`, dependencies first |
| Jai | public; `#scope_module`, `#scope_file` | allowed (unverified) | any | none; globals computed at build time |
| Goose | all public (v1) | allowed (unverified) | any | global initializers, imported files first |
| Carbon | public in the API file; `private`; impl-only names private | error (API files compile in order); `extern library` forward declarations | declare before use | run-time globals in `llvm.global_ctors`, order unspecified |
| Swift | `internal`; `private`, `fileprivate`, `package`, `public`, `open` | error (dependencies built first) | any | none; globals lazy (`swift_once`) |
| Rust | private (module and children); `pub(super)`, `pub(in path)`, `pub(crate)`, `pub` | allowed inside a crate; error between crates | any | none; `LazyLock` |
| C++ | not exported (module linkage); `static` (unit); `export` | ill-formed (the interface must be built first) | declare before use | dynamic initializers, imported units first |
| D | public; `private` (module), `package`, `export` | allowed; startup abort if two modules in a cycle have constructors | any | `static this()`, `shared static this()`, dependencies first |
| Cpp2 | C++'s; no access keywords at namespace scope | as C++ | any within a file (cppfront reorders) | C++'s dynamic initialization |
| Terra | Lua `local`; public is what the returned table holds | no (a cycle sees a half-loaded module) | in order (a Lua script); forward declarations | the whole file runs at build time, on first `require` |
| Java | package; `private`, `protected`, `public`, plus module `exports` | packages allowed; modules error | any | per class, lazily on first use |
| Go | package; a capital letter exports; `internal/` directories | error (builds and init need a DAG) | any | `var` initializers, then `init()`; exact order since 1.21 |
| Kotlin | public; `private` (file), `internal` (module) | packages allowed; modules error (build tool) | any | top-level properties, lazily per file |
| Scala | public; `private[pkg]`, `protected` | allowed in one compile; error between subprojects | any | each `object` lazily on first access |
| Nelua | `local` (file) or `global` (whole program); two levels | loaded once, cycles not well supported (unverified) | declare before use (one pass, like Lua) | top-level statements run at start, in `require` order |
| Ada | spec visible part public; `private` part seen by children; body private; `private with`, `limited with` | `with` cycles among specs illegal; `limited with` for mutual types; bodies may `with` each other | declare before use; incomplete types for forward refs | package body `begin … end` (elaboration); binder orders by `with` graph; `Elaborate_All`, `Preelaborate`, `Pure` |
| Modula-2 | private unless listed in the `.def`; opaque types hide fields | definition modules: error; implementation modules: allowed (init order then unclear) | declare before use (ISO/PIM, one pass); gm2 is multi-pass and looser (unverified) | module body `BEGIN … END` runs after its imports; ISO `FINALLY` at exit |
| Oberon | private; one level, `*` export (variables read-only outside) | error (import graph must be a DAG) | declare before use; sections `CONST TYPE VAR PROCEDURE`; forward `POINTER TO R` allowed | module body `BEGIN … END M.` runs once at load, after its imports |
| OCaml | public; `.mli` or signature hides; abstract and `private` types; dune `(private_modules …)` | error between files (must be a DAG); `module rec` inside a file | matters: define before use; files linked in dependency order | every top-level `let` runs at start, in link order; `let () = …` |
| Racket | private; `provide`, `all-defined-out`, `contract-out`, protected exports; phase levels (`for-syntax`, `for-template`, `for-label`) | error (cycle in loading) | functions may refer forward; values run top to bottom (use before define raises); macros before use | body runs top to bottom when instantiated, once per namespace and phase; `main` submodule runs from the command line |
| Python | all public; `_name` is a hint; `__all__` limits `import *` | allowed; importer sees a half-initialised module (fails on early `from m import x`) | top to bottom at run time; a name must be bound before use (function bodies run later) | the whole top level runs once, on first import (or first use with `lazy`) |
| JavaScript | module-private; `export`; package `exports` hides subpaths; `#x` private class fields | allowed; live bindings; TDZ error if used before init | function declarations hoisted; `let`/`const`/`class` must run first (run-time order) | top-level code runs once, dependencies first (post-order); top-level `await` |
| TypeScript | private; `export`, `export type`; package `exports` blocks deep imports; class `private`, `#x` | allowed (live bindings; TDZ error at runtime if used too early) | functions hoisted; `let`/`const`/`class` unusable before they run | top-level statements run once on first import, depth-first; top-level `await` |
| C# | top types `internal`, members `private`; `public`, `internal`, `protected`, `private protected`, `protected internal`, `file`; `[InternalsVisibleTo]` | free within an assembly; error between projects | any | static constructors (lazy, per type); `[ModuleInitializer]` methods |
| Visual Basic | types `Friend` (assembly), class fields `Private`, methods `Public`; levels `Public`, `Friend`, `Protected`, `Protected Friend`, `Private Protected`, `Private` | allowed inside an assembly; project references must form a DAG | any | `Shared Sub New` (type initializer), lazy on first use |
| R | in a package only `NAMESPACE` `export()`s are public; `::` public, `:::` internal | error at load ("cyclic namespace dependency") | files run in C-locale name order or `Collate:` field; order matters only for top-level calls | yes: top-level code runs at install time; `.onLoad()`, `.onAttach()` at load |
| C | external; `static` (unit) | include cycles need guards; link-time cycles fine | declare before use | none standard; `__attribute__((constructor))` |

**Compilation**

| Language | Importer reads | Compile / rebuild unit | Generics across modules | Symbol name |
|---|---|---|---|---|
| Zig | source | whole artifact; incremental per declaration (maturing) | instantiated in the user, from source, memoized | `main.foo`, `array_list.ArrayListAligned(u8,null).append` |
| C3 | source; or `.c3i` interface files with a prebuilt library | whole program; one object per module | in the user, from source (not through `.c3i`) | module-prefixed (exact form unverified) |
| Odin | source | whole program; one LLVM module per package, or one | in the whole-program checker | `pkg.proc` |
| Hare | `.td` file: generated Hare listing the exports | one module | none (no generics) | `fmt.println` |
| Jai | source | whole program; no incremental build | in the one compilation | undocumented |
| Goose | source | whole program, emitted as one C file | monomorphized, whole program | flattened C names |
| Carbon | the API file's source (no binary interface yet) | file; depends on API files only | per using file, `linkonce_odr` | `_CF.Pkg` (innermost scope first) |
| Swift | `.swiftmodule` (AST and SIL, tied to the compiler version) or textual `.swiftinterface` | module; per-file incremental; `-wmo` | one shared body with witness tables; `@inlinable` exports a body to specialize | `$s3Foo3baryyF` |
| Rust | `.rmeta`: signatures, MIR of generic and inline functions | crate; codegen units; query-level incremental | monomorphized in the using crate, from MIR | v0: `_RNvCs…_7mycrate3foo` |
| C++ | BMI (`.pcm`, `.gcm`, `.ifc`), not portable between compilers or flags | translation unit | instantiated in the importer; the BMI carries bodies; COMDAT merge | `_ZW3foo1fv` (`W` = owning module) |
| D | source, or `.di` (source with template bodies kept) | any: one file, a package, or everything | in the user, from source; COMDAT; `-allinst` | `_D3std5stdio7writelnFZv` |
| Cpp2 | C++'s (headers) | `.cpp2` file | C++ templates | C++ mangling |
| Terra | source (runs it) | each `saveobj` call is one whole program | Lua functions, memoized | only `saveobj` keys are external, under that name |
| Java | `.class` files (signatures, annotations) | file; incremental by build tools | erased: one body | no linker names; JNI `Java_pkg_Cls_m` |
| Go | export data (unified IR: types, inline and generic bodies) | package; content-hash cache | in the importer, one copy per memory shape plus a dictionary; linker merges | `example.com/m/pkg.Func` |
| Kotlin | `.class` plus metadata; `.klib` (IR) | module; per-file incremental | erased; `inline` bodies copied from bytecode or IR | JVM `pkg.FooKt`; Native mangled |
| Scala | `.tasty` (typed AST) | subproject; per-file incremental (Zinc) | erased; `inline` expanded from TASTy | `a/b/C$` |
| Nelua | source (re-analysed, with its Lua preprocessor code) | whole program into one C file; no incremental build | instantiated in the user, from source | module-prefixed C names, `mymod_foo` (unverified) |
| Ada | spec source (with private part); body too for inlining / generics; GNAT `.ali` files | each spec/body → `.o` + `.ali`; `gprbuild` recompiles dependents on spec change (checksums) | instantiated in the user from the generic body source | `ada__text_io__put_line` (`pkg__child__name`, `__2` for overloads) |
| Modula-2 | the `.def` source (gm2); other compilers read `.sym` files | module; change a `.def` and every importer rebuilds | ISO: refinement modules; gm2 none | gm2 `Module_Proc` (e.g. `StrIO_WriteString`); `FOR "C"` names unmangled |
| Oberon | symbol file (compiled interface, with a key) | module; importers recompile when the interface key changes (checked at load) | none | `Texts.Write` (`Module.Name`) |
| OCaml | `.cmi` (compiled interface); `.cmx` for cross-module inlining in native | file; dependents rebuild when `.cmi` changes (`.cmx` too unless `-opaque`) | compiled once in the defining module (uniform values); flambda inlines via `.cmx` | `camlFoo$bar_123` (5.x, unverified); wrapped library `Lib__Foo` |
| Racket | compiled `.zo` in `compiled/` (expanded code, macro definitions, exports; Typed Racket types) | module; `raco make` rebuilds by SHA-1 dependency checks (`.dep` files) | none (dynamic); Typed types erased; small functions inlined across modules (schemify) | no linker symbols; module path plus name, `racket/list` `first` |
| Python | source or cached bytecode, run at import; `.pyi` stubs for checkers | file; `.pyc` in `__pycache__`, checked by mtime or hash | erased; nothing to instantiate | `__module__` + `__qualname__`, e.g. `pkg.mod.Class.method` |
| JavaScript | source of each imported module (parsed and linked at load) | module file; lazy per-function JIT; V8 code cache, Node `module.enableCompileCache()`; bundlers rebuild the graph | none (dynamic); JIT specializes at run time | none at link; module URL plus export name (`file:///app/m.js` + `add`); bundlers rename |
| TypeScript | source `.ts` or `.d.ts` (types only); `isolatedDeclarations` makes `.d.ts` per file | whole program for checking; per-file emit (`isolatedModules`); `--incremental` `.tsbuildinfo`; `composite` projects | erased; checked in the user from `.d.ts`; nothing instantiated | no mangling; JS export name; bundlers rename |
| C# | metadata of referenced assemblies (or slim reference assemblies): types, signatures; no bodies | project (assembly); MSBuild incremental; ref assemblies skip rebuild if only bodies change | stored once as generic IL in the defining assembly; instantiated by JIT at run time (AOT at publish) | metadata, `[System.Runtime]System.String`, `Ns.Type.Method` |
| Visual Basic | assembly metadata (ECMA-335; reference assemblies) | project/assembly; MSBuild incremental | reified in metadata; instantiated by JIT (or AOT) at run time | `Namespace.Type.Method` metadata names, e.g. `System.Console.WriteLine` |
| R | installed lazy-load database (serialized, byte-compiled objects) | package (`R CMD INSTALL`); no incremental | runtime dispatch; S3 methods registered by `S3method()` in `NAMESPACE` | `stats::median`; C side via `useDynLib(pkg, .registration = TRUE)` |
| C | header text, parsed again in every unit | translation unit | macros, `static inline` in headers | the identifier itself |

**Packages and platforms**

| Language | Package tool, manifest, lock | Versions | Build script | Per-platform code |
|---|---|---|---|---|
| Zig | `zig build`, `build.zig.zon`; no lock (content hashes pin) | informational; no solver | `build.zig` (Zig) | build-time `switch (builtin.os.tag)` picks an `@import` |
| C3 | `project.json`, `.c3l` manifest, `c3c vendor-fetch`; no lock | none | JSON | `@if`, `@feat(...)` on module sections |
| Odin | none, by design | none | none needed | `_linux.odin` suffixes, `#+build`, `when` |
| Hare | none, by design (distro packages) | the distro's | Makefile | `+linux` in file or directory names |
| Jai | none, by design | none | a Jai metaprogram | `#if OS == .LINUX { #load … }` |
| Goose | in the root file: `import x from "repo@ref";` | a git ref | `.build` sidecar | none in the language |
| Carbon | none yet | none | none (Bazel) | the build system |
| Swift | SwiftPM, `Package.swift`, `Package.resolved` | semver tags, registry | Swift | `#if os(Linux)`, manifest conditions |
| Rust | Cargo, `Cargo.toml`, `Cargo.lock`, crates.io | semver; several majors in one build | `build.rs` (Rust) | `#[cfg(...)]` on modules |
| C++ | none standard (vcpkg, Conan, build2) | per tool | CMake and others | preprocessor; the build system |
| D | DUB, `dub.json`/`dub.sdl`, `dub.selections.json` | semver | declarative | `version (...)`, `static if` |
| Cpp2 | C++'s | C++'s | C++'s | preprocessor |
| Terra | none | none | Terra itself (Lua) | Lua `if ffi.os == …` |
| Java | Maven, Gradle; JPMS has no versions | Maven coordinates | XML, Groovy, Kotlin | none at build time; multi-release JARs |
| Go | the `go` command, `go.mod`, `go.sum` (hashes) | minimal version selection; `/v2` in the path | none (declarative) | `_linux.go`, `//go:build` |
| Kotlin | Gradle, Maven Central | Maven's | Kotlin (Gradle DSL) | multiplatform source sets, `expect`/`actual` |
| Scala | sbt, Mill, Scala CLI; Coursier | Maven's, plus `_3` suffixes | Scala | source directories per platform |
| Nelua | none official; community tools (unverified) | none | none; Lua preprocessor and `--cflags`, `## linklib 'm'` | `## if ccinfo.is_windows then … ## end` |
| Ada | `alr` (Alire), `alire.toml`, `alire.lock`; community index | semver constraints (`^1.2`); dependency solver; `[[pins]]` | GPR project files (declarative, `gprbuild`); GPRbuild2 preview in Pro 26 (unverified); Alire `[[actions]]` | GPR scenario `case OS is when "linux" => for Source_Dirs use ("src/linux");`; Alire `case(os)` in manifest |
| Modula-2 | none; `make` | none | Makefile | `-I` path picks a per-platform `.mod`; gm2 `-fcpp` with `#ifdef` |
| Oberon | none (OBNC `obnc` builds imports by itself) | none (symbol-file keys only) | none | none; swap in a module with the same name and interface |
| OCaml | opam (`foo.opam`) and dune (`dune-project`, `dune` files); lock: `opam lock`, `dune pkg lock` (`dune.lock/`) | ranges; opam SAT-style solver | `dune` s-expression rules (`(rule (action (run …)))`); dune-configurator `discover.ml` | dune `(enabled_if (= %{system} linux))`, `(select …)`; `Sys.os_type` at run time |
| Racket | `raco pkg`, `info.rkt` (`deps`, `version`), catalog pkgs.racket-lang.org; no lock (checksums from catalog) | `version` in `info.rkt`; deps give a minimum `#:version`; no solver | none; `info.rkt` fields plus `raco setup` (optional install hooks) | `#:platform` on deps, `install-platform` in `info.rkt`; run-time `(system-type 'os*)` |
| Python | `pip` (`uv`, Poetry third party); `pyproject.toml`; `pylock.toml` (PEP 751) | PEP 440 specifiers; backtracking resolver | PEP 517 build backend (setuptools `setup.py`, hatchling) | run-time `sys.platform` checks; markers `; sys_platform == "win32"`; wheel platform tags |
| JavaScript | npm (also pnpm, Yarn, Deno, Bun), `package.json`, `package-lock.json` | semver ranges `^1.2.0`; nested `node_modules` allows several versions | `scripts` in `package.json` (`postinstall`); bundlers (esbuild, Vite) | conditional `exports` (`"node"`, `"browser"`), `os`/`cpu` fields, `optionalDependencies`; run-time `process.platform` |
| TypeScript | npm (or pnpm, yarn, bun), `package.json`, `package-lock.json` | semver ranges `^1.2.0`; nested `node_modules` allow many versions | `scripts` in `package.json` (`postinstall`) | `exports` conditions (`"node"`, `"browser"`, `"types"`); `os`/`cpu` fields; optional deps per platform |
| C# | `dotnet` CLI + MSBuild, `.csproj` `<PackageReference>`, opt-in `packages.lock.json`; NuGet | SemVer ranges; lowest match, nearest wins; `Directory.Packages.props` central versions | MSBuild XML targets; `Directory.Build.props` | `<TargetFrameworks>net10.0;net10.0-windows</TargetFrameworks>`, `#if WINDOWS`, `OperatingSystem.IsLinux()`, `runtimes/linux-x64/native` |
| Visual Basic | `dotnet` / NuGet, `.vbproj` `PackageReference`, optional `packages.lock.json` | SemVer ranges; lowest version that fits | MSBuild targets (XML) | `#If` with `DefineConstants`; `<TargetFrameworks>` multi-targeting; `OperatingSystem.IsLinux()` at run time |
| R | `R CMD build/check/INSTALL`, `install.packages()`; `DESCRIPTION`; no lock in base (`renv.lock` via renv) | lower bounds only `Imports: dplyr (>= 1.1.0)`; CRAN keeps one current version; no solver | `configure`, `configure.win`, `src/Makevars`, `Makevars.win` | `R/unix/`, `R/windows/` dirs; runtime `.Platform$OS.type` |
| C | none (vcpkg, Conan, pkg-config) | per tool | Make, CMake | preprocessor; the build system |

- The unit is a file (Zig, D, Terra, Jai, Goose, Nelua, Oberon, OCaml, Racket, Python,
  JavaScript, TypeScript, C), a pair of interface and body under one name (Ada spec and
  body, Modula-2 `.def` and `.mod`; OCaml's `.mli` is optional), a directory (Odin, Hare,
  Go), a declared name over many files (C3, Carbon, Swift, C++, Java, Kotlin, Scala;
  Rust's `mod` tree inside a crate), or a whole project (C# and Visual Basic assemblies,
  R packages). With a file, the name needs no manifest and one file gives one compiled
  unit; with a directory, per-OS files can be picked by name. In C# and Visual Basic,
  namespaces are only names and can span assemblies; the assembly is the unit of build,
  shipping and `internal` visibility.
- A module as a value: Zig (a struct type), Terra (a Lua table), Nelua (whatever the file
  returns, often a record type), Scala `object`s; D and Jai partly (build-time symbols).
  At run time: Python's `module` object, the JavaScript and TypeScript namespace object,
  an R namespace (an environment). OCaml packs a module into a value (`(module M : S)`)
  and has functors, functions from modules to modules; Ada passes generic package
  instances as formal packages; Racket units are first-class. Zig, Terra and Nelua are
  the closest to "`import` is a build-time function returning a struct" (kernel decision
  9): Nelua's `require` runs at compile time and loads a file once.
- Name to file: a path in the import (Zig, Odin, Hare, D, Go, Terra, Nelua, Racket,
  Python, JavaScript, TypeScript) keeps tools simple; so does a module name that maps to
  one file name by a fixed rule (Ada, Modula-2, Oberon, OCaml), with no path in the code;
  names searched among the files given (C3, Carbon, Kotlin, Scala, C#, Visual Basic)
  need every file named; C++ has no mapping at all, and its scan step is its most cited
  tooling burden. JavaScript and TypeScript leave bare names to the host (import maps,
  `node_modules` plus `exports`); TypeScript grew several resolution modes, and 7.0
  removed `node10`, `classic` and `baseUrl`.
- Cycles are allowed where the whole unit is analysed at once (Zig, C3, Jai, Goose, Rust
  inside a crate, Java packages, Kotlin, Scala in one compile, D, C# and Visual Basic
  inside an assembly) or where modules load at run time (Python, JavaScript,
  TypeScript), and forbidden where a dependency's interface is built first (Odin, Hare,
  Carbon, Swift, C++, Go, Rust crates, Java modules, Ada specs, Modula-2 definition
  modules, Oberon, OCaml files, Racket, R, C# and Visual Basic projects). The two reasons
  are always the same: separate compilation needs an order, and so does run-time
  initialization. D allows cycles and fails at startup when two modules in one have
  constructors. Ada and Modula-2 let bodies import each other, since only the interfaces
  must come first; Modula-2's init order is then unclear. Ways around a cycle: Ada
  `limited with`, Carbon `extern library`, OCaml `module rec` inside one file. Run-time
  cycles cost at run time: Python's importer sees a half-built module (an early
  `from m import x` fails); JavaScript and TypeScript throw a TDZ error on a binding
  read before its module runs.
- Init code: none (Zig, Jai, Rust: globals are build-time constants; Swift: lazy);
  ordered by dependency (Go, D, Odin, Hare, C++ modules, Ada, Modula-2, Oberon, OCaml in
  link order, Racket, JavaScript, TypeScript, Nelua in `require` order); on first import
  (Python); lazy on first use (Java, Kotlin, Scala, C#, Visual Basic). R runs a
  package's top level once at install time and keeps the result, plus `.onLoad()` at
  load. Go tightened its order in 1.21 after bugs; Ada's binder checks elaboration
  order, and `Elaborate_All`, `Preelaborate` and `Pure` exist only to control it; Java,
  Kotlin and Scala can read a zero or `null` in an init cycle. Rust and Zig have no init
  order to get wrong. Python's `lazy import` (3.15) and JavaScript's `import defer`
  (Stage 3) put off a module's init to first use, for cheap startup; JavaScript's
  top-level `await` makes init async.
- What an importer reads: source (Zig, C3, Odin, Jai, Goose, D, Terra, Carbon today,
  Nelua, JavaScript; Python runs it, or its cached bytecode); a hand-written interface
  (Ada spec, Modula-2 `.def` in gm2, OCaml `.mli`); generated declarations as text
  (Hare `.td`, D `.di`, C3 `.c3i`, Swift `.swiftinterface`, TypeScript `.d.ts`, Python
  `.pyi` stubs for checkers); a binary interface (Swift `.swiftmodule`, Rust `.rmeta`,
  C++ BMI, Go export data, Kotlin `.klib`, Scala `.tasty`, Java `.class`, Oberon symbol
  files, OCaml `.cmi`, Racket `.zo`, C# and Visual Basic assembly metadata, R's
  lazy-load database). Binary interfaces are tied to one compiler version (Swift, Rust)
  or to one compiler and its flags (C++). With a hand-written interface, a body edit
  rebuilds no importer and an interface edit rebuilds them all (Ada, Modula-2); Ada
  still reads the body for inlining and generics.
- Knowing when an interface changed: Oberon puts a key in each symbol file, and the
  loader rejects a client built against an old key; OCaml rebuilds dependents when a
  `.cmi` changes (and a `.cmx`, unless `-opaque`); `gprbuild` (Ada) and `raco make`
  (Racket) compare checksums; C# reference assemblies let a body-only change skip
  rebuilding dependents. TypeScript's `isolatedDeclarations` asks for explicit export
  types, so each `.d.ts` comes from one file without whole-program inference. Each is a
  way to keep an interface file cheap to check.
- Generics and build-time code across modules always need bodies in the interface: Rust
  ships MIR, Go IR, C++ the AST, Scala TASTy, Swift `@inlinable` SIL; the source
  languages have them already (Ada and Nelua instantiate from source). Hare's `.td` works
  only because Hare has no generics; Oberon and gm2's Modula-2 have none either. C3's
  `.c3i` can't carry generics. C# and Visual Basic keep one IL body in the defining
  assembly and let the JIT make copies at run time; Native AOT must see every use ahead
  of time. OCaml needs no body: a generic is compiled once over uniform boxed values,
  and flambda inlines through `.cmx`. Erased generics (Java, Kotlin, Scala, TypeScript,
  Python) need one body only. Alcor's layer 1 runs an imported module's layer-1 code,
  the same need.
- Build-time code across modules: Racket runs macros in their own phase, with their own
  `require (for-syntax …)`, and makes each module fresh per phase, so build-time state
  never leaks into run time; its `.zo` files carry macro definitions to importers. Nelua's
  build-time code is full Lua with access to the compiler's AST and types, close to
  Terra; it is strong but unhygienic, two languages in one file. R runs a package's code
  once at install time and ships the resulting objects, a simple form of build-time
  evaluation. Ada, Modula-2, Oberon, C# and Visual Basic have little or no build-time
  code; OCaml's is outside the language (PPX), and TypeScript's works only on types.
- Whole program (Zig, C3, Odin, Jai, Goose, Terra, Nelua) bets on compiler speed; Zig
  adds per-declaration incremental builds. Per unit: Rust crate, Go package, Swift
  module, Hare module, C and C++ translation units, Ada spec or body, Modula-2, Oberon
  and Racket modules, OCaml and Python files, C# and Visual Basic assemblies, R package.
  Rust's crate as the unit forces splitting big crates by hand. TypeScript checks the
  whole program but emits per file; 7.0, a line-by-line port to Go with threads, builds
  about ten times faster.
- Symbol names: the module path with dots (Zig `main.foo`, Hare `fmt.println`, Odin, Go
  `example.com/m/pkg.Func`, Carbon, Oberon `Texts.Write`); the path joined with
  underscores (Ada `ada__text_io__put_line`, gm2 `StrIO_WriteString`; Nelua and OCaml
  much the same, unverified); C++-style mangling (C++, D, Rust, Swift); none (C, and
  Terra exports only the names it is given). No linker names at all: Racket, Python,
  JavaScript, TypeScript, Java (JNI aside); C# and Visual Basic use metadata names
  (`Ns.Type.Method`). A dot is not a C identifier, so C can't call such a symbol by
  accident, and LLVM accepts it; an underscore name is a valid C identifier. A plain C
  name comes from `export` (Zig, Goose), an attribute (C3 `@export`, Odin `@(export)`,
  Hare `@symbol`, Swift `@c`, Rust `#[unsafe(no_mangle)]`, Kotlin `@CName`, Scala Native
  `@exported`, Jai `#program_export`, Go `//export`) or `extern "C"` (C++, D
  `extern(C)`, Modula-2 `DEFINITION MODULE FOR "C"`).
- Private by default: Zig, Hare, Rust, Swift (`internal`), C++ modules, Go, Java, Ada
  and Modula-2 (unless in the spec or `.def`), Oberon, Racket, JavaScript, TypeScript,
  C# (`internal` types, `private` members), R packages (fifteen). Public by default:
  C3, Odin, Jai, Goose, Carbon (API file), D, Kotlin, Scala, OCaml (unless a `.mli`
  hides), Python (ten), C. Visual Basic mixes them (types `Friend`, methods `Public`);
  Nelua has `local` (file) or `global` (whole program), and its globals share one flat
  name space. Levels run from one (Python: `_name` and `__all__` are only hints) and two
  (Zig, Hare, Go, Oberon, Nelua, C) to six (Swift, Visual Basic) and seven (C#).
  File-private: Odin, C3 `@local`, Jai, Swift, Kotlin, Nelua `local`, C# `file`, C
  `static`. A friend level: Ada private children and `private with`, C#
  `[InternalsVisibleTo]`. Other border ideas: Oberon's exported variables are read-only
  to importers; Ada's spec `private` part shows layout to the compiler but not to user
  code; Modula-2 opaque types hide fields but force a pointer; Racket's `contract-out`
  checks values at the border; R lists exports in a separate `NAMESPACE` file, and `:::`
  still reaches private names.
- Import forms: qualified access by default (Zig, Odin, Hare, Goose, Go, Carbon across
  packages, Rust, Modula-2 `IMPORT M`, Oberon, OCaml, Python `import m`); names listed
  one by one (Modula-2 `FROM M IMPORT f`, Python `from m import x`, JavaScript and
  TypeScript `import { x }`); everything unqualified (Jai's unnamed import, Swift, D,
  C++, C# `using`, Visual Basic `Imports`, R `library`, C), which makes clashes. Zig
  removed `usingnamespace` (0.15): names were hard to trace and it complicated
  incremental builds. Re-export: Rust `pub use`, D `public import`, Scala `export`, C++
  `export import`, Carbon `export`, Java `requires transitive`; Zig needs none
  (`pub const x = @import("x.zig");`); Modula-2 has none and no wildcard import in ISO.
- Packages: none, on purpose (Odin, Hare, Jai); none yet or none official (Carbon,
  Modula-2, Oberon, Nelua); built into the compiler's tool (Zig, Go, Rust, Swift, D,
  Racket `raco pkg`, C# and Visual Basic `dotnet`, R); outside the language (C, C++,
  Java, Kotlin, Scala, Ada Alire, OCaml opam and dune, Python pip, JavaScript and
  TypeScript npm). Content hashes instead of a version lock: Zig, Go; Racket has no lock
  and takes checksums from its catalog. Lock files: Rust, Swift, D, Ada, OCaml
  (`dune.lock/`), Python (`pylock.toml`), npm, C# (opt-in); R needs renv. A solver: Ada,
  OCaml, Python; none: Zig, Racket, R (lower bounds only, and CRAN keeps one version).
  Several versions in one build: Rust (several majors), npm's nested `node_modules`. A
  build script in the language: Zig, Jai, Rust `build.rs`, Swift, Terra, Kotlin, Scala,
  Python (`setup.py`), OCaml (dune-configurator); declarative: Go, D, Ada GPR, Racket
  `info.rkt`, Python `pyproject.toml`.
- Per-platform code: file or directory names (Odin, Hare, Go, R `R/unix/` and
  `R/windows/`); a build-time `if` in the source (Zig, Jai, D, Swift, C3, Terra's Lua
  `if`, Nelua `## if`, C# `#if`, Visual Basic `#If`); the build system (C++, Carbon,
  Java, Kotlin, Scala, Ada GPR scenarios, OCaml dune `enabled_if`, C# target
  frameworks); package metadata (JavaScript and TypeScript `exports` conditions and
  `os`/`cpu` fields, Racket `#:platform`, Python markers and wheel tags); a module with
  the same name and interface, picked by the search path (Oberon, Modula-2 `-I`). gm2
  adds the C preprocessor (`-fcpp`) for `#ifdef`, a sign the gap hurts. Many also check
  at run time (Python `sys.platform`, JavaScript `process.platform`, OCaml `Sys.os_type`,
  Racket `system-type`, C# `OperatingSystem.IsLinux()`, R `.Platform$OS.type`). Zig's
  build-time `switch` choosing an `@import` is the closest to kernel decision 7
  ("conditional compilation is an ordinary `if`").
- Lessons the designers and users name: C++'s missing name-to-file mapping and
  non-portable BMIs; Go's `/v2` import paths and cycle-breaking "util" packages;
  Swift's binary module fragility and leaky transitive imports (fixed by access-level
  imports, SE-0409); Rust's crate sprawl and orphan rule; D's constructor cycles at run
  time; Java's split packages and slow JPMS adoption; Kotlin's missing package-private;
  C3 rebuilt generics twice, the second time moving them out of modules (too coarse);
  Jai's generic code can't see the user's overloads (`#poke_name`); Odin answers cycle
  errors with "fewer, bigger packages"; Ada's elaboration order; Python's half-built
  modules in cycles and its weak, all-public borders; JavaScript's two module systems
  (CommonJS and ESM) side by side for about ten years; TypeScript's many resolution
  modes; npm's `postinstall` scripts as a supply-chain risk; R's weak versioning (lower
  bounds only, a lock needs renv); Modula-2 opaque types that force a pointer; Nelua's
  one flat space of globals, weak for big code.
- Agree: no headers (twenty-eight; Ada, Modula-2 and OCaml keep a hand-written interface
  file, but it is compiled, not pasted); qualified access by default (eleven); private
  by default (fifteen); no cycles between separately compiled interfaces (all with
  separate compilation; Ada and Modula-2 bodies may still import each other); bodies in
  the interface for generics (all with one copy per type; C# and Visual Basic make the
  copies at run time from IL); path in the import (eleven); module path in the symbol
  name (Zig, Hare, Odin, Go, Carbon, Oberon; joined with underscores in Ada and gm2); no
  init code (Zig, Jai, Rust, Swift).

## Sources

The official pages each research pass relied on (seen through search summaries):

- Zig: ziglang.org/documentation/master, ziglang.org/download/0.16.0/release-notes.html,
  0.17.0 release notes (reported), github.com/ziglang/zig, ziggit.dev
- C3: c3-lang.org (docs and blog: 0.8.0, 0.8.4), github.com/c3lang/c3c
  (`releasenotes.md`), learn-c3.org
- Odin: odin-lang.org/docs/overview, odin-lang.org/docs/faq, odin-lang.org/news,
  github.com/odin-lang/Odin/releases
- Hare: harelang.org (blog: 0.26.0), harelang.org/specification,
  harelang.org/tutorials/introduction, harelang.org/documentation/faq, harebyexample.org
- Jai: The Way to Jai (github.com/Ivo-Balbaert/The_Way_to_Jai), jaimanual.com,
  jai.community, forrestthewoods.com (Advent of Code in Jai), Jonathan Blow's streams
- Goose: github.com/aardappel/goose, aardappel.github.io/goose
- Carbon: github.com/carbon-language/carbon-lang (`docs/design/`, `proposals/`),
  docs.carbon-lang.dev (roadmap, error handling principles, safety, interoperability)
- Swift: swift.org/blog (6.2, 6.3, 6.4), docs.swift.org/swift-book (lexical structure,
  control flow, error handling, macros), swift-evolution SE-0380, SE-0390, SE-0413,
  SE-0452, SE-0458, SE-0483, SE-0495, swift.org/documentation/cxx-interop,
  docs.swift.org/embedded
- Rust: blog.rust-lang.org/releases, doc.rust-lang.org/reference (keywords, tokens,
  undefined behaviour), doc.rust-lang.org/edition-guide/rust-2024,
  doc.rust-lang.org/cargo/reference/profiles.html, rust-lang.github.io/rust-bindgen
- C++: herbsutter.com (C++26 trip report, Mar 2026), cppreference.com/w/cpp, wg21.link
  P2996 (reflection), P2900 (contracts), P2795 (erroneous behaviour), P3471 (hardening)
- D: dlang.org/changelog (2.111–2.113), dlang.org/spec (betterc, importc, function,
  statement, template, lex), dlang.org/dmd-linux.html
- Cpp2: github.com/hsutter/cppfront (releases 0.8.0, 0.8.1), hsutter.github.io/cppfront
- Terra: terralang.org (getting started, API), github.com/terralang/terra (releases,
  CHANGES.md)
- Java: openjdk.org (JDK 25, 26, 27; JEPs 286, 361, 378, 395, 401, 409, 441, 454, 467,
  511, 512), JLS 25 §3
- Go: go.dev/ref/spec, go.dev/doc/go1.26, go.dev/blog/error-syntax, pkg.go.dev/cmd/cgo,
  pkg.go.dev/unsafe
- Kotlin: kotlinlang.org/docs (releases, whatsnew24, control flow, null safety, sealed
  classes, generics, native C interop, keyword reference)
- Scala: docs.scala-lang.org/scala3/reference (enums, indentation, inline, macros,
  given/using), scala-native.org (interop, build modes), sn-bindgen
- C: ISO/IEC 9899:2024, WG14 N3220 (C23 draft), N3550 (C2y draft), N3355 (named loops),
  TS 25755 (`defer`), cppreference.com/w/c/23

Section 13 (module systems) added these:

- Zig: ziglang.org/learn/build-system, 0.14–0.16 release notes, `doc/build.zig.zon.md`,
  issue 20663 (`usingnamespace`)
- C3: c3-lang.org (modules, project config, libraries, cinterop, generics), discussions
  441 and 1165, github.com/c3lang/vendor
- Odin: odin-lang.org/docs/overview, odin-lang.org/docs/faq, gingerbill.org ("Package
  Managers are Evil")
- Hare: harelang.org/specification, `hare(1)`, `hare-module(5)`, harelang.org FAQ
- Jai: Jai-Community wiki, jaimanual.com, withoutfearofwindorvertigo.com
  (`#poke_name`)
- Goose: github.com/aardappel/goose (`docs/design/namespaces.md`, `src/blessed.txt`)
- Carbon: `docs/design/code_and_name_organization/`, proposals p0107, p0752, p0875,
  p3762, p3927, p3938, p3980; toolchain `sem_ir/mangler.cpp`, `lower/file_context.cpp`
- Swift: swift-book access control, SE-0339, SE-0386, SE-0409, SE-0444, SE-0491,
  SE-0492, SE-0495, SE-0497, `docs/ABI/Mangling.rst`, `docs/LibraryEvolution.rst`
- Rust: reference (modules, visibility, preludes, conditional compilation), RFCs 2126,
  2603, 1977, rustc-dev-guide (monomorphization, incremental), Cargo reference
- C++: cppreference modules, eel.is [module] and [basic.start.dynamic], P1103, P1689,
  P3034, P1427, Clang and GCC module docs, cmake-cxxmodules(7), Itanium ABI module
  mangling, arewemodulesyet.org
- D: dlang.org/spec/module.html, spec/abi.html, changelog 2.071, dub.pm
- Cpp2: hsutter.github.io/cppfront (options, namespaces, types)
- Terra: terralang.org/getting-started.html, terralang.org/api.html
- Java: JEP 261, JEP 511, JLS 25 ch. 7 and §12.4, JSR 376 requirements
- Go: go.dev/ref/spec, go.dev/ref/mod, go.dev/doc/go1.21, generics dictionaries design
  doc, research.swtch.com/vgo
- Kotlin: kotlinlang.org/docs (packages, visibility, Java interop, multiplatform
  expect/actual), YouTrack KT-29227
- Scala: Scala 3 reference (export, imports, safe initialization), TASTy overview,
  binary compatibility guide
- C: N3220 §6.2.2 and §6.10.2, clang.llvm.org/docs/Modules.html

The twelve languages added on Oct 30 (all topics):

- Nelua: nelua.io (overview, manual, libraries, FAQ), github.com/edubart/nelua-lang
- Ada: ada-auth.org/standards/ada22.html, adaic.org (Ada 2022), ISO/IEC 8652:2023,
  docs.adacore.com (GNAT reference manual, GNAT user's guide, SPARK user's guide),
  alire.ada.dev/docs
- Modula-2: ISO/IEC 10514-1, gcc.gnu.org/onlinedocs/gm2 (options, interface to C,
  extensions), gcc.gnu.org/gcc-16/changes.html, nongnu.org/gm2, modula2.org/reference
- Oberon: people.inf.ethz.ch/wirth (Oberon-07 report, Project Oberon), miasap.se/obnc,
  ssw.jku.at (Oberon-2 report)
- OCaml: ocaml.org/releases (5.4, 5.5), ocaml.org/manual (compilation units, modules,
  C interface, effects, memory model)
- Racket: blog.racket-lang.org (v9.0–v9.3), docs.racket-lang.org (reference, guide:
  modules, `require`, macros)
- Python: docs.python.org (What's New 3.14, 3.15), PEPs 517, 621, 649, 695, 751, 790, 810
- JavaScript: tc39.es/ecma262, github.com/tc39/proposals (explicit resource management,
  deferred import evaluation), nodejs.org/api (ESM, packages, modules, Node-API)
- TypeScript: devblogs.microsoft.com/typescript (6.0, 7.0, native port),
  github.com/microsoft/typescript-go, typescriptlang.org/docs/handbook (narrowing,
  conditional types, modules reference)
- C#: learn.microsoft.com/dotnet/csharp (What's new in C# 14 and 15, language reference,
  checked and unchecked, unsafe code, source generators), P/Invoke source generation
- Visual Basic: learn.microsoft.com/dotnet/visual-basic (what's new, language reference,
  access levels, conditional compilation, `-removeintchecks`), devblogs.microsoft.com/vbteam
- R: r-project.org, cran.r-project.org/doc/manuals (NEWS, R Language Definition, Writing R
  Extensions), stat.ethz.ch R manual (Reserved, Quotes)
