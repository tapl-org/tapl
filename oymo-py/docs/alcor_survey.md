# Alcor syntax survey

Zig, C3, Odin, Hare, Jai, Goose, Carbon, Swift, Rust, C++, D, Cpp2 and Terra each answer
"a better C" differently; Java, Go, Kotlin and Scala show what mainstream programmers
read every day. Each topic below has one table of the seventeen plus C, then
pros and cons for Alcor, then where the languages agree. The syntax Alcor chooses is in
[alcor_kernel_syntax.md](alcor_kernel_syntax.md); this survey makes no decisions.

> [!NOTE]
> Checked in Oct 2026 from web-search summaries of the official docs, specs, release
> notes and repos; the official pages could not be opened directly. "(unverified)"
> marks a weak or conflicting source. Jai has no public spec (closed beta); its facts
> come from community docs and beta users. Carbon's and Cpp2's designs still change
> often. Check a detail against the language's own docs before a decision rests on it.

Already decided before the survey: `name: Type` declarations and
`fn add(a: i32, b: i32) -> i32 { return a + b; }`. Later decisions are in
[alcor_kernel_syntax.md](alcor_kernel_syntax.md).

The decision rules, from the roadmap: keep the form mainstream languages share (C's
first) unless fixing a known problem; everything is an expression; a type is a layer-1
expression; lowers simply to oymomo; when two of the seventeen agree, take that.

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
| C | C23 = ISO/IEC 9899:2024; C2y in progress; `defer` in TS 25755 | WG14 | Baseline: "trust the programmer", small, fast |

- Closest to Alcor's goals: C3 (stated aim), Odin and Hare (`name: Type`, C fixes), and
  D with `-betterC`, the longest-proven "C, but modern" with build-time code.
- Closest to "a type is a build-time value": Terra (types are Lua values, the strongest
  proof), Zig, Jai and Carbon (`Stack(i32)` is a build-time call).
- Closest to "`name: Type` everywhere over an existing language": Cpp2
  (`name: kind = value`, lowered 1:1 to C++).
- Mainstream readers: Java, Go, Kotlin and Scala have a GC or a managed runtime, so they
  say little about memory, but they set what "any programmer reads it at once" means.
  Kotlin and Scala are the expression languages Alcor's syntax follows (`if` and blocks
  give values, `val`/`var` with `name: Type`); Go is the small C-family language with
  `name Type` order.
- C++, Carbon and Cpp2 are the C++ family; Swift is far bigger than C (ARC, protocols, a
  runtime); Rust is large (traits, lifetimes). They are here for single ideas: header
  import through Clang, safety modes, owned values, `name: Type` in a C family.
- C++ never breaks compatibility, so each fix sits beside the C feature it fixes (headers
  and modules, `int` and `int32_t`, `T a[N]` and `std::array`): the opposite of "keep the
  shared form unless fixing". Java's long previews (`--enable-preview`) show a way to test
  syntax before freezing it.
- Pre-1.0 syntax churns (Zig, C3, Hare, Jai, Carbon, Cpp2): borrow ideas, not surface
  details. C3 renamed keywords as late as 0.8.4; Zig moved `@cImport` out of the language
  in 0.17 (unverified); Carbon changed arrays from `[T; N]` to `array(T, N)`; Cpp2 is a
  prototype whose author now works on ISO papers (unverified). Rust's editions (chosen
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
| C | `int count = 0;` | `auto x = 1.5f;` (C23) | `constexpr int N = 16;` (C23), `#define`, `enum` | indeterminate |

- `name: Type`: twelve of seventeen (not C3, C++, D, Java; Go writes `name Type` with no
  colon). D keeps C's order but drops the spiral (`int* p, q;` makes two pointers).
- A keyword first: Zig, Hare, Goose, Carbon, Swift, Rust, Terra, Go, Kotlin, Scala (ten).
  Greppable, and a statement never starts with a bare name. Odin, Jai and Cpp2 have no
  keyword (`count: i32 = 0`).
- Immutable bindings with `let` or `val`: Goose, Carbon, Swift, Rust (`let mut`), Kotlin,
  Scala (six); Java writes `final`, Go has only build-time `const`; Hare's `let` is
  mutable.
- `:=` inference: Odin, Jai, Cpp2, Go. Go's `:=` next to `=` causes shadowing bugs (`err`
  declared again in an inner scope).
- Build-time constants are spelled many ways: `::` (Odin, Jai), `==` (Cpp2, a comparison
  to C readers), `:!` (Carbon), `enum N =` (D), `def` (Hare), `const` (Zig, Rust, Go),
  `const val` (Kotlin, primitives only), `inline val` (Scala), `static final` (Java),
  `constexpr` (C, C++). Scala's `inline val` and Zig's `const` show a constant can just be
  a build-time value of an ordinary binding. C++'s four words (`const`, `constexpr`,
  `constinit`, `consteval`) show the cost of no single build-time layer.
- Goose splits binding mutability (`let`/`var`) from data constness (`const u8[:]`), a
  fix for C's `const int *` vs `int *const`.
- Uninitialized: zero by default (Odin, Jai, D, Go); an explicit opt-out marker (Zig
  `undefined`, Odin and Jai `---`, Hare `@undefined`, D `= void`); always a value (Zig,
  Kotlin, Scala); or checked to be set before use (Swift, Rust, Cpp2, Java locals). C++26
  makes an uninitialized read an "erroneous value" instead of UB.
- Agree: `name: Type` (twelve of seventeen); a keyword first (ten); immutable `let`/`val`
  (six); `:=` (Odin, Jai, Cpp2, Go); zero by default (Odin, Jai, D, Go); checked before use
  (Swift, Rust, Cpp2, Java).

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
| C | `int add(int a, int b) { … }` | struct or out-pointers | no; compound literal idiom |

- `fn` keyword: Zig, C3, Hare, Goose, Carbon, Rust (six of seventeen). Others: `func`
  (Swift, Go), `fun` (Kotlin), `def` (Scala), `proc` (Odin), `terra` (Terra); none: Jai,
  C++, D, Cpp2, Java (and C), so definitions can't be grepped.
- `->` before the result: Odin, Jai, Goose, Carbon, Swift, Rust, Cpp2, and C++'s
  trailing `auto f(int a) -> int` (eight). `: T` after the parameters: Kotlin, Scala,
  Terra (reads like a declaration). Right after `)`: Zig, Hare, Go.
- The body's value is its last expression: Scala, Rust, Goose; Kotlin and Scala write a
  one-expression body with `=` (`fun add(a: Int, b: Int) = a + b`); Swift returns a
  single expression implicitly. Always `return`: C, Java, Go, Zig, Odin.
- Rust's result without `return` (a last expression with no `;`) is easy to miss;
  Scala and Kotlin have no such `;` rule.
- Multiple results: named results (Odin, Jai, Cpp2, Go) or a result list (Goose), tuples
  (Zig, Hare, Carbon, Swift, Rust, Terra; Scala named tuples), a record or data class
  (Java, Kotlin with destructuring), structs (C++ structured bindings, C), `out`
  parameters (D). All lower to a struct return with no new ABI concept. Go's bare
  `return` with named results hides what is returned.
- Named arguments (C3, Odin, Jai, Swift, D, Kotlin, Scala) and defaults (also C++, Cpp2)
  are call-site rewriting; Zig gets both from an options struct. Swift's labels become
  part of the function name. Overloading: Java, Kotlin, Scala, C++, Swift, D; none in Go.
- Parameter modes state intent and lower to a value or a pointer: Cpp2 `in`, `inout`,
  `out`, `move`; Swift `inout`, `borrowing`, `consuming`; D `ref`, `out`.
- Odin's default calling convention passes a hidden `context` pointer; Scala's `using`
  parameters are explicit in the signature and implicit at the call.
- Contracts on the signature: C++26 and Cpp2 `pre(b != 0)`, C3 `@require` in comments.
- Agree: `fn` (six of seventeen); `->` (eight); last expression is the value (Scala,
  Rust, Goose, Kotlin and Swift for one-expression bodies); named arguments (seven).

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
| C | `T *p` | (same as `T *`) | none | `T a[N]`, decays | null pointer | `int32_t`, `size_t`, `_BitInt(N)` | `(T)x` |

- Prefix pointers read left to right with `name: Type` ("p is a pointer to T"): Zig,
  Hare, Jai, Cpp2, Go (`*T`), Rust (`*const T`), Odin (`^T`), Terra (`&T`) (eight).
  Suffix `T*` keeps C's look: C3, Carbon, D, C++ (Goose `T&`). Generic-type spelling:
  Swift `UnsafePointer<T>`, Kotlin Native `CPointer<T>`, Scala Native `Ptr[T]`: closest
  to Alcor's types-as-calls `Ptr(T)`. Java, Kotlin and Scala have no pointers in the
  core language.
- Dereference: postfix `p.*` (Zig), `p^` (Odin), `p*` (Cpp2), `!p` (Scala Native); prefix
  `@p` (Terra); C's `*p` (C++, D, Carbon, Rust, Go).
- Separate one-item and many-item pointers (Zig, Odin, Hare) fix C's `T*` meaning both.
  Go has no pointer arithmetic outside `unsafe` (`unsafe.Add`, `unsafe.Slice`).
- Slices built in: Zig, C3, Odin, Hare, Jai, Goose, Rust, D, Go (nine); library: C++,
  Cpp2, Swift; none: Terra, C, Java, Kotlin, Scala (Carbon unsettled).
- Fixed arrays: `[N]T` (Zig, Odin, Hare, Jai, Go); `T[N]` (C3, D, Terra, C); `[T; N]`
  (Rust); `array(T, N)` (Carbon); library (C++, Cpp2 `std::array`, Swift `[N of T]`,
  Scala Native `CArray[T, Nat._8]`, awkward without number parameters). Java's `int[]`
  is a heap object that carries its length.
- Non-null by default: Hare (`nullable *T`), Carbon (`Optional(T*)`), Rust (`&T`,
  `Option<&T>`), Swift and Kotlin (`T?`), Zig and Goose (`?T`, `T?`). Java's implicit
  nullable references and Go's `nil` are widely seen as mistakes.
- Types as applied calls: Carbon `array(T, N)`, `iN`; Terra `vector(float, 4)`; Swift
  `InlineArray<N, T>`; C `_BitInt(N)`; Zig `@Int(.unsigned, 10)`. A width or length
  parameter fits "a type is a layer-1 expression".
- Integer names: `i32`/`u8` (Zig, Odin, Hare, Goose, Carbon, Rust, Cpp2: seven); `int32`
  (Go, Terra); `s32` (Jai); `Int32` (Swift); `Int`, `Long`, `UInt` (Kotlin, Scala); C
  names (C3, D, C++, C, Java). Java has no unsigned types, another known mistake.
- Conversions: `x as T` (Hare, Goose, Carbon, Rust, Cpp2); `T(x)` (Go, Odin, Swift);
  `cast(T) x` (Odin, Jai, D); methods `x.toLong()` (Kotlin, Scala); `(T)x` (C, Java);
  `[T](e)` (Terra); `static_cast<T>(x)` (C++).
- No implicit conversions: Go, Rust, Kotlin, Swift, Odin, Hare (six); widening only: Zig,
  Java, C3, D.
- Agree: prefix pointers (eight); built-in slices (nine); `[N]T` (five); `i32`/`u8`
  names (seven); non-null pointers (Hare, Carbon, Swift, Rust, Kotlin); no implicit
  conversions (six); `as` casts (five); `T(x)` (three).

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
| C | `struct P { int x; };` | `{ .x = 1 }`, `(struct P){…}` | `->` | manual struct plus union | none |

- `.` through pointers: ten of seventeen (Zig, C3, Odin, Hare, Jai, Goose, Rust, D, Terra,
  Go); Java, Kotlin and Scala have only references and use `.` too. Carbon and C++ keep
  `->`; Cpp2 writes `p*.x`, Swift `p.pointee.x`.
- Literals: designated `{ .x = 1 }` (C, C3, Zig, Carbon, C++20); `Point{X: 1}` (Go); a
  constructor call (`P(x: 1)` D, Swift; `P(1, y = 2)` Kotlin, Scala; `new P(1, 2)` Java).
- A type bound to a name (`const P = struct {…}`, `P :: struct`, Terra's
  `local S = struct {…}`, Go's `type P struct {…}`) is the honest form if types are
  layer-1 values; `struct P {…}` (C, C3, Goose, Swift, Rust, D, C++, Terra) is what C
  readers expect.
- Tagged unions built in with an exhaustive `switch`/`match`: Zig, Odin, Hare, Goose,
  Carbon `choice`, Swift and Rust `enum`, Scala `enum` (eight). Sealed hierarchies with
  exhaustive matching: Java, Kotlin. Library only: C++ `std::variant`, D `SumType`.
  Generated: Cpp2 `@union`. None: C3, Jai, Terra, Go (Go's most criticized gap).
- Methods: in the type (Zig, C3, Carbon, Swift, Rust `impl`, C++, D, Java, Kotlin,
  Scala); outside the struct with a receiver (Go); called as `x.f(a)` for any `f(x, a)`
  (UFCS: Goose, D, Cpp2; extension functions: Kotlin, Scala, Swift); a method table,
  `p:m()` (Terra); none (Odin, Hare, Jai).
- Cpp2's metafunctions (`@struct`, `@enum`, `@union`) make these kinds build-time
  library code instead of keywords.
- Rust reorders struct fields unless `#[repr(C)]`. Calling sum types `enum` (Rust, Swift,
  Goose, Scala) overloads C's meaning.
- Agree: `.` through pointers or references (thirteen of seventeen); built-in tagged
  unions (eight, plus sealed types in Java, Kotlin); UFCS or extension calls (six);
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
| C | `for (;;)`, `while`, `do` | `case 1: … break;` | default; `[[fallthrough]]` | TS 25755 | C2y `break outer;` | `?:` only |

- No fallthrough by default: sixteen of seventeen in their modern form (C++ keeps C's;
  Java's old `case X:` falls through, its arrow `case X ->` doesn't). Opt-in spelling:
  `nextcase` (C3), `fallthrough` (Odin, Swift, Go), `#through` (Jai), `goto case` (D).
- Arm syntax: C's `case x:` with an implicit `break` (C3, Swift, Go); with a required
  `break` (D); `=>` arms (Zig, Hare, Goose, Carbon, Rust, Scala); `->` arms (Java,
  Kotlin `when`); `is 0 = …` (Cpp2 `inspect`); `case 1 then` (Terra).
- C's three-part `for`: kept by C3, Odin, Hare, C++, D, Go, Java (seven); dropped by Zig,
  Jai, Goose, Carbon, Swift, Rust, Cpp2, Terra, Kotlin, Scala. All seventeen add a range
  or each form.
- `defer`: Zig, C3, Odin, Hare, Jai, Goose, Swift, D (`scope(exit)`), Terra, Go (ten of
  seventeen), and C's own TS 25755. Go's `defer` runs at function exit, a known trap in
  loops; block-scoped `defer` (Zig, Swift) is better. Destructors: C++, Rust, Carbon,
  Cpp2; `try`/`finally`: Java, Kotlin, Scala.
- Labelled break: Zig, C3, Odin, Hare, Swift, Rust (`'outer:`), D, Cpp2, Go, Java, Kotlin
  (`outer@`) (eleven), and C2y; Scala's `boundary`/`break(v)` carries a value. C++ and
  Terra have none.
- `if`, `switch` and blocks as expressions: Zig, Hare, Goose, Swift, Rust, Cpp2, Kotlin,
  Scala, and Java's `switch` (nine). Kotlin and Scala have no `?:` because `if` is an
  expression; Java's `yield` exists because blocks are not expressions.
- Scala 3 and Terra replace braces with `then`/`do` and indentation or `end`; Go puts no
  parentheses around conditions.
- Agree: no fallthrough (sixteen); labelled loops (eleven); `defer` (ten); expressions
  (nine); a range or each loop (seventeen).

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
| C | return codes, `errno`, out-parameters | by hand (`goto fail`) | by hand | yes |

- Errors as values: eleven of seventeen and C. Exceptions with unwinding: C++, D (none in
  `-betterC`), Cpp2 (opt in with `throws`), Java (checked and unchecked), Kotlin and
  Scala (unchecked). Unwinding needs run-time support and is hard to lower; Swift's
  `throws` is a plain return path.
- A short propagate operator (`try`, `!`, `or_return`, `?`): Zig, C3, Odin, Hare, Swift,
  Rust (six of seventeen); Carbon plans one. By hand: Jai, C++, D, Cpp2, Terra, Go
  (`if err != nil`; Go decided in 2025 to stop pursuing new error syntax), Kotlin
  (`f() ?: return null`), Scala (`for` comprehensions), C.
- `try` as a prefix: Zig and Swift. `?` as a postfix: Hare and Rust. `??` for a default:
  C3 and Swift; Kotlin's `?:` (elvis) and `?.` do the same for null.
- Errors as ordinary sum or result types: Hare, Carbon, Rust `Result<T, E>`, Odin, C++
  `std::expected`, Swift `Result`, Scala `Either`, Kotlin `Result<T>`. Go's `(T, error)`
  is a product, not a sum, so both can be set. Zig's and C3's codes can't carry data.
- Wrapping errors with context: Go's `%w`, `errors.Is`, `errors.As`.
- Terra shows a propagate construct can be a build-time macro.
- A split between recoverable errors and bugs: D (`Exception` vs `Error`), Rust
  (`Result` vs `panic!`), Go (`error` vs `panic`), Zig (errors vs `unreachable`).
- Agree: errors as values (eleven); a propagate operator (six); prefix `try` (Zig,
  Swift); postfix `?` (Hare, Rust); contracts (C3, C++26, Cpp2).

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
| C | preprocessor, `constexpr` objects, `_Generic`, `static_assert`, `#embed` | no | `#if` |

- Types as build-time values: Zig, Jai, Carbon, Terra (four); partly: C3, Odin, C++26
  (reflection), Cpp2 (metafunctions), Scala (match types, a separate type-level
  language); no: Hare, Goose, Swift, Rust, D, Java, Go, Kotlin.
- Terra is the strongest proof of layer 1, but uses a second language (Lua) for it.
- D runs any ordinary function at build time (CTFE), with no keyword; types are computed
  in a separate template language.
- Zig and Jai show one build-time mechanism replaces macros, templates, `#ifdef` and code
  generators.
- Code generators grow where build-time code is missing: Java annotation processors,
  Kotlin KSP and compiler plugins, Go `//go:generate`. That is the strongest argument
  for Alcor's layer 1 among mainstream languages.
- Scala's `inline if` and `inline match`, reduced at build time, are the closest
  mainstream form of an ordinary `if` on a build-time condition.
- Several mechanisms where layer 1 would be one: C++ four, Rust three (generics, `const
  fn`, macros), Scala three (`inline`, match types, quoted macros compiled separately),
  D two, C3 and Odin a `$if`/`when` sublanguage, Swift plugin macros.
- C's bolt-ons (`constexpr`, `typeof`, `_Generic`) show the demand; `#embed` (C, C++26),
  D's `import("file")` and Go's `//go:embed` are build-time file reads worth keeping as
  functions.
- A visible marker for build-time names: C3 `$name`, Odin and Jai `$T`, Carbon `:!`, Zig
  `comptime`, Cpp2 `==`, Scala `inline`; D and Terra need none.
- Agree: types as build-time values (Zig, Jai, Carbon, Terra); ordinary functions run at
  build time (Zig, Jai, D, C++ `constexpr`, Rust `const fn`, Terra); compile-time `if`
  (Zig, C3, Odin, Jai, Swift, Rust, D, C++, Scala).

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
| C | `void *` plus size, macro templates | `_Generic` dispatch | none | erased or text |

- One copy per type: Zig, C3, Odin, Jai, Goose, Carbon, Rust, C++, D, Cpp2, Terra and
  Embedded Swift (twelve of seventeen). Shared code: Java, Kotlin and Scala erase types
  (boxing primitives); Go shares code per memory shape and passes a dictionary; full
  Swift passes witness tables. Hare has no generics.
- Inference from arguments: fourteen of seventeen; explicit only in Terra and C3 types.
- Instantiation spelling: a call `List(T)` (Zig, Carbon, Terra, Jai `FixedBuf(64)`),
  matching the roadmap's `List(T)`, `Map(K, V)`; `<T>` (Swift, Rust, C++, Cpp2, Java,
  Kotlin), which makes parsing ambiguous (C++'s `template`, Rust's `::<>`); `[T]` (Go,
  Scala), ambiguous next to indexing; `!(…)` (D); `{…}` (C3).
- Constraints: checked at the definition (Carbon, Swift, Rust traits, Java, Kotlin, Scala
  bounds), which needs a constraint language; or build-time predicates (D, C++ concepts,
  Odin `where`, Jai `#modify`, Zig `@typeInfo`, Go type sets `~int | ~float64`). Variance
  (`out T`, `+T`) in Kotlin and Scala is GC-runtime complexity.
- Terra and Zig need no generics feature: a build-time function returns a type.
- Rust's const generics allow only integers, `bool` and `char`; Scala Native's
  `CArray[T, Nat._8]` shows the same gap.
- Agree: one copy per type (twelve); inference (fourteen); call form `List(T)` (Zig,
  Carbon, Terra, Jai); `<T>` (six); `[T]` (Go, Scala).

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
| C | none (`#include`) | `#include "x.h"` | `static` is private | (is the ABI) | is the format |

- No header files: sixteen of seventeen. C++ added modules after headers and never
  replaced them. Cpp2 is order independent and writes the forward declarations itself.
- Private by default (Zig, Hare, Rust, Swift `internal`, Go lowercase names; Java's
  package-private is close) vs public by default (C3, Odin, Jai, Carbon, D, Kotlin,
  Scala). Go's capitalization needs no keyword but makes renaming painful.
- Declaring a C function: `extern` (Zig, C3, Goose, Rust, C++ `extern "C"`, D
  `extern(C)`, Scala Native `@extern`) (seven).
- Importing C headers inside the language: Carbon (`import Cpp library "x.h"`), Swift
  (modulemap, `import CLib`), Terra (`terralib.includec`), D (ImportC), Go (cgo: the
  header in a comment above `import "C"`), C++ and Cpp2 (`#include`), and Zig until 0.16
  (seven of seventeen today). A separate tool generates bindings: Jai, Rust (`bindgen`),
  Java (`jextract`), Kotlin (`.def` file and `cinterop`), Scala (`sn-bindgen`). By hand:
  C3, Odin, Hare, Goose.
- A namespace prefix keeps foreign names visible: Carbon `Cpp.f()`, Terra `C.printf`, Go
  `C.puts`.
- A build tool or script in the language itself: Zig `build.zig`, Jai, Swift
  `Package.swift`, Terra, Go (the `go` tool, no build files), Kotlin (Gradle Kotlin DSL).
- Agree: no headers (sixteen); header import in the language (seven); `extern` for C
  (seven); private by default (five).

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
| C | `malloc`, `free` | none standard | `goto cleanup`; TS `defer` | none (`restrict` is a promise) |

- Explicit allocator (Zig parameter, C3 first argument, C++ `std::pmr` resource) vs an
  implicit one (Odin and Jai context; Kotlin's `memScoped` receiver; Scala's `using Zone`
  parameter, explicit in the signature and implicit at the call). The rest have none in
  the language; Java, Go, Kotlin and Scala use a GC.
- Scoped arenas freed at block exit: Java FFM `Arena`, Kotlin `memScoped`, Scala `Zone`,
  C3 `@pool`.
- No hidden allocation: Zig, C3, Hare, Goose, Terra, D `-betterC`, C. Hidden: Odin and Jai
  (from the context), Rust, C++, Cpp2, full D, Swift, and all four GC languages (boxing,
  closures, `append`).
- Out-of-memory as an ordinary error (Hare `nomem`, Zig `error.OutOfMemory`).
- Owned values: Rust's moves and checked borrows; Swift's `~Copyable`; C++ `unique_ptr`
  and Cpp2's move at last use (unchecked); D's `@live` (experimental); Scala's capture
  checking (experimental). Prior art for `alcor-safety-syntax`: Rust and Swift, plus ATS,
  Austral, Vale.
- Marking unsafe code: Rust `unsafe { }` blocks; Swift strict mode; D `@safe`/`@trusted`/
  `@system` (default `@system`); Go's `unsafe` package; Scala Native's `unsafe` import;
  Java's restricted methods behind `--enable-native-access`; Kotlin's opt-in annotation
  (weaker than a lexical block).
- Destructors (C++, Rust, Carbon, Cpp2) free with invisible calls; `defer free(p)` keeps
  the same benefit visible.
- Agree: `defer` frees (ten); scoped arenas (Java, Kotlin, Scala, C3); explicit
  allocators (Zig, C3, C++ `pmr`); marked unsafe code (seven).

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
| C | none in the standard (sanitizers) | signed UB; `ckd_add` (C23) | none | all of the above |

- Checks on in debug builds, off or UB in fast builds: Zig, C3, Jai, D. Checks always on:
  Java, Go, Kotlin, Scala (JVM), Swift, Odin (bounds), Cpp2 (opt out per check), Carbon's
  hardened mode.
- A third category between defined and UB: Carbon's "hardened" mode and C++26's
  "erroneous behaviour", plus C++26 contract modes.
- Overflow: UB (Zig fast, C, C++, Cpp2, Carbon performance) vs defined wrap (C3, Odin,
  Hare, D, Rust release, Java, Go, Kotlin, Scala) vs trap always (Swift). The four GC
  languages wrap silently, which hides bugs; their checked helpers (`Math.addExact`)
  show the need. Explicit wrap operators: Zig `+%`, Swift `&+`, Rust `wrapping_add`.
- Opting out: per scope (Zig, Odin, Jai); per function (D `@system`); per check for a
  whole file (Cpp2); global (Swift `-Ounchecked`, D `-boundscheck=off`, Go `-B`).
- Zero initialization removes uninitialized-read UB (Odin, Jai, D, Go).
- Use after free stays undefined in all but Goose, safe Rust, safe Swift and the four GC
  languages. Rust's "safe code has no UB; UB only inside `unsafe`" is the clearest
  boundary; Java, Kotlin and Scala keep UB only in foreign-memory code.
- Debug tools as build options: Go's race detector (`-race`), sanitizers in C and C++.
- Agree: bounds checks on by default (fifteen of seventeen; not C++ raw arrays, Terra);
  defined wrap (nine); trap in checked builds (Zig, C3, Jai, Goose, Carbon, Swift, Rust,
  D, Cpp2); explicit wrap operators (Zig, Swift, Rust).

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
| C | required | `//`, non-nesting `/* */` | none (concatenation) | `0x 0b`, `1'000` (C23), leading `0` octal | about 59 |

- Semicolons: required in eleven of seventeen; optional or inserted: Odin, Swift, Terra,
  Go, Kotlin, Scala. Go's automatic insertion forces the `{` onto the same line.
- Block comments: nesting (C3, Odin, Jai, Goose, Swift, Rust, D `/+ +/`, Kotlin, Scala:
  nine); non-nesting `/* */` (C, C++, Cpp2, Java, Go); `//` only (Zig, Hare, Carbon);
  Lua's `--` (Terra).
- Raw strings: backticks (C3, Odin, Hare, D, Go: five); `"""` (Swift, Goose, Kotlin,
  Scala; Java text blocks, not raw); `#"…"#` (Carbon, Swift; Rust `r#"…"#`); `R"(…)"`
  (C++, Cpp2); long brackets (Terra). Interpolation: Kotlin `"$x"`, Scala `s"$x"`,
  Swift `"\(x)"`, Cpp2 `"(x)$"`.
- Digit separators: `_` (Zig, C3, Odin, Jai, Carbon, Swift, Rust, D, Java, Go, Kotlin,
  Scala: twelve) vs `'` (C23, C++, Cpp2). `0o` octal (Zig, C3, Odin, Hare, Swift, Rust,
  Go, C2y); no octal at all (Kotlin, Scala); leading `0` still octal (C, C++, Java), an
  error in D.
- Keyword counts: small (Goose about 25, Go 25, Kotlin about 28 hard, Terra about 31,
  Rust 38, Scala about 41, Zig about 43); large (Java about 51, Hare, Carbon, Swift about
  70; C++ about 92; D about 100). Soft or contextual keywords (Kotlin, Scala, Swift,
  Java, Cpp2) keep the reserved set small but make parsing context-sensitive.
- Lexer clashes: Rust's lifetime `'a` and C++'s `'` separator vs character literals;
  Cpp2's postfix `p*` vs multiply. Terra's `--` comments and `~=` break C familiarity.
- Agree: required `;` (eleven); `_` separators (twelve); nesting block comments (nine);
  `0o` octal (seven and C2y); backtick raw strings (five); `"""` strings (five).

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
